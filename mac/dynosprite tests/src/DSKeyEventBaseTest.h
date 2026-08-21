//
//  DSKeyEventBaseTest.h
//  dynosprite tests
//
//  Created by Jamie Cho on 6/1/24.
//

#import <XCTest/XCTest.h>

@interface DSKeyEventBaseTest<T> : XCTestCase

@property T target;
- (NSSet <UIPress *> *)pressKey:(NSString *)unmodifiedChars modifiedChars:(NSString *)modifiedChars;
- (NSSet <UIPress *> *)unpressKey:(NSString *)unmodifiedChars modifiedChars:(NSString *)modifiedChars;

/* A modifier key reports no characters at all, only a HID key code, which is
 * the whole reason the scene has to translate them.  These press one. */
- (NSSet <UIPress *> *)pressKeyCode:(UIKeyboardHIDUsage)keyCode;
- (NSSet <UIPress *> *)unpressKeyCode:(UIKeyboardHIDUsage)keyCode;

@end
