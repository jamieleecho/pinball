#ifdef DynospriteObject_DataDefinition

/** sizeof(LiteObjectState) */
#define DynospriteObject_DataSize 4

/** Two bytes of init data: which kind of target, and which one of them. */
#define DynospriteObject_InitSize 2

#else

#ifndef _04_lite_h
#define _04_lite_h

#include "dynosprite.h"

/**
 * An overlay that shows a target's state.  The targets themselves are painted
 * into the tilemap, so only the ones that have changed cost a sprite draw.
 */
typedef struct LiteObjectState {
    byte spriteIdx; /* must be first */
    byte kind;
    byte index;
    byte timer; /* frames left on a flash */
} LiteObjectState;

#endif /* _04_lite_h */

#endif /* DynospriteObject_DataDefinition */
