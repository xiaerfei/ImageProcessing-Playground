//
//  IAAffineTransform.m
//  ImageAlgorithm
//

#import "IAAffineTransform.h"

#pragma mark - 矩阵构造

// simd_matrix_from_rows 允许按课本的行布局书写,内部虽是列主序但对调用方透明。

simd_double3x3 IAMatrixTranslation(double tx, double ty) {
    return simd_matrix_from_rows((simd_double3){1.0, 0.0, tx},
                                 (simd_double3){0.0, 1.0, ty},
                                 (simd_double3){0.0, 0.0, 1.0});
}

simd_double3x3 IAMatrixScale(double sx, double sy) {
    return simd_matrix_from_rows((simd_double3){ sx, 0.0, 0.0},
                                 (simd_double3){0.0,  sy, 0.0},
                                 (simd_double3){0.0, 0.0, 1.0});
}

simd_double3x3 IAMatrixRotation(double degrees) {
    double rad = degrees * M_PI / 180.0;
    double c = cos(rad), s = sin(rad);
    // 位图 y 轴向下,所以这个矩阵在屏幕上看起来是顺时针旋转
    return simd_matrix_from_rows((simd_double3){  c,  -s, 0.0},
                                 (simd_double3){  s,   c, 0.0},
                                 (simd_double3){0.0, 0.0, 1.0});
}

simd_double3x3 IAMatrixTranspose2D(void) {
    return simd_matrix_from_rows((simd_double3){0.0, 1.0, 0.0},
                                 (simd_double3){1.0, 0.0, 0.0},
                                 (simd_double3){0.0, 0.0, 1.0});
}

IATransformParams IATransformParamsDefault(void) {
    return (IATransformParams){
        .translateX = 0.0, .translateY = 0.0,
        .rotationDegrees = 0.0,
        .scaleX = 1.0, .scaleY = 1.0,
        .mirrorHorizontal = NO, .mirrorVertical = NO, .transpose = NO,
    };
}

#pragma mark - 采样

/// 最近邻:四舍五入取整,越界返回透明
static inline void IASampleNearest(const uint8_t *src, NSInteger w, NSInteger h,
                                   double x, double y, uint8_t out[4]) {
    NSInteger sx = (NSInteger)lround(x);
    NSInteger sy = (NSInteger)lround(y);
    if (sx < 0 || sx >= w || sy < 0 || sy >= h) {
        out[0] = out[1] = out[2] = out[3] = 0;
        return;
    }
    const uint8_t *p = src + (sy * w + sx) * 4;
    out[0] = p[0]; out[1] = p[1]; out[2] = p[2]; out[3] = p[3];
}

/// 双线性:相邻 4 点按距离加权
///
/// 与参考实现的区别:参考用 `x >= width - 1` 直接判越界,会把最右一列/最下一行
/// 整条丢掉;这里改为把 4 个采样点各自 clamp 到边界内,保留边缘像素。
static inline void IASampleBilinear(const uint8_t *src, NSInteger w, NSInteger h,
                                    double x, double y, uint8_t out[4]) {
    if (x < -0.5 || x > (double)w - 0.5 || y < -0.5 || y > (double)h - 0.5) {
        out[0] = out[1] = out[2] = out[3] = 0;
        return;
    }

    NSInteger x0 = (NSInteger)floor(x);
    NSInteger y0 = (NSInteger)floor(y);
    double dx = x - (double)x0;
    double dy = y - (double)y0;

    NSInteger x1 = x0 + 1, y1 = y0 + 1;
    if (x0 < 0) { x0 = 0; }  if (x0 > w - 1) { x0 = w - 1; }
    if (y0 < 0) { y0 = 0; }  if (y0 > h - 1) { y0 = h - 1; }
    if (x1 < 0) { x1 = 0; }  if (x1 > w - 1) { x1 = w - 1; }
    if (y1 < 0) { y1 = 0; }  if (y1 > h - 1) { y1 = h - 1; }

    const uint8_t *p00 = src + (y0 * w + x0) * 4;
    const uint8_t *p10 = src + (y0 * w + x1) * 4;
    const uint8_t *p01 = src + (y1 * w + x0) * 4;
    const uint8_t *p11 = src + (y1 * w + x1) * 4;

    double w00 = (1.0 - dx) * (1.0 - dy);
    double w10 = dx         * (1.0 - dy);
    double w01 = (1.0 - dx) * dy;
    double w11 = dx         * dy;

    for (int c = 0; c < 4; c++) {
        double v = w00 * p00[c] + w10 * p10[c] + w01 * p01[c] + w11 * p11[c];
        out[c] = (uint8_t)lround(fmin(fmax(v, 0.0), 255.0));
    }
}

