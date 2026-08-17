#ifdef __cplusplus
extern "C" {
#endif

#include "06-lava.h"
#include "object_info.h"

static byte didNotInit = TRUE;
static GameGlobals *globals;

#ifdef __APPLE__
void LavaClassInit() {
    didNotInit = TRUE;
}
#endif

void LavaInit(DynospriteCOB *cob, DynospriteODT *odt, byte *initData) {
    LavaObjectState *s = (LavaObjectState *)(cob->statePtr);

    if (didNotInit) {
        didNotInit = FALSE;
        globals = gameGlobals();
    }

    s->side = initData[0];
    s->along = initData[1];
    /* A little spread, so the drops do not run in lockstep down the slope. */
    s->speed = 3 + (initData[1] & 3);
    s->spriteIdx = LAVA_SPRITE_HOT;
    cob->globalX = VOLCANO_X;
    cob->globalY = VOLCANO_Y;
    cob->active = OBJECT_UPDATE_ACTIVE;
}

byte LavaReactivate(DynospriteCOB *cob, DynospriteODT *odt) {
    return 0;
}

byte LavaUpdate(DynospriteCOB *cob, DynospriteODT *odt) {
    LavaObjectState *s = (LavaObjectState *)(cob->statePtr);
    unsigned along;

    if (!globals->volcano) {
        /* Nothing to see until it erupts.  Back to the apex so the next
         * eruption starts from the top rather than mid-slope. */
        s->along = 0;
        cob->active = OBJECT_UPDATE_ACTIVE;
        return 0;
    }

    /* `along` is a byte, so this wraps at the foot of the slope on its own and
     * the drop reappears at the apex. */
    s->along += s->speed;
    along = (unsigned)s->along;

    if (s->side) {
        cob->globalX = VOLCANO_X + (unsigned)((LAVA_R_DX * along) >> 8);
        cob->globalY = VOLCANO_Y + (unsigned)((LAVA_R_DY * along) >> 8);
    } else {
        cob->globalX = VOLCANO_X - (unsigned)((LAVA_L_DX * along) >> 8);
        cob->globalY = VOLCANO_Y + (unsigned)((LAVA_L_DY * along) >> 8);
    }

    /* Cooling as it goes, and flickering on the way. */
    s->spriteIdx = (s->along & 8) ? LAVA_SPRITE_HOT : LAVA_SPRITE_COOL;
    cob->active = OBJECT_ACTIVE;
    return 0;
}

RegisterObject(LavaClassInit, LavaInit, 2, LavaReactivate, LavaUpdate, NULL,
               sizeof(LavaObjectState));

#ifdef __cplusplus
}
#endif
