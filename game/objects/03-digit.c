#ifdef __cplusplus
extern "C" {
#endif

#include "03-digit.h"
#include "object_info.h"

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
    s->spriteIdx = 0;

    switch (s->board) {
    case DIGIT_BOARD_BALLS:
        cob->globalX = BALLS_DIGIT_X;
        cob->globalY = BALLS_DIGIT_Y;
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

byte DigitUpdate(DynospriteCOB *cob, DynospriteODT *odt) {
    DigitObjectState *s = (DigitObjectState *)(cob->statePtr);
    const byte *digits;
    byte index, packed;

    switch (s->board) {
    case DIGIT_BOARD_BALLS:
        s->spriteIdx = globals->ballsLeft > 9 ? 9 : globals->ballsLeft;
        cob->active = OBJECT_ACTIVE;
        return 0;

    case DIGIT_BOARD_MULT_TENS:
        /* Only 10X needs a tens digit; 2X and 3X leave it blank. */
        s->spriteIdx = (globals->multiplier >= 10) ? 1 : DIGIT_SPRITE_BLANK;
        cob->active = OBJECT_ACTIVE;
        return 0;

    case DIGIT_BOARD_MULT_ONES:
        if (globals->multiplier > 1) {
            s->spriteIdx = (globals->multiplier >= 10) ? 0 : globals->multiplier;
        } else {
            s->spriteIdx = DIGIT_SPRITE_BLANK;
        }
        cob->active = OBJECT_ACTIVE;
        return 0;

    default:
        break;
    }

    digits = (s->board == DIGIT_BOARD_HIGH) ? globals->highScore : globals->score;
    /* Seven digits are shown out of the eight the counter holds, so column 0
     * is overall digit 1. */
    index = s->column + 1;
    packed = digits[index >> 1];
    s->spriteIdx = (index & 1) ? (packed & 0x0f) : (packed >> 4);

    /* The manual says the high score board flashes when the game ends. */
    if (s->board == DIGIT_BOARD_HIGH && globals->gameState == GameStateOver &&
        (globals->flashTimer & 0x10)) {
        s->spriteIdx = DIGIT_SPRITE_BLANK;
    }
    cob->active = OBJECT_ACTIVE;
    return 0;
}

RegisterObject(DigitClassInit, DigitInit, 2, DigitReactivate, DigitUpdate, NULL,
               sizeof(DigitObjectState));

#ifdef __cplusplus
}
#endif
