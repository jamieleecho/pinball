#ifndef _object_info_h
#define _object_info_h

#include "coco.h"
#include "dynosprite.h"
#include "table_data.h"

#define SCREEN_WIDTH 320
#define SCREEN_HEIGHT 200

#define LEVEL_TABLE 1

/* Sprite/object groups */
#define BALL_GROUP_IDX 1
#define FLIPPER_GROUP_IDX 2
#define DIGIT_GROUP_IDX 3
#define LITE_GROUP_IDX 4

/* Sounds, numbered to match game/sounds/XX-*.wav */
#define SOUND_BUMPER 1
#define SOUND_TARGET 2
#define SOUND_FLIPPER 3
#define SOUND_DRAIN 4
#define SOUND_LAUNCH 5
#define SOUND_LANE 6
/* Six notes of a pentatonic scale, 7..12.  A scoring target picks one by its
 * index, so the table has a voice rather than a thump. */
#define SOUND_NOTE 7
#define NUM_NOTES 6
/* The clank is the flipper's own clack, reused for anything that is struck but
 * does not score: a wall, a piece of scenery, a foot already spent. */
#define SOUND_CLANK SOUND_FLIPPER

/* Ball sprites */
#define BALL_SPRITE_BALL 0
#define BALL_SPRITE_LAUNCHER 1

/* Digit sprites.  The blank is drawn in place of a hidden read-out: these
 * sprites carry no erase code, so an object that simply stopped drawing would
 * leave its last digit on screen for good. */
#define DIGIT_SPRITE_BLANK 10
#define DIGIT_SPRITE_BALL 11
#define DIGIT_SPRITE_BALL_BLANK 12

/* Table overlays, in the order draw_lite_sheet() lays them out */
#define LITE_SPRITE_DIAMOND_HOT 0
#define LITE_SPRITE_DIAMOND_COOL 1
#define LITE_SPRITE_TALL_LIVE 2
#define LITE_SPRITE_TALL_SPENT 3
#define LITE_SPRITE_WIDE_LIVE 4
#define LITE_SPRITE_WIDE_SPENT 5

/* Which sort of overlay an instance is, passed as its first init byte */
#define LITE_KIND_FOOT 0
#define LITE_KIND_DIAMOND 1

/* Ticks a struck bumper's middle stays magenta -- about half a second */
#define DIAMOND_FLASH 20

/* Panel sprites, in the order they appear in 05-panel.json */
#define PANEL_SPRITE_TONGUE1 0
#define PANEL_SPRITE_GAMEOVER 6
#define PANEL_SPRITE_MULTX 7
#define PANEL_SPRITE_GATE_SHUT 8
#define PANEL_SPRITE_GATE_OPEN 9

/* Lava sprites, in the order draw_lava_sheet() lays them out */
#define LAVA_SPRITE_HOT 0
#define LAVA_SPRITE_COOL 1
#define PANEL_TONGUE_STAGES 6

/* Where the panel read-outs sit.  The multiplier and ball count are drawn with
 * score digits, so they use the digit grid.  Everything on the panel is placed
 * by table_data.h, from the same constants that drew the artwork beneath it --
 * PANEL_TONGUE_X/Y, for instance, is exactly where the generator put Vally's
 * mouth.  Only the end-of-game plate is positioned here, because it is drawn
 * across the table rather than on the panel. */
#define PANEL_OVER_X 54
#define PANEL_OVER_Y 96
#define PANEL_MULTX_X (MULT_DIGIT_X + 2 * SCORE_DIGIT_PITCH)
#define PANEL_MULTX_Y (MULT_DIGIT_Y + 2)

/* Rules from the manual */
#define BALLS_PER_GAME 3
#define TONGUE_TARGET 12 /* top-mark hits needed to make the volcano erupt */
#define FLASH_FRAMES 10  /* how long a struck target stays lit */

/* Launcher */
#define LANE_CX ((LANE_X0 + LANE_X1) / 2)
#define LAUNCHER_REST_Y 180
#define LAUNCHER_MAX_PULL 18
#define LAUNCH_SPEED_MIN 1300 /* 8.8 fixed point pixels per frame */
#define LAUNCH_STEP 115        /* added per notch of pull */
#define LAUNCH_SPEED_MAX 3400

enum GameState {
    /* Title screen is up; SPACE starts a game. */
    GameStateAttract = 0,
    /* Ball sits on the launcher waiting for ENTER. */
    GameStateReady = 1,
    /* Ball is live on the table. */
    GameStatePlaying = 2,
    /* Ball just drained; short pause before the next one. */
    GameStateDrained = 3,
    /* Out of balls; the high score board flashes. */
    GameStateOver = 4
};

