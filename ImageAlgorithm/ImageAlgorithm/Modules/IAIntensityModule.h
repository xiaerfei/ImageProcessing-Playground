//
//  IAIntensityModule.h
//  ImageAlgorithm
//

#import "IAAlgorithmModule.h"

NS_ASSUME_NONNULL_BEGIN

/// 灰度变换:反色 / 对数 / 幂律(Gamma) / 分段线性,统一走 256 项 LUT
@interface IAIntensityModule : IAAlgorithmModule
@end

NS_ASSUME_NONNULL_END
