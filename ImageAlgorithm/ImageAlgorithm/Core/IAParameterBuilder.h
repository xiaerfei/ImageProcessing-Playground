//
//  IAParameterBuilder.h
//  ImageAlgorithm
//
//  声明式参数面板:模块只描述"有哪些参数",不碰 Auto Layout。
//
//      [builder addSection:@"平移 (px)"];
//      [builder addSlider:@"tx" label:@"X" min:-1000 max:1000 value:0 format:@"%.0f"];
//

#import <Cocoa/Cocoa.h>
#import "IAParameterStore.h"

NS_ASSUME_NONNULL_BEGIN

@interface IAParameterBuilder : NSObject

/// onChange 的参数是发生变化的参数 key;按钮触发时为 nil
- (instancetype)initWithStore:(IAParameterStore *)store
                     onChange:(void (^)(NSString * _Nullable key))onChange;

/// 全部 add 完成后取出,交给宿主放进 NSScrollView
@property (nonatomic, readonly) NSView *containerView;

- (void)addSection:(NSString *)title;
- (void)addSeparator;
/// 灰色小字说明,用来写公式或提示
- (void)addNote:(NSString *)text;

/// format 只能含**一个**占位符(值只传一个 double);
/// 多写一个 %f 会去读栈上的垃圾
- (void)addSlider:(NSString *)key
            label:(NSString *)label
              min:(double)min
              max:(double)max
            value:(double)value
           format:(NSString *)format;

- (void)addCheckbox:(NSString *)key title:(NSString *)title value:(BOOL)value;

- (void)addSegmented:(NSString *)key
               items:(NSArray<NSString *> *)items
               value:(NSInteger)value;

/// 选项多于 4 个时用下拉,分段控件在窄面板里会挤
- (void)addPopUp:(NSString *)key
           items:(NSArray<NSString *> *)items
           value:(NSInteger)value;

- (void)addButton:(NSString *)title action:(void (^)(void))action;

/// 塞一个模块自备的视图(直方图、曲线之类)。宽度自动撑满面板,高度由调用方定。
/// 模块持有这个视图的引用,算完之后自己往里灌数据。
- (void)addCustomView:(NSView *)view height:(CGFloat)height;

/// 参数联动后调用,把滑杆右侧的数值文字刷新一遍
- (void)refreshValueLabels;

@end

NS_ASSUME_NONNULL_END
