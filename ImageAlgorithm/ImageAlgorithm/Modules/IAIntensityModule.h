//
//  IAIntensityModule.h
//  ImageAlgorithm
//

#import "IAAlgorithmModule.h"

NS_ASSUME_NONNULL_BEGIN

/// 变换类型。反色/拉伸本质都是线性变换的特例,这里分开列出便于对照课本。
typedef NS_ENUM(NSInteger, IAIntensityMode) {
    IAIntensityModeIdentity = 0,   ///< 原图
    IAIntensityModeLinear   = 1,   ///< 线性 s = a·r + b
    IAIntensityModeInvert   = 2,   ///< 反色(= a:-1, b:255)
    IAIntensityModeLog      = 3,   ///< 对数
    IAIntensityModeGamma    = 4,   ///< 幂律
    IAIntensityModeStretch  = 5,   ///< 分段拉伸(= 线性的区间截断版)
};

/// 灰度变换:线性 / 反色 / 对数 / 幂律 / 分段线性,统一走 256 项 LUT
@interface IAIntensityModule : IAAlgorithmModule
@end

NS_ASSUME_NONNULL_END
