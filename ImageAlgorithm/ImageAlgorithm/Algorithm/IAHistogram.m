//
//  IAHistogram.m
//  ImageAlgorithm
//

#import "IAHistogram.h"

// Rec.601 亮度权重。和 IAIntensityModule 的"转灰度"用同一套,
// 两个模块对"亮度"的定义必须一致,否则对比实验会得出错误结论。
static const double kR = 0.299, kG = 0.587, kB = 0.114;

static inline uint8_t clamp8(double v) {
    return (uint8_t)lround(fmin(fmax(v, 0.0), 255.0));
}

@implementation IAHistogram

#pragma mark - 统计

+ (void)computePlane:(const uint8_t *)plane count:(NSInteger)count into:(double[256])hist {
    memset(hist, 0, sizeof(double) * 256);
    for (NSInteger i = 0; i < count; i++) { hist[plane[i]] += 1.0; }
}

+ (void)normalize:(double[256])hist {
    double sum = 0.0;
    for (int i = 0; i < 256; i++) { sum += hist[i]; }
    if (sum <= 0.0) { return; }
    for (int i = 0; i < 256; i++) { hist[i] /= sum; }
}

+ (void)cdfFromPDF:(const double[256])pdf into:(double[256])cdf {
    double run = 0.0;
    for (int i = 0; i < 256; i++) { run += pdf[i]; cdf[i] = run; }
    // 浮点累加的尾差会让末项停在 0.9999997,映射表就少了最亮的那一级。
    // CDF 的定义要求末项恰为 1,这里补齐。
    if (cdf[255] > 0.0) {
        double fix = 1.0 / cdf[255];
        for (int i = 0; i < 256; i++) { cdf[i] *= fix; }
    }
}

#pragma mark - 映射表

+ (void)equalizeLUTFromCDF:(const double[256])cdf into:(uint8_t[256])lut {
    for (int r = 0; r < 256; r++) { lut[r] = clamp8(255.0 * cdf[r]); }
}

+ (void)specifyLUTFromCDF:(const double[256])srcCDF
                    toCDF:(const double[256])dstCDF
                     into:(uint8_t[256])lut {
    // 两条 CDF 都单调不减,所以 s 指针只会往前走,整体 O(512) 而不是 O(256·log256)
    int s = 0;
    for (int r = 0; r < 256; r++) {
        while (s < 255 && dstCDF[s] < srcCDF[r]) { s++; }
        // s 是第一个 dstCDF ≥ srcCDF[r] 的位置;看看前一格是不是更接近
        if (s > 0 && fabs(dstCDF[s - 1] - srcCDF[r]) < fabs(dstCDF[s] - srcCDF[r])) {
            lut[r] = (uint8_t)(s - 1);
        } else {
            lut[r] = (uint8_t)s;
        }
    }
}

+ (void)targetPDF:(IAHistogramTarget)target into:(double[256])pdf {
    for (int i = 0; i < 256; i++) {
        double x = i / 255.0;
        double v;
        switch (target) {
            case IAHistogramTargetGaussian: {
                double d = (x - 0.5) / 0.22;
                v = exp(-0.5 * d * d);
                break;
            }
            case IAHistogramTargetBimodal: {
                double d1 = (x - 0.25) / 0.10, d2 = (x - 0.75) / 0.10;
                v = exp(-0.5 * d1 * d1) + exp(-0.5 * d2 * d2);
                break;
            }
            // 幂函数偏斜:x^2 把密度堆到亮端,sqrt 堆到暗端
            case IAHistogramTargetBrightSkew: v = x * x + 0.02;         break;
            case IAHistogramTargetDarkSkew:   v = (1 - x) * (1 - x) + 0.02; break;
            case IAHistogramTargetUniform:
            default:                          v = 1.0;                  break;
        }
        pdf[i] = v;
    }
    [self normalize:pdf];
}

+ (void)stretchLUTFromCDF:(const double[256])cdf
                   lowPct:(double)lowPct
                  highPct:(double)highPct
                     into:(uint8_t[256])lut {
    double lo = lowPct / 100.0, hi = 1.0 - highPct / 100.0;
    int rLow = 0, rHigh = 255;
    for (int i = 0; i < 256; i++) { if (cdf[i] >= lo) { rLow = i; break; } }
    for (int i = 255; i >= 0; i--) { if (cdf[i] <= hi) { rHigh = i; break; } }
    if (rHigh <= rLow) { rLow = 0; rHigh = 255; }   // 参数过激时退化成恒等,不要除以 0

    for (int r = 0; r < 256; r++) {
        lut[r] = clamp8((r - rLow) * 255.0 / (rHigh - rLow));
    }
}

#pragma mark - CLAHE

/// 削顶回填:把超过 clipAbs 的部分砍掉,总量均摊回 256 个格子。
/// 砍的是"柱子高度",而柱子高度决定 CDF 的斜率,CDF 的斜率就是对比度增益 ——
/// 所以这一步的名字才叫 Contrast **Limited**。
static void clipAndRedistribute(double hist[256], double clipAbs) {
    double excess = 0.0;
    for (int i = 0; i < 256; i++) {
        if (hist[i] > clipAbs) { excess += hist[i] - clipAbs; hist[i] = clipAbs; }
    }
    if (excess <= 0.0) { return; }
    // 回填后个别格子可能又冒过 clipAbs,但溢出量已经很小,
    // OpenCV 同样只做一轮,不迭代到收敛
    double inc = excess / 256.0;
    for (int i = 0; i < 256; i++) { hist[i] += inc; }
}

