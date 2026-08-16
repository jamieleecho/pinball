#ifdef __cplusplus
extern "C" {
#endif

/* The three read-outs on the score panel: the score multiplier, the balls
 * still to play, and how far Vally's tongue has reached. */

#include "05-panel.h"
#include "object_info.h"

static byte didNotInit = TRUE;
static GameGlobals *globals;

#ifdef __APPLE__
void PanelClassInit() {
    didNotInit = TRUE;
}
#endif

void PanelInit(DynospriteCOB *cob, DynospriteODT *odt, byte *initData) {
    PanelObjectState *s = (PanelObjectState *)(cob->statePtr);

    if (didNotInit) {
        didNotInit = FALSE;
        globals = gameGlobals();
    }

    s->role = initData[0];
    s->spriteIdx = 0;

    if (s->role == PANEL_ROLE_GAMEOVER) {
        cob->globalX = PANEL_OVER_X;
        cob->globalY = PANEL_OVER_Y;
        s->spriteIdx = PANEL_SPRITE_GAMEOVER;
    } else if (s->role == PANEL_ROLE_MULTX) {
        cob->globalX = PANEL_MULTX_X;
        cob->globalY = PANEL_MULTX_Y;
        s->spriteIdx = PANEL_SPRITE_MULTX;
    } else if (s->role == PANEL_ROLE_GATE) {
        cob->globalX = GATE_X0;
        cob->globalY = GATE_Y0;
        s->spriteIdx = PANEL_SPRITE_GATE_OPEN;
    } else {
        cob->globalX = PANEL_TONGUE_X;
        cob->globalY = PANEL_TONGUE_Y;
    }
    cob->active = OBJECT_UPDATE_ACTIVE;
}

byte PanelReactivate(DynospriteCOB *cob, DynospriteODT *odt) {
    return 0;
}

byte PanelUpdate(DynospriteCOB *cob, DynospriteODT *odt) {
    PanelObjectState *s = (PanelObjectState *)(cob->statePtr);
    byte show = 0;

    if (s->role == PANEL_ROLE_GATE) {
        /* The gate always draws, shut or open.  These sprites save no
         * background, so going inactive would leave the bar across the lane
         * for good; the open one is what takes it away. */
        s->spriteIdx = globals->gate ? PANEL_SPRITE_GATE_SHUT
                                     : PANEL_SPRITE_GATE_OPEN;
        cob->active = OBJECT_ACTIVE;
        return 0;
    }

    if (s->role == PANEL_ROLE_GAMEOVER) {
        show = (globals->gameState == GameStateOver);
    } else if (s->role == PANEL_ROLE_MULTX) {
        show = (globals->multiplier > 1);
    } else {
        /* The tongue grows one stage for every two top marks hit, and its
         * length carries over from ball to ball for the whole game. */
        byte stage = globals->tongue >> 1;
        if (stage) {
            if (stage > PANEL_TONGUE_STAGES) {
                stage = PANEL_TONGUE_STAGES;
            }
            s->spriteIdx = PANEL_SPRITE_TONGUE1 + stage - 1;
            show = 1;
        }
    }

    cob->active = show ? OBJECT_ACTIVE : OBJECT_UPDATE_ACTIVE;
    return 0;
}

RegisterObject(PanelClassInit, PanelInit, 1, PanelReactivate, PanelUpdate, NULL,
               sizeof(PanelObjectState));

#ifdef __cplusplus
}
#endif
