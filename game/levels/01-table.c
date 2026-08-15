#ifdef __cplusplus
extern "C" {
#endif

#include <coco.h>

#include "dynosprite.h"
#include "../objects/object_info.h"

/*
 * The table does not scroll: the playfield and the score panel are both drawn
 * straight into the tilemap and stay put.  Object initialisation runs before
 * this file's Init (see engine/loader.asm), so the ball has already set the
 * game up by the time we get here and there is nothing to do but hold the
 * background still.
 */

void TableInit(void) {
    DynospriteDirectPageGlobalsPtr->Gfx_BkgrndNewX = 0;
    DynospriteDirectPageGlobalsPtr->Gfx_BkgrndNewY = 0;
}

byte TableCalculateBkgrndNewXY(void) {
    DynospriteDirectPageGlobalsPtr->Gfx_BkgrndNewX = 0;
    DynospriteDirectPageGlobalsPtr->Gfx_BkgrndNewY = 0;
    return 0;
}

RegisterLevel(TableInit, TableCalculateBkgrndNewXY);

#ifdef __cplusplus
}
#endif
