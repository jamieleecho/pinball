#ifdef __cplusplus
extern "C" {
#endif

#include "02-flipper.h"
#include "object_info.h"

/* Two frame buffers, so a sprite that saves no background has to be painted
 * into each of them and then not again until what it shows changes. */
#define BUFFERS 2

static byte didNotInit = TRUE;
static GameGlobals *globals;

#ifdef __APPLE__
void FlipperClassInit() {
    didNotInit = TRUE;
}
#endif

void FlipperInit(DynospriteCOB *cob, DynospriteODT *odt, byte *initData) {
    FlipperObjectState *s = (FlipperObjectState *)(cob->statePtr);

    if (didNotInit) {
        didNotInit = FALSE;
        globals = gameGlobals();
    }

    s->side = initData[0];
    s->frame = 0;
    s->rising = 0;
    if (s->side == FLIPPER_RIGHT) {
        cob->globalX = FLIP_R_X;
        cob->globalY = FLIP_R_Y;
        s->spriteIdx = FLIPPER_FRAMES;
    } else {
        cob->globalX = FLIP_L_X;
        cob->globalY = FLIP_L_Y;
        s->spriteIdx = 0;
    }
    s->redraw = BUFFERS;
}

byte FlipperReactivate(DynospriteCOB *cob, DynospriteODT *odt) {
    return 0;
}

byte FlipperUpdate(DynospriteCOB *cob, DynospriteODT *odt) {
    FlipperObjectState *s = (FlipperObjectState *)(cob->statePtr);
    byte held, idx;

    /* The flippers only answer the keys while a ball is actually in play, so
     * they sit still during the pause after a drain. */
    if (globals->gameState != GameStatePlaying && globals->gameState != GameStateReady) {
        held = 0;
    } else {
        held = (s->side == FLIPPER_RIGHT) ? rightFlipperKey() : leftFlipperKey();
    }

    s->rising = 0;
    if (held) {
        if (s->frame < FLIPPER_FRAMES - 1) {
            s->frame++;
            s->rising = 1;
        }
    } else if (s->frame) {
        s->frame--;
    }

    idx = (byte)((s->side == FLIPPER_RIGHT ? FLIPPER_FRAMES : 0) + s->frame);
    if (s->spriteIdx != idx) {
        s->spriteIdx = idx;
        s->redraw = BUFFERS;
    }
    /* A flipper at rest is the common case by a long way, and it now costs
     * nothing: every frame of the sweep is opaque over the same box, so one
     * paints out the last and there is no background to put back. */
    if (s->redraw) {
        s->redraw--;
        cob->active = OBJECT_ACTIVE;
    } else {
        cob->active = OBJECT_UPDATE_ACTIVE;
    }
    return 0;
}

RegisterObject(FlipperClassInit, FlipperInit, 1, FlipperReactivate, FlipperUpdate,
               NULL, sizeof(FlipperObjectState));

#ifdef __cplusplus
}
#endif