/** Global game data.  Lives in DynoSprite's 32-byte UserGlobals block. */
typedef struct GameGlobals {
    /* The engine zeroes the first byte of UserGlobals every time a level is
     * launched from the menu, which is exactly the "new game" signal we want.
     * The high score has to outlive that, so it is guarded by a magic number
     * that only a cold start will fail to match. */
    byte initialized;
    byte magic0;
    byte magic1;
    byte gameState;
    byte ballsLeft;
    byte score[4];     /* 8 BCD digits, score[0] most significant */
    byte highScore[4]; /* ditto */
    byte multiplier;   /* 1, 2, 3 or 10 */
    byte feetHit[2];   /* bit per foot; nine of them, so nine bits */
    byte tongue;       /* top-mark hits so far this game */
    byte diamondHit;   /* bit per bumper the ball has just struck */
    byte gate;         /* the lane gate is shut once the shot is in play */
    byte volcano;      /* non-zero once the volcano has erupted this ball */
    byte extraBalls;   /* 10,000-point thresholds already awarded */
    byte stateTimer;   /* counts down state transitions */
    byte flashTimer;   /* free-running counter for flashing displays */
} GameGlobals;

MAYBE_UNUSED
static GameGlobals *gameGlobals(void) {
    return (GameGlobals *)DynospriteGlobalsPtr;
}

/**
 * Starting from obj, finds an object with the given group index.
 */
MAYBE_UNUSED
static DynospriteCOB *findObjectByGroup(DynospriteCOB *obj, byte groupIdx) {
    DynospriteCOB *endObj = DynospriteDirectPageGlobalsPtr->Obj_CurrentTablePtr +
                            DynospriteDirectPageGlobalsPtr->Obj_NumCurrent;
    for (; obj < endObj; ++obj) {
        if (obj->groupIdx == groupIdx) {
            return obj;
        }
    }
    return 0;
}

/**
 * Reads a key straight out of the scanned keyboard matrix.  The engine
 * refreshes the matrix every frame, and unlike the joystick emulation this
 * lets both flippers be held at once -- which a pinball game rather needs.
 *
 * Key codes are the KEY_* values from engine/constants.asm: the low nibble is
 * the column that was strobed, the high nibble the row bit.  A pressed key
 * pulls its row low.
 */
MAYBE_UNUSED
static byte keyDown(byte keyCode) {
    byte col = keyCode & 0x0f;
    byte mask = 1 << (keyCode >> 4);
    return (DynospriteDirectPageGlobalsPtr->Input_KeyMatrix[col] & mask) ? 0 : 1;
}

#define PB_KEY_CTRL 0x64
#define PB_KEY_SHIFT 0x67
#define PB_KEY_ENTER 0x60
#define PB_KEY_SPACE 0x37
#define PB_KEY_LEFT 0x35
#define PB_KEY_RIGHT 0x36
#define PB_KEY_Z 0x32
#define PB_KEY_SLASH 0x57
#define PB_KEY_BREAK 0x62

/** Left flipper: CONTROL, as on the MC-10, or the left arrow / Z. */
MAYBE_UNUSED
static byte leftFlipperKey(void) {
    return keyDown(PB_KEY_CTRL) || keyDown(PB_KEY_LEFT) || keyDown(PB_KEY_Z);
}

/** Right flipper: SHIFT, as on the MC-10, or the right arrow / slash. */
MAYBE_UNUSED
static byte rightFlipperKey(void) {
    return keyDown(PB_KEY_SHIFT) || keyDown(PB_KEY_RIGHT) || keyDown(PB_KEY_SLASH);
}

/**
 * Adds hi*100 + lo points, both given as packed BCD, to the running score.
 */
MAYBE_UNUSED
static void addScoreBCD(byte hi, byte lo) {
    GameGlobals *g = gameGlobals();
    byte amount[4];
    byte carry = 0;
    signed char i;

    amount[0] = 0;
    amount[1] = 0;
    amount[2] = hi;
    amount[3] = lo;

    for (i = 3; i >= 0; i--) {
        byte low = (g->score[i] & 0x0f) + (amount[i] & 0x0f) + carry;
        byte high;
        carry = 0;
        if (low > 9) {
            low -= 10;
            carry = 1;
        }
        high = (g->score[i] >> 4) + (amount[i] >> 4) + carry;
        carry = 0;
        if (high > 9) {
            high -= 10;
            carry = 1;
        }
        g->score[i] = (high << 4) | low;
    }
}

/**
 * Scores a target worth `tens` tens of points, applying the current
 * multiplier, and hands out an extra ball at every 10,000 points.
 */
MAYBE_UNUSED
static void scoreTens(byte tens) {
    GameGlobals *g = gameGlobals();
    /* Every target on this table is worth a whole number of tens, and the
     * multiplier tops out at 10, so the award is always under 1000 points and
     * always a multiple of ten.  That keeps the BCD conversion to counting. */
    byte t = tens * g->multiplier; /* at most 30 */
    byte hundreds = 0;
    byte tenThousands;

    while (t >= 10) {
        t -= 10;
        hundreds++;
    }
    addScoreBCD(hundreds, (byte)(t << 4));

    /* score[1] is the ten-thousands and hundred-thousands digits. */
    tenThousands = (g->score[1] & 0x0f) + ((g->score[1] >> 4) * 10);
    if (tenThousands > g->extraBalls) {
        g->extraBalls = tenThousands;
        if (g->ballsLeft < 9) {
            g->ballsLeft++;
        }
    }
}

#endif /* _object_info_h */
