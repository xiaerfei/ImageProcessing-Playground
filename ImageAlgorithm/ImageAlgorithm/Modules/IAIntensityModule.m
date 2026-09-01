//
//  IAIntensityModule.m
//  ImageAlgorithm
//
//  第 3 章 3.2 基本灰度变换。
//  这些都是"点运算":输出只取决于当前像素值,与邻居无关,
//  所以工程上一律退化成一张 256 项查找表(LUT)—— 和调色管线里的做法一致。
//

#import "IAIntensityModule.h"

static NSString * const kToGray    = @"toGray";
static NSString * const kMode      = @"mode";
static NSString * const kGamma     = @"gamma";
static NSString * const kLowIn     = @"lowIn";
static NSString * const kHighIn    = @"highIn";
static NSString * const kSlope     = @"slope";
static NSString * const kIntercept = @"intercept";

@implementation IAIntensityModule {
    double _clipLowRatio;    // 被压到 0 的像素占比
    double _clipHighRatio;   // 被压到 255 的像素占比
}

+ (NSString *)title { return @"灰度变换"; }
+ (NSString *)subtitle { return @"第 3 章 · 第 4 周"; }
- (NSString *)resultTitle { return @"变换结果"; }

- (void)buildParameters:(IAParameterBuilder *)builder {
    [builder addSection:@"预处理"];
    [builder addCheckbox:kToGray title:@"先转灰度 (BT.601)" value:NO];

    [builder addSeparator];
    [builder addSection:@"变换类型"];
    [builder addPopUp:kMode
                items:@[@"原图", @"线性 s=a·r+b", @"反色", @"对数", @"幂律", @"分段拉伸"]
                value:IAIntensityModeLinear];

    [builder addSeparator];
    [builder addSection:@"线性 s = a·r + b"];
    [builder addSlider:kSlope     label:@"a" min:-2.0 max:3.0   value:1.0 format:@"%.2f"];
    [builder addSlider:kIntercept label:@"b" min:-255 max:255   value:0   format:@"%.0f"];
    [builder addNote:@"a 管对比度(斜率),b 管亮度(截距)。超出 0~255 的部分被截断,不可逆。"];

    [builder addSeparator];
    [builder addSection:@"幂律 (Gamma)"];
    [builder addSlider:kGamma label:@"γ" min:0.1 max:3.0 value:1.0 format:@"%.2f"];
    [builder addNote:@"s = 255·(r/255)^γ。γ<1 提亮暗部,γ>1 压暗 —— 屏幕 sRGB 编码就是这条曲线。"];

    [builder addSeparator];
    [builder addSection:@"分段线性拉伸"];
    [builder addSlider:kLowIn label:@"低" min:0 max:255 value:0 format:@"%.0f"];
    [builder addSlider:kHighIn label:@"高" min:0 max:255 value:255 format:@"%.0f"];
    [builder addNote:@"把 [低, 高] 区间线性拉满到 [0, 255],区间外截断。"];
}

- (void)parameterDidChange:(nullable NSString *)key {
    // 保证 低 < 高,否则拉伸的分母为 0
    double low = [self.parameters doubleForKey:kLowIn];
    double high = [self.parameters doubleForKey:kHighIn];
    if (low >= high) {
        if ([key isEqualToString:kLowIn]) {
            [self.parameters setDouble:fmin(low + 1.0, 255.0) forKey:kHighIn];
        } else if ([key isEqualToString:kHighIn]) {
            [self.parameters setDouble:fmax(high - 1.0, 0.0) forKey:kLowIn];
        }
    }
}

- (nullable NSString *)extraStatus {
    NSString *formula = [self formulaText];
    if (_clipLowRatio < 0.05 && _clipHighRatio < 0.05) { return formula; }
    return [NSString stringWithFormat:@"%@\n截断: %.1f%% → 0,%.1f%% → 255",
            formula, _clipLowRatio, _clipHighRatio];
}

