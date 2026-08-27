//
//  IAAffineTransform.h
//  ImageAlgorithm
//
//  3x3 齐次矩阵 + 反向映射(Backward Mapping)的通用几何变换。
//
//  设计参考 Documents/数字图像处理自学路线规划.md 中的纯 C 实现,
//  这里扩展为 RGBA 四通道,并补上最近邻插值与自适应画布。
//
//  矩阵运算用 Apple 的 simd(系统框架,零依赖)。它同时也是 Metal 的矩阵类型,
//  以后把算法搬到 shader 时可以直接复用。实测每像素的矩阵×向量比手写循环快约 1.3 倍。
//
//  为什么用 3x3 而不是 2x2:
//    2x2 只能表达旋转/缩放/剪切(线性变换),平移无法用矩阵乘法表示。
//    升到齐次坐标 (x, y, 1) 后平移变成第三列 tx/ty,于是
//    "缩放 → 旋转 → 平移" 可以预先连乘成单个矩阵 M,每像素只算一次乘法;
//    求反向映射也只需对 M 求一次逆,不用手推逆公式。
//    最下行留作 [p q 1] 还能扩展到透视变换(本文件已按齐次坐标归一化处理)。
//

#import <Foundation/Foundation.h>
#import <simd/simd.h>

#import "IAImageBuffer.h"

NS_ASSUME_NONNULL_BEGIN

/// 插值方式:决定反推出的浮点源坐标如何取色
typedef NS_ENUM(NSInteger, IAInterpolation) {
    IAInterpolationNearest  = 0,   ///< 最近邻:直接取整,块状锯齿
    IAInterpolationBilinear = 1,   ///< 双线性:相邻 4 点距离加权,平滑
};

/// 输出画布策略
typedef NS_ENUM(NSInteger, IACanvasMode) {
    IACanvasModeKeepSize = 0,   ///< 与原图同尺寸,转出画布的部分被裁掉
    IACanvasModeFit      = 1,   ///< 扩展到刚好容纳变换后的四个角
};

#pragma mark - 矩阵构造

// 乘法 / 求逆 / 行列式直接用 simd:
//   simd_mul(A, B)      矩阵相乘
//   simd_mul(M, v)      矩阵乘齐次向量
//   simd_inverse(M)     求逆(反向映射用)
//   simd_determinant(M) 判断是否奇异

FOUNDATION_EXPORT simd_double3x3 IAMatrixTranslation(double tx, double ty);
FOUNDATION_EXPORT simd_double3x3 IAMatrixScale(double sx, double sy);
FOUNDATION_EXPORT simd_double3x3 IAMatrixRotation(double degrees);
/// 转置(x 与 y 互换),等价于沿主对角线镜像
FOUNDATION_EXPORT simd_double3x3 IAMatrixTranspose2D(void);

#pragma mark - 变换参数

/// 一次几何变换的全部可调参数
typedef struct {
    double translateX;
    double translateY;
    double rotationDegrees;
    double scaleX;
    double scaleY;
    BOOL   mirrorHorizontal;
    BOOL   mirrorVertical;
    BOOL   transpose;
} IATransformParams;

FOUNDATION_EXPORT IATransformParams IATransformParamsDefault(void);

@interface IAAffineTransform : NSObject

/// 按 "缩放 → 转置 → 镜像 → 旋转 → 平移" 的顺序复合出正向矩阵。
/// 旋转/缩放都绕图像中心进行,所以前后各夹了一次到原点的平移。
+ (simd_double3x3)matrixWithParams:(IATransformParams)params imageSize:(NSSize)size;

/// 反向映射执行变换:遍历目标画布每个像素,用逆矩阵反推源坐标再采样。
/// 落在源图之外的像素填透明(而非黑),空出来的区域一眼可辨。
+ (nullable IAImageBuffer *)warpImage:(IAImageBuffer *)src
                               matrix:(simd_double3x3)forward
                        interpolation:(IAInterpolation)interpolation
                           canvasMode:(IACanvasMode)canvasMode;

@end

NS_ASSUME_NONNULL_END
