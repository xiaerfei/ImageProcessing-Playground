//
//  histogram_tests.m
//  ImageAlgorithm
//
//  IAHistogram 的算法层测试(不涉及 UI)。
//
//      cd ImageAlgorithm
//      clang -fobjc-arc -framework Cocoa -I ImageAlgorithm/Algorithm \
//            -o /tmp/histogram_tests Tests/histogram_tests.m ImageAlgorithm/Algorithm/*.m \
//      && /tmp/histogram_tests
//

#import <Cocoa/Cocoa.h>
#import "IAHistogram.h"

static int gFail = 0;
static void check(BOOL cond, NSString *msg) {
    printf("%s  %s\n", cond ? "PASS" : "FAIL", msg.UTF8String);
    if (!cond) { gFail++; }
}

/// 一块常数灰度的平面
static uint8_t *makeFlat(NSInteger n, uint8_t v) {
    uint8_t *p = malloc((size_t)n);
    memset(p, v, (size_t)n);
    return p;
}

int main(void) { @autoreleasepool {

    // ── 统计 → PDF → CDF ────────────────────────────────────────
    {
        uint8_t plane[8] = {0, 0, 128, 128, 128, 128, 255, 255};
        double hist[256], cdf[256];
        [IAHistogram computePlane:plane count:8 into:hist];
        check(hist[0] == 2 && hist[128] == 4 && hist[255] == 2, @"直方图计数正确");

        [IAHistogram normalize:hist];
        check(fabs(hist[128] - 0.5) < 1e-12, @"PDF 归一化:4/8 = 0.5");
        double sum = 0; for (int i = 0; i < 256; i++) { sum += hist[i]; }
        check(fabs(sum - 1.0) < 1e-12, @"PDF 总和为 1");

        [IAHistogram cdfFromPDF:hist into:cdf];
        check(fabs(cdf[0] - 0.25) < 1e-12, @"CDF[0] = 2/8");
        check(fabs(cdf[128] - 0.75) < 1e-12, @"CDF[128] = 6/8");
        check(cdf[255] == 1.0, @"CDF 末项恰为 1(浮点尾差已补齐)");
        BOOL mono = YES;
        for (int i = 1; i < 256; i++) { if (cdf[i] < cdf[i-1]) { mono = NO; } }
        check(mono, @"CDF 单调不减");
    }

    // ── 均衡化 ──────────────────────────────────────────────────
    {
        // 均匀分布的输入,均衡化后应该基本不动(它已经是平的了)
        uint8_t ramp[256];
        for (int i = 0; i < 256; i++) { ramp[i] = (uint8_t)i; }
        double hist[256], cdf[256]; uint8_t lut[256];
        [IAHistogram computePlane:ramp count:256 into:hist];
        [IAHistogram normalize:hist];
        [IAHistogram cdfFromPDF:hist into:cdf];
        [IAHistogram equalizeLUTFromCDF:cdf into:lut];
        int maxDiff = 0;
        for (int i = 0; i < 256; i++) { maxDiff = MAX(maxDiff, abs(lut[i] - i)); }
        check(maxDiff <= 1, ([NSString stringWithFormat:@"均匀分布均衡化近似恒等(最大偏差 %d)", maxDiff]));

        BOOL mono = YES;
        for (int i = 1; i < 256; i++) { if (lut[i] < lut[i-1]) { mono = NO; } }
        check(mono, @"均衡化映射表单调 —— 亮暗顺序不会被颠倒");
        check(lut[255] == 255, @"最亮值映射到 255,动态范围铺满");
    }
    {
        // 挤在窄区间的输入,均衡化后应该被摊开
        uint8_t narrow[300];
        for (int i = 0; i < 300; i++) { narrow[i] = (uint8_t)(100 + i % 10); }
        double hist[256], cdf[256]; uint8_t lut[256];
        [IAHistogram computePlane:narrow count:300 into:hist];
        [IAHistogram normalize:hist];
        [IAHistogram cdfFromPDF:hist into:cdf];
        [IAHistogram equalizeLUTFromCDF:cdf into:lut];
        check(lut[109] - lut[100] > 200,
              ([NSString stringWithFormat:@"窄区间被摊开:100~109 → %d~%d", lut[100], lut[109]]));
    }

    // ── 规定化 ──────────────────────────────────────────────────
    {
        uint8_t ramp[256];
        for (int i = 0; i < 256; i++) { ramp[i] = (uint8_t)i; }
        double hist[256], srcCDF[256], tgt[256], tgtCDF[256];
        uint8_t lutSpec[256], lutEq[256];
        [IAHistogram computePlane:ramp count:256 into:hist];
        [IAHistogram normalize:hist];
        [IAHistogram cdfFromPDF:hist into:srcCDF];

        // 规定化到"均匀",结果应当与均衡化一致 —— 两者本就同源
        [IAHistogram targetPDF:IAHistogramTargetUniform into:tgt];
        [IAHistogram cdfFromPDF:tgt into:tgtCDF];
        [IAHistogram specifyLUTFromCDF:srcCDF toCDF:tgtCDF into:lutSpec];
        [IAHistogram equalizeLUTFromCDF:srcCDF into:lutEq];
        int maxDiff = 0;
        for (int i = 0; i < 256; i++) { maxDiff = MAX(maxDiff, abs(lutSpec[i] - lutEq[i])); }
        check(maxDiff <= 1,
              ([NSString stringWithFormat:@"规定化到均匀 == 均衡化(最大偏差 %d)", maxDiff]));

        // 规定化到高斯:按定义验 —— 输出分布应当贴近目标分布。
        // (别去验"两端收进来":σ=0.22 的高斯在 x=0 处密度还有 0.076,
        //  尾巴被截在 [0,1] 内并没消失,极端值本就不该收缩多少)
        [IAHistogram targetPDF:IAHistogramTargetGaussian into:tgt];
        [IAHistogram cdfFromPDF:tgt into:tgtCDF];
        [IAHistogram specifyLUTFromCDF:srcCDF toCDF:tgtCDF into:lutSpec];

        uint8_t mapped[256];
        for (int i = 0; i < 256; i++) { mapped[i] = lutSpec[ramp[i]]; }
        double outPDF[256];
        [IAHistogram computePlane:mapped count:256 into:outPDF];
        [IAHistogram normalize:outPDF];

        // 比 CDF 而不是 PDF。逐格比 PDF 在这里没有意义:输入是 256 个值各 1 像素,
        // 每个输出 bin 的计数只能是整数,而高斯中心的期望值是 1.84 个像素 ——
        // 这个误差下限拆不掉,正是"并列名次拆不开"(文档第六节)。
        // CDF 是累积量,离散化的抖动会互相抵消,才看得出匹配得好不好。
        double outCDF[256];
        [IAHistogram cdfFromPDF:outPDF into:outCDF];
        double ksSpec = 0, ksIdentity = 0;
        for (int i = 0; i < 256; i++) {
            ksSpec     = fmax(ksSpec,     fabs(outCDF[i] - tgtCDF[i]));
            ksIdentity = fmax(ksIdentity, fabs(srcCDF[i] - tgtCDF[i]));   // 不变换时的差距
        }
        check(ksSpec < 0.02 && ksSpec < ksIdentity * 0.2,
              ([NSString stringWithFormat:@"规定化后 CDF 贴合目标:KS 距离 %.4f,不变换是 %.4f",
                ksSpec, ksIdentity]));
        check(lutSpec[0] < lutSpec[128] && lutSpec[128] < lutSpec[255],
              @"规定化到高斯:映射后次序不变");
        BOOL mono = YES;
        for (int i = 1; i < 256; i++) { if (lutSpec[i] < lutSpec[i-1]) { mono = NO; } }
        check(mono, @"规定化映射表单调");
    }

    // ── 目标分布 ────────────────────────────────────────────────
    {
        double pdf[256];
        for (int t = 0; t <= IAHistogramTargetDarkSkew; t++) {
            [IAHistogram targetPDF:(IAHistogramTarget)t into:pdf];
            double sum = 0; BOOL nonneg = YES;
            for (int i = 0; i < 256; i++) { sum += pdf[i]; if (pdf[i] < 0) { nonneg = NO; } }
            check(fabs(sum - 1.0) < 1e-9 && nonneg,
                  ([NSString stringWithFormat:@"目标分布 %d 非负且总和为 1", t]));
        }
        [IAHistogram targetPDF:IAHistogramTargetBimodal into:pdf];
        check(pdf[64] > pdf[128] && pdf[191] > pdf[128], @"双峰:两个峰高于中间的谷");
        [IAHistogram targetPDF:IAHistogramTargetBrightSkew into:pdf];
        check(pdf[200] > pdf[50], @"偏亮:亮端密度更高");
    }

    // ── 百分位拉伸 ──────────────────────────────────────────────
    {
        // 100~150 的主体 + 一个孤零零的亮点:拉伸应该忽略这个离群点
        uint8_t data[1000];
        for (int i = 0; i < 999; i++) { data[i] = (uint8_t)(100 + i % 51); }
        data[999] = 255;
        double hist[256], cdf[256]; uint8_t lut[256];
        [IAHistogram computePlane:data count:1000 into:hist];
        [IAHistogram normalize:hist];
        [IAHistogram cdfFromPDF:hist into:cdf];

        [IAHistogram stretchLUTFromCDF:cdf lowPct:1.0 highPct:1.0 into:lut];
        check(lut[100] == 0 && lut[150] == 255,
              ([NSString stringWithFormat:@"1%% 拉伸忽略离群亮点:100→%d, 150→%d", lut[100], lut[150]]));

        [IAHistogram stretchLUTFromCDF:cdf lowPct:0.0 highPct:0.0 into:lut];
        check(lut[150] < 200,
              ([NSString stringWithFormat:@"0%% 拉伸被离群点绑架:150→%d(远不到 255)", lut[150]]));
    }

    // ── CLAHE ───────────────────────────────────────────────────
    {
        // 常数平面:任何映射都不该造出纹理来
        NSInteger n = 64 * 64;
        uint8_t *flat = makeFlat(n, 120);
        [IAHistogram claheOnPlane:flat width:64 height:64 tilesX:8 tilesY:8 clipLimit:2.0];
        BOOL uniform = YES;
        for (NSInteger i = 1; i < n; i++) { if (flat[i] != flat[0]) { uniform = NO; break; } }
        check(uniform, ([NSString stringWithFormat:@"常数平面 CLAHE 后仍是常数(值 %d)", flat[0]]));
        free(flat);
    }
    {
        // 左暗右亮:全局均衡化救不了两边,CLAHE 应该让两边各自展开
        NSInteger w = 128, h = 64;
        uint8_t *img = malloc((size_t)(w * h));
        for (NSInteger y = 0; y < h; y++)
            for (NSInteger x = 0; x < w; x++)
                // 每半边内部只有 ±8 的微弱起伏,肉眼几乎看不出细节
                img[y * w + x] = (uint8_t)((x < w / 2 ? 40 : 200) + (x % 16) / 2);

        double before = 0, after = 0;
        // 只看左半边的标准差 —— 局部对比度是否被提起来
        double mean = 0;
        for (NSInteger y = 0; y < h; y++) for (NSInteger x = 0; x < w/2; x++) { mean += img[y*w+x]; }
        mean /= (h * w / 2);
        for (NSInteger y = 0; y < h; y++) for (NSInteger x = 0; x < w/2; x++) {
            double d = img[y*w+x] - mean; before += d * d;
        }
        before = sqrt(before / (h * w / 2));

        [IAHistogram claheOnPlane:img width:w height:h tilesX:8 tilesY:4 clipLimit:4.0];

        mean = 0;
        for (NSInteger y = 0; y < h; y++) for (NSInteger x = 0; x < w/2; x++) { mean += img[y*w+x]; }
        mean /= (h * w / 2);
        for (NSInteger y = 0; y < h; y++) for (NSInteger x = 0; x < w/2; x++) {
            double d = img[y*w+x] - mean; after += d * d;
        }
        after = sqrt(after / (h * w / 2));
        check(after > before * 2.0,
              ([NSString stringWithFormat:@"CLAHE 提起暗部局部对比度:std %.2f → %.2f", before, after]));
        free(img);
    }
    {
        // clipLimit 越大越接近 AHE:输出的对比度应当单调变强
        NSInteger w = 96, h = 96;
        double stds[3]; double clips[3] = {1.0, 4.0, 40.0};
        for (int k = 0; k < 3; k++) {
            uint8_t *img = malloc((size_t)(w * h));
            srandom(42);
            for (NSInteger i = 0; i < w * h; i++) { img[i] = (uint8_t)(118 + (random() % 21)); }
            [IAHistogram claheOnPlane:img width:w height:h tilesX:4 tilesY:4 clipLimit:clips[k]];
            double mean = 0, var = 0;
            for (NSInteger i = 0; i < w * h; i++) { mean += img[i]; }
            mean /= (w * h);
            for (NSInteger i = 0; i < w * h; i++) { double d = img[i] - mean; var += d * d; }
            stds[k] = sqrt(var / (w * h));
            free(img);
        }
        check(stds[0] < stds[1] && stds[1] < stds[2],
              ([NSString stringWithFormat:@"clipLimit 越大对比度越强(也越放大噪声):%.1f → %.1f → %.1f",
                stds[0], stds[1], stds[2]]));
    }
    {
        // tile 数为 1 时,CLAHE 应当退化成"限制过的全局均衡化"
        NSInteger n = 64 * 64;
        uint8_t *a = malloc((size_t)n);
        srandom(7);
        for (NSInteger i = 0; i < n; i++) { a[i] = (uint8_t)(random() % 256); }
        uint8_t *b = malloc((size_t)n);
        memcpy(b, a, (size_t)n);

        [IAHistogram claheOnPlane:a width:64 height:64 tilesX:1 tilesY:1 clipLimit:1000.0];
        double hist[256], cdf[256]; uint8_t lut[256];
        [IAHistogram computePlane:b count:n into:hist];
        [IAHistogram normalize:hist];
        [IAHistogram cdfFromPDF:hist into:cdf];
        [IAHistogram equalizeLUTFromCDF:cdf into:lut];
        int maxDiff = 0;
        for (NSInteger i = 0; i < n; i++) { maxDiff = MAX(maxDiff, abs(a[i] - lut[b[i]])); }
        check(maxDiff <= 1,
              ([NSString stringWithFormat:@"tile=1 且不限幅 == 全局均衡化(最大偏差 %d)", maxDiff]));
        free(a); free(b);
    }

    // ── 亮度平面往返 ────────────────────────────────────────────
    {
        IAImageBuffer *src = [IAImageBuffer bufferWithWidth:4 height:1];
        uint8_t colors[4][3] = {{200,50,50}, {50,200,50}, {50,50,200}, {128,128,128}};
        for (int i = 0; i < 4; i++) {
            uint8_t *p = src.data + i * 4;
            p[0] = colors[i][0]; p[1] = colors[i][1]; p[2] = colors[i][2]; p[3] = 255;
        }
        uint8_t *luma = [IAHistogram lumaPlaneFrom:src];
        check(luma[3] == 128, ([NSString stringWithFormat:@"灰色的亮度还是自己:%d", luma[3]]));

        IAImageBuffer *dst = [IAImageBuffer bufferWithWidth:4 height:1];
        [IAHistogram applyLumaPlane:luma to:dst from:src];   // 亮度未改动 → 应还原原图
        BOOL same = YES;
        for (int i = 0; i < 4 * 4; i++) { if (abs(dst.data[i] - src.data[i]) > 1) { same = NO; } }
        check(same, @"亮度不变时往返还原原图(色度未被破坏)");

        // 把亮度整体抬高,色相不该跑掉:R/G/B 的相对次序保持
        for (int i = 0; i < 4; i++) { luma[i] = (uint8_t)MIN(255, luma[i] + 40); }
        [IAHistogram applyLumaPlane:luma to:dst from:src];
        uint8_t *p0 = dst.data;
        check(p0[0] > p0[1] && p0[1] == p0[2], @"提亮后红色仍是红色(R 最大,G/B 相等)");
        free(luma);
    }

    printf("\n%s (%d 处失败)\n", gFail == 0 ? "全部通过" : "有失败", gFail);
    return gFail == 0 ? 0 : 1;
} }
