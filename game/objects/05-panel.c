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
        s->redraw = 2;
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
        byte idx = globals->gate ? PANEL_SPRITE_GATE_SHUT
                                 : PANEL_SPRITE_GATE_OPEN;
        /* Saves no background and never moves, so it only needs painting into
         * each of the two buffers when it changes -- not every frame. */
        if (s->spriteIdx != idx) {
            s->spriteIdx = idx;
            s->redraw = 2;
        }
        if (s->redraw) {
            s->redraw--;
            cob->active = OBJECT_ACTIVE;
        } else {
            cob->active = OBJECT_UPDATE_ACTIVE;
        }
        return 0;
    }

    if (s->role == PANEL_ROLE_GAMEOVER) {
        show = (globals->gameState == GameStateOver);
    } else if (s->role == PANEL_ROLE_MULTX) {
        show = (globals->multiplier > 1);
    } else {
        /* The tongue grows one stage for every two plunger hits, and its
         * length carries over from ball to ball for the whole game.  It is not
         * held out, though: it strikes once per pass of the fly, timed so that
         * full stretch falls on the tick the fly is furthest left, which is
         * the only place it can be caught.  Out of that window the tongue is
         * not drawn at all, which is most of the time and most of the saving.
         */
        byte stage = globals->tongue >> 1;
        /* Ticks since the strike should have started.  Wrapped with a
         * comparison rather than a mask: the flight is no longer a power of
         * two ticks long, and a mask would silently fold it in half. */
        int rel = (int)globals->flyTick - FLY_CATCH_TICK + TONGUE_REACH_STAGES;
        if (rel < 0) {
            rel += FLY_PERIOD;
        }
        if (stage > PANEL_TONGUE_STAGES) {
            stage = PANEL_TONGUE_STAGES;
        }
        if (stage && rel < 2 * TONGUE_REACH_STAGES) {
            byte reach = rel < TONGUE_REACH_STAGES
                             ? (byte)(rel + 1)
                             : (byte)(2 * TONGUE_REACH_STAGES - rel);
            if (reach > stage) {
                reach = stage;
            }
            s->spriteIdx = PANEL_SPRITE_TONGUE1 + reach - 1;
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
