*********************************************************************************
* DynoSprite - menu.asm
* Copyright (c) 2014, Richard Goedeken
* All rights reserved.
* 
* Redistribution and use in source and binary forms, with or without
* modification, are permitted provided that the following conditions are met:
* 
* * Redistributions of source code must retain the above copyright notice, this
*   list of conditions and the following disclaimer.
* 
* * Redistributions in binary form must reproduce the above copyright notice,
*   this list of conditions and the following disclaimer in the documentation
*   and/or other materials provided with the distribution.
* 
* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
* AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
* IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
* DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
* FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
* DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
* SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
* CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
* OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
* OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*********************************************************************************

* Which rows the menu offers.  Set either to 1 to put its row back.
*
* A row that can only be left at the one setting that works is worse than no
* row at all, and this game has two of those.  It reads the keyboard matrix
* itself because the joystick emulation cannot report two keys at once and a
* pinball table needs both flippers at once; and it ships no music.  Both are
* assembled out rather than merely defaulted, so there is nothing to set.
MenuShowControl         equ     0
MenuShowMusic           equ     0

* The rows are laid out from these rather than written down four times each,
* so a hidden row closes its gap instead of leaving a hole in the middle of
* the menu, and what is left stays centred on the same part of the splash.
* X is in bytes: two pixels each, four bytes to a character, 160 to a screen.
MenuRowDY               equ     16
MenuNumRows             equ     2+MenuShowControl+MenuShowMusic
MenuRowMonitorY         equ     107+(4-MenuNumRows)*MenuRowDY/2
MenuRowControlY         equ     MenuRowMonitorY+MenuRowDY
MenuRowSoundY           equ     MenuRowControlY+MenuShowControl*MenuRowDY
MenuRowMusicY           equ     MenuRowSoundY+MenuRowDY
MenuLabelX              equ     30
MenuValueX              equ     32+10*4

*Local Data
*
Menu_Monitor            fcn     '[M]onitor:'
Menu_RGB                fcn     'RGB'
Menu_CMP                fcn     'Composite'
 IFNE MenuShowControl
Menu_Control            fcn     '[C]ontrol:'
Menu_Joystick           fcn     'Joystick'
Menu_Keyboard           fcn     'Keyboard'
 ENDC
Menu_Sound              fcn     '[S]ound:'
Menu_Internal           fcn     'Coco internal'
Menu_Orc90              fcn     'Orchestra-90'
Menu_NoSound            fcn     'No sound'
 IFNE MenuShowMusic
Menu_Music              fcn     'M[u]sic:'
Menu_MusicYes           fcn     'Yes'
Menu_MusicNo            fcn     'No'
Menu_MusicEnabled       fcb     EnableMusic     * $FF=music on, 0=music off (from defaults-config.json)
 ELSE
Menu_MusicEnabled       fcb     0               * no Music row: music never comes on
 ENDC
 IFNE MenuShowControl
Menu_StartMsg           fcn     '[Space] or joystick button to start'
MenuStartX              equ     (160-35*4)/2
 ELSE
Menu_StartMsg           fcn     '[Space] to start'
MenuStartX              equ     (160-16*4)/2
 ENDC

