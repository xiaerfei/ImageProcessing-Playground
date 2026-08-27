//
//  IAAlgorithmModule.m
//  ImageAlgorithm
//

#import "IAAlgorithmModule.h"

@interface IAAlgorithmModule ()
@property (nonatomic, strong) IAParameterStore *parameters;
@property (nonatomic, strong, nullable) IAParameterBuilder *builder;
@end

@implementation IAAlgorithmModule

+ (NSString *)title {
    NSAssert(NO, @"子类必须重写 +title");
    return NSStringFromClass(self);
}

+ (nullable NSString *)subtitle {
    return nil;
}

- (void)buildParameters:(IAParameterBuilder *)builder {
    NSAssert(NO, @"子类必须重写 -buildParameters:");
}

- (nullable IAImageBuffer *)processImage:(IAImageBuffer *)source {
    NSAssert(NO, @"子类必须重写 -processImage:");
    return nil;
}

- (void)parameterDidChange:(nullable NSString *)key {
    // 默认什么都不做;需要联动的子类重写
}

- (nullable NSString *)resultTitle {
    return @"处理结果";
}

- (nullable NSString *)extraStatus {
    return nil;
}

#pragma mark - 参数面板

- (IAParameterStore *)parameters {
    [self buildIfNeeded];
    return _parameters;
}

- (NSView *)parameterView {
    [self buildIfNeeded];
    return self.builder.containerView;
}

- (void)buildIfNeeded {
    if (_parameters) { return; }
    _parameters = [[IAParameterStore alloc] init];

    __weak typeof(self) weakSelf = self;
    _builder = [[IAParameterBuilder alloc] initWithStore:_parameters
                                                onChange:^(NSString * _Nullable key) {
        __strong typeof(weakSelf) self = weakSelf;
        if (!self) { return; }
        [self parameterDidChange:key];       // 先给子类联动的机会
        [self.builder refreshValueLabels];   // 联动可能改了别的控件,统一刷新
        if (self.onNeedsReprocess) { self.onNeedsReprocess(); }
    }];
    [self buildParameters:_builder];
}

- (void)resetParameters {
    [self.parameters resetAll];
    [self refreshParameterLabels];
    if (self.onNeedsReprocess) { self.onNeedsReprocess(); }
}

- (void)refreshParameterLabels {
    [self.builder refreshValueLabels];
}

@end
