//
//  DSSceneTest.m
//  DynospriteCoreTests
//
//  Created by Jamie Cho on 5/7/20.
//  Copyright © 2020 Jamie Cho. All rights reserved.
//

#import <OCMock/OCMock.h>
#import "DSKeyEventBaseTest.h"
#import "DSScene.h"

@interface DSSceneTest : DSKeyEventBaseTest<DSScene *> {
    DSCoCoJoystickController *_joystickController;
}

@end

@implementation DSSceneTest

- (void)setUp {
    self.target = [[DSScene alloc] init];
    XCTAssertNil(self.target.joystickController);
    _joystickController = OCMClassMock(DSCoCoJoystickController.class);
    self.target.joystickController = _joystickController;
    XCTAssertEqual(self.target.levelNumber, 0);
    XCTAssertFalse(self.target.isDone);
}

- (void)testInit {
    XCTAssertTrue(CGSizeEqualToSize(self.target.size, CGSizeMake(320, 200)));
    XCTAssertTrue(CGPointEqualToPoint(self.target.anchorPoint, CGPointMake(0, 1)));
    XCTAssertEqual(self.target.scaleMode, SKSceneScaleModeAspectFit);

    XCTAssertEqual(self.target.debouncedKeys[0], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[1], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[2], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[3], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[4], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[5], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[6], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[7], 0xff);
    
    [self.target updateDebouncedKeys];
    XCTAssertEqual(self.target.debouncedKeys[0], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[1], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[2], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[3], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[4], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[5], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[6], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[7], 0xff);
}

- (void)testIsDone {
    self.target.isDone = NO;
    XCTAssertFalse(self.target.isDone);
    self.target.isDone = YES;
    XCTAssertTrue(self.target.isDone);
}

- (void)testSetJoystickControler {
    XCTAssertEqualObjects(self.target.joystickController, _joystickController);
}

- (void)testLevelNumber {
    self.target.levelNumber = 4;
    XCTAssertEqual(self.target.levelNumber, 4);
}

- (void)testKeyDown {
    NSSet<UIPress *> *presses1 = [self pressKey:@"p" modifiedChars:@""];
    OCMVerify([_joystickController pressesBegan:presses1 withEvent:OCMArg.any]);
    NSSet<UIPress *> *presses2 = [self pressKey:@"p" modifiedChars:@""];
    OCMVerify([_joystickController pressesBegan:presses2 withEvent:OCMArg.any]);
}

- (void)testKeyUp {
    NSSet<UIPress *> *presses1 = [self unpressKey:@"p" modifiedChars:@""];
    OCMVerify([_joystickController pressesEnded:presses1 withEvent:OCMArg.any]);
    NSSet<UIPress *> *presses2 = [self unpressKey:@"p" modifiedChars:@""];
    OCMVerify([_joystickController pressesEnded:presses2 withEvent:OCMArg.any]);
}

- (void)testUpdatesKeyMatrix {
    // Test p
    [self pressKey:@"p" modifiedChars:@""];
    XCTAssertEqual(self.target.debouncedKeys[0], 0xff & ~0x04);
    [self unpressKey:@"p" modifiedChars:@""];
    XCTAssertEqual(self.target.debouncedKeys[0], 0xff);

    // Test esc
    [self pressKey:UIKeyInputEscape modifiedChars:@""];
    XCTAssertEqual(self.target.debouncedKeys[2], 0xff & ~0x40);
    [self unpressKey:UIKeyInputEscape modifiedChars:@""];
    XCTAssertEqual(self.target.debouncedKeys[2], 0xff);

    // y
    [self pressKey:@"y" modifiedChars:@""];
    XCTAssertEqual(self.target.debouncedKeys[1], 0xff & ~0x08);
    [self unpressKey:@"y" modifiedChars:@""];
    XCTAssertEqual(self.target.debouncedKeys[1], 0xff);

    // n
    [self pressKey:@"n" modifiedChars:@""];
    XCTAssertEqual(self.target.debouncedKeys[6], 0xff & ~0x02);
    [self unpressKey:@"n" modifiedChars:@""];
    XCTAssertEqual(self.target.debouncedKeys[6], 0xff);

    // p esc yn
    [self pressKey:@"p" modifiedChars:@""];
    [self pressKey:UIKeyInputEscape modifiedChars:@""];
    [self pressKey:@"y" modifiedChars:@""];
    [self pressKey:@"n" modifiedChars:@""];
    XCTAssertEqual(self.target.debouncedKeys[0], 0xff & ~0x04);
    XCTAssertEqual(self.target.debouncedKeys[2], 0xff & ~0x40);
    XCTAssertEqual(self.target.debouncedKeys[1], 0xff & ~0x08);
    XCTAssertEqual(self.target.debouncedKeys[6], 0xff & ~0x02);
    [self unpressKey:@"p" modifiedChars:@""];
    [self unpressKey:UIKeyInputEscape modifiedChars:@""];
    [self unpressKey:@"y" modifiedChars:@""];
    [self unpressKey:@"n" modifiedChars:@""];
    XCTAssertEqual(self.target.debouncedKeys[0], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[2], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[1], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[6], 0xff);
}

/* The keys this game is actually played with, and the ones that are hardest
 * to get right: none of them arrive as a character.  A modifier press reports
 * an empty charactersIgnoringModifiers and nothing but a HID key code, and
 * RETURN reports \r rather than \n.  Getting either wrong leaves the build
 * looking perfectly healthy and unplayable -- no flippers, no plunger.
 *
 * Column and bit here are the CoCo matrix positions keyDown() decodes from the
 * KEY_* codes in engine/constants.asm: CTRL is 0x64, SHIFT 0x67, ENTER 0x60. */
