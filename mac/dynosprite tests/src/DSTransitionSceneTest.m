//
//  DSTransitionSceneTest.m
//  DynospriteCoreTests
//
//  Created by Jamie Cho on 12/29/18.
//  Copyright © 2018 Jamie Cho. All rights reserved.
//

#import <OCMock/OCMock.h>
#import <XCTest/XCTest.h>

#import "DSCoCoJoystickController.h"
#import "DSTestUtils.h"
#import "DSTransitionScene.h"
#import "DSResourceController.h"
#import "DSSceneController.h"


@interface DSTransitionSceneTest : XCTestCase {
    DSTransitionScene *_target;
    DSCoCoJoystickController *_joystickController;
    DSResourceController *_resourceController;
    DSSceneController *_sceneController;
    DSSoundManager *_soundManager;
}
@end

@implementation DSTransitionSceneTest

- (void)setUp {
    _target = [[DSTransitionScene alloc] init];
    _joystickController = OCMClassMock(DSCoCoJoystickController.class);
    _resourceController = OCMClassMock(DSResourceController.class);
    _sceneController = OCMClassMock(DSSceneController.class);
    _soundManager = OCMClassMock(DSSoundManager.class);
    XCTAssertNil(_target.resourceController);
    XCTAssertNil(_target.joystickController);
    XCTAssertNil(_target.sceneController);
    XCTAssertNil(_target.soundManager);
    _target.resourceController = _resourceController;
    _target.sceneController = _sceneController;
    _target.soundManager = _soundManager;
}

- (void)testInit {
    XCTAssertEqualObjects(_target.backgroundColor, [UIColor colorWithRed:.15f green:.15f blue:.15f alpha:1]);
    XCTAssertEqualObjects(_target.foregroundColor, UIColor.blackColor);
    XCTAssertEqualObjects(_target.progressBarColor, UIColor.greenColor);
    XCTAssertTrue([_target.labels isKindOfClass:NSArray.class]);
    XCTAssertEqual(_target.labels.count, 0);
    XCTAssertNil(_target.backgroundImageName);
    XCTAssertEqual(_target.yScale, 1);
    XCTAssertEqualObjects(((SKSpriteNode *)(_target.children[0])).color, _target.backgroundColor);
    
    XCTAssertEqual(_target.resourceController, _resourceController);
    XCTAssertEqual(_target.sceneController, _sceneController);
}

/* The two halves of addLabelWithText:atPosition:withBackground: put the label
 * in different places in the node tree, so they need asserting separately.
 * With a plate the label sits at the origin of a sprite that carries the
 * position; without one the label is a child of the scene and carries the
 * position itself. */
- (void)testAddsLabelsWithBackground {
    OCMStub([_resourceController fontForDisplay]).andReturn(@"Courier");
    SKLabelNode *label = [_target addLabelWithText:@"Hello World" atPosition:CGPointMake(100, 50) withBackground:YES];
    XCTAssertEqualObjects(label.text, @"Hello World");
    XCTAssert(label.fontName, @"Courier");
    XCTAssertEqual(label.horizontalAlignmentMode, SKLabelHorizontalAlignmentModeLeft);
    XCTAssertEqual(label.verticalAlignmentMode, SKLabelVerticalAlignmentModeTop);
    XCTAssertTrue(CGPointEqualToPoint(label.position, CGPointMake(0, 0)));
    XCTAssertEqual(label.fontSize, 12);
    XCTAssertTrue([DSTestUtils color:label.fontColor isSameAs:_target.foregroundColor]);
    XCTAssertTrue([label.parent isKindOfClass:SKSpriteNode.class]);
    SKSpriteNode *background = (SKSpriteNode *)label.parent;
    XCTAssertEqualObjects(background.parent, _target);
    XCTAssertTrue([DSTestUtils color:background.color isSameAs:_target.backgroundColor]);
    XCTAssertEqual(_target.labels.count, 1);
    /* The plate is nudged down a tenth of the font size to sit on the row. */
    XCTAssertTrue(CGPointEqualToPoint(background.position, CGPointMake(100.0f, -51.2f)));
    XCTAssertTrue(CGPointEqualToPoint(background.anchorPoint, CGPointMake(0, 1)));
}