- (NSString *)formulaText {
    switch ((IAIntensityMode)[self.parameters integerForKey:kMode]) {
        case IAIntensityModeLinear:
            return [NSString stringWithFormat:@"s = %.2f·r %+.0f",
                    [self.parameters doubleForKey:kSlope],
                    [self.parameters doubleForKey:kIntercept]];
        case IAIntensityModeInvert:  return @"s = 255 − r";
        case IAIntensityModeLog:     return @"s = c·log(1+r), c = 255/log(256)";
        case IAIntensityModeGamma:
            return [NSString stringWithFormat:@"γ = %.2f", [self.parameters doubleForKey:kGamma]];
        case IAIntensityModeStretch:
            return [NSString stringWithFormat:@"[%.0f, %.0f] → [0, 255]",
                    [self.parameters doubleForKey:kLowIn], [self.parameters doubleForKey:kHighIn]];
        case IAIntensityModeIdentity: return @"未做变换";
    }
}

/// 按当前参数生成 256 项查找表,同时标记哪些输入值会被截断
- (void)buildLUT:(uint8_t[256])lut clipLow:(BOOL[256])clipLow clipHigh:(BOOL[256])clipHigh {
    IAIntensityMode mode = (IAIntensityMode)[self.parameters integerForKey:kMode];
    double gamma = [self.parameters doubleForKey:kGamma];
    double low = [self.parameters doubleForKey:kLowIn];
    double high = [self.parameters doubleForKey:kHighIn];
    double logC = 255.0 / log(256.0);

    double a = [self.parameters doubleForKey:kSlope];
    double b = [self.parameters doubleForKey:kIntercept];

    for (int r = 0; r < 256; r++) {
        double s;
        switch (mode) {
            case IAIntensityModeLinear:  s = a * r + b; break;
            case IAIntensityModeInvert:  s = 255.0 - r; break;
            case IAIntensityModeLog:     s = logC * log(1.0 + r); break;
            case IAIntensityModeGamma:   s = 255.0 * pow(r / 255.0, gamma); break;
            case IAIntensityModeStretch: s = (r - low) * 255.0 / (high - low); break;
            case IAIntensityModeIdentity:
            default:                     s = r; break;
        }
        clipLow[r]  = (s < 0.0);
        clipHigh[r] = (s > 255.0);
        lut[r] = (uint8_t)lround(fmin(fmax(s, 0.0), 255.0));
    }
}

- (nullable IAImageBuffer *)processImage:(IAImageBuffer *)source {
    uint8_t lut[256];
    BOOL clipLow[256], clipHigh[256];
    [self buildLUT:lut clipLow:clipLow clipHigh:clipHigh];
    BOOL toGray = [self.parameters boolForKey:kToGray];
    long nLow = 0, nHigh = 0, nTotal = 0;

    IAImageBuffer *dst = [IAImageBuffer bufferWithWidth:source.width height:source.height];
    if (!dst) { return nil; }

    const uint8_t *sp = source.data;
    uint8_t *dp = dst.data;
    NSInteger count = source.width * source.height;

    // 注:缓冲是预乘 alpha 的。测试图都是不透明(a=255),此处直接对 RGB 查表;
    // 将来若要处理带透明度的图,需先反预乘再查表。
    for (NSInteger i = 0; i < count; i++) {
        const uint8_t *s = sp + i * 4;
        uint8_t *d = dp + i * 4;
        if (toGray) {
            uint8_t y = (uint8_t)lround(0.299 * s[0] + 0.587 * s[1] + 0.114 * s[2]);
            d[0] = d[1] = d[2] = lut[y];
            nLow += clipLow[y]; nHigh += clipHigh[y]; nTotal += 1;
        } else {
            d[0] = lut[s[0]];
            d[1] = lut[s[1]];
            d[2] = lut[s[2]];
            for (int c = 0; c < 3; c++) { nLow += clipLow[s[c]]; nHigh += clipHigh[s[c]]; }
            nTotal += 3;
        }
        d[3] = s[3];
    }
    _clipLowRatio  = nTotal ? (double)nLow  / nTotal * 100.0 : 0.0;
    _clipHighRatio = nTotal ? (double)nHigh / nTotal * 100.0 : 0.0;
    return dst;
}

@end