#pragma mark - IAAffineTransform

@implementation IAAffineTransform

+ (simd_double3x3)matrixWithParams:(IATransformParams)params imageSize:(NSSize)size {
    double cx = (size.width  - 1.0) * 0.5;
    double cy = (size.height - 1.0) * 0.5;

    // 从右往左读 = 施加顺序:先移到原点,缩放/转置/镜像/旋转,再移回中心,最后平移
    simd_double3x3 M = IAMatrixTranslation(-cx, -cy);
    M = simd_mul(IAMatrixScale(params.scaleX, params.scaleY), M);
    if (params.transpose) {
        M = simd_mul(IAMatrixTranspose2D(), M);
    }
    double mx = params.mirrorHorizontal ? -1.0 : 1.0;
    double my = params.mirrorVertical   ? -1.0 : 1.0;
    if (mx < 0.0 || my < 0.0) {
        M = simd_mul(IAMatrixScale(mx, my), M);
    }
    M = simd_mul(IAMatrixRotation(params.rotationDegrees), M);
    M = simd_mul(IAMatrixTranslation(cx + params.translateX, cy + params.translateY), M);
    return M;
}

+ (nullable IAImageBuffer *)warpImage:(IAImageBuffer *)src
                               matrix:(simd_double3x3)forward
                        interpolation:(IAInterpolation)interpolation
                           canvasMode:(IACanvasMode)canvasMode {
    if (!src) { return nil; }

    NSInteger sw = src.width, sh = src.height;
    NSInteger dw = sw, dh = sh;
    double offsetX = 0.0, offsetY = 0.0;

    if (canvasMode == IACanvasModeFit) {
        // 正向变换四个角,取包围盒作为新画布
        double xs[4], ys[4];
        double cornerX[4] = {0.0, (double)sw - 1.0, 0.0,             (double)sw - 1.0};
        double cornerY[4] = {0.0, 0.0,              (double)sh - 1.0, (double)sh - 1.0};
        for (int i = 0; i < 4; i++) {
            simd_double3 p = simd_mul(forward, (simd_double3){cornerX[i], cornerY[i], 1.0});
            double wgt = (fabs(p.z) < 1e-12) ? 1.0 : p.z;
            xs[i] = p.x / wgt;
            ys[i] = p.y / wgt;
        }
        double minX = xs[0], maxX = xs[0], minY = ys[0], maxY = ys[0];
        for (int i = 1; i < 4; i++) {
            minX = fmin(minX, xs[i]); maxX = fmax(maxX, xs[i]);
            minY = fmin(minY, ys[i]); maxY = fmax(maxY, ys[i]);
        }
        dw = (NSInteger)ceil(maxX - minX) + 1;
        dh = (NSInteger)ceil(maxY - minY) + 1;
        offsetX = minX;
        offsetY = minY;

        const NSInteger kMaxSide = 8192;   // 防止缩放调得过大把内存吃光
        if (dw <= 0 || dh <= 0 || dw > kMaxSide || dh > kMaxSide) { return nil; }
    }

    // 奇异矩阵(例如某方向缩放为 0)信息已丢失,无法反推
    if (fabs(simd_determinant(forward)) < 1e-12) { return nil; }
    simd_double3x3 inverse = simd_inverse(forward);

    IAImageBuffer *dst = [IAImageBuffer bufferWithWidth:dw height:dh];
    if (!dst) { return nil; }

    const uint8_t *sp = src.data;
    uint8_t *dp = dst.data;

    // 反向映射:遍历目标画布,反推源坐标。
    // 若改成遍历源图正向投射,放大时目标画布会出现没被写到的空洞。
    for (NSInteger yd = 0; yd < dh; yd++) {
        for (NSInteger xd = 0; xd < dw; xd++) {
            simd_double3 ps = simd_mul(inverse, (simd_double3){ (double)xd + offsetX,
                                                                (double)yd + offsetY, 1.0 });

            // 齐次归一化:仿射变换下 z 恒为 1,透视变换时才有实际作用
            double wgt = (fabs(ps.z) < 1e-12) ? 1.0 : ps.z;
            double sx = ps.x / wgt;
            double sy = ps.y / wgt;

            uint8_t *out = dp + (yd * dw + xd) * 4;
            if (interpolation == IAInterpolationNearest) {
                IASampleNearest(sp, sw, sh, sx, sy, out);
            } else {
                IASampleBilinear(sp, sw, sh, sx, sy, out);
            }
        }
    }
    return dst;
}

@end
