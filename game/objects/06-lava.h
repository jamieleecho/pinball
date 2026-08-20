#ifdef DynospriteObject_DataDefinition

/** sizeof(LavaObjectState) */
#define DynospriteObject_DataSize 5

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
    /* Ticks of drawing still owed.  The flow saves no background now, so it
     * only needs painting into each of the two buffers when the frame
     * changes -- which is once in fifty-six. */
    byte redraw;
} LavaObjectState;

#endif /* _06_lava_h */

#endif /* DynospriteObject_DataDefinition */
