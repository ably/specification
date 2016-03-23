//
//  ARTRealtimeInitTets.m
//  ably-ios
//
//  Created by vic on 16/03/2015.
//  Copyright (c) 2015 Ably. All rights reserved.
//
#import <UIKit/UIKit.h>
#import <XCTest/XCTest.h>
#import "ARTMessage.h"
#import "ARTClientOptions.h"
#import "ARTPresenceMessage.h"

#import "ARTRealtime.h"
#import "ARTTestUtil.h"
#import "ARTClientOptions.h"
#import "ARTLog.h"
#import "ARTEventEmitter.h"
#import "ARTAuth.h"
#import "ARTRealtime+Private.h"
#import "ARTDefault.h"

@interface ARTRealtimeInitTest : XCTestCase {
    ARTRealtime *_realtime;
}
@end

@implementation ARTRealtimeInitTest

- (void)tearDown {
    if (_realtime) {
        [ARTTestUtil removeAllChannels:_realtime];
        [_realtime resetEventEmitter];
        [_realtime close];
    }
    _realtime = nil;
    [super tearDown];
}

- (void)getBaseOptions:(void (^)(ARTClientOptions *options)) cb {
    [ARTTestUtil setupApp:[ARTTestUtil clientOptions] withDebug:NO callback:cb];
}

- (void)testInitWithOptions {
    __weak XCTestExpectation *expectation = [self expectationWithDescription:@"initWithOptions"];
    [ARTTestUtil testRealtime:^(ARTRealtime *realtime) {
        _realtime = realtime;
        [realtime.connection on:^(ARTConnectionStateChange *stateChange) {
            ARTRealtimeConnectionState state = stateChange.current;
            if(state == ARTRealtimeConnected) {
                [expectation fulfill];
            }
            else {
                XCTAssertEqual(state, ARTRealtimeConnecting);
            }
        }];
    }];
    [self waitForExpectationsWithTimeout:[ARTTestUtil timeout] handler:nil];
}

- (void)testInitWithHost {
    __weak XCTestExpectation *expectation = [self expectationWithDescription:@"testInitWithHost"];
    [self getBaseOptions:^(ARTClientOptions *options) {
        options.environment = @"test";
        ARTRealtime *realtime = [[ARTRealtime alloc] initWithOptions:options];
        _realtime = realtime;
        [realtime.connection on:^(ARTConnectionStateChange *stateChange) {
            ARTRealtimeConnectionState state = stateChange.current;
            if(state == ARTRealtimeFailed) {
                [expectation fulfill];
            }
            else {
                XCTAssertEqual(state, ARTRealtimeConnecting);
            }
        }];
    }];
    [self waitForExpectationsWithTimeout:[ARTTestUtil timeout] handler:nil];
}

- (void)testInitWithPort {
    __weak XCTestExpectation *expectation = [self expectationWithDescription:@"testInitWithPort"];
    [self getBaseOptions:^(ARTClientOptions *options) {
        options.tlsPort = 9998;
        ARTRealtime *realtime = [[ARTRealtime alloc] initWithOptions:options];
        _realtime = realtime;
        [realtime.connection on:^(ARTConnectionStateChange *stateChange) {
            ARTRealtimeConnectionState state = stateChange.current;
            if(state == ARTRealtimeFailed) {
                [expectation fulfill];
            }
            else {
                XCTAssertEqual(state, ARTRealtimeConnecting);
            }
        }];
    }];
    [self waitForExpectationsWithTimeout:[ARTTestUtil timeout]+[ARTDefault connectTimeout] handler:nil];
}

- (void)testInitWithKey {
    __weak XCTestExpectation *expectation = [self expectationWithDescription:@"testInitWithKey"];
    [self getBaseOptions:^(ARTClientOptions *options) {
        _realtime = [[ARTRealtime alloc] initWithKey:options.key];
        if (_realtime.connection.state == ARTRealtimeConnecting) {
            XCTAssertEqual(_realtime.auth.options.key, options.key);
            [expectation fulfill];
        }
    }];
    [self waitForExpectationsWithTimeout:[ARTTestUtil timeout] handler:nil];
}

- (void)testInitAutoConnectDefault {
    __weak XCTestExpectation *expectation = [self expectationWithDescription:@"testInitAutoConnectDefault"];
    [ARTTestUtil testRealtime:^(ARTRealtime *realtime) {
        _realtime = realtime;
        [realtime.connection on:^(ARTConnectionStateChange *stateChange) {
            ARTRealtimeConnectionState state = stateChange.current;
            if(state == ARTRealtimeConnected) {
                [expectation fulfill];
            }
        }];
    }];
    [self waitForExpectationsWithTimeout:[ARTTestUtil timeout] handler:nil];
}

- (void)testInitAutoConnectFalse {
    __weak XCTestExpectation *expectation = [self expectationWithDescription:@"testInitAutoConnectDefault"];
    [ARTTestUtil setupApp:[ARTTestUtil clientOptions] callback:^(ARTClientOptions *options) {
        options.autoConnect = false;
        ARTRealtime *realtime = [[ARTRealtime alloc] initWithOptions:options];
        _realtime = realtime;
        [realtime.connection on:^(ARTConnectionStateChange *stateChange) {
            ARTRealtimeConnectionState state = stateChange.current;
            if(state == ARTRealtimeConnected) {
                [expectation fulfill];
            }
        }];
        [realtime connect];
    }];
    [self waitForExpectationsWithTimeout:[ARTTestUtil timeout] handler:nil];
}

@end