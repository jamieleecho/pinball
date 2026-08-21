#ifdef __cplusplus
extern "C" {
#endif

#include "08-fly.h"
#include "object_info.h"
#include "fly_data.h"

static byte didNotInit = TRUE;
static GameGlobals *globals;

#ifdef __APPLE__
void FlyClassInit() {
    didNotInit = TRUE;
}
#endif

void FlyInit(DynospriteCOB *cob, DynospriteODT *odt, byte *initData) {
    FlyObjectState *s = (FlyObjectState *)(cob->statePtr);

    if (didNotInit) {
        didNotInit = FALSE;
        globals = gameGlobals();
    }

    s->tick = 0;
    s->caught = FALSE;
    s->spriteIdx = 0;
    cob->globalX = tblFlyX[0];
    cob->globalY = tblFlyY[0];
    cob->active = OBJECT_ACTIVE;
}

byte FlyReactivate(DynospriteCOB *cob, DynospriteODT *odt) {
    return 0;
}

byte FlyUpdate(DynospriteCOB *cob, DynospriteODT *odt) {
    FlyObjectState *s = (FlyObjectState *)(cob->statePtr);

    /* A caught fly comes back with the next ball, along with the volcano. */
    if (!globals->volcano) {
        s->caught = FALSE;
    }
    if (s->caught || globals->gameState != GameStatePlaying) {
        /* Held still rather than hidden: it saves its background, so the
         * engine puts the desert back the moment it stops being drawn. */
        cob->active = OBJECT_ACTIVE;
        return 0;
    }

    s->tick++;
    if (s->tick >= FLY_PERIOD) {
        s->tick = 0;
    }
    globals->flyTick = s->tick;
    cob->globalX = tblFlyX[s->tick];
    cob->globalY = tblFlyY[s->tick];

    /* The tongue is only long enough after twelve plunger hits, and it can
     * only reach the far left of the beat, so this is the one tick in the
     * cycle at which the catch can happen. */
    if (s->tick == FLY_CATCH_TICK && globals->tongue >= TONGUE_TARGET &&
        !globals->volcano) {
        s->caught = TRUE;
        globals->volcano = 1;
        /* She has had her fly.  The next one has to be earned from nothing,
         * which is the only thing that stops the rest of the game erupting on
         * every pass. */
        globals->tongue = 0;
        globals->multiplier = 10;
        globals->quake = QUAKE_TICKS;
        PlaySound(SOUND_DRAIN);
    }

    cob->active = OBJECT_ACTIVE;
    return 0;
}

RegisterObject(FlyClassInit, FlyInit, 1, FlyReactivate, FlyUpdate, NULL,
               sizeof(FlyObjectState));

#ifdef __cplusplus
}
#endif
