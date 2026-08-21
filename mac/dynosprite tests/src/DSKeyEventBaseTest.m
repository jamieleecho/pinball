//
//  DSKeyEventBaseTest.m
//  dynosprite tests
//
//  Created by Jamie Cho on 6/1/24.
//

#import <OCMock/OCMock.h>
#import "DSKeyEventBaseTest.h"


@implementation DSKeyEventBaseTest

- (NSSet <UIPress *> *)keyCodePresses:(UIKeyboardHIDUsage)keyCode {
    NSMutableSet<UIPress *> *presses = [[NSMutableSet alloc] init];
    id press = OCMClassMock(UIPress.class);
    id key = OCMClassMock(UIKey.class);
    [presses addObject:press];
    OCMStub([(UIPress *)press key]).andReturn(key);
    OCMStub([key charactersIgnoringModifiers]).andReturn(@"");
    OCMStub([key characters]).andReturn(@"");
    OCMStub([key keyCode]).andReturn(keyCode);
    return presses;
}

- (NSSet <UIPress *> *)pressKeyCode:(UIKeyboardHIDUsage)keyCode {
    NSSet<UIPress *> *presses = [self keyCodePresses:keyCode];
    [self.target pressesBegan:presses withEvent:[[UIPressesEvent alloc] init]];
    return presses;
}

- (NSSet <UIPress *> *)unpressKeyCode:(UIKeyboardHIDUsage)keyCode {
    NSSet<UIPress *> *presses = [self keyCodePresses:keyCode];
    [self.target pressesEnded:presses withEvent:[[UIPressesEvent alloc] init]];
    return presses;
}

- (NSSet <UIPress *> *)pressKey:(NSString *)unmodifiedChars modifiedChars:(NSString *)modifiedChars {
    UIPressesEvent *event = [[UIPressesEvent alloc] init];
    NSMutableSet<UIPress *> *presses = [[NSMutableSet alloc] init];
    id press = OCMClassMock(UIPress.class);
    id key = OCMClassMock(UIKey.class);
    [presses addObject:press];
    OCMStub([(UIPress *)press key]).andReturn(key);
    OCMStub([key charactersIgnoringModifiers]).andReturn(unmodifiedChars);
    OCMStub([key characters]).andReturn(modifiedChars);
    [self.target pressesBegan:presses withEvent:event];
    return presses;
}

- (NSSet <UIPress *> *)unpressKey:(NSString *)unmodifiedChars modifiedChars:(NSString *)modifiedChars {
    UIPressesEvent *event = [[UIPressesEvent alloc] init];
    NSMutableSet<UIPress *> *presses = [[NSMutableSet alloc] init];
    id press = OCMClassMock(UIPress.class);
    id key = OCMClassMock(UIKey.class);
    [presses addObject:press];
    OCMStub([(UIPress *)press key]).andReturn(key);
    OCMStub([key charactersIgnoringModifiers]).andReturn(unmodifiedChars);
    OCMStub([key characters]).andReturn(modifiedChars);
    [self.target pressesEnded:presses withEvent:event];
    return presses;
}

@end
