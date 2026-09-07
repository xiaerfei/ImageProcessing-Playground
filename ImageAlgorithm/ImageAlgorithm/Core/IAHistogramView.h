//
//  IAHistogramView.h
//  ImageAlgorithm
//
//  直方图显示控件。一张图上最多叠三层,对应文档第十节说的
//  "直方图 / PDF / CDF 是同一条数据的三种形态":
//
//    ① 灰色柱   PDF —— 每一级亮度占了多少像素
//    ② 蓝色线   CDF —— 从左往右累加,末端必然到顶
//    ③ 黄色线   映射曲线 —— 这一次变换把输入 r 送到了哪个输出 s
//
//  把三层叠在一起看,均衡化就一目了然了:黄线和蓝线会重合 ——
//  因为均衡化的映射表就是 CDF 本身。
//

#import <Cocoa/Cocoa.h>

NS_ASSUME_NONNULL_BEGIN

@interface IAHistogramView : NSView

/// 左上角的小标题,如 @"原图" / @"结果"
@property (nonatomic, copy, nullable) NSString *caption;
/// 右上角的补充文字,一般放均值/标准差
@property (nonatomic, copy, nullable) NSString *detail;

/// 柱子。传入归一化后的 PDF(总和为 1);传 NULL 清空。
- (void)setPDF:(nullable const double *)pdf;
/// 蓝色累积曲线;传 NULL 不画
- (void)setCDF:(nullable const double *)cdf;
/// 黄色映射曲线;传 NULL 不画
- (void)setMappingLUT:(nullable const uint8_t *)lut;

/// 纵轴用对数刻度。直方图常有一根盖过一切的尖峰(大片纯色背景),
/// 线性刻度下其余柱子会被压成贴地的一条线,什么也看不出来。
@property (nonatomic) BOOL logScale;

@end

NS_ASSUME_NONNULL_END
