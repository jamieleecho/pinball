#ifdef __cplusplus
extern "C" {
#endif

#include "03-digit.h"
#include "object_info.h"

/* These sprites save no background, and they never move: once drawn they stay
 * on screen until something paints over them.  So they only need drawing
 * twice -- once into each of the double buffers -- and then not again until
 * what they show changes.  BUFFERS is that two.
 *
 * This holds only while the camera stands still.  Scrolling makes the engine
 * repaint the strips coming into view, which would wipe any of these that sat
 * in one, and nothing would put it back.  If the volcano ever shakes the
 * screen, every read-out using this needs its redraw counter reloaded for the
 * duration. */
#define BUFFERS 2

static byte didNotInit = TRUE;
static GameGlobals *globals;

#ifdef __APPLE__
void DigitClassInit() {
    didNotInit = TRUE;
}
#endif

void DigitInit(DynospriteCOB *cob, DynospriteODT *odt, byte *initData) {
    DigitObjectState *s = (DigitObjectState *)(cob->statePtr);
    byte column;

    if (didNotInit) {
        didNotInit = FALSE;
        globals = gameGlobals();
    }

    s->board = initData[0];
    s->column = initData[1];
    /* Whatever this read-out ends up being, it must start on a sprite the
     * same size as the ones it will draw later.  None of these save the
     * background, so a taller sprite drawn even once leaves the rows the
     * shorter one cannot reach on screen for good -- and in one buffer only,
     * so it blinks.  Digit0 is eleven rows; a ball is eight. */
    s->spriteIdx = (initData[0] == DIGIT_BOARD_BALLS) ? DIGIT_SPRITE_BALL_BLANK : 0;
    s->redraw = BUFFERS;

    switch (s->board) {
    case DIGIT_BOARD_BALLS:
        /* One indicator per ball, stacked up the strip between the table and
         * the boards.  Indicator 0 is the bottom one, so losing a ball takes
         * the top of the pile away. */
        cob->globalX = BALLS_DIGIT_X;
        cob->globalY = BALLS_DIGIT_Y - (unsigned)s->column * BALLS_PITCH;
        break;
    case DIGIT_BOARD_MULT_TENS:
        cob->globalX = MULT_DIGIT_X;
        cob->globalY = MULT_DIGIT_Y;
        break;
    case DIGIT_BOARD_MULT_ONES:
        cob->globalX = MULT_DIGIT_X + SCORE_DIGIT_PITCH;
        cob->globalY = MULT_DIGIT_Y;
        break;
    default:
        /* Every term is widened deliberately: the rightmost columns land past
         * x=255, which byte arithmetic would wrap back to the playfield. */
        column = s->column;
        cob->globalX = (unsigned)SCORE_DIGIT_X0 +
                       (unsigned)column * (unsigned)SCORE_DIGIT_PITCH +
                       (unsigned)(column >= 1 ? SCORE_GROUP_GAP : 0) +
                       (unsigned)(column >= 4 ? SCORE_GROUP_GAP : 0);
        cob->globalY =
            (s->board == DIGIT_BOARD_HIGH) ? HIGH_DIGIT_Y : SCORE_DIGIT_Y;
        break;
    }
}

byte DigitReactivate(DynospriteCOB *cob, DynospriteODT *odt) {
    return 0;
}

/** Show this sprite, and draw only while a buffer still needs it. */
static void show(DynospriteCOB *cob, DigitObjectState *s, byte idx) {
    if (s->spriteIdx != idx) {
        s->spriteIdx = idx;
        s->redraw = BUFFERS;
    }
    if (s->redraw) {
        s->redraw--;
        cob->active = OBJECT_ACTIVE;
    } else {
        cob->active = OBJECT_UPDATE_ACTIVE;
    }
}

byte DigitUpdate(DynospriteCOB *cob, DynospriteODT *odt) {
    DigitObjectState *s = (DigitObjectState *)(cob->statePtr);
    const byte *digits;
    byte index, packed;

    switch (s->board) {
    case DIGIT_BOARD_BALLS:
        /* A ball is drawn for every ball still to play.  Both sprites are
         * opaque and neither saves the background, so the blank is what takes
         * a used ball away -- simply not drawing would leave it there. */
        show(cob, s, (s->column < globals->ballsLeft) ? DIGIT_SPRITE_BALL
                                                      : DIGIT_SPRITE_BALL_BLANK);
        return 0;

    case DIGIT_BOARD_MULT_TENS:
        /* Only 10X needs a tens digit; 2X and 3X leave it blank. */
        show(cob, s, (globals->multiplier >= 10) ? 1 : DIGIT_SPRITE_BLANK);
        return 0;

    case DIGIT_BOARD_MULT_ONES:
        show(cob, s, (globals->multiplier > 1)
                        ? ((globals->multiplier >= 10) ? 0 : globals->multiplier)
                        : DIGIT_SPRITE_BLANK);
        return 0;

    default:
        break;
    }

    digits = (s->board == DIGIT_BOARD_HIGH) ? globals->highScore : globals->score;
    /* Seven digits are shown out of the eight the counter holds, so column 0
     * is overall digit 1. */
    index = s->column + 1;
    packed = digits[index >> 1];
    index = (index & 1) ? (packed & 0x0f) : (packed >> 4);

    /* The manual says the high score board flashes when the game ends. */
    if (s->board == DIGIT_BOARD_HIGH && globals->gameState == GameStateOver &&
        (globals->flashTimer & 0x10)) {
        index = DIGIT_SPRITE_BLANK;
    }
    show(cob, s, index);
    return 0;
}

RegisterObject(DigitClassInit, DigitInit, 2, DigitReactivate, DigitUpdate, NULL,
               sizeof(DigitObjectState));

#ifdef __cplusplus
}
#endif
