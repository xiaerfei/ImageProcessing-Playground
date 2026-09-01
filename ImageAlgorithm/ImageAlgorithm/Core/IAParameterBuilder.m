//
//  IAParameterBuilder.m
//  ImageAlgorithm
//

#import "IAParameterBuilder.h"

/// NSControl 只认 target/action,这个小包装让按钮能用 block
@interface IABlockAction : NSObject
@property (nonatomic, copy) void (^block)(void);
@end

@implementation IABlockAction
- (void)invoke:(id)sender { if (self.block) { self.block(); } }
@end

/// 坐标翻转的容器,放进 NSScrollView 后内容从顶部开始排
@interface IAFlippedView : NSView
@end

@implementation IAFlippedView
- (BOOL)isFlipped { return YES; }
@end

@interface IAParameterBuilder ()
@property (nonatomic, strong) IAParameterStore *store;
@property (nonatomic, copy) void (^onChange)(NSString * _Nullable);
@property (nonatomic, strong) NSStackView *stack;
@property (nonatomic, strong) NSView *container;
@property (nonatomic, strong) NSMutableArray<IABlockAction *> *buttonActions;
@property (nonatomic, strong) NSMutableDictionary<NSString *, NSTextField *> *valueLabels;
@property (nonatomic, strong) NSMutableDictionary<NSString *, NSString *> *valueFormats;
@end

@implementation IAParameterBuilder

- (instancetype)initWithStore:(IAParameterStore *)store
                     onChange:(void (^)(NSString * _Nullable))onChange {
    self = [super init];
    if (self) {
        _store = store;
        _onChange = [onChange copy];
        _buttonActions = [NSMutableArray array];
        _valueLabels = [NSMutableDictionary dictionary];
        _valueFormats = [NSMutableDictionary dictionary];
        [self buildContainer];
    }
    return self;
}

- (void)buildContainer {
    _container = [[IAFlippedView alloc] init];
    _container.translatesAutoresizingMaskIntoConstraints = NO;

    _stack = [[NSStackView alloc] init];
    _stack.orientation = NSUserInterfaceLayoutOrientationVertical;
    _stack.alignment = NSLayoutAttributeLeading;
    _stack.spacing = 9.0;
    _stack.edgeInsets = NSEdgeInsetsMake(14, 16, 18, 16);
    _stack.translatesAutoresizingMaskIntoConstraints = NO;
    [_container addSubview:_stack];

    [NSLayoutConstraint activateConstraints:@[
        [_stack.topAnchor constraintEqualToAnchor:_container.topAnchor],
        [_stack.leadingAnchor constraintEqualToAnchor:_container.leadingAnchor],
        [_stack.trailingAnchor constraintEqualToAnchor:_container.trailingAnchor],
        [_stack.bottomAnchor constraintEqualToAnchor:_container.bottomAnchor],
    ]];
}

- (NSView *)containerView {
    return _container;
}

#pragma mark - 添加控件

- (void)addSection:(NSString *)title {
    NSTextField *label = [NSTextField labelWithString:title];
    label.font = [NSFont boldSystemFontOfSize:11];
    label.textColor = NSColor.secondaryLabelColor;
    [self.stack addArrangedSubview:label];
}

- (void)addNote:(NSString *)text {
    NSTextField *label = [NSTextField wrappingLabelWithString:text];
    label.font = [NSFont systemFontOfSize:10];
    label.textColor = NSColor.tertiaryLabelColor;
    [self.stack addArrangedSubview:label];
    [label.widthAnchor constraintEqualToAnchor:self.stack.widthAnchor constant:-32].active = YES;
}

- (void)addSeparator {
    NSBox *box = [[NSBox alloc] init];
    box.boxType = NSBoxSeparator;
    box.translatesAutoresizingMaskIntoConstraints = NO;
    [self.stack addArrangedSubview:box];
    [box.widthAnchor constraintEqualToAnchor:self.stack.widthAnchor constant:-32].active = YES;
}

