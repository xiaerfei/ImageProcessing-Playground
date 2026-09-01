//
//  IAParameterStore.m
//  ImageAlgorithm
//

#import "IAParameterStore.h"

@implementation IAParameterStore {
    NSMutableDictionary<NSString *, NSControl *> *_controls;
    NSMutableDictionary<NSString *, NSNumber *> *_defaults;
    NSMutableArray<NSString *> *_order;
}

- (instancetype)init {
    self = [super init];
    if (self) {
        _controls = [NSMutableDictionary dictionary];
        _defaults = [NSMutableDictionary dictionary];
        _order = [NSMutableArray array];
    }
    return self;
}

- (void)registerControl:(NSControl *)control forKey:(NSString *)key defaultValue:(double)defaultValue {
    NSAssert(_controls[key] == nil, @"参数 key 重复: %@", key);
    _controls[key] = control;
    _defaults[key] = @(defaultValue);
    [_order addObject:key];
}

- (nullable NSControl *)controlForKey:(NSString *)key {
    return _controls[key];
}

- (NSArray<NSString *> *)allKeys {
    return [_order copy];
}

#pragma mark - 读

- (double)doubleForKey:(NSString *)key {
    NSControl *control = _controls[key];
    if ([control isKindOfClass:NSSegmentedControl.class]) {
        return (double)((NSSegmentedControl *)control).selectedSegment;
    }
    // NSPopUpButton 继承自 NSButton,必须先判断它,否则会被当成勾选框读 state
    if ([control isKindOfClass:NSPopUpButton.class]) {
        return (double)((NSPopUpButton *)control).indexOfSelectedItem;
    }
    if ([control isKindOfClass:NSButton.class]) {
        return ((NSButton *)control).state == NSControlStateValueOn ? 1.0 : 0.0;
    }
    return control.doubleValue;
}

- (NSInteger)integerForKey:(NSString *)key {
    return (NSInteger)lround([self doubleForKey:key]);
}

- (BOOL)boolForKey:(NSString *)key {
    return [self doubleForKey:key] != 0.0;
}

#pragma mark - 写

- (void)setDouble:(double)value forKey:(NSString *)key {
    NSControl *control = _controls[key];
    if ([control isKindOfClass:NSSegmentedControl.class]) {
        ((NSSegmentedControl *)control).selectedSegment = (NSInteger)lround(value);
    } else if ([control isKindOfClass:NSPopUpButton.class]) {
        [(NSPopUpButton *)control selectItemAtIndex:(NSInteger)lround(value)];
    } else if ([control isKindOfClass:NSButton.class]) {
        ((NSButton *)control).state = (value != 0.0) ? NSControlStateValueOn : NSControlStateValueOff;
    } else {
        control.doubleValue = value;
    }
}

- (void)setBool:(BOOL)value forKey:(NSString *)key {
    [self setDouble:(value ? 1.0 : 0.0) forKey:key];
}

- (void)resetAll {
    for (NSString *key in _order) {
        [self setDouble:_defaults[key].doubleValue forKey:key];
    }
}

@end
