//
//  IAHistogramModule.m
//  ImageAlgorithm
//
//  第 3 章 3.3 直方图处理。
//
//  和"灰度变换"那一章的根本区别:那边的映射表是你手工调参数调出来的
//  (γ 给多少、a 和 b 给多少),这边的映射表是**从图像自己的统计量算出来的** ——
//  同一份参数换一张图,得到的曲线完全不同。这就是"自适应"。
//
//  面板上那两张直方图是这个模块的主角:一次能同时看到
//  原图的分布、结果的分布、以及把前者变成后者的那条映射曲线。
//

#import "IAHistogramModule.h"
#import "IAHistogram.h"
#import "IAHistogramView.h"

static NSString * const kMode      = @"mode";
static NSString * const kColorMode = @"colorMode";
static NSString * const kTarget    = @"target";
static NSString * const kClipLimit = @"clipLimit";
static NSString * const kTiles     = @"tiles";
static NSString * const kLowPct    = @"lowPct";
static NSString * const kHighPct   = @"highPct";
static NSString * const kShowCDF   = @"showCDF";
static NSString * const kShowLUT   = @"showLUT";
static NSString * const kLogScale  = @"logScale";

@implementation IAHistogramModule {
    IAHistogramView *_srcView;
    IAHistogramView *_dstView;
    NSString *_statusLine;
}

+ (NSString *)title { return @"直方图变换"; }
+ (NSString *)subtitle { return @"第 3 章 · 第 5 周"; }
- (NSString *)resultTitle { return @"变换结果"; }

#pragma mark - 参数

- (void)buildParameters:(IAParameterBuilder *)builder {
    [builder addSection:@"直方图"];
    _srcView = [[IAHistogramView alloc] init];
    _srcView.caption = @"原图";
    [builder addCustomView:_srcView height:96];
    _dstView = [[IAHistogramView alloc] init];
    _dstView.caption = @"结果";
    [builder addCustomView:_dstView height:96];

    [builder addCheckbox:kShowCDF  title:@"叠加 CDF(蓝)" value:YES];
    [builder addCheckbox:kShowLUT  title:@"叠加映射曲线(黄虚线)" value:YES];
    [builder addCheckbox:kLogScale title:@"纵轴对数刻度" value:NO];
    [builder addNote:@"柱子是 PDF,蓝线是它的累加(CDF),黄线是这次用的映射表。"
                      "选“全局均衡化”时黄线会和蓝线重合 —— 因为均衡化的映射表就是 CDF 本身。"];

    [builder addSeparator];
    [builder addSection:@"变换方式"];
    [builder addPopUp:kMode
                items:@[@"原图(只看直方图)", @"全局均衡化", @"CLAHE", @"规定化", @"百分位拉伸"]
                value:IAHistogramModeEqualize];

    [builder addSeparator];
    [builder addSection:@"彩色图怎么处理"];
    [builder addSegmented:kColorMode items:@[@"只动亮度", @"分通道", @"转灰度"] value:IAHistogramColorModeLuma];
    [builder addNote:@"“分通道”是错误示范:R/G/B 各自算一条映射曲线,三条曲线形状不同,"
                      "颜色必然跑掉。切过去看一眼偏色有多严重。"];

    [builder addSeparator];
    [builder addSection:@"CLAHE"];
    [builder addSlider:kTiles     label:@"分块" min:1  max:16 value:8   format:@"%.0f×%.0f"];
    [builder addSlider:kClipLimit label:@"削顶" min:1  max:40 value:2.0 format:@"%.1f"];
    [builder addNote:@"削顶以“摊平后的平均柱高”为单位:1.0 = 削到全平,40 ≈ 不限制(退化成 AHE,"
                      "平坦区的噪声会被放大几十倍)。分块越多越局部,块间用双线性插值消接缝。"];

    [builder addSeparator];
    [builder addSection:@"规定化目标"];
    [builder addPopUp:kTarget
                items:@[@"均匀(等于均衡化)", @"高斯(中间调厚)", @"双峰", @"偏亮", @"偏暗"]
                value:IAHistogramTargetGaussian];
    [builder addNote:@"宿主只能载入一张图,所以目标分布是算出来的而不是取自参考图。"
                      "选“均匀”会得到和全局均衡化一样的结果 —— 两者本就同源。"];

    [builder addSeparator];
    [builder addSection:@"百分位拉伸(线性对照组)"];
    [builder addSlider:kLowPct  label:@"暗端丢弃 %" min:0 max:10 value:1.0 format:@"%.1f"];
    [builder addSlider:kHighPct label:@"亮端丢弃 %" min:0 max:10 value:1.0 format:@"%.1f"];
    [builder addNote:@"只把两个端点挪一挪,曲线始终是直线 —— 对比均衡化那条弯曲的映射线,"
                      "就知道“线性拉伸”和“按密度重排”差在哪。"];
}

