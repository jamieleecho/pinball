#ifdef DynospriteObject_DataDefinition

/** sizeof(FlipperObjectState) */
#define DynospriteObject_DataSize 9

/** One byte of init data: which side this flipper is. */
#define DynospriteObject_InitSize 1

#else

#ifndef _02_flipper_h
#define _02_flipper_h

#include "dynosprite.h"

#define FLIPPER_LEFT 0
#define FLIPPER_RIGHT 1

/** State of one flipper. */
typedef struct FlipperObjectState {
    byte spriteIdx; /* must be first */
    byte side;
    byte frame;  /* 0 at rest, FLIPPER_FRAMES-1 fully raised */
    byte rising; /* set on the frames the flipper is sweeping upward */
    /* Ticks of drawing still owed.  Every frame of the sweep is opaque over
     * the same box, so one paints out the last and nothing has to save a
     * background; a flipper sitting at rest costs nothing at all. */
    byte redraw;
} FlipperObjectState;

#endif /* _02_flipper_h */

#endif /* DynospriteObject_DataDefinition */