- (void)testAddsLabelsWithoutBackground {
    OCMStub([_resourceController fontForDisplay]).andReturn(@"Courier");
    SKLabelNode *label = [_target addLabelWithText:@"Hello World" atPosition:CGPointMake(100, 50) withBackground:NO];
    XCTAssertEqualObjects(label.text, @"Hello World");
    XCTAssert(label.fontName, @"Courier");
    XCTAssertEqual(label.horizontalAlignmentMode, SKLabelHorizontalAlignmentModeLeft);
    XCTAssertEqual(label.verticalAlignmentMode, SKLabelVerticalAlignmentModeTop);
    XCTAssertEqual(label.fontSize, 12);
    XCTAssertTrue([DSTestUtils color:label.fontColor isSameAs:_target.foregroundColor]);
    /* No plate at all -- the scene is the parent, and there is nothing behind
     * the text but the artwork. */
    XCTAssertEqualObjects(label.parent, _target);
    XCTAssertFalse([label.parent isKindOfClass:SKSpriteNode.class]);
    XCTAssertTrue(CGPointEqualToPoint(label.position, CGPointMake(100.0f, -50.0f)));
    XCTAssertEqual(_target.labels.count, 1);
    XCTAssertEqual(_target.labels[0], label);
}

/* Both kinds have to survive a resolution change, which walks every label and
 * repositions it from the point it was added at. */
- (void)testBothKindsOfLabelSurviveAFontChange {
    __block int calls = 0;
    /* __block so the block does not capture them const -- setReturnValue:
     * wants a plain pointer. */
    __block NSString *courier = @"Courier";
    __block NSString *monaco = @"Monaco";
    OCMStub([_resourceController fontForDisplay]).andDo(^(NSInvocation *invocation) {
        [invocation setReturnValue:(calls++ < 2) ? &courier : &monaco];
    });
    SKLabelNode *plated = [_target addLabelWithText:@"A" atPosition:CGPointMake(10, 20) withBackground:YES];
    SKLabelNode *bare = [_target addLabelWithText:@"B" atPosition:CGPointMake(30, 40) withBackground:NO];
    _target.resourceController = _resourceController;
    XCTAssertEqualObjects(plated.fontName, monaco);
    XCTAssertEqualObjects(bare.fontName, monaco);
    XCTAssertTrue(CGPointEqualToPoint(bare.position, CGPointMake(30.0f, -40.0f)));
}

- (void)testSetBackgroundImageName {
    NSString *backgroundImageName = @"forest";
    NSString *resourceImagePath = [[NSBundle bundleForClass:self.class] pathForResource:backgroundImageName ofType:@"png"];
    UIImage *image = [[UIImage alloc] initWithContentsOfFile:resourceImagePath];
    
    OCMStub([_resourceController imageWithName:backgroundImageName]).andReturn(resourceImagePath);
    _target.backgroundImageName = backgroundImageName;
    XCTAssertEqual(_target.backgroundImage, (SKSpriteNode *)(_target.children[0]));
    CGImageRef backgroundCGImage = ((SKSpriteNode *)(_target.children[0])).texture.CGImage;
    UIImage *backgroundImage = [DSTestUtils convertToUIImage:backgroundCGImage];
    XCTAssertTrue([DSTestUtils image:image isSameAsImage:backgroundImage]);
    XCTAssertEqual(_target.backgroundImageName, backgroundImageName);
}

