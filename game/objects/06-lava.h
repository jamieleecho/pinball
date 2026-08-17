#ifdef DynospriteObject_DataDefinition

/** sizeof(LavaObjectState) */
#define DynospriteObject_DataSize 6

/** Two bytes of init data: which slope, and where in the run it starts. */
#define DynospriteObject_InitSize 2

#else

#ifndef _06_lava_h
#define _06_lava_h

#include "dynosprite.h"

/**
 * One drop of lava running down one slope of the volcano.
 *
 * The upside-down V the original drew is not a picture anywhere: it is what
 * these drops trace out between them.  Each carries how far down its slope it
 * has got, and restarts at the apex when it reaches the bottom.
 */
typedef struct LavaObjectState {
    byte spriteIdx; /* must be first */
    byte side;      /* 0 = left slope, 1 = right */
    unsigned along; /* how far down, in 256ths of 0..255 of the way to the
                     * foot.  Sixteen bits so the drops can move less than one
                     * step a tick; a byte bottomed out at one, which was still
                     * too quick for lava. */
    byte speed;     /* added to `along` each tick, in those same 256ths */
} LavaObjectState;

#endif /* _06_lava_h */

#endif /* DynospriteObject_DataDefinition */
