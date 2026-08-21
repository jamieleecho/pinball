//
//  InitScene.m
//  dynosprite
//
//  Created by Jamie Cho on 1/6/19.
//  Copyright © 2019 Jamie Cho. All rights reserved.
//

#import "DSInitScene.h"



static NSString *MenuControlJoystick = @"Joystick";
static NSString *MenuControlKeyboard = @"Keyboard";
static NSString *MenuDisplayHigh = @"High";
static NSString *MenuDisplayLow = @"Low";
static NSString *MenuSoundNone = @"No Sound";
static NSString *MenuSoundLow = @"LoFi";
static NSString *MenuSoundHigh = @"HiFi";


@implementation DSInitScene {
}

+ (NSString *)textFromResolution:(DSInitSceneDisplay)resolution {
    return resolution == DSInitSceneDisplayHigh ? MenuDisplayHigh : MenuDisplayLow;
}

+ (NSString *)textFromControl:(DSInitSceneControl)control {
    return control == DSInitSceneControlJoystick ? MenuControlJoystick : MenuControlKeyboard;
}

+ (NSString *)textFromSound:(DSInitSceneSound)sound {
    return sound == DSInitSceneSoundHigh ? MenuSoundHigh : (sound == DSInitSceneSoundNone ? MenuSoundNone : MenuSoundLow);
}

- (id)init {
    if (self = [super init]) {
        self.firstLevel = 1;
    }
    return self;
}

- (void)didMoveToView:(SKView *)view {
    [super didMoveToView:view];
    _alwaysPressed = YES;
    _isTransitioning = NO;
    self.isDone = NO;
    if (self.labels.count < 1) {
        [self addLabelWithText:@"[D]isplay:" atPosition:CGPointMake(MenuLabelX, MenuRowDisplayY)];
        _resolutionLabelNode = [self addLabelWithText:@"" atPosition:CGPointMake(MenuValueX, MenuRowDisplayY)];
#if MenuShowControl
        [self addLabelWithText:@"[C]ontrol:" atPosition:CGPointMake(MenuLabelX, MenuRowControlY)];
        _controlLabelNode = [self addLabelWithText:@"" atPosition:CGPointMake(MenuValueX, MenuRowControlY)];
#endif
        [self addLabelWithText:@"[S]ound:" atPosition:CGPointMake(MenuLabelX, MenuRowSoundY)];
        _soundLabelNode = [self addLabelWithText:@"" atPosition:CGPointMake(MenuValueX, MenuRowSoundY)];
#if MenuShowMusic
        [self addLabelWithText:@"M[u]sic:" atPosition:CGPointMake(MenuLabelX, MenuRowMusicY)];
        _musicLabelNode = [self addLabelWithText:@"" atPosition:CGPointMake(MenuValueX, MenuRowMusicY)];
#endif
#if MenuShowControl
        [self addLabelWithText:@"[Space] or joystick button to start" atPosition:CGPointMake(MenuStartX(35), MenuStartY)];
#else
        [self addLabelWithText:@"[Space] to start" atPosition:CGPointMake(MenuStartX(16), MenuStartY)];
#endif

        _resolution = self.resourceController.hiresMode ? DSInitSceneDisplayHigh : DSInitSceneDisplayLow;
#if MenuShowControl
        _control = self.joystickController.useHardwareJoystick ? DSInitSceneControlJoystick : DSInitSceneControlKeyboard;
#else
        /* No Control row, so the keyboard it is -- which is also what makes
         * SPACE start the game, as that is the emulated joystick's button 0. */
        _control = DSInitSceneControlKeyboard;
#endif
        _sound = self.soundManager.enabled ? (self.resourceController.hifiMode ? DSInitSceneSoundHigh : DSInitSceneSoundLow) : DSInitSceneSoundNone;
#if MenuShowMusic
        _musicEnabled = MusicGetEnabled() ? YES : NO;
#else
        _musicEnabled = NO;      /* no Music row: music never comes on */
#endif
    }

    [self refreshState];
}

