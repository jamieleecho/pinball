#ifdef DynospriteObject_DataDefinition

/**
 * sizeof(BallObjectState), rounded up.
 *
 * This must never be smaller than the struct below.  The engine packs each
 * object's state back to back, so one byte of overrun lands in the next
 * object's state -- which shows up as the launcher suddenly drawing itself as
 * a ball, because its sprite index is the first byte of its block.
 */
#define DynospriteObject_DataSize 19

/** One byte of init data: the role this instance plays. */
#define DynospriteObject_InitSize 1

#else

#ifndef _01_ball_h
#define _01_ball_h

#include "dynosprite.h"

#define BALL_ROLE_BALL 0
#define BALL_ROLE_LAUNCHER 1
#define BALL_ROLE_SPRING 2

/**
 * State of a ball (or of the launcher that fires it).
 *
 * Whole pixels of the position live in the object's globalX/globalY, which the
 * engine needs anyway; only the fraction is kept here.  A single 8.8 position
 * would not fit: the table is 208 pixels tall, and 208 * 256 overflows a
 * signed 16-bit int.
 */
typedef struct BallObjectState {
    byte spriteIdx; /* must be the first byte: the engine draws this sprite */
    byte role;
    byte fx; /* sub-pixel position, 1/256ths of a pixel */
    byte fy;
    int vx; /* velocity, 8.8 fixed point pixels per frame */
    int vy;
    byte cooldown; /* frames before this ball can score again */
    byte pull;     /* launcher only: how far it is drawn back */
    byte lastEnter;
    byte stillFor; /* frames spent barely moving, used to unstick the ball */
    byte nudge;    /* alternates the direction of the unsticking nudge */
    byte rnd;      /* running seed for the randomised bounce */
    byte laneTick; /* frames until the next blip on the way up the lane */
    byte clank;    /* frames before the next clank; kept apart from cooldown
                    * so that scraping along a wall cannot mute a bumper */
    /* Spring only, and last on purpose: the playtest driver reads this struct
     * by offset, so anything new goes on the end.  The spring saves no
     * background, which means it has to be painted into both buffers when its
     * length changes and into neither when it has not. */
    byte redraw;
    /* Where the ball was when stillFor last restarted, at half resolution so
     * each fits a byte.  Also last on purpose, for the same reason. */
    byte anchorX;
    byte anchorY;
} BallObjectState;

#endif /* _01_ball_h */

#endif /* DynospriteObject_DataDefinition */
