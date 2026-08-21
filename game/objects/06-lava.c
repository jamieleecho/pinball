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

/* Two frame buffers, so a sprite that saves no background has to be painted
 * into each of them and then not again until what it shows changes. */
#define BUFFERS 2

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

    /* The volcano simmers all the time rather than only when it erupts --
     * erupting is what the multiplier is for -- but it simmers only while a
     * ball is in play. */
    s->frame = 0;
    s->timer = LAVA_FRAME_TICKS;
    s->spriteIdx = 0;
    s->redraw = BUFFERS;
    cob->globalX = LAVA_BOX_X;
    cob->globalY = LAVA_BOX_Y;
    cob->active = OBJECT_ACTIVE;
}

byte LavaReactivate(DynospriteCOB *cob, DynospriteODT *odt) {
    return 0;
}

byte LavaUpdate(DynospriteCOB *cob, DynospriteODT *odt) {
    LavaObjectState *s = (LavaObjectState *)(cob->statePtr);

    if (globals->gameState == GameStatePlaying && --s->timer == 0) {
        s->timer = LAVA_FRAME_TICKS;
        if (++s->frame >= LAVA_FRAMES) {
            s->frame = 0;
        }
        s->spriteIdx = s->frame;
        s->redraw = BUFFERS;
    }

    /* Every frame is opaque across the same box, so a new one paints the old
     * one out and the mountain never needs putting back.  Fifty-five ticks in
     * fifty-six there is nothing to do at all: this was the largest sprite on
     * the screen and it was being redrawn identically every tick. */
    if (s->redraw) {
        s->redraw--;
        cob->active = OBJECT_ACTIVE;
    } else {
        cob->active = OBJECT_UPDATE_ACTIVE;
    }
    return 0;
}

RegisterObject(LavaClassInit, LavaInit, 1, LavaReactivate, LavaUpdate, NULL,
               sizeof(LavaObjectState));

#ifdef __cplusplus
}
#endif