- (nullable NSString *)extraStatus { return _statusLine; }

#pragma mark - 算法

- (nullable IAImageBuffer *)processImage:(IAImageBuffer *)source {
    IAHistogramMode mode = (IAHistogramMode)[self.parameters integerForKey:kMode];
    IAHistogramColorMode colorMode = (IAHistogramColorMode)[self.parameters integerForKey:kColorMode];

    IAImageBuffer *dst = [IAImageBuffer bufferWithWidth:source.width height:source.height];
    if (!dst) { return nil; }
    NSInteger count = source.width * source.height;
    if (count <= 0) { return nil; }

    uint8_t lutForDisplay[256];
    for (int i = 0; i < 256; i++) { lutForDisplay[i] = (uint8_t)i; }

    if (colorMode == IAHistogramColorModePerChannel) {
        [self processPerChannel:source into:dst mode:mode displayLUT:lutForDisplay];
    } else {
        [self processLuma:source into:dst mode:mode colorMode:colorMode displayLUT:lutForDisplay];
    }

    [self refreshHistogramViewsFrom:source to:dst lut:lutForDisplay];
    return dst;
}

/// 正路:只在亮度平面上做,色度原样搬过去
- (void)processLuma:(IAImageBuffer *)src
               into:(IAImageBuffer *)dst
               mode:(IAHistogramMode)mode
          colorMode:(IAHistogramColorMode)colorMode
         displayLUT:(uint8_t[256])displayLUT {
    NSInteger count = src.width * src.height;
    uint8_t *plane = [IAHistogram lumaPlaneFrom:src];
    if (!plane) { return; }

    if (mode == IAHistogramModeCLAHE) {
        NSInteger tiles = (NSInteger)lround([self.parameters doubleForKey:kTiles]);
        double clip = [self.parameters doubleForKey:kClipLimit];
        // CLAHE 每块一张映射表,没有"唯一的一条曲线"可画。
        // 黄线在这里画的是**全局均衡化**的曲线,当对照用:
        // 看这条全局曲线在暗部有多陡,再看 CLAHE 的结果暗部并没有跟着糊掉,
        // 就知道"分块 + 削顶"到底改变了什么。
        [self buildGlobalLUT:plane count:count mode:IAHistogramModeEqualize into:displayLUT];
        [IAHistogram claheOnPlane:plane width:src.width height:src.height
                           tilesX:tiles tilesY:tiles clipLimit:clip];
        _statusLine = [NSString stringWithFormat:@"CLAHE  分块 %ld×%ld,削顶 %.1f×平均柱高",
                       (long)tiles, (long)tiles, clip];
    } else {
        [self buildGlobalLUT:plane count:count mode:mode into:displayLUT];
        for (NSInteger i = 0; i < count; i++) { plane[i] = displayLUT[plane[i]]; }
    }

    if (colorMode == IAHistogramColorModeGray) {
        uint8_t *dp = dst.data;
        const uint8_t *sp = src.data;
        for (NSInteger i = 0; i < count; i++) {
            dp[i * 4] = dp[i * 4 + 1] = dp[i * 4 + 2] = plane[i];
            dp[i * 4 + 3] = sp[i * 4 + 3];
        }
    } else {
        [IAHistogram applyLumaPlane:plane to:dst from:src];
    }
    free(plane);
}

/// 错误示范:R/G/B 各算各的映射表
- (void)processPerChannel:(IAImageBuffer *)src
                     into:(IAImageBuffer *)dst
                     mode:(IAHistogramMode)mode
               displayLUT:(uint8_t[256])displayLUT {
    NSInteger count = src.width * src.height;
    uint8_t *plane = malloc((size_t)count);
    if (!plane) { return; }
    const uint8_t *sp = src.data;
    uint8_t *dp = dst.data;

    for (int c = 0; c < 3; c++) {
        for (NSInteger i = 0; i < count; i++) { plane[i] = sp[i * 4 + c]; }

        if (mode == IAHistogramModeCLAHE) {
            NSInteger tiles = (NSInteger)lround([self.parameters doubleForKey:kTiles]);
            double clip = [self.parameters doubleForKey:kClipLimit];
            // 分通道 CLAHE:偏色比全局均衡化更花 —— 每个通道、每一块都各走各的
            [IAHistogram claheOnPlane:plane width:src.width height:src.height
                               tilesX:tiles tilesY:tiles clipLimit:clip];
            for (NSInteger i = 0; i < count; i++) { dp[i * 4 + c] = plane[i]; }
            if (c == 1) { [self buildGlobalLUT:plane count:count mode:IAHistogramModeEqualize into:displayLUT]; }
        } else {
            uint8_t lut[256];
            [self buildGlobalLUT:plane count:count mode:mode into:lut];
            for (NSInteger i = 0; i < count; i++) { dp[i * 4 + c] = lut[sp[i * 4 + c]]; }
            // 面板上只画得下一条曲线,用绿色通道的 —— 它在亮度里权重最大(0.587)
            if (c == 1) { memcpy(displayLUT, lut, 256); }
        }
    }
    for (NSInteger i = 0; i < count; i++) { dp[i * 4 + 3] = sp[i * 4 + 3]; }
    free(plane);
    _statusLine = (mode == IAHistogramModeIdentity)
        ? @"未做变换,只统计直方图"
        : @"分通道处理:R/G/B 各算各的映射曲线,偏色由此而来";
}

