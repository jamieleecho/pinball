#ifdef __cplusplus
extern "C" {
#endif

#include "06-lava.h"
#include "object_info.h"

/* Ticks each frame is held.  Eight frames carry the gobbets one spacing down
 * the slope, and there are four spacings in a slope, so a gobbet takes 32
 * frame changes to travel it.  At 56 ticks a frame and 30 ticks a second that
 * is about a minute from apex to foot. */
#define LAVA_FRAME_TICKS 56

#ifdef __APPLE__
void LavaClassInit() {
}
#endif

void LavaInit(DynospriteCOB *cob, DynospriteODT *odt, byte *initData) {
    LavaObjectState *s = (LavaObjectState *)(cob->statePtr);

    /* No globals: the volcano simmers all the time, so the flow has nothing to
     * ask the game about.  Erupting is what the multiplier is for. */
    s->frame = 0;
    s->timer = LAVA_FRAME_TICKS;
    s->spriteIdx = 0;
    cob->globalX = VOLCANO_X;
    cob->globalY = VOLCANO_Y;
    cob->active = OBJECT_ACTIVE;
}

byte LavaReactivate(DynospriteCOB *cob, DynospriteODT *odt) {
    return 0;
}

byte LavaUpdate(DynospriteCOB *cob, DynospriteODT *odt) {
    LavaObjectState *s = (LavaObjectState *)(cob->statePtr);

    if (--s->timer == 0) {
        s->timer = LAVA_FRAME_TICKS;
        if (++s->frame >= LAVA_FRAMES) {
            s->frame = 0;
        }
        s->spriteIdx = s->frame;
    }

    /* This one saves its background, so it has to be drawn every tick: stop
     * and the engine puts the mountain back over it. */
    cob->active = OBJECT_ACTIVE;
    return 0;
}

RegisterObject(LavaClassInit, LavaInit, 1, LavaReactivate, LavaUpdate, NULL,
               sizeof(LavaObjectState));

#ifdef __cplusplus
}
#endif
