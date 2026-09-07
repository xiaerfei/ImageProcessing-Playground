//
//  IAZoomImageView.h
//  ImageAlgorithm
//
//  可缩放 / 可平移的图像画布,用来放大观察处理细节(插值锯齿、边缘、噪声等
//  只有在放大到 1:1 以上才看得清)。与算法无关,属于宿主层 UI 组件。
//
//  交互(对齐 Photoshop):
//    捏合 / ⌘+滚轮        以光标为锚点缩放
//    滚轮                  平移
//    空格 + 拖拽           平移(空格是全局临时抓手,和 PS 一致;
//                          光标随之变张开手,按下去变握拳)
//    双击                  在"适应窗口"与 1:1 之间切换
//    0 / 1 / +/- (可带 ⌘)  适应 / 1:1 / 按标准档位缩放
//  点击视图会自动取得键盘焦点,快捷键无需额外操作。
//  "适应窗口"会把小图放大填满窗口(PS 的适应屏幕),不再卡在 100%。
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

/// 同步缩放 + 位置。center 是"视口中心落在图像的哪里",0~1 归一化 ——
/// 用归一化坐标而不是 origin,两边图像尺寸不同也不会错位,
/// 同时能做到"A 拖到左眼,B 也停在左眼",这才是 Photoshop 的匹配缩放手感。
- (void)applyScale:(double)scale center:(NSPoint)center;
/// 把当前的缩放推给同步方(刚打开"同步"开关时用)
- (void)syncToPartner;

@end

NS_ASSUME_NONNULL_END
