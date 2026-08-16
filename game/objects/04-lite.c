#ifdef __cplusplus
extern "C" {
#endif

#include "04-lite.h"
#include "object_info.h"

static byte didNotInit = TRUE;
static GameGlobals *globals;

#ifdef __APPLE__
void LiteClassInit() {
    didNotInit = TRUE;
}
#endif

void LiteInit(DynospriteCOB *cob, DynospriteODT *odt, byte *initData) {
    FootObjectState *s = (FootObjectState *)(cob->statePtr);
    const unsigned char *box;

    if (didNotInit) {
        didNotInit = FALSE;
        globals = gameGlobals();
    }

    s->index = initData[0];
    box = tblFootBox + ((unsigned)s->index << 2);
    cob->globalX = box[0];
    cob->globalY = box[1];

    /* The two beside the head stand on end; the other seven lie flat. */
    s->spriteIdx = (box[2] - box[0] < box[3] - box[1]) ? LITE_SPRITE_TALL_LIVE
                                                       : LITE_SPRITE_WIDE_LIVE;
    cob->active = OBJECT_ACTIVE;
}

byte LiteReactivate(DynospriteCOB *cob, DynospriteODT *odt) {
    return 0;
}

byte LiteUpdate(DynospriteCOB *cob, DynospriteODT *odt) {
    FootObjectState *s = (FootObjectState *)(cob->statePtr);
    byte spent = globals->feetHit[s->index >> 3] & (byte)(1 << (s->index & 7));
    byte tall = (s->spriteIdx == LITE_SPRITE_TALL_LIVE ||
                 s->spriteIdx == LITE_SPRITE_TALL_SPENT);

    if (tall) {
        s->spriteIdx = spent ? LITE_SPRITE_TALL_SPENT : LITE_SPRITE_TALL_LIVE;
    } else {
        s->spriteIdx = spent ? LITE_SPRITE_WIDE_SPENT : LITE_SPRITE_WIDE_LIVE;
    }
    cob->active = OBJECT_ACTIVE;
    return 0;
}

RegisterObject(LiteClassInit, LiteInit, 1, LiteReactivate, LiteUpdate, NULL,
               sizeof(FootObjectState));

#ifdef __cplusplus
}
#endif
