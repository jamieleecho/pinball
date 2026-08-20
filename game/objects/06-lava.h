#ifdef DynospriteObject_DataDefinition

/** sizeof(LavaObjectState) */
#define DynospriteObject_DataSize 4

/** One byte of init data, unused: there is only ever one flow. */
#define DynospriteObject_InitSize 1

#else

#ifndef _06_lava_h
#define _06_lava_h

#include "dynosprite.h"

/**
 * The lava running down the volcano.
 *
 * One object in one place, cycling through frames of the flow.  It began as
 * thirty-six drops each moving under their own steam, which looked right and
 * cost the game a third of its frame rate: every one of them saved and
 * restored a patch of mountain on every tick.  Drawing the whole flow as one
 * sprite costs the same whether there is a little lava or a lot.
 */
typedef struct LavaObjectState {
    byte spriteIdx; /* must be first */
    byte frame;     /* which frame of the flow */
    byte timer;     /* ticks left on this frame */
} LavaObjectState;

#endif /* _06_lava_h */

#endif /* DynospriteObject_DataDefinition */
