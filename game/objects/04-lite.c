#ifdef __cplusplus
extern "C" {
#endif

#include "04-lite.h"
#include "01-ball.h"
#include "object_info.h"

static byte didNotInit = TRUE;
static GameGlobals *globals;

#ifdef __APPLE__
void LiteClassInit() {
    didNotInit = TRUE;
}
#endif

static const unsigned char *boxFor(byte kind, byte index) {
    if (kind == LITE_KIND_PLUNGER) {
        return tblPlungerBox + (index << 2);
    }
    return tblMarkBox + (index << 2);
}

void LiteInit(DynospriteCOB *cob, DynospriteODT *odt, byte *initData) {
    LiteObjectState *s = (LiteObjectState *)(cob->statePtr);

    if (didNotInit) {
        didNotInit = FALSE;
        globals = gameGlobals();
    }

    s->kind = initData[0];
    s->index = initData[1];
    s->timer = 0;

    /* Overlays are anchored by their top-left corner and every element in
     * table_spec.py starts on an even pixel column, which lets the sprite
     * compiler emit byte-aligned draw code only. */
    if (s->kind == LITE_KIND_BUMPER) {
        s->spriteIdx = LITE_SPRITE_BUMPER;
        cob->globalX = tblBumperX[s->index] - BUMPER_R;
        cob->globalY = tblBumperY[s->index] - BUMPER_R;
    } else {
        const unsigned char *b = boxFor(s->kind, s->index);
        if (s->kind == LITE_KIND_PLUNGER) {
            s->spriteIdx =
                (s->index < NUM_PODS) ? LITE_SPRITE_POD : LITE_SPRITE_CAP;
        } else {
            s->spriteIdx = LITE_SPRITE_MARK;
        }
        cob->globalX = b[0];
        cob->globalY = b[1];
    }
    cob->active = OBJECT_UPDATE_ACTIVE;
}

byte LiteReactivate(DynospriteCOB *cob, DynospriteODT *odt) {
    return 0;
}

byte LiteUpdate(DynospriteCOB *cob, DynospriteODT *odt) {
    LiteObjectState *s = (LiteObjectState *)(cob->statePtr);
    byte lit = 0;

    if (s->kind == LITE_KIND_PLUNGER) {
        /* A plunger stays green until every plunger has been hit. */
        lit = (globals->plungerHit >> s->index) & 1;
    } else {
        /* Bumpers and marks light for a moment as the ball goes past.  Each
         * overlay watches the ball itself, which is cheaper than having the
         * ball keep a record of what it last touched. */
        DynospriteCOB *ballCob = findObjectByGroup(
            DynospriteDirectPageGlobalsPtr->Obj_CurrentTablePtr, BALL_GROUP_IDX);
        if (s->timer) {
            s->timer--;
        }
        if (ballCob && globals->gameState == GameStatePlaying) {
            /* cob is the overlay's top-left, so compare against its middle. */
            int halfW = (s->kind == LITE_KIND_BUMPER) ? BUMPER_R : 4;
            int halfH = (s->kind == LITE_KIND_BUMPER) ? BUMPER_R : 2;
            int dx = (int)ballCob->globalX - ((int)cob->globalX + halfW);
            int dy = (int)ballCob->globalY - ((int)cob->globalY + halfH);
            if (dx < 0) {
                dx = -dx;
            }
            if (dy < 0) {
                dy = -dy;
            }
            if (s->kind == LITE_KIND_BUMPER) {
                if (dx + dy <= BUMPER_R + BALL_R + 1) {
                    s->timer = FLASH_FRAMES;
                }
            } else if (dx <= halfW + BALL_R && dy <= halfH + BALL_R + 1) {
                s->timer = FLASH_FRAMES;
            }
        }
        lit = s->timer ? 1 : 0;
    }

    cob->active = lit ? OBJECT_ACTIVE : OBJECT_UPDATE_ACTIVE;
    return 0;
}

RegisterObject(LiteClassInit, LiteInit, 2, LiteReactivate, LiteUpdate, NULL,
               sizeof(LiteObjectState));

#ifdef __cplusplus
}
#endif