- (void)willMoveFromView:(SKView *)view {
    [super willMoveFromView:view];
    [self refreshState];
}

- (void)pressesEnded:(NSSet<UIPress *> *)presses withEvent:(UIPressesEvent *)event {
    [self.joystickController pressesEnded:presses withEvent:event];
    NSMutableString *chars = [[NSMutableString alloc] init];
    for(UIPress *press in presses) {
        [chars appendString:press.key.charactersIgnoringModifiers];
    }

    // Now check the rest of the keyboard
    for (int s = 0; s < chars.length; s++) {
        unichar character = [chars characterAtIndex:s];
        switch (character) {
            case 'd':
                [self toggleDisplay];
                break;

#if MenuShowControl
            case 'c':
                [self toggleControl];
                break;
#endif

            case 's':
                [self toggleSound];
                break;

#if MenuShowMusic
            case 'u':
                [self toggleMusic];
                break;
#endif

            case ' ':
                break;
        }
    }

}

- (void)transitionToNextScreen {
    _isTransitioning = YES;
    MusicSetEnabled(_musicEnabled ? 1 : 0);
    [self.soundManager loadCache];
    [self.spriteObjectClassFactory loadCache];
    self.soundManager.maxNumSounds = (self.resourceController.hifiMode) ? 10 : 2;
    DynospriteGlobalsPtr->UserGlobals_Init = NO;
    self.isDone = YES;
    DSTransitionScene *transitionScene = [self.sceneController transitionSceneForLevel:(int)self.firstLevel];
    SKTransition *transition = [SKTransition doorwayWithDuration:1.0];
    [self.view presentScene:transitionScene transition:transition];
}

- (void)toggleDisplay {
    _resolution = (_resolution >= DSInitSceneDisplayHigh) ? DSInitSceneDisplayLow : _resolution + 1;
    [self refreshState];
}

- (DSInitSceneDisplay)display {
    return _resolution;
}

- (void)toggleControl {
    _control = (_control >= DSInitSceneControlJoystick) ? DSInitSceneControlKeyboard : _control + 1;
    [self refreshState];
}

- (DSInitSceneControl)control {
    return _control;
}

- (void)toggleSound {
    _sound = (_sound >= DSInitSceneSoundHigh) ? DSInitSceneSoundNone : _sound + 1;
    if (_sound == DSInitSceneSoundNone) {
        _musicEnabled = NO;
    }
    [self refreshState];
}

- (DSInitSceneSound)sound {
    return _sound;
}

- (void)toggleMusic {
    if (_sound == DSInitSceneSoundNone) return;  /* no toggle when sound is off */
    _musicEnabled = !_musicEnabled;
    [self refreshState];
}

- (bool)musicEnabled {
    return _musicEnabled;
}

- (void)poll {
    if (self.joystickController.joystick.button0Pressed) {
        if (!_alwaysPressed && !_isTransitioning && !self.isDone) {
            [self transitionToNextScreen];
        }
    } else {
        _alwaysPressed = NO;
    }
}

- (void)refreshState {
    _resolutionLabelNode.text = [DSInitScene textFromResolution:_resolution];
#if MenuShowControl
    _controlLabelNode.text = [DSInitScene textFromControl:_control];
#endif
    _soundLabelNode.text = [DSInitScene textFromSound:_sound];
#if MenuShowMusic
    _musicLabelNode.text = _musicEnabled ? @"Yes" : @"No";
#endif

    self.joystickController.useHardwareJoystick = (_control == DSInitSceneControlJoystick);
    self.soundManager.enabled = (_sound != DSInitSceneSoundNone);
    self.resourceController.hifiMode = (_sound == DSInitSceneSoundHigh);
    self.resourceController.hiresMode = (_resolution == DSInitSceneDisplayHigh);
}

@end
