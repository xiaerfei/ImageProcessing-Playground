//
//  IAHistogram.h
//  ImageAlgorithm
//
//  直方图算法原语。全部是纯函数,不碰 UI、不碰 NSImage —— 单通道平面进,查找表出。
//
//  一条主线贯穿这里所有函数:
//      直方图(计数) → PDF(归一化) → CDF(累加) → 映射表
//  均衡化就是"拿 CDF 当映射表",规定化就是"拿目标 CDF 反查",
//  CLAHE 则是"分块各算一张 CDF,再限制它的斜率、并在块之间插值"。
//  详见 Documents/histogram-transform.md 第十、十一、十四节。
//

#import <Cocoa/Cocoa.h>
#import "IAImageBuffer.h"

NS_ASSUME_NONNULL_BEGIN

/// 合成的目标分布,用于直方图规定化。
/// 宿主一次只能载入一张图,没法用"参考图"的直方图当目标,
/// 于是改用解析式生成的目标分布 —— 教学上反而更干净:
/// 目标长什么样一目了然,不用先去猜参考图的分布。
typedef NS_ENUM(NSInteger, IAHistogramTarget) {
    IAHistogramTargetUniform = 0,   ///< 均匀:等价于均衡化,用来验证两者确实同源
    IAHistogramTargetGaussian,      ///< 高斯:中间调厚、两端薄,接近"讨喜"的胶片调
    IAHistogramTargetBimodal,       ///< 双峰:亮暗分离,逼近二值化的观感
    IAHistogramTargetBrightSkew,    ///< 偏亮:高调
    IAHistogramTargetDarkSkew,      ///< 偏暗:低调
};

@interface IAHistogram : NSObject

#pragma mark - 统计

/// 统计单通道平面的 256 格直方图(计数,未归一化)
+ (void)computePlane:(const uint8_t *)plane
               count:(NSInteger)count
                into:(double[_Nonnull 256])hist;

/// 计数 → PDF。原地归一化成"总和为 1",这样不同尺寸的图能直接比。
/// 一张图放大 2 倍,像素数变 4 倍,柱子整体高 4 倍 —— 但形状没变,
/// 我们关心的一直是形状。
+ (void)normalize:(double[_Nonnull 256])hist;

/// PDF → CDF(前缀和)。CDF 单调不减,末项必为 1。
+ (void)cdfFromPDF:(const double[_Nonnull 256])pdf into:(double[_Nonnull 256])cdf;

#pragma mark - 映射表

/// 均衡化:s = round(255 · CDF(r))。
/// 为什么这样就能摊平,见文档第十一节的"换成排名百分比"。
+ (void)equalizeLUTFromCDF:(const double[_Nonnull 256])cdf into:(uint8_t[_Nonnull 256])lut;

/// 规定化:对每个 r,找到使 dstCDF(s) 最接近 srcCDF(r) 的 s。
/// 两条 CDF 都单调,所以一次同向扫描即可,不必对每个 r 都二分。
+ (void)specifyLUTFromCDF:(const double[_Nonnull 256])srcCDF
                    toCDF:(const double[_Nonnull 256])dstCDF
                     into:(uint8_t[_Nonnull 256])lut;

/// 生成目标分布的 PDF(已归一化)
+ (void)targetPDF:(IAHistogramTarget)target into:(double[_Nonnull 256])pdf;

/// 百分位拉伸:丢掉最暗 lowPct%、最亮 highPct% 的像素,把剩下的拉满 0~255。
/// 放在这里是为了和均衡化做对照 —— 拉伸只改区间端点(线性),
/// 均衡化会按密度重排整条曲线(非线性)。
+ (void)stretchLUTFromCDF:(const double[_Nonnull 256])cdf
                   lowPct:(double)lowPct
                  highPct:(double)highPct
                     into:(uint8_t[_Nonnull 256])lut;

#pragma mark - CLAHE

/// 对单通道平面原地做 CLAHE。
///   tilesX/tilesY  分块数,越多越局部
///   clipLimit      削顶高度,以"平均柱高"为单位(1.0 = 削到全平,越大越接近 AHE)
/// 三步:分块各算映射表 → 削顶回填(限制曲线斜率 = 限制对比度增益)→ 块间双线性插值消接缝。
+ (void)claheOnPlane:(uint8_t *)plane
               width:(NSInteger)width
              height:(NSInteger)height
              tilesX:(NSInteger)tilesX
              tilesY:(NSInteger)tilesY
           clipLimit:(double)clipLimit;

#pragma mark - 通道工具

/// 取出亮度平面(Rec.601)。调用方负责 free。
+ (uint8_t *)lumaPlaneFrom:(IAImageBuffer *)src;

/// 把处理过的亮度平面写回,色度保持不变 —— 这样只改明暗、不偏色。
/// 直接对 R/G/B 各做一遍均衡化会让三条映射曲线各走各的,颜色必然跑掉,
/// 见文档第十六节。
+ (void)applyLumaPlane:(const uint8_t *)luma to:(IAImageBuffer *)dst from:(IAImageBuffer *)src;

@end

NS_ASSUME_NONNULL_END