- (void)testForegroundColor {
    OCMStub([_resourceController fontForDisplay]).andReturn(@"Courier");
    _target.foregroundColor = UIColor.purpleColor;
    [_target addLabelWithText:@"Test" atPosition:CGPointMake(100, 200) withBackground:NO];
    XCTAssertTrue([DSTestUtils color:_target.foregroundColor isSameAs:UIColor.purpleColor]);
    XCTAssertTrue([DSTestUtils color:_target.foregroundColor isSameAs:_target.labels[0].fontColor]);
    _target.foregroundColor = UIColor.brownColor;
    XCTAssertTrue([DSTestUtils color:_target.foregroundColor isSameAs:UIColor.brownColor]);
    XCTAssertTrue([DSTestUtils color:_target.foregroundColor isSameAs:_target.labels[0].fontColor]);
}

- (void)testBackgroundColor {
    OCMStub([_resourceController fontForDisplay]).andReturn(@"Courier");
    /* The plate is the thing under test here, so this one asks for one. */
    _target.backgroundColor = UIColor.purpleColor;
    [_target addLabelWithText:@"Test" atPosition:CGPointMake(100, 200) withBackground:YES];
    XCTAssertTrue([DSTestUtils color:_target.backgroundColor isSameAs:UIColor.purpleColor]);
    XCTAssertTrue([DSTestUtils color:_target.backgroundColor isSameAs:((SKSpriteNode *)(_target.labels[0].parent)).color]);
    _target.backgroundColor = UIColor.brownColor;
    XCTAssertTrue([DSTestUtils color:_target.backgroundColor isSameAs:UIColor.brownColor]);
    XCTAssertTrue([DSTestUtils color:_target.backgroundColor isSameAs:((SKSpriteNode *)(_target.labels[0].parent)).color]);
}

/* A label with no plate behind it has the scene for a parent, and SKScene has
 * no color property at all -- assigning one is an unrecognised selector, not a
 * quiet no-op.  Changing either colour after the menu had drawn itself used to
 * take the app down with it. */
- (void)testColourChangeWithNoBackground {
    OCMStub([_resourceController fontForDisplay]).andReturn(@"Courier");
    SKLabelNode *label = [_target addLabelWithText:@"Test"
                                        atPosition:CGPointMake(100, 200)
                                    withBackground:NO];
    XCTAssertFalse([label.parent isKindOfClass:SKSpriteNode.class]);
    _target.backgroundColor = UIColor.brownColor;
    _target.foregroundColor = UIColor.purpleColor;
    XCTAssertTrue([DSTestUtils color:label.fontColor isSameAs:UIColor.purpleColor]);
}

- (void)testLabels {
    OCMStub([_resourceController fontForDisplay]).andReturn(@"Courier");
    SKLabelNode *label1 = [_target addLabelWithText:@"Test1" atPosition:CGPointMake(100, 200) withBackground:NO];
    SKLabelNode *label2 = [_target addLabelWithText:@"Test2" atPosition:CGPointMake(100, 200) withBackground:NO];
    XCTAssertEqual(_target.labels.count, 2);
    XCTAssertEqual(_target.labels[0], label1);
    XCTAssertEqual(_target.labels[1], label2);
}

- (void)testUpdatingResourceControllerUpdatesGetter {
    id newResourceController = OCMClassMock(DSResourceController.class);
    _target.resourceController = newResourceController;
    XCTAssertEqual(_target.resourceController, newResourceController);
}

- (void)testUpdatingResourceControllerUpdatesObservers {
    id newResourceController = OCMClassMock(DSResourceController.class);
    _target.resourceController = newResourceController;
    OCMVerify([_resourceController removeObserver:_target forKeyPath:@"hiresMode"]);
    OCMVerify([newResourceController addObserver:_target forKeyPath:@"hiresMode" options:NSKeyValueObservingOptionNew | NSKeyValueObservingOptionOld context:nil]);
}

