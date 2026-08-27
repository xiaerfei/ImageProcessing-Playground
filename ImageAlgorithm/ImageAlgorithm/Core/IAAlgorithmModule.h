//
//  IAAlgorithmModule.h
//  ImageAlgorithm
//
//  算法模块基类。每章算法(几何变换 / 灰度变换 / 分割 …)写一个子类即可,
//  界面、计时、图片载入等共用部分由宿主 ViewController 负责。
//
//  子类最少只需重写三个方法:
//      + title              显示名
//      - buildParameters:   声明参数(不写 Auto Layout)
//      - processImage:      算法本体
//

#import <Cocoa/Cocoa.h>
#import "IAParameterStore.h"
#import "IAParameterBuilder.h"
#import "IAImageBuffer.h"

NS_ASSUME_NONNULL_BEGIN

@interface IAAlgorithmModule : NSObject

#pragma mark - 子类必须重写

/// 模块显示名,如 @"几何变换"
+ (NSString *)title;
/// 声明参数;不要在这里做布局
- (void)buildParameters:(IAParameterBuilder *)builder;
/// 算法本体。返回 nil 表示当前参数下无法处理(宿主会显示提示而不是崩溃)
- (nullable IAImageBuffer *)processImage:(IAImageBuffer *)source;

#pragma mark - 子类可选重写

/// 副标题,建议标注书上章节/学习周次,如 @"第 2 章 · 第 3 周"
+ (nullable NSString *)subtitle;
/// 参数联动钩子。key 为变化的参数;按钮触发时为 nil
- (void)parameterDidChange:(nullable NSString *)key;
/// 结果面板的标题,默认 @"处理结果"
- (nullable NSString *)resultTitle;
/// 追加到状态栏的一行文字,如阈值、核大小等算出来的中间量
- (nullable NSString *)extraStatus;

#pragma mark - 基类提供

@property (nonatomic, readonly) IAParameterStore *parameters;
/// 懒构建的参数面板,宿主直接塞进 NSScrollView
@property (nonatomic, readonly) NSView *parameterView;
/// 参数变化时由基类回调,宿主据此重跑算法
@property (nonatomic, copy, nullable) void (^onNeedsReprocess)(void);

/// 参数恢复默认值并触发重算
- (void)resetParameters;
/// 供子类在联动后刷新滑杆右侧数值
- (void)refreshParameterLabels;

@end

NS_ASSUME_NONNULL_END
