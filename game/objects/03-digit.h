#ifdef DynospriteObject_DataDefinition

/** sizeof(DigitObjectState) */
#define DynospriteObject_DataSize 4

/** Two bytes of init data: which board, and which column of it. */
#define DynospriteObject_InitSize 2

#else

#ifndef _03_digit_h
#define _03_digit_h

#include "dynosprite.h"

#define DIGIT_BOARD_SCORE 0
#define DIGIT_BOARD_HIGH 1
#define DIGIT_BOARD_BALLS 2      /* balls still to play */
#define DIGIT_BOARD_MULT_TENS 3  /* the "1" of a 10X multiplier */
#define DIGIT_BOARD_MULT_ONES 4

/** One digit of a score board or of a panel read-out. */
typedef struct DigitObjectState {
    byte spriteIdx; /* must be first */
    byte board;
    byte column; /* 0 is the most significant of the seven shown */
} DigitObjectState;

#endif /* _03_digit_h */

#endif /* DynospriteObject_DataDefinition */
