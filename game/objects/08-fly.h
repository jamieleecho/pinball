#ifdef DynospriteObject_DataDefinition

/** sizeof(FlyObjectState) */
#define DynospriteObject_DataSize 3

/** One byte of init data, unused: there is only ever the one fly. */
#define DynospriteObject_InitSize 1

#else

#ifndef _08_fly_h
#define _08_fly_h

#include "dynosprite.h"

/**
 * The prehistoric fly, beating back and forth across the panel's desert.
 *
 * Catching it is the whole of the volcano: the manual has Vally reach for it
 * with her tongue, and the tongue only stretches far enough after twelve
 * plunger hits.  The fly is catchable at one point in its flight -- the far
 * left of its beat -- so the tongue and the fly share this object's clock.
 */
typedef struct FlyObjectState {
    byte spriteIdx; /* must be first */
    byte tick;      /* place in the flight, 0..FLY_PERIOD-1 */
    byte caught;
} FlyObjectState;

#endif /* _08_fly_h */

#endif /* DynospriteObject_DataDefinition */