- (void)testUpdatingResourceControllerUpdatesDisplay {
    // Setup a basic display
    OCMStub([_resourceController fontForDisplay]).andReturn(@"Courier");
    _target.foregroundColor = UIColor.purpleColor;
    SKLabelNode *label = [_target addLabelWithText:@"Test" atPosition:CGPointMake(100, 200) withBackground:NO];
    NSString *backgroundImageName = @"forest";
    NSString *resourceImagePath = [[NSBundle bundleForClass:self.class] pathForResource:backgroundImageName ofType:@"png"];
    OCMStub([_resourceController imageWithName:backgroundImageName]).andReturn(resourceImagePath);
    _target.backgroundImageName = backgroundImageName;

    // Update the resource controller
    id newResourceController = OCMClassMock(DSResourceController.class);
    NSString *hiresBackgroundImageName = @"forest-hires";
    OCMStub([newResourceController fontForDisplay]).andReturn(@"Monaco");
    NSString *hiresResourceImagePath = [[NSBundle bundleForClass:self.class] pathForResource:hiresBackgroundImageName ofType:@"png"];
    OCMStub([newResourceController imageWithName:backgroundImageName]).andReturn(hiresResourceImagePath);
    _target.resourceController = newResourceController;
    
    // Verify that the background was updated
    CGImageRef hiresBackgroundCGImage = ((SKSpriteNode *)(_target.children[0])).texture.CGImage;
    UIImage *hiresBackgroundImage = [DSTestUtils convertToUIImage:hiresBackgroundCGImage];
    UIImage *hiresImage = [[UIImage alloc] initWithContentsOfFile:hiresResourceImagePath];
    XCTAssertTrue([DSTestUtils image:hiresImage isSameAsImage:hiresBackgroundImage]);
    
    // Verify that the font was updated
    XCTAssertEqual(label.fontSize, 12);

    XCTAssert(label.fontName, @"Monaco");
    /* This label was added without a plate, so it carries its own position and
     * misses the tenth-of-a-font-size nudge a plate gets.  Reading the parent
     * here would read the scene, which sits at the origin. */
    XCTAssertTrue(CGPointEqualToPoint(label.position, CGPointMake(100.0f, -200.0f)));
}

- (void)testResourceControllerUpdatingHiresModeUpdatesDisplay {
    __block int numFontForDisplayCalls = 0;
    __block NSString *courierFont = @"Courier";
    __block NSString *monacoFont = @"Monaco";
    // Setup a basic display
    OCMStub([_resourceController fontForDisplay]).andDo(^(NSInvocation *invocation) {
        [invocation setReturnValue:(numFontForDisplayCalls++ < 1) ? &courierFont : &monacoFont];
    });
    _target.foregroundColor = UIColor.purpleColor;
    SKLabelNode *label = [_target addLabelWithText:@"Test" atPosition:CGPointMake(100, 200) withBackground:NO];
    NSString *backgroundImageName = @"forest";
    NSString *resourceImagePath = [[NSBundle bundleForClass:self.class] pathForResource:backgroundImageName ofType:@"png"];
    OCMStub([_resourceController imageWithName:backgroundImageName]).andReturn(resourceImagePath);
    _target.backgroundImageName = backgroundImageName;

    // Fake a change to hiresMode
    OCMStub([_resourceController fontForDisplay]).andReturn(@"Monaco");
    NSString *hiresBackgroundImageName = @"forest-hires";
    NSString *hiresResourceImagePath = [[NSBundle bundleForClass:self.class] pathForResource:hiresBackgroundImageName ofType:@"png"];
    OCMStub([_resourceController imageWithName:backgroundImageName]).andReturn(hiresResourceImagePath);
    _resourceController.hiresMode = YES;
    [_target observeValueForKeyPath:@"hiresMode" ofObject:_resourceController change:nil context:nil];

    // Verify that the font was updated
    XCTAssertEqual(label.fontSize, 12);

    XCTAssert(label.fontName, @"Monaco");
    /* This label was added without a plate, so it carries its own position and
     * misses the tenth-of-a-font-size nudge a plate gets.  Reading the parent
     * here would read the scene, which sits at the origin. */
    XCTAssertTrue(CGPointEqualToPoint(label.position, CGPointMake(100.0f, -200.0f)));
}

@end
