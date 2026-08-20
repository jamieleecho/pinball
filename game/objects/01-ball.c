#ifdef __cplusplus
extern "C" {
#endif

/* The ball owns the table's physics, its scoring rules, and the run of play.
 * Everything else on the playfield is either scenery baked into the tilemap or
 * an overlay that reads the state this file maintains. */

#define TBL_WANT_GRID

#include "01-ball.h"
#include "02-flipper.h"
#include "object_info.h"

/* Velocities are 8.8 fixed point: 256 == one pixel per frame.  The game ticks
 * at 30Hz, so MAX_SPEED of 2000 is a little under 8 pixels per tick. */
#define GRAVITY 14
#define MAX_SPEED 2000
#define DRAG_MASK 15 /* shed a little speed every 16th frame */
#define MAX_SUBSTEPS 8

/* Bounce gain is (1 + restitution) * 16. */
#define GAIN_WALL 27
#define GAIN_SCENERY 24
#define GAIN_FLIPPER 20

#define BUMPER_KICK 1000
#define BUMPER_SKEW 160
#define SLING_KICK 600
#define FLIPPER_KICK 72

#define TARGET_COOLDOWN 8
/* The clank is only a sound, so it has its own shorter guard.  Sharing the
 * scoring cooldown made every wall bounce swallow the bumper hit after it. */
#define CLANK_COOLDOWN 6
#define STUCK_FRAMES 60
#define STUCK_SPEED 120

#define DRAIN_PAUSE 60

/* Probe ring: eight points around the ball's rim.  Four would let a corner
 * slip between them at speed. */
static const signed char probeDX[8] = {3, 2, 0, -2, -3, -2, 0, 2};
static const signed char probeDY[8] = {0, 2, 3, 2, 0, -2, -3, -2};

static byte didNotInit = TRUE;
static GameGlobals *globals;

/* ------------------------------------------------------------------ */

/**
 * Advances the ball by (dx, dy) in 8.8 fixed point, carrying the sub-pixel
 * remainder.  Whole pixels go into the object, where the engine needs them
 * anyway; a single 8.8 position would not fit in a signed 16-bit int over a
 * 208-pixel-tall table.
 */
static void addPos(DynospriteCOB *cob, BallObjectState *s, int dx, int dy) {
    unsigned f;

    f = (unsigned)s->fx + (unsigned)(dx & 0xff);
    cob->globalX += (dx >> 8) + (f >> 8);
    s->fx = (byte)f;

    f = (unsigned)s->fy + (unsigned)(dy & 0xff);
    cob->globalY += (dy >> 8) + (f >> 8);
    s->fy = (byte)f;
}

static byte probeCell(int x, int y) {
    /* The grid covers the table only, not the whole world, so a world position
     * has to be brought back to the grid's origin before it can be indexed.
     * Getting this wrong does not fail loudly: the ball simply reads cells
     * belonging to somewhere else and walks out through the wall. */
    x -= TBL_ORIGIN_X;
    y -= TBL_ORIGIN_Y;
    if (x < 0) {
        x = 0;
    } else if (x >= TBL_GRID_W * TBL_CELL) {
        x = TBL_GRID_W * TBL_CELL - 1;
    }
    if (y < 0) {
        y = 0;
    } else if (y >= TBL_GRID_H * TBL_CELL) {
        return 0; /* below the table: the ball is on its way out */
    }
    return tblGrid[((y >> TBL_CELL_SHIFT) * TBL_GRID_W) + (x >> TBL_CELL_SHIFT)];
}

/**
 * Velocity projected onto a normal that has been scaled by 32.
 *
 * The velocity is shifted down before the multiply so the product still fits a
 * signed 16-bit register at full speed; the cost is quantising the projection
 * to a sixty-fourth of a pixel per tick, which is far below anything visible.
 */
static int dotNormal(int vx, int vy, signed char nx, signed char ny) {
    return (((vx >> 2) * nx) >> 3) + (((vy >> 2) * ny) >> 3);
}

/**
 * Bounces the velocity off a surface whose outward normal is (nx, ny), scaled
 * by 32.  gain is (1 + restitution) * 16.
 *
 * The shifts keep every intermediate inside a signed 16-bit register, which is
 * why this looks more roundabout than the textbook v -= 2(v.n)n.
 */
static void reflect(BallObjectState *s, signed char nx, signed char ny, byte gain) {
    int dot = dotNormal(s->vx, s->vy, nx, ny);
    int j;
    if (dot >= 0) {
        return; /* already moving away from the surface */
    }
    j = ((dot >> 2) * gain) >> 2;
    s->vx -= ((j >> 3) * nx) >> 2;
    s->vy -= ((j >> 3) * ny) >> 2;
}

/**
 * Nudges the ball along the surface it just hit by a small random amount.
 *
 * Without this, a perfectly symmetrical situation stays symmetrical: a ball
 * dropped straight down a gap onto a bumper is fired straight back up and
 * repeats for ever.  Real tables have a nudge button; this one has arithmetic.
 */
static void jitter(BallObjectState *s, signed char nx, signed char ny) {
    int amt;
    s->rnd = s->rnd * 5 + 13;
    amt = (int)(s->rnd & 31) - 16;
    /* The tangent of (nx, ny) is (-ny, nx). */
    s->vx += ((int)(-ny) * amt) >> 3;
    s->vy += ((int)nx * amt) >> 3;
}

static void clampSpeed(BallObjectState *s) {
    if (s->vx > MAX_SPEED) {
        s->vx = MAX_SPEED;
    } else if (s->vx < -MAX_SPEED) {
        s->vx = -MAX_SPEED;
    }
    if (s->vy > MAX_SPEED) {
        s->vy = MAX_SPEED;
    } else if (s->vy < -MAX_SPEED) {
        s->vy = -MAX_SPEED;
    }
}

/** Index of the box in the table that contains (x, y), or -1. */
static int findBox(const unsigned char *boxes, byte count, int x, int y) {
    byte i;
    for (i = 0; i < count; i++) {
        const unsigned char *b = boxes + (i << 2);
        if (x >= (int)b[0] - BALL_R && x <= (int)b[2] + BALL_R &&
            y >= (int)b[1] - BALL_R && y <= (int)b[3] + BALL_R) {
            return i;
        }
    }
    return -1;
}

/** Every foot has been hit, so they all reset and the multiplier steps up. */
static void stepMultiplier(void) {
    globals->feetHit[0] = 0;
    globals->feetHit[1] = 0;
    if (globals->multiplier == 1) {
        globals->multiplier = 2;
    } else if (globals->multiplier == 2) {
        globals->multiplier = 3;
    }
}

/** Nine feet need nine bits, which is one more than a byte will hold. */
static byte footSpent(byte idx) {
    return globals->feetHit[idx >> 3] & (byte)(1 << (idx & 7));
}

static void spendFoot(byte idx) {
    globals->feetHit[idx >> 3] |= (byte)(1 << (idx & 7));
    scoreTens(3);
    /* Each foot has its own note, so working round them plays a phrase. */
    PlaySound(SOUND_NOTE + (idx % NUM_NOTES));

    /* Only the feet under the top pods feed Vally's tongue, as the manual has
     * it.  Twelve of them and she catches the fly: the volcano erupts, lava
     * runs down it, and the rest of the ball is worth ten times as much.
     * Tongue length carries across the whole game, not just this ball. */
    if (idx < NUM_TOP_FEET && globals->tongue < TONGUE_TARGET) {
        globals->tongue++;
        if (globals->tongue == TONGUE_TARGET && !globals->volcano) {
            globals->volcano = 1;
            globals->multiplier = 10;
            PlaySound(SOUND_DRAIN);
        }
    }
    /* All nine: they come back and scoring steps up, which is what the manual
     * described for the plungers on the original table. */
    if (globals->feetHit[0] == 0xff && globals->feetHit[1] == 0x01) {
        stepMultiplier();
    }
}

/**
 * Applies whatever the ball just ran into: the bounce, the points, the kick.
 */
static void resolveHit(BallObjectState *s, byte cell, int hx, int hy,
                       signed char nx, signed char ny) {
    byte kind = TBL_KIND(cell);
    byte kick = 0;

    if (kind == K_BUMPER) {
        kick = 1;
        if (!s->cooldown) {
            /* The three big bumpers flash their middles and each has its own
             * note; the strips and the little wall diamonds score the same but
             * take the note below them. */
            int d = findBox(tblDiamondBox, NUM_DIAMONDS, hx, hy);
            scoreTens(1);
            if (d >= 0) {
                globals->diamondHit |= (byte)(1 << d);
                PlaySound(SOUND_NOTE + (byte)d);
            } else {
                PlaySound(SOUND_NOTE + NUM_NOTES - 1);
            }
            s->cooldown = TARGET_COOLDOWN;
        }
    } else if (kind == K_FOOT) {
        /* A foot is a bumper until it is hit.  After that it turns cyan and is
         * ordinary scenery -- still solid, because it is part of the pod or the
         * crest it hangs off, but it neither kicks nor scores until the ball
         * drains and all nine come back. */
        int idx = findBox(tblFootBox, NUM_FEET, hx, hy);
        if (idx >= 0 && !footSpent((byte)idx)) {
            kick = 1;
            if (!s->cooldown) {
                spendFoot((byte)idx);
                s->cooldown = TARGET_COOLDOWN;
            }
        } else if (!s->clank) {
            /* Spent: it is scenery now, and sounds like it. */
            PlaySound(SOUND_CLANK);
            s->clank = CLANK_COOLDOWN;
        }
    }

    if (kick) {
        /* A bumper does not so much bounce the ball as throw it.  The kick is
         * deliberately thrown off-axis, alternating side each time: a ball
         * that lands squarely on top of a bumper under a vertical gap would
         * otherwise be fired straight up and come straight back down for
         * ever. */
        s->vx = (int)nx * (BUMPER_KICK >> 5) + (s->nudge ? BUMPER_SKEW : -BUMPER_SKEW);
        s->vy = (int)ny * (BUMPER_KICK >> 5);
        s->nudge ^= 1;
        jitter(s, nx, ny);
        return;
    }

    /* Anything else the ball meets -- wall, scenery -- just clanks.  The
     * guard keeps a ball running along a wall from rattling. */
    if (!s->clank) {
        PlaySound(SOUND_CLANK);
        s->clank = CLANK_COOLDOWN;
    }
    reflect(s, nx, ny, kind == K_SCENERY ? GAIN_SCENERY : GAIN_WALL);
    jitter(s, nx, ny);
}

/**
 * Moves the ball one sub-step and deals with whatever it touches.  Returns
 * non-zero if it hit something, in which case the step has been rolled back.
 */
static byte stepBall(DynospriteCOB *cob, BallObjectState *s, int dx, int dy) {
    unsigned oldX = cob->globalX;
    unsigned oldY = cob->globalY;
    byte oldFx = s->fx;
    byte oldFy = s->fy;
    int ix, iy;
    byte i;
    byte bestCell = 0;
    int bestDot = 32767;
    signed char bnx = 0;
    signed char bny = 0;
    int bestX = 0;
    int bestY = 0;

    addPos(cob, s, dx, dy);
    ix = (int)cob->globalX;
    iy = (int)cob->globalY;

    for (i = 0; i < 8; i++) {
        int qx = ix + probeDX[i];
        int qy = iy + probeDY[i];
        byte cell = probeCell(qx, qy);
        if (cell) {
            byte d = TBL_DIR(cell);
            signed char cnx = tblDirX[d];
            signed char cny = tblDirY[d];
            /* Of everything we are touching, the surface we are running into
             * hardest is the one that decides the bounce. */
            int dot = dotNormal(s->vx, s->vy, cnx, cny);
            if (dot < bestDot) {
                bestDot = dot;
                bestCell = cell;
                bnx = cnx;
                bny = cny;
                bestX = qx;
                bestY = qy;
            }
        }
    }

    if (!bestCell) {
        /* The stopper.  The table and the launch lane are joined by one gap,
         * in the divider's columns above where the divider itself begins; a
         * shot on its way up goes through it, and once the ball is in play the
         * bar fills it so it cannot come back.  The bar is not in the grid --
         * it comes and goes -- so the ball meets it here. */
        if (globals->gate && ix >= GATE_X0 - BALL_R && ix <= GATE_X1 + BALL_R &&
            iy >= GATE_Y0 - BALL_R && iy <= GATE_Y1 + BALL_R) {
            cob->globalX = oldX;
            cob->globalY = oldY;
            s->fx = oldFx;
            s->fy = oldFy;
            /* It is tall and narrow, so the ball is nearly always arriving
             * side-on; push it back the way it came. */
            reflect(s, ix < GATE_X0 ? -32 : 32, 0, GAIN_WALL);
            return 1;
        }
        return 0;
    }

    cob->globalX = oldX;
    cob->globalY = oldY;
    s->fx = oldFx;
    s->fy = oldFy;
    resolveHit(s, bestCell, bestX, bestY, bnx, bny);
    /* Ease off the surface so the next frame does not start inside it. */
    addPos(cob, s, (int)bnx << 3, (int)bny << 3);
    return 1;
}

/** Ball against both flippers. */
static void collideFlippers(DynospriteCOB *cob, BallObjectState *s) {
    DynospriteCOB *obj = DynospriteDirectPageGlobalsPtr->Obj_CurrentTablePtr;
    DynospriteCOB *endObj = obj + DynospriteDirectPageGlobalsPtr->Obj_NumCurrent;

    for (; obj < endObj; obj++) {
        FlipperObjectState *f;
        int rx, ry, along, perp, limit, push;
        byte slot;
        signed char dirX, dirY, nrmX, nrmY, nx, ny;

        if (obj->groupIdx != FLIPPER_GROUP_IDX) {
            continue;
        }
        f = (FlipperObjectState *)(obj->statePtr);
        slot = (f->side == FLIPPER_RIGHT ? FLIPPER_FRAMES : 0) + f->frame;
        dirX = tblFlipDirX[slot];
        dirY = tblFlipDirY[slot];
        nrmX = tblFlipNrmX[slot];
        nrmY = tblFlipNrmY[slot];

        rx = (int)cob->globalX - (int)obj->globalX;
        ry = (int)cob->globalY - (int)obj->globalY;

        along = (((rx * dirX) >> 5) + ((ry * dirY) >> 5));
        if (along < 0 || along > FLIPPER_LEN) {
            continue;
        }
        perp = ((rx * nrmX) >> 5) + ((ry * nrmY) >> 5);
        limit = BALL_R + FLIPPER_HALF_THICK;
        if (perp >= limit || perp <= -limit) {
            continue;
        }

        if (perp >= 0) {
            nx = nrmX;
            ny = nrmY;
            push = limit - perp;
        } else {
            nx = -nrmX;
            ny = -nrmY;
            push = limit + perp;
        }

        /* Lift the ball clear of the bat, then bounce it. */
        addPos(cob, s, ((int)nx * push) << 3, ((int)ny * push) << 3);
        reflect(s, nx, ny, GAIN_FLIPPER);

        /* A rising flipper adds the speed of the bat at the point of contact,
         * so the tip throws the ball much harder than the hub does. */
        if (f->rising && perp >= 0) {
            int kick = along * FLIPPER_KICK;
            s->vx += ((int)nx * (kick >> 2)) >> 3;
            s->vy += ((int)ny * (kick >> 2)) >> 3;
            PlaySound(SOUND_FLIPPER);
        }
        clampSpeed(s);
    }
}

/* ------------------------------------------------------------------ */

static void placeOnLauncher(DynospriteCOB *cob, BallObjectState *s, byte pull) {
    cob->globalX = LANE_CX;
    cob->globalY = LAUNCHER_REST_Y - 6 + pull;
    s->fx = 0;
    s->fy = 0;
    s->vx = 0;
    s->vy = 0;
}

static void startBall(DynospriteCOB *cob, BallObjectState *s) {
    globals->gameState = GameStateReady;
    globals->multiplier = 1;
    /* The nine feet come back with every new ball, and the lane opens up. */
    globals->feetHit[0] = 0;
    globals->feetHit[1] = 0;
    globals->gate = 0;
    globals->volcano = 0;
    s->pull = 0;
    s->cooldown = 0;
    s->clank = 0;
    s->stillFor = 0;
    placeOnLauncher(cob, s, 0);
}

static void startGame(DynospriteCOB *cob, BallObjectState *s) {
    byte i;
    globals->ballsLeft = BALLS_PER_GAME;
    for (i = 0; i < 4; i++) {
        globals->score[i] = 0;
    }
    globals->extraBalls = 0;
    globals->tongue = 0;
    startBall(cob, s);
}

static void recordHighScore(void) {
    byte i;
    for (i = 0; i < 4; i++) {
        if (globals->score[i] > globals->highScore[i]) {
            break;
        }
        if (globals->score[i] < globals->highScore[i]) {
            return;
        }
    }
    for (i = 0; i < 4; i++) {
        globals->highScore[i] = globals->score[i];
    }
}

/* ------------------------------------------------------------------ */

#ifdef __APPLE__
void BallClassInit() {
    didNotInit = TRUE;
}
#endif

void BallInit(DynospriteCOB *cob, DynospriteODT *odt, byte *initData) {
    BallObjectState *s = (BallObjectState *)(cob->statePtr);

    if (didNotInit) {
        didNotInit = FALSE;
        globals = gameGlobals();
    }

    s->role = initData[0];
    s->spriteIdx =
        (s->role == BALL_ROLE_LAUNCHER) ? BALL_SPRITE_LAUNCHER : BALL_SPRITE_BALL;
    s->vx = 0;
    s->vy = 0;
    s->fx = 0;
    s->fy = 0;
    s->pull = 0;
    s->cooldown = 0;
    s->clank = 0;
    s->lastEnter = 0;
    s->stillFor = 0;
    s->nudge = 0;
    s->rnd = 0x5a;

    if (s->role == BALL_ROLE_LAUNCHER) {
        cob->globalX = LANE_CX;
        cob->globalY = LAUNCHER_REST_Y;
    } else {
        globals->initialized = TRUE;
        if (globals->magic0 != 0x5a || globals->magic1 != 0x3c) {
            /* Cold start: there is no high score to keep. */
            globals->magic0 = 0x5a;
            globals->magic1 = 0x3c;
            globals->highScore[0] = 0;
            globals->highScore[1] = 0;
            globals->highScore[2] = 0;
            globals->highScore[3] = 0;
        }
        startGame(cob, s);
    }
}

byte BallReactivate(DynospriteCOB *cob, DynospriteODT *odt) {
    return 0;
}

/**
 * The ball, wherever it is in the object table.
 *
 * It shares its group with the launcher head, so a search on the group alone
 * finds whichever of the two comes first -- which used to be the ball only
 * because the ball was listed first.  It is listed last now, so that it draws
 * over everything, and this asks for the role instead.
 */
static DynospriteCOB *findBall(void) {
    DynospriteCOB *o = DynospriteDirectPageGlobalsPtr->Obj_CurrentTablePtr;
    DynospriteCOB *end = o + DynospriteDirectPageGlobalsPtr->Obj_NumCurrent;
    for (; o < end; ++o) {
        if (o->groupIdx == BALL_GROUP_IDX &&
            ((BallObjectState *)(o->statePtr))->role == BALL_ROLE_BALL) {
            return o;
        }
    }
    return 0;
}

byte BallUpdate(DynospriteCOB *cob, DynospriteODT *odt) {
    BallObjectState *s = (BallObjectState *)(cob->statePtr);
    byte state = globals->gameState;

    if (s->role == BALL_ROLE_LAUNCHER) {
        /* The launcher head mirrors however far the ball is drawn back, and
         * disappears once the ball is away. */
        DynospriteCOB *ballCob = findBall();
        byte pull = 0;
        if (ballCob) {
            pull = ((BallObjectState *)(ballCob->statePtr))->pull;
        }
        cob->globalY = LAUNCHER_REST_Y + pull;
        cob->active = (state == GameStateReady) ? OBJECT_ACTIVE : OBJECT_UPDATE_ACTIVE;
        return 0;
    }

    globals->flashTimer++;

    /* BREAK abandons the game and goes back to the title screen, as it did on
     * the MC-10.  A negative return sends DynoSprite to its menu. */
    if (keyDown(PB_KEY_BREAK)) {
        recordHighScore();
        return 0xff;
    }

    if (s->cooldown) {
        s->cooldown--;
    }
    if (s->clank) {
        s->clank--;
    }

    switch (state) {
    case GameStateReady: {
        byte enter = keyDown(PB_KEY_ENTER);
        if (enter) {
            s->pull++;
            if (s->pull > LAUNCHER_MAX_PULL) {
                s->pull = 0; /* held too long: the launcher springs back */
            }
        } else if (s->lastEnter && s->pull) {
            s->vy = -(LAUNCH_SPEED_MIN + (int)s->pull * LAUNCH_STEP);
            if (s->vy < -LAUNCH_SPEED_MAX) {
                s->vy = -LAUNCH_SPEED_MAX;
            }
            s->vx = 0;
            s->pull = 0;
            globals->gameState = GameStatePlaying;
            PlaySound(SOUND_LAUNCH);
            cob->active = OBJECT_ACTIVE;
            break;
        }
        s->lastEnter = enter;
        placeOnLauncher(cob, s, s->pull);
        cob->active = OBJECT_ACTIVE;
        break;
    }

    case GameStatePlaying: {
        int ax, ay, amax, dx, dy;
        byte steps, i;

        s->vy += GRAVITY;
        if ((globals->flashTimer & DRAG_MASK) == 0) {
            s->vx -= s->vx >> 6;
            s->vy -= s->vy >> 6;
        }
        clampSpeed(s);

        ax = s->vx < 0 ? -s->vx : s->vx;
        ay = s->vy < 0 ? -s->vy : s->vy;
        amax = ax > ay ? ax : ay;
        steps = (byte)(amax >> 8) + 1;
        if (steps > MAX_SUBSTEPS) {
            steps = MAX_SUBSTEPS;
        }
        dx = s->vx / (int)steps;
        dy = s->vy / (int)steps;
        for (i = 0; i < steps; i++) {
            if (stepBall(cob, s, dx, dy)) {
                break;
            }
        }

        collideFlippers(cob, s);
        clampSpeed(s);

        /* A ball that has wedged itself, or that is trapped bouncing straight
         * up and down between two walls, gets a shove.  This table -- like the
         * original -- has no nudge button to do it with. */
        if (ax < STUCK_SPEED) {
            s->stillFor++;
            if (s->stillFor > STUCK_FRAMES) {
                s->stillFor = 0;
                s->nudge ^= 1;
                s->vx += s->nudge ? 200 : -200;
                s->vy -= 120;
            }
        } else {
            s->stillFor = 0;
        }

        /* Once the shot is clear of the gap, the stopper fills it in behind.
         * "Clear" has to mean clear of the bar itself, not merely out of the
         * lane: dropping it as soon as the ball left the lane put the bar down
         * on top of a ball still passing through, and it was pinned there for
         * the rest of the game. */
        if (!globals->gate && (int)cob->globalX < GATE_X0 - BALL_R) {
            globals->gate = 1;
        }

        /* Climbing the lane, the ball ticks: every frame off the launcher,
         * stretching to a quarter of a second by the top, and silent once it
         * is over.  Thirty a second is the ceiling -- the game samples and
         * sounds on its own 30Hz tick, so one blip a frame is as fast as it
         * goes.
         *
         * The interval comes from how far up the lane the ball is, not from
         * how fast it is going.  Speed is the obvious choice and it does not
         * work: this lane is short enough that the ball barely slows on the
         * way up -- measured, it leaves at seven pixels a frame and arrives at
         * six -- so a speed-derived interval hardly varies at all.  Height
         * covers the whole run. */
        if ((int)cob->globalX >= LANE_X0 - BALL_R && s->vy < 0) {
            if (s->laneTick) {
                s->laneTick--;
            } else {
                byte up = (byte)((LAUNCHER_REST_Y - (int)cob->globalY) >> 4);
                PlaySound(SOUND_LANE);
                s->laneTick = (up > 7) ? 7 : up;
            }
        } else {
            s->laneTick = 0;
        }

        if (s->vy > 0 && (int)cob->globalX >= LANE_X0 &&
            (int)cob->globalY > LAUNCHER_REST_Y - 8) {
            /* A shot too weak to round the top slides back down the lane.
             * The shooter lane is not a drain, so a dud costs nothing but
             * another go at the launcher. */
            startBall(cob, s);
        } else if ((int)cob->globalY > DRAIN_Y) {
            globals->gameState = GameStateDrained;
            globals->stateTimer = DRAIN_PAUSE;
            PlaySound(SOUND_DRAIN);
        }
        cob->active = OBJECT_ACTIVE;
        break;
    }

    case GameStateDrained:
        cob->active = OBJECT_UPDATE_ACTIVE;
        if (globals->stateTimer) {
            globals->stateTimer--;
        } else {
            globals->ballsLeft--;
            if (globals->ballsLeft) {
                startBall(cob, s);
            } else {
                recordHighScore();
                globals->gameState = GameStateOver;
            }
        }
        break;

    case GameStateOver:
        cob->active = OBJECT_UPDATE_ACTIVE;
        if (keyDown(PB_KEY_SPACE)) {
            startGame(cob, s);
        }
        break;

    default:
        globals->gameState = GameStateReady;
        break;
    }

    return 0;
}

RegisterObject(BallClassInit, BallInit, 1, BallReactivate, BallUpdate, NULL,
               sizeof(BallObjectState));

#ifdef __cplusplus
}
#endif
