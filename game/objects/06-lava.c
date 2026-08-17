#ifdef __cplusplus
extern "C" {
#endif

#include "06-lava.h"
#include "object_info.h"

#ifdef __APPLE__
void LavaClassInit() {
}
#endif

void LavaInit(DynospriteCOB *cob, DynospriteODT *odt, byte *initData) {
    LavaObjectState *s = (LavaObjectState *)(cob->statePtr);

    /* No globals here: the lava runs all the time, so it has nothing to ask
     * the game about. */
    s->side = initData[0];
    s->along = initData[1];
    /* One or two 256ths of the slope per tick.  At thirty ticks a second that
     * is a pixel every few tenths of a second -- lava oozes, it does not run.
     * Mixing the two speeds keeps the drops from moving in lockstep. */
    s->speed = 1 + (initData[1] & 1);
    s->spriteIdx = LAVA_SPRITE_HOT;
    cob->globalX = VOLCANO_X;
    cob->globalY = VOLCANO_Y;
    cob->active = OBJECT_ACTIVE;
}

byte LavaReactivate(DynospriteCOB *cob, DynospriteODT *odt) {
    return 0;
}

byte LavaUpdate(DynospriteCOB *cob, DynospriteODT *odt) {
    LavaObjectState *s = (LavaObjectState *)(cob->statePtr);
    unsigned along;

    /* The volcano is always simmering: the lava runs whether or not it has
     * erupted, and erupting is what the multiplier and the shake are for.
     *
     * `along` is a byte, so this wraps at the foot of the slope on its own and
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
