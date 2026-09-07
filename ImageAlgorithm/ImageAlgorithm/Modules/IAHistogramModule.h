//
//  IAHistogramModule.h
//  ImageAlgorithm
//

#import "IAAlgorithmModule.h"

NS_ASSUME_NONNULL_BEGIN

/// 变换方式。前四种共享同一条主线(直方图 → CDF → 映射表),
/// 只是"映射表从哪来"不同;最后一种是线性对照组。
typedef NS_ENUM(NSInteger, IAHistogramMode) {
    IAHistogramModeIdentity = 0,   ///< 原图:只看直方图,不动像素
    IAHistogramModeEqualize,       ///< 全局均衡化:映射表 = 自己的 CDF
    IAHistogramModeCLAHE,          ///< 限制对比度的自适应均衡化
    IAHistogramModeSpecify,        ///< 规定化:映射到指定的目标分布
    IAHistogramModeStretch,        ///< 百分位拉伸:线性,只挪端点(对照组)
};

/// 彩色图怎么处理
typedef NS_ENUM(NSInteger, IAHistogramColorMode) {
    IAHistogramColorModeLuma = 0,  ///< 只动亮度,色度保持 —— 正确做法
    IAHistogramColorModePerChannel,///< R/G/B 各做各的 —— 错误示范,会偏色
    IAHistogramColorModeGray,      ///< 先转灰度再处理
};

@interface IAHistogramModule : IAAlgorithmModule
@end

NS_ASSUME_NONNULL_END