- (void)testControlUpdatesKeyMatrix {
    [self pressKeyCode:UIKeyboardHIDUsageKeyboardLeftControl];
    XCTAssertEqual(self.target.debouncedKeys[4], 0xff & ~0x40);
    [self unpressKeyCode:UIKeyboardHIDUsageKeyboardLeftControl];
    XCTAssertEqual(self.target.debouncedKeys[4], 0xff);

    [self pressKeyCode:UIKeyboardHIDUsageKeyboardRightControl];
    XCTAssertEqual(self.target.debouncedKeys[4], 0xff & ~0x40);
    [self unpressKeyCode:UIKeyboardHIDUsageKeyboardRightControl];
    XCTAssertEqual(self.target.debouncedKeys[4], 0xff);
}

- (void)testShiftUpdatesKeyMatrix {
    [self pressKeyCode:UIKeyboardHIDUsageKeyboardLeftShift];
    XCTAssertEqual(self.target.debouncedKeys[7], 0xff & ~0x40);
    [self unpressKeyCode:UIKeyboardHIDUsageKeyboardLeftShift];
    XCTAssertEqual(self.target.debouncedKeys[7], 0xff);

    [self pressKeyCode:UIKeyboardHIDUsageKeyboardRightShift];
    XCTAssertEqual(self.target.debouncedKeys[7], 0xff & ~0x40);
    [self unpressKeyCode:UIKeyboardHIDUsageKeyboardRightShift];
    XCTAssertEqual(self.target.debouncedKeys[7], 0xff);
}

- (void)testAltUpdatesKeyMatrix {
    [self pressKeyCode:UIKeyboardHIDUsageKeyboardLeftAlt];
    XCTAssertEqual(self.target.debouncedKeys[3], 0xff & ~0x40);
    [self unpressKeyCode:UIKeyboardHIDUsageKeyboardLeftAlt];
    XCTAssertEqual(self.target.debouncedKeys[3], 0xff);
}

/* ALT and CONTROL are different keys on different rows.  They shared a
 * dictionary entry once -- the literal named UIKeyInputF3 twice -- and a
 * repeated key is silently dropped, taking CONTROL with it. */
- (void)testAltAndControlAreSeparateKeys {
    [self pressKeyCode:UIKeyboardHIDUsageKeyboardLeftAlt];
    XCTAssertEqual(self.target.debouncedKeys[3], 0xff & ~0x40);
    XCTAssertEqual(self.target.debouncedKeys[4], 0xff);
    [self unpressKeyCode:UIKeyboardHIDUsageKeyboardLeftAlt];

    [self pressKeyCode:UIKeyboardHIDUsageKeyboardLeftControl];
    XCTAssertEqual(self.target.debouncedKeys[3], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[4], 0xff & ~0x40);
    [self unpressKeyCode:UIKeyboardHIDUsageKeyboardLeftControl];
}

/* Both flippers at once is the whole reason this game reads the matrix
 * instead of the joystick, so it had better work. */
- (void)testBothFlippersAtOnce {
    [self pressKeyCode:UIKeyboardHIDUsageKeyboardLeftControl];
    [self pressKeyCode:UIKeyboardHIDUsageKeyboardLeftShift];
    XCTAssertEqual(self.target.debouncedKeys[4], 0xff & ~0x40);
    XCTAssertEqual(self.target.debouncedKeys[7], 0xff & ~0x40);
    [self unpressKeyCode:UIKeyboardHIDUsageKeyboardLeftControl];
    XCTAssertEqual(self.target.debouncedKeys[4], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[7], 0xff & ~0x40);
    [self unpressKeyCode:UIKeyboardHIDUsageKeyboardLeftShift];
    XCTAssertEqual(self.target.debouncedKeys[7], 0xff);
}

/* RETURN launches the ball.  UIKit reports it as a carriage return. */
- (void)testReturnUpdatesKeyMatrix {
    [self pressKey:@"\r" modifiedChars:@""];
    XCTAssertEqual(self.target.debouncedKeys[0], 0xff & ~0x40);
    [self unpressKey:@"\r" modifiedChars:@""];
    XCTAssertEqual(self.target.debouncedKeys[0], 0xff);
}

/* SPACE starts the game, and is also the emulated joystick's button 0. */
- (void)testSpaceUpdatesKeyMatrix {
    [self pressKey:@" " modifiedChars:@""];
    XCTAssertEqual(self.target.debouncedKeys[7], 0xff & ~0x08);
    [self unpressKey:@" " modifiedChars:@""];
    XCTAssertEqual(self.target.debouncedKeys[7], 0xff);
}

/* A modifier this game does not use must not land on some other key's cell. */
- (void)testUnmappedModifierChangesNothing {
    [self pressKeyCode:UIKeyboardHIDUsageKeyboardLeftGUI];
    for (int ii = 0; ii < 8; ii++) {
        XCTAssertEqual(self.target.debouncedKeys[ii], 0xff);
    }
    [self unpressKeyCode:UIKeyboardHIDUsageKeyboardLeftGUI];
}

#ifdef __TODO__

- (void)testClearsMatrixWhenMovedFromView {
    NSEvent *keyEvent = [NSEvent keyEventWithType:NSEventTypeKeyUp location:CGPointMake(0, 0) modifierFlags:NSEventModifierFlagCapsLock timestamp:[NSDate date].timeIntervalSince1970 windowNumber:0 context:nil characters:@"" charactersIgnoringModifiers:@"p\x1byn" isARepeat:NO keyCode:0];
    [self.target keyDown:keyEvent];
    [self.target willMoveFromView:[[SKView alloc] init]];
    XCTAssertEqual(self.target.debouncedKeys[0], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[2], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[1], 0xff);
    XCTAssertEqual(self.target.debouncedKeys[6], 0xff);
}
#endif
@end