+ (void)claheOnPlane:(uint8_t *)plane
               width:(NSInteger)width
              height:(NSInteger)height
              tilesX:(NSInteger)tilesX
              tilesY:(NSInteger)tilesY
           clipLimit:(double)clipLimit {
    if (width <= 0 || height <= 0 || tilesX <= 0 || tilesY <= 0) { return; }
    tilesX = MIN(tilesX, width);
    tilesY = MIN(tilesY, height);

    // 向上取整,最后一块可能小一点;下面统计时用真实边界,不会越界
    NSInteger tileW = (width  + tilesX - 1) / tilesX;
    NSInteger tileH = (height + tilesY - 1) / tilesY;

    // 每块一张 256 项映射表
    uint8_t *luts = calloc((size_t)(tilesX * tilesY * 256), sizeof(uint8_t));
    if (!luts) { return; }

    for (NSInteger ty = 0; ty < tilesY; ty++) {
        for (NSInteger tx = 0; tx < tilesX; tx++) {
            NSInteger x0 = tx * tileW, x1 = MIN(x0 + tileW, width);
            NSInteger y0 = ty * tileH, y1 = MIN(y0 + tileH, height);
            NSInteger area = (x1 - x0) * (y1 - y0);
            if (area <= 0) { continue; }

            double hist[256] = {0};
            for (NSInteger y = y0; y < y1; y++) {
                const uint8_t *row = plane + y * width;
                for (NSInteger x = x0; x < x1; x++) { hist[row[x]] += 1.0; }
            }

            // clipLimit 以"平均柱高"为单位:area/256 是这一块摊平后每格该有的高度。
            // 所以 clipLimit=1 就是削到全平,=40 基本等于不限制(即退化成 AHE)。
            clipAndRedistribute(hist, fmax(clipLimit, 1.0) * (double)area / 256.0);

            uint8_t *lut = luts + (ty * tilesX + tx) * 256;
            double run = 0.0;
            for (int i = 0; i < 256; i++) {
                run += hist[i];
                lut[i] = clamp8(255.0 * run / (double)area);
            }
        }
    }

    // 逐像素在四张相邻的映射表之间双线性插值。
    // 插的是"映射结果",不是"映射表" —— 两者数值上等价(线性组合可交换),
    // 但按结果插值省掉了为每个像素合成一张 256 项表的开销。
    // 不插值的话,块与块的边界会出现肉眼可见的方格接缝。
    for (NSInteger y = 0; y < height; y++) {
        // 像素落在哪两排块中心之间:块 j 的中心在 (j+0.5)*tileH
        double gy = ((double)y + 0.5) / (double)tileH - 0.5;
        NSInteger j0 = (NSInteger)floor(gy);
        double fy = gy - (double)j0;
        // 边缘半块内 clamp 成同一排 → 角落不插值、边缘单向插值,与 CLAHE 标准一致
        NSInteger j0c = MIN(MAX(j0, (NSInteger)0), tilesY - 1);
        NSInteger j1c = MIN(MAX(j0 + 1, (NSInteger)0), tilesY - 1);

        uint8_t *row = plane + y * width;
        for (NSInteger x = 0; x < width; x++) {
            double gx = ((double)x + 0.5) / (double)tileW - 0.5;
            NSInteger i0 = (NSInteger)floor(gx);
            double fx = gx - (double)i0;
            NSInteger i0c = MIN(MAX(i0, (NSInteger)0), tilesX - 1);
            NSInteger i1c = MIN(MAX(i0 + 1, (NSInteger)0), tilesX - 1);

            uint8_t v = row[x];
            double v00 = luts[(j0c * tilesX + i0c) * 256 + v];
            double v10 = luts[(j0c * tilesX + i1c) * 256 + v];
            double v01 = luts[(j1c * tilesX + i0c) * 256 + v];
            double v11 = luts[(j1c * tilesX + i1c) * 256 + v];

            double top = v00 + (v10 - v00) * fx;
            double bot = v01 + (v11 - v01) * fx;
            row[x] = clamp8(top + (bot - top) * fy);
        }
    }
    free(luts);
}

#pragma mark - 通道工具

+ (uint8_t *)lumaPlaneFrom:(IAImageBuffer *)src {
    NSInteger count = src.width * src.height;
    uint8_t *plane = malloc((size_t)count);
    if (!plane) { return NULL; }
    const uint8_t *sp = src.data;
    for (NSInteger i = 0; i < count; i++) {
        const uint8_t *p = sp + i * 4;
        plane[i] = clamp8(kR * p[0] + kG * p[1] + kB * p[2]);
    }
    return plane;
}

+ (void)applyLumaPlane:(const uint8_t *)luma to:(IAImageBuffer *)dst from:(IAImageBuffer *)src {
    NSInteger count = src.width * src.height;
    const uint8_t *sp = src.data;
    uint8_t *dp = dst.data;
    for (NSInteger i = 0; i < count; i++) {
        const uint8_t *s = sp + i * 4;
        uint8_t *d = dp + i * 4;
        double y0 = kR * s[0] + kG * s[1] + kB * s[2];
        double y1 = luma[i];
        // 保色度的写法:算出色差分量再套回新亮度。
        // 等价于在 YCbCr 里只改 Y —— 展开后就是"每个通道加上同一个亮度增量",
        // 但增量按通道原值的偏离量走,饱和区不会翻车。
        d[0] = clamp8(y1 + (s[0] - y0));
        d[1] = clamp8(y1 + (s[1] - y0));
        d[2] = clamp8(y1 + (s[2] - y0));
        d[3] = s[3];
    }
}

@end
