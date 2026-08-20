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
    GameGlobals *g = gameGlobals();
    int dx = 0;
    int dy = 0;

    /* The volcano is the one thing that moves the camera.  The shake is not
     * random: it walks a short fixed loop, which at this size is indis-
     * tinguishable from noise and costs nothing to work out.  The horizontal
     * step stays even because the background scrolls a byte at a time, which
     * at four bits a pixel is two pixels. */
    if (g->quake) {
        byte phase = g->quake & 7;
        g->quake--;
        dx = (phase & 1) ? QUAKE_X : -QUAKE_X;
        dy = (phase & 2) ? QUAKE_Y : -QUAKE_Y;
        if (phase & 4) {
            dy = -dy;
        }
    }
    DynospriteDirectPageGlobalsPtr->Gfx_BkgrndNewX = CAMERA_X + dx;
    DynospriteDirectPageGlobalsPtr->Gfx_BkgrndNewY = CAMERA_Y + dy;
    return 0;
}

RegisterLevel(TableInit, TableCalculateBkgrndNewXY);

#ifdef __cplusplus
}
#endif
