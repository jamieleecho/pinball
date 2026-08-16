#ifdef __cplusplus
extern "C" {
#endif

#include <coco.h>

#include "dynosprite.h"
#include "../objects/object_info.h"

/*
 * The table does not scroll during play, but the world is deliberately larger
 * than the screen (336x224 against 320x200) so the camera has somewhere to go
 * when the volcano erupts.  Until then it sits still at CAMERA_X/CAMERA_Y,
 * which is the middle, leaving 8 pixels of slack left and right and 12 above
 * and below.
 *
 * Object initialisation runs before this file's Init (see engine/loader.asm),
 * so the ball has already set the game up by the time we get here.
 */

void TableInit(void) {
    DynospriteDirectPageGlobalsPtr->Gfx_BkgrndNewX = CAMERA_X;
    DynospriteDirectPageGlobalsPtr->Gfx_BkgrndNewY = CAMERA_Y;
}

byte TableCalculateBkgrndNewXY(void) {
    DynospriteDirectPageGlobalsPtr->Gfx_BkgrndNewX = CAMERA_X;
    DynospriteDirectPageGlobalsPtr->Gfx_BkgrndNewY = CAMERA_Y;
    return 0;
}

RegisterLevel(TableInit, TableCalculateBkgrndNewXY);

#ifdef __cplusplus
}
#endif
