#ifdef __cplusplus
extern "C" {
#endif

#include "04-lite.h"
#include "object_info.h"

static byte didNotInit = TRUE;
static GameGlobals *globals;

/* These sprites save no background and never move: once drawn they stay until
 * something paints over them, so they only need painting into each of the two
 * buffers and then not again until what they show changes. */
#define BUFFERS 2

#ifdef __APPLE__
void LiteClassInit() {
    didNotInit = TRUE;
}
#endif

void LiteInit(DynospriteCOB *cob, DynospriteODT *odt, byte *initData) {
    LiteObjectState *s = (LiteObjectState *)(cob->statePtr);
    const unsigned char *box;

    if (didNotInit) {
        didNotInit = FALSE;
        globals = gameGlobals();
    }

    s->kind = initData[0];
    s->index = initData[1];
    s->timer = 0;
    s->redraw = BUFFERS;

    if (s->kind == LITE_KIND_DIAMOND) {
        box = tblDiamondBox + ((unsigned)s->index << 2);
        cob->globalX = box[0] + DIAMOND_MID_OFF;
        cob->globalY = box[1] + DIAMOND_MID_OFF;
        s->spriteIdx = LITE_SPRITE_DIAMOND_COOL;
    } else if (s->kind == LITE_KIND_PLUNGER) {
        box = tblPlungerBox + ((unsigned)s->index << 2);
        cob->globalX = box[0];
        cob->globalY = box[1];
        s->spriteIdx = LITE_SPRITE_PLUNGER_OFF;
    } else {
        box = tblFootBox + ((unsigned)s->index << 2);
        cob->globalX = box[0];
        cob->globalY = box[1];
        /* The two beside the head stand on end; the other seven lie flat. */
        s->spriteIdx = (box[2] - box[0] < box[3] - box[1])
                           ? LITE_SPRITE_TALL_LIVE
                           : LITE_SPRITE_WIDE_LIVE;
    }
    cob->active = OBJECT_ACTIVE;
}

byte LiteReactivate(DynospriteCOB *cob, DynospriteODT *odt) {
    return 0;
}

byte LiteUpdate(DynospriteCOB *cob, DynospriteODT *odt) {
    LiteObjectState *s = (LiteObjectState *)(cob->statePtr);
    byte idx;

    if (s->kind == LITE_KIND_DIAMOND) {
        byte bit = (byte)(1 << s->index);
        if (globals->diamondHit & bit) {
            globals->diamondHit &= (byte)~bit;
            s->timer = DIAMOND_FLASH;
        }
        if (s->timer) {
            s->timer--;
        }
        idx = s->timer ? LITE_SPRITE_DIAMOND_HOT : LITE_SPRITE_DIAMOND_COOL;
    } else if (s->kind == LITE_KIND_PLUNGER) {
        idx = (globals->plunger & (byte)(1 << s->index))
                  ? LITE_SPRITE_PLUNGER_ON
                  : LITE_SPRITE_PLUNGER_OFF;
    } else {
        byte spent = globals->feetHit[s->index >> 3] &
                     (byte)(1 << (s->index & 7));
        byte tall = (s->spriteIdx == LITE_SPRITE_TALL_LIVE ||
                     s->spriteIdx == LITE_SPRITE_TALL_SPENT);
        if (tall) {
            idx = spent ? LITE_SPRITE_TALL_SPENT : LITE_SPRITE_TALL_LIVE;
        } else {
            idx = spent ? LITE_SPRITE_WIDE_SPENT : LITE_SPRITE_WIDE_LIVE;
        }
    }

    if (s->spriteIdx != idx) {
        s->spriteIdx = idx;
        s->redraw = BUFFERS;
    }
    if (s->redraw) {
        s->redraw--;
        cob->active = OBJECT_ACTIVE;
    } else {
        cob->active = OBJECT_UPDATE_ACTIVE;
    }
    return 0;
}

RegisterObject(LiteClassInit, LiteInit, 2, LiteReactivate, LiteUpdate, NULL,
               sizeof(LiteObjectState));

#ifdef __cplusplus
}
#endif
