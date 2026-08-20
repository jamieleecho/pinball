#ifdef DynospriteObject_DataDefinition

/** sizeof(PanelObjectState) */
#define DynospriteObject_DataSize 4

/** One byte of init data: which read-out this instance is. */
#define DynospriteObject_InitSize 1

#else

#ifndef _05_panel_h
#define _05_panel_h

#include "dynosprite.h"

#define PANEL_ROLE_TONGUE 0
#define PANEL_ROLE_GAMEOVER 1
#define PANEL_ROLE_MULTX 2
#define PANEL_ROLE_GATE 3

/** One of the read-outs on the score panel. */
typedef struct PanelObjectState {
    byte spriteIdx; /* must be first */
    byte role;
    byte redraw;    /* the gate only: buffers still to be painted */
} PanelObjectState;

#endif /* _05_panel_h */

#endif /* DynospriteObject_DataDefinition */
