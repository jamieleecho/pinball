#ifdef __cplusplus
extern "C" {
#endif

#include "07-tongue.h"
#include "object_info.h"

/* Two frame buffers, so a sprite that saves no background has to be painted
 * into each of them and then not again until what it shows changes. */
#define BUFFERS 2

static byte didNotInit = TRUE;
static GameGlobals *globals;

#ifdef __APPLE__
void TongueClassInit() {
    didNotInit = TRUE;
}
#endif

void TongueInit(DynospriteCOB *cob, DynospriteODT *odt, byte *initData) {
    TongueObjectState *s = (TongueObjectState *)(cob->statePtr);

    if (didNotInit) {
        didNotInit = FALSE;
        globals = gameGlobals();
    }

    s->side = initData[0];
    /* Half a cycle apart, so one is always further out than the other. */
    s->phase = (byte)(s->side ? TONGUE_PERIOD / 2 : 0);
    s->spriteIdx = (byte)(s->side ? TONGUE_MAX : 0);
    /* Written out rather than picked with ?:.  CMOC gives a conditional
     * expression whose arms are both small constants a char's type, and
     * TONGUE_R_X is 156, which comes back as -100 once it is sign extended
     * into globalX.  The object then sits off the left of the world and
     * simply never draws -- no warning, no trap, just a tongue that is
     * never there. */
    if (s->side) {
        cob->globalX = TONGUE_BOX_R_X;
    } else {
        cob->globalX = TONGUE_BOX_L_X;
    }
    cob->globalY = TONGUE_BOX_Y;
    s->redraw = BUFFERS;
    cob->active = OBJECT_ACTIVE;
}

byte TongueReactivate(DynospriteCOB *cob, DynospriteODT *odt) {
    return 0;
}

byte TongueUpdate(DynospriteCOB *cob, DynospriteODT *odt) {
    TongueObjectState *s = (TongueObjectState *)(cob->statePtr);
    byte out, idx;

    /* Tongues flick only while a ball is in play.  A table sitting on its
     * launcher, or waiting out a drain, holds still. */
    if (globals->gameState == GameStatePlaying) {
        s->phase = (byte)(s->phase + 1) & (byte)(TONGUE_PERIOD - 1);
    }
    out = tblTongueLen[s->phase];

    globals->tongueOut[s->side] = out;
    idx = (byte)((s->side ? TONGUE_MAX : 0) + out - 1);
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

RegisterObject(TongueClassInit, TongueInit, 1, TongueReactivate, TongueUpdate,
               NULL, sizeof(TongueObjectState));

#ifdef __cplusplus
}
#endif
