//
//  IAZoomImageView.h
//  ImageAlgorithm
//
//  可缩放 / 可平移的图像画布,用来放大观察处理细节(插值锯齿、边缘、噪声等
//  只有在放大到 1:1 以上才看得清)。与算法无关,属于宿主层 UI 组件。
//
//  交互:
//    捏合 / ⌘+滚轮   以光标为锚点缩放
//    滚轮 / 拖拽      平移
//    双击             在 1:1 与"适应窗口"之间切换
//    键盘 0 / 1 / +/- 适应 / 1:1 / 缩放(需先点过该视图)
//
//  放大时不开启插值:观察最近邻与双线性的差别,必须看到真实像素。
//

#import <Cocoa/Cocoa.h>

NS_ASSUME_NONNULL_BEGIN

@interface IAZoomImageView : NSView

@property (nonatomic, strong, nullable) NSImage *image;
/// 当前缩放,1.0 = 一个图像像素占一个屏幕点
@property (nonatomic, readonly) double scale;
/// 恰好铺满视图的缩放值(沿用"只缩不放"的惯例,上限 1.0)
@property (nonatomic, readonly) double fitScale;

/// 缩放或平移后回调,参数是新的缩放与"图片左上角在视图中的位置"
@property (nonatomic, copy, nullable) void (^onViewDidChange)(double scale, NSPoint origin);

/// 双向同步:设了之后,一边的缩放/平移会同步给另一边(对比同一区域时很有用)
@property (nonatomic, weak, nullable) IAZoomImageView *syncPartner;

/// 换图或视图尺寸变化时自动重新适应;用户手动缩放过之后不再自动干预
@property (nonatomic) BOOL autoFitsOnResize;

- (void)zoomToFit;
- (void)zoomToActualSize;
/// 以视图中心为锚缩放(供面板 +/- 按钮调用)
- (void)zoomBy:(double)factor;

/// 供同步方调用:只同步缩放比例,origin 由接收方自己重新居中。
/// 之前传 origin 时会出现"两个视图尺寸/图像尺寸不同 → origin 错位 → 图片被
/// clipsToBounds 裁光"的 bug(见 ViewController 反馈)。
- (void)applyScale:(double)scale;
/// 把当前的缩放推给同步方(刚打开"同步"开关时用)
- (void)syncToPartner;

@end

NS_ASSUME_NONNULL_END
