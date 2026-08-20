#ifdef DynospriteObject_DataDefinition

/** sizeof(TongueObjectState) */
#define DynospriteObject_DataSize 3

/** One byte of init data: which side this tongue is on. */
#define DynospriteObject_InitSize 1

#else

#ifndef _07_tongue_h
#define _07_tongue_h

#include "dynosprite.h"

#define TONGUE_LEFT 0
#define TONGUE_RIGHT 1

/**
 * A tongue, flicking out of one of the dinosaurs at the bottom of the table.
 *
 * It runs out and back on its own, half a period behind its opposite number,
 * and at full stretch it touches the wall beside it.  That is what it is for:
 * the gap between a dinosaur's head and the wall is an outlane, and a ball
 * running down it while the tongue is out gets turned back into the table.
 *
 * The extension is published in GameGlobals rather than worked out twice.  The
 * tongues update before the ball does, so what the ball bounces off is exactly
 * what is on the screen.
 */
typedef struct TongueObjectState {
    byte spriteIdx; /* must be first */
    byte side;
    /* Its own place in the cycle, rather than a phase read off the game's
     * free-running counter: this one stops with the ball, and picking up
     * where it left off is the point of keeping it here. */
    byte phase;
} TongueObjectState;

#endif /* _07_tongue_h */

#endif /* DynospriteObject_DataDefinition */