- (void)addSlider:(NSString *)key label:(NSString *)label
              min:(double)min max:(double)max value:(double)value format:(NSString *)format {
    NSSlider *slider = [NSSlider sliderWithValue:value minValue:min maxValue:max
                                          target:self action:@selector(controlChanged:)];
    slider.continuous = YES;
    [slider.widthAnchor constraintEqualToConstant:126].active = YES;
    [self.store registerControl:slider forKey:key defaultValue:value];

    NSTextField *nameLabel = [NSTextField labelWithString:label];
    nameLabel.font = [NSFont monospacedDigitSystemFontOfSize:11 weight:NSFontWeightRegular];
    [nameLabel.widthAnchor constraintEqualToConstant:34].active = YES;

    NSTextField *valueLabel = [NSTextField labelWithString:@""];
    valueLabel.font = [NSFont monospacedDigitSystemFontOfSize:11 weight:NSFontWeightRegular];
    valueLabel.alignment = NSTextAlignmentRight;
    [valueLabel.widthAnchor constraintEqualToConstant:46].active = YES;

    self.valueLabels[key] = valueLabel;
    self.valueFormats[key] = format;

    NSStackView *row = [NSStackView stackViewWithViews:@[nameLabel, slider, valueLabel]];
    row.orientation = NSUserInterfaceLayoutOrientationHorizontal;
    row.spacing = 5.0;
    [self.stack addArrangedSubview:row];
    [self refreshValueLabelForKey:key];
}

- (void)addCheckbox:(NSString *)key title:(NSString *)title value:(BOOL)value {
    NSButton *button = [NSButton checkboxWithTitle:title target:self action:@selector(controlChanged:)];
    button.state = value ? NSControlStateValueOn : NSControlStateValueOff;
    [self.store registerControl:button forKey:key defaultValue:(value ? 1.0 : 0.0)];
    [self.stack addArrangedSubview:button];
}

- (void)addSegmented:(NSString *)key items:(NSArray<NSString *> *)items value:(NSInteger)value {
    NSSegmentedControl *control =
        [NSSegmentedControl segmentedControlWithLabels:items
                                          trackingMode:NSSegmentSwitchTrackingSelectOne
                                                target:self
                                                action:@selector(controlChanged:)];
    control.selectedSegment = value;
    [self.store registerControl:control forKey:key defaultValue:(double)value];
    [self.stack addArrangedSubview:control];
}

- (void)addPopUp:(NSString *)key items:(NSArray<NSString *> *)items value:(NSInteger)value {
    NSPopUpButton *control = [NSPopUpButton buttonWithTitle:@""
                                                     target:self action:@selector(controlChanged:)];
    [control addItemsWithTitles:items];
    [control selectItemAtIndex:value];
    [self.store registerControl:control forKey:key defaultValue:(double)value];
    [self.stack addArrangedSubview:control];
}

- (void)addButton:(NSString *)title action:(void (^)(void))action {
    IABlockAction *wrapper = [[IABlockAction alloc] init];
    wrapper.block = action;
    [self.buttonActions addObject:wrapper];   // 持有,否则会被立即释放

    NSButton *button = [NSButton buttonWithTitle:title target:wrapper action:@selector(invoke:)];
    [self.stack addArrangedSubview:button];
}

#pragma mark - 事件

- (void)controlChanged:(NSControl *)sender {
    NSString *changedKey = nil;
    for (NSString *key in self.store.allKeys) {
        if ([self.store controlForKey:key] == sender) { changedKey = key; break; }
    }
    if (changedKey) { [self refreshValueLabelForKey:changedKey]; }
    if (self.onChange) { self.onChange(changedKey); }
}

- (void)refreshValueLabels {
    for (NSString *key in self.valueLabels.allKeys) {
        [self refreshValueLabelForKey:key];
    }
}

- (void)refreshValueLabelForKey:(NSString *)key {
    NSTextField *label = self.valueLabels[key];
    NSString *format = self.valueFormats[key];
    if (label && format) {
        label.stringValue = [NSString stringWithFormat:format, [self.store doubleForKey:key]];
    }
}

@end
