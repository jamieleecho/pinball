#ifdef DynospriteObject_DataDefinition

/** sizeof(FootObjectState) */
#define DynospriteObject_DataSize 4

/** One byte of init data: which of the nine feet this is. */
#define DynospriteObject_InitSize 1

#else

#ifndef _04_lite_h
#define _04_lite_h

#include "dynosprite.h"

/**
 * One of the nine feet.  The foot itself is painted into the tilemap; this
 * object sits on top of it and draws it live (orange) or spent (cyan).
 *
 * It always draws one or the other, never nothing, because these sprites carry
 * no erase code -- see the sheet in scripts/gen-assets.py.  "Stop drawing the
 * cyan" would leave the cyan on screen for good, so the orange is what puts it
 * back when the ball drains.
 */
typedef struct FootObjectState {
    byte spriteIdx; /* must be first */
    byte index;     /* 0..NUM_FEET-1 */
    byte redraw;    /* buffers still to be painted with the current sprite */
} FootObjectState;

#endif /* _04_lite_h */

#endif /* DynospriteObject_DataDefinition */
