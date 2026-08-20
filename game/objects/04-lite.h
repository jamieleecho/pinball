#ifdef DynospriteObject_DataDefinition

/** sizeof(LiteObjectState) */
#define DynospriteObject_DataSize 6

/** Two bytes of init data: which sort of overlay, and which one of them. */
#define DynospriteObject_InitSize 2

#else

#ifndef _04_lite_h
#define _04_lite_h

#include "dynosprite.h"

/**
 * An overlay sitting on top of something painted into the tilemap: one of the
 * nine feet, or the middle of one of the three big bumpers.
 *
 * All of these draw one of two opaque sprites and never nothing, because they
 * carry no erase code -- see the sheet in scripts/gen-assets.py.  "Stop
 * drawing the second one" would leave it on screen for good, so it is the
 * first that puts things back.
 */
typedef struct LiteObjectState {
    byte spriteIdx; /* must be first */
    byte kind;      /* LITE_KIND_FOOT or LITE_KIND_DIAMOND */
    byte index;     /* which foot, or which bumper */
    byte redraw;    /* buffers still to be painted with the current sprite */
    byte timer;     /* bumpers only: ticks left of the flash */
} LiteObjectState;

#endif /* _04_lite_h */

#endif /* DynospriteObject_DataDefinition */