/// 统一的"算一张全局映射表"入口:统计 → PDF → CDF → 按 mode 生成 LUT
- (void)buildGlobalLUT:(const uint8_t *)plane
                 count:(NSInteger)count
                  mode:(IAHistogramMode)mode
                  into:(uint8_t[256])lut {
    double hist[256], cdf[256];
    [IAHistogram computePlane:plane count:count into:hist];
    [IAHistogram normalize:hist];
    [IAHistogram cdfFromPDF:hist into:cdf];

    switch (mode) {
        case IAHistogramModeEqualize:
            [IAHistogram equalizeLUTFromCDF:cdf into:lut];
            _statusLine = @"全局均衡化  映射表 = 自己的 CDF";
            break;
        case IAHistogramModeSpecify: {
            IAHistogramTarget target = (IAHistogramTarget)[self.parameters integerForKey:kTarget];
            double tgt[256], tgtCDF[256];
            [IAHistogram targetPDF:target into:tgt];
            [IAHistogram cdfFromPDF:tgt into:tgtCDF];
            [IAHistogram specifyLUTFromCDF:cdf toCDF:tgtCDF into:lut];
            _statusLine = @"规定化  对每个 r 找使目标 CDF 最接近的 s";
            break;
        }
        case IAHistogramModeStretch: {
            double lo = [self.parameters doubleForKey:kLowPct];
            double hi = [self.parameters doubleForKey:kHighPct];
            [IAHistogram stretchLUTFromCDF:cdf lowPct:lo highPct:hi into:lut];
            _statusLine = [NSString stringWithFormat:@"百分位拉伸  丢掉最暗 %.1f%% / 最亮 %.1f%%", lo, hi];
            break;
        }
        case IAHistogramModeCLAHE:      // 走不到这里,CLAHE 在 processLuma 里分流了
        case IAHistogramModeIdentity:
        default:
            for (int i = 0; i < 256; i++) { lut[i] = (uint8_t)i; }
            _statusLine = @"未做变换,只统计直方图";
            break;
    }
}

#pragma mark - 面板刷新

- (void)refreshHistogramViewsFrom:(IAImageBuffer *)src to:(IAImageBuffer *)dst lut:(const uint8_t *)lut {
    BOOL showCDF = [self.parameters boolForKey:kShowCDF];
    BOOL showLUT = [self.parameters boolForKey:kShowLUT];
    BOOL logScale = [self.parameters boolForKey:kLogScale];

    [self fillView:_srcView from:src caption:@"原图" cdf:showCDF lut:showLUT ? lut : NULL];
    // 结果那张不画映射曲线:曲线描述的是"从原图到结果"的关系,挂在原图那张才讲得通
    [self fillView:_dstView from:dst caption:@"结果" cdf:showCDF lut:NULL];
    _srcView.logScale = logScale;
    _dstView.logScale = logScale;
}

- (void)fillView:(IAHistogramView *)view
            from:(IAImageBuffer *)buffer
         caption:(NSString *)caption
             cdf:(BOOL)wantCDF
             lut:(const uint8_t *)lut {
    uint8_t *plane = [IAHistogram lumaPlaneFrom:buffer];
    if (!plane) { return; }
    NSInteger count = buffer.width * buffer.height;

    double hist[256], cdf[256];
    [IAHistogram computePlane:plane count:count into:hist];
    [IAHistogram normalize:hist];
    [IAHistogram cdfFromPDF:hist into:cdf];

    // 均值与标准差:标准差就是文档里说的 RMS 对比度,均衡化后它应该明显变大
    double mean = 0.0, var = 0.0;
    for (int i = 0; i < 256; i++) { mean += i * hist[i]; }
    for (int i = 0; i < 256; i++) { double d = i - mean; var += d * d * hist[i]; }

    view.caption = caption;
    view.detail = [NSString stringWithFormat:@"均值 %.0f  σ %.1f", mean, sqrt(var)];
    [view setPDF:hist];
    [view setCDF:wantCDF ? cdf : NULL];
    [view setMappingLUT:lut];
    free(plane);
}

@end