***********************************************************
* Menu_RunMain:
*   This function never returns.  When the player starts the game, this routine
*   will load and execute the first level.
*
* - IN:      N/A
* - OUT:     This function never returns
***********************************************************
*
Menu_RunMain
            * Initialize the graphics aperature, prior to allocating any virtual 8k blocks
            ldy         #0                      * setup Gfx_BkgrndStartXYList
            ldx         #0
            stx         <Gfx_BkgrndStartXYList
            sty         <Gfx_BkgrndStartXYList+2
            stx         <Gfx_BkgrndStartXYList+4
            sty         <Gfx_BkgrndStartXYList+6
            stx         <Gfx_BkgrndNewX         * set up NewX/Y and RedrawOldX/Y globals so 2nd frame will be drawn in correct place
            stx         <Gfx_BkgrndRedrawOldX
            sty         <Gfx_BkgrndNewY
            sty         <Gfx_BkgrndRedrawOldY
            jsr         Gfx_SetInitialAperature * Initialize graphics aperature
            clra
            jsr         System_SetPaletteConst  * set palette to all 0
            * Set up double-buffering variables
            clr         <Gfx_CurrentFieldCount
            orcc        #$50                    * disable interrupts
            clr         <Gfx_LastRenderedFrame
            clr         <Gfx_DisplayedFrame
            andcc       #$AF                    * re-enable interrupts
            ldb         #4
            stb         <Gfx_RenderingFrameX4   * set back buffer to second pair
            ldx         #Gfx_BkgrndStartXYList  * set both physical addresses
            jsr         Gfx_UpdatePhyAddress
            ldx         #Gfx_BkgrndStartXYList+4
            jsr         Gfx_UpdatePhyAddress
            clrb
            jsr         System_SetVideoStart    * then set GIME video start address for correct buffer pair
            * Load main menu splash image (Image #0)
            clra
            clrb
            ldu         #0
            jsr         Img_Load_Splash_Image
            * Draw menu text on top of the splash image
            clra
            ldb         Gfx_PalIdx_BarColor
            andb        #$0f
            tfr         d,u
            pshs        u
            ldx         #Menu_Monitor
            ldb         #MenuLabelX
            lda         #MenuRowMonitorY
            jsr         Gfx_DrawTextLine_Back
 IFNE MenuShowControl
            ldx         #Menu_Control
            ldb         #MenuLabelX
            lda         #MenuRowControlY
            ldu         ,s
            jsr         Gfx_DrawTextLine_Back
 ENDC
            ldx         #Menu_Sound
            ldb         #MenuLabelX
            lda         #MenuRowSoundY
            ldu         ,s
            jsr         Gfx_DrawTextLine_Back
 IFNE MenuShowMusic
            ldx         #Menu_Music
            ldb         #MenuLabelX
            lda         #MenuRowMusicY
            ldu         ,s
            jsr         Gfx_DrawTextLine_Back
 ENDC
            ldx         #Menu_StartMsg
            ldb         #MenuStartX
            lda         #184
            puls        u
            jsr         Gfx_DrawTextLine_Back
            clra
            ldb         Gfx_PalIdx_FGColor
            andb        #$0f
            tfr         d,u
            pshs        u
            ldx         #Menu_CMP
            tst         <Gfx_MonitorIsRGB
            beq         >
            ldx         #Menu_RGB
!           ldb         #MenuValueX
            lda         #MenuRowMonitorY
            jsr         Gfx_DrawTextLine_Back
 IFNE MenuShowControl
            ldx         #Menu_Joystick
            tst         <Input_UseKeyboard
            beq         >
            ldx         #Menu_Keyboard
!           ldb         #MenuValueX
            lda         #MenuRowControlY
            ldu         ,s
            jsr         Gfx_DrawTextLine_Back
 ELSE
            lda         #$ff
            sta         <Input_UseKeyboard      * no Control row: keyboard, always
 ENDC
            ldx         #Menu_NoSound
            tst         <Sound_OutputMode
            bmi         SoundMenuInitTextDone@
            bgt         >
            ldx         #Menu_Internal
            bra         SoundMenuInitTextDone@
!           ldx         #Menu_Orc90
SoundMenuInitTextDone@
            ldb         #MenuValueX
            lda         #MenuRowSoundY
            ldu         ,s
            jsr         Gfx_DrawTextLine_Back
 IFNE MenuShowMusic
            * Draw music value
            ldx         #Menu_MusicYes
            tst         <Sound_OutputMode
            bmi         MusicMenuInitOff@       * no sound = no music
            tst         Menu_MusicEnabled
            bne         MusicMenuInitTextDone@
MusicMenuInitOff@
            clr         Menu_MusicEnabled
            ldx         #Menu_MusicNo
MusicMenuInitTextDone@
            ldb         #MenuValueX
            lda         #MenuRowMusicY
            puls        u
            jsr         Gfx_DrawTextLine_Back
 ELSE
            puls        u
 ENDC
            * clear front buffer and set the new palette
            clra
            jsr         Gfx_FillScreen_Front
            jsr         System_SetPaletteAuto
            * fade in to the menu
            lda         #1
            jsr         Img_FadeIn
MenuKeyLoop@
            jsr         Input_ScanKeyboardDebounced
            bcc         CheckJoyButton@
            ldy         #Input_KeyMatrixDB
            jsr         Input_FindPressedKeys
            lda         #KEY_M
            jsr         Input_IsKeyPressed
            tstb
            beq         >
            jsr         Menu_Keypress_M
 IFNE MenuShowControl
!           lda         #KEY_C
            jsr         Input_IsKeyPressed
            tstb
            beq         >
            jsr         Menu_Keypress_C
 ENDC
!           lda         #KEY_S
            jsr         Input_IsKeyPressed
            tstb
            beq         >
            jsr         Menu_Keypress_S
 IFNE MenuShowMusic
!           lda         #KEY_U
            jsr         Input_IsKeyPressed
            tstb
            beq         >
            jsr         Menu_Keypress_U
 ENDC
!           lda         #KEY_SPACE
            jsr         Input_IsKeyPressed
            tstb
            beq         >
            jmp         Menu_Keypress_Space     * this starts a level and doesn't return, so jump there
CheckJoyButton@
 IFNE MenuShowControl
            * read joystick button state
!           ldb         <Input_JoyButtonMask
            bitb        #Joy1Button1
            beq         >
            jmp         Menu_Keypress_Space     * this starts a level and doesn't return, so jump there
 ENDC
!           bra         MenuKeyLoop@

 IFNE MenuShowControl
Menu_Keypress_C
            * flip state of Controller option
            com         <Input_UseKeyboard
            * wait for next vertical retrace to start
            sync
            * erase box around option text
            ldb         #MenuValueX
            lda         #MenuRowControlY
            ldu         #8
            jsr         Menu_EraseBox
            * redraw new option value
            ldx         #Menu_Joystick
            tst         <Input_UseKeyboard
            beq         >
            ldx         #Menu_Keyboard
!           clra
            ldb         Gfx_PalIdx_FGColor
            andb        #$0f
            tfr         d,u
            ldb         #MenuValueX
            lda         #MenuRowControlY
            jsr         Gfx_DrawTextLine
            rts
 ENDC

Menu_Keypress_S
            * advance state of Sound option
            lda         <Sound_OutputMode
            inca
            cmpa        #2
            blt         >
            lda         #-1
!           sta         <Sound_OutputMode
            * wait for next vertical retrace to start
            sync
            * erase box around option text
            ldb         #MenuValueX
            lda         #MenuRowSoundY
            ldu         #13
            jsr         Menu_EraseBox
            * redraw new option value
            ldx         #Menu_NoSound
            tst         <Sound_OutputMode
            bmi         SoundMenuTextDone@
            bgt         >
            ldx         #Menu_Internal
            bra         SoundMenuTextDone@
!           ldx         #Menu_Orc90
SoundMenuTextDone@
            clra
            ldb         Gfx_PalIdx_FGColor
            andb        #$0f
            tfr         d,u
            ldb         #MenuValueX
            lda         #MenuRowSoundY
            jsr         Gfx_DrawTextLine
            * update audio hardware state if necessary
 IFEQ SOUND_METHOD-1
            tst         <Sound_OutputMode
            beq         >
            lda         #(PIA1B_Ctrl&$F7)       * set ORCC90/NoSound mode: disable audio on SC77526 chip
            sta         $FF23
            bra         AudioSwitchDone@
!           lda         #(PIA1B_Ctrl|$08)       * set DAC6 mod: enable audio on SC77526 chip
            sta         $FF23
            lda         #$82
            sta         $FF20                   * set DAC to mid-range, serial bit to 1
AudioSwitchDone@
 ENDC
            * If sound is off, force music off and redraw music row
            tst         <Sound_OutputMode
            bpl         >
            clr         Menu_MusicEnabled
            clr         Music_Playing
 IFNE MenuShowMusic
            jsr         Menu_RedrawMusic
 ENDC
!           rts

 IFNE MenuShowMusic
***********************************************************
* Menu_Keypress_U — toggle music on/off
***********************************************************
Menu_Keypress_U
            * If sound is off, music stays off
            tst         <Sound_OutputMode
            bmi         MusicToggleDone@
            * Toggle music ($FF <-> $00)
            com         Menu_MusicEnabled
            bne         MusicToggleRedraw@
            * Music just turned off — stop any playing music
            clr         Music_Playing
MusicToggleRedraw@
            jsr         Menu_RedrawMusic
MusicToggleDone@
            rts

***********************************************************
* Menu_RedrawMusic — redraw the music Yes/No value
***********************************************************
Menu_RedrawMusic
            sync
            ldb         #MenuValueX
            lda         #MenuRowMusicY
            ldu         #3
            jsr         Menu_EraseBox
            ldx         #Menu_MusicYes
            tst         Menu_MusicEnabled
            bne         >
            ldx         #Menu_MusicNo
!           clra
            ldb         Gfx_PalIdx_FGColor
            andb        #$0f
            tfr         d,u
            ldb         #MenuValueX
            lda         #MenuRowMusicY
            jsr         Gfx_DrawTextLine
            rts
 ENDC

Menu_Keypress_M
            * flip state of Monitor option
            com         <Gfx_MonitorIsRGB
            * wait for next vertical retrace to start
            sync
            * erase box around option text
            ldb         #MenuValueX
            lda         #MenuRowMonitorY
            ldu         #9
            jsr         Menu_EraseBox
            * redraw new option value
            ldx         #Menu_CMP
            tst         <Gfx_MonitorIsRGB
            beq         >
            ldx         #Menu_RGB
!           clra
            ldb         Gfx_PalIdx_FGColor
            andb        #$0f
            tfr         d,u
            ldb         #MenuValueX
            lda         #MenuRowMonitorY
            jsr         Gfx_DrawTextLine
            * set new palette
            jsr         System_SetPaletteAuto
            rts

Menu_Keypress_Space
            * fade out to background color (white)
            lda         #0
            jsr         Img_FadeOut
            * then set all palette entries to white
            lda         #63
            jsr         System_SetPaletteConst
            * mark the graphics aperature as free
            jsr         MemMgr_FreeGfxAperature
            * load and execute Level 1
            lda         #FirstLevel             * Load the first level defined by defaults-config
	    clr		UserGlobals_Init
            jmp         Ldr_Load_Level          * jump to loader (it does not return, but jumps to mainloop)


***********************************************************
* Menu_EraseBox:
*   This function writes the background color to a one-row block of text, erasing a text line
*
* - IN:      A=Y coordinate, B=X coordinate, U=Number of characters to erase horizontally
* - OUT:     N/A
* - Trashed: All
***********************************************************
*
Menu_EraseBox
            jsr         Gfx_GetPixelAddress_Front   * (A=page number, Y=offset)
            sta         $FFA2                   * map starting graphics pages to $4000-$7FFF
            inca
            sta         $FFA3
            leay        $4000,y                 * Y is destination pointer (upper-left corner)
            tfr         u,d
            lslb
            lslb                                * 4 bytes (8 pixels) per character
            stb         ClearLoopRow@+1
            ldx         #16                     * X is row counter
            ldb         Gfx_PalIdx_BKColor
ClearLoopRow@
            lda         #0                      * SMC: width of block to erase is store in code above
            pshs        y
ClearLoopCol@
            stb         ,y+
            deca
            bne         ClearLoopCol@
            puls        y
            leay        256,y
!           leax        -1,x
            bne         ClearLoopRow@
            rts

