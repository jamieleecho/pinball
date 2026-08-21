//
//  InitScene.h
//  dynosprite
//
//  Created by Jamie Cho on 1/6/19.
//  Copyright © 2019 Jamie Cho. All rights reserved.
//

#import "DSTransitionScene.h"
#import "DSSceneControllerProtocol.h"

NS_ASSUME_NONNULL_BEGIN

/* Which rows the menu offers.  Set either to 1 to put its row back.
 *
 * These mirror MenuShowControl and MenuShowMusic in engine/menu.asm, and must
 * be kept in step with them: the black box the rows sit on is painted into
 * art/boxart.jpg by scripts/gen-assets.py, which sizes it from the same row
 * count, so a row hidden on one side and shown on the other lands off the box.
 *
 * A row that can only be left at the one setting that works is worse than no
 * row at all, and this game has two of those.  It reads the key matrix itself
 * because the joystick cannot report two keys at once and a pinball table
 * needs both flippers; and it ships no music.
 */
#define MenuShowControl 0
#define MenuShowMusic   0

/* Laid out from the row count rather than written down, so a hidden row
 * closes its gap and what is left stays centred on the same part of the
 * splash.  The scene is 320x200 and the font advances 8 points a character.
 */
#define MenuRowDY       16
#define MenuNumRows     (2 + MenuShowControl + MenuShowMusic)
#define MenuRowDisplayY (107 + (4 - MenuNumRows) * MenuRowDY / 2)
#define MenuRowControlY (MenuRowDisplayY + MenuRowDY)
#define MenuRowSoundY   (MenuRowControlY + MenuShowControl * MenuRowDY)
#define MenuRowMusicY   (MenuRowSoundY + MenuRowDY)
#define MenuLabelX      62
#define MenuValueX      152
#define MenuStartY      182
#define MenuStartX(n)   ((320 - (n) * 8) / 2)

typedef enum DSInitSceneDisplay {
    DSInitSceneDisplayLow,
    DSInitSceneDisplayHigh
} DSInitSceneDisplay;

typedef enum DSInitSceneControl {
    DSInitSceneControlKeyboard,
    DSInitSceneControlJoystick
} DSInitSceneControl;

typedef enum DSInitSceneSound {
    DSInitSceneSoundNone = -1,
    DSInitSceneSoundLow,
    DSInitSceneSoundHigh
} DSInitSceneSound;

@interface DSInitScene : DSTransitionScene {
    SKLabelNode *_resolutionLabelNode;
    SKLabelNode *_controlLabelNode;
    SKLabelNode *_soundLabelNode;
    SKLabelNode *_musicLabelNode;

    DSInitSceneDisplay _resolution;
    DSInitSceneControl _control;
    DSInitSceneSound _sound;
    bool _musicEnabled;
    
    bool _alwaysPressed;
    bool _isTransitioning;
}
+ (NSString *)textFromResolution:(DSInitSceneDisplay)resolution;
+ (NSString *)textFromControl:(DSInitSceneControl)control;
+ (NSString *)textFromSound:(DSInitSceneSound)sound;

@property (nonatomic) NSInteger firstLevel;

- (void)didMoveToView:(SKView *)view;
- (void)willMoveFromView:(SKView *)view;

- (void)pressesEnded:(NSSet<UIPress *> *)presses withEvent:(nullable UIPressesEvent *)event;

- (void)transitionToNextScreen;

- (void)toggleDisplay;
- (DSInitSceneDisplay)display;

- (void)toggleControl;
- (DSInitSceneControl)control;

- (void)toggleSound;
- (DSInitSceneSound)sound;

- (void)toggleMusic;
- (bool)musicEnabled;

- (void)poll;

@end

NS_ASSUME_NONNULL_END
