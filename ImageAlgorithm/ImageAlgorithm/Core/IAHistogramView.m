//
//  IAHistogramView.m
//  ImageAlgorithm
//

#import "IAHistogramView.h"

static const CGFloat kTopInset = 15.0;   // 给标题让出的高度

@implementation IAHistogramView {
    double  _pdf[256];
    double  _cdf[256];
    uint8_t _lut[256];
    BOOL    _hasPDF, _hasCDF, _hasLUT;
}

- (instancetype)initWithFrame:(NSRect)frameRect {
    self = [super initWithFrame:frameRect];
    if (self) {
        self.wantsLayer = YES;
        self.layer.cornerRadius = 4.0;
    }
    return self;
}

- (BOOL)isFlipped { return NO; }   // 直方图纵轴向上,和数学习惯一致

#pragma mark - 数据

- (void)setPDF:(nullable const double *)pdf {
    _hasPDF = (pdf != NULL);
    if (pdf) { memcpy(_pdf, pdf, sizeof(_pdf)); }
    self.needsDisplay = YES;
}

- (void)setCDF:(nullable const double *)cdf {
    _hasCDF = (cdf != NULL);
    if (cdf) { memcpy(_cdf, cdf, sizeof(_cdf)); }
    self.needsDisplay = YES;
}

- (void)setMappingLUT:(nullable const uint8_t *)lut {
    _hasLUT = (lut != NULL);
    if (lut) { memcpy(_lut, lut, sizeof(_lut)); }
    self.needsDisplay = YES;
}

- (void)setLogScale:(BOOL)logScale {
    if (_logScale == logScale) { return; }
    _logScale = logScale;
    self.needsDisplay = YES;
}

- (void)setCaption:(NSString *)caption { _caption = [caption copy]; self.needsDisplay = YES; }
- (void)setDetail:(NSString *)detail   { _detail  = [detail copy];  self.needsDisplay = YES; }

#pragma mark - 主题

- (BOOL)isDarkAppearance {
    NSAppearanceName name = [self.effectiveAppearance
        bestMatchFromAppearancesWithNames:@[NSAppearanceNameAqua, NSAppearanceNameDarkAqua]];
    return [name isEqualToString:NSAppearanceNameDarkAqua];
}

- (void)viewDidChangeEffectiveAppearance {
    [super viewDidChangeEffectiveAppearance];
    self.needsDisplay = YES;
}

#pragma mark - 绘制

- (void)drawRect:(NSRect)dirtyRect {
    BOOL dark = [self isDarkAppearance];
    NSRect b = self.bounds;

    [(dark ? [NSColor colorWithWhite:0.10 alpha:1.0]
           : [NSColor colorWithWhite:0.97 alpha:1.0]) setFill];
    NSRectFill(b);

    NSRect plot = NSMakeRect(0, 0, b.size.width, b.size.height - kTopInset);
    if (plot.size.height < 4 || plot.size.width < 8) { return; }

    [self drawGridInRect:plot dark:dark];
    if (_hasPDF) { [self drawBarsInRect:plot dark:dark]; }
    if (_hasCDF) { [self drawCurve:_cdf inRect:plot color:[NSColor systemBlueColor]]; }
    if (_hasLUT) { [self drawLUTInRect:plot]; }
    [self drawTitlesInRect:b dark:dark];
}

/// 四分之一处的竖线 = 常说的"四分之一调 / 中间调 / 四分之三调",和 PS 直方图一样
- (void)drawGridInRect:(NSRect)plot dark:(BOOL)dark {
    [[NSColor colorWithWhite:(dark ? 1.0 : 0.0) alpha:0.08] setStroke];
    NSBezierPath *path = [NSBezierPath bezierPath];
    for (int i = 1; i < 4; i++) {
        CGFloat x = round(plot.size.width * i / 4.0) + 0.5;
        [path moveToPoint:NSMakePoint(x, plot.origin.y)];
        [path lineToPoint:NSMakePoint(x, NSMaxY(plot))];
    }
    path.lineWidth = 1.0;
    [path stroke];
}

- (void)drawBarsInRect:(NSRect)plot dark:(BOOL)dark {
    // 按最大柱归一化(PS 也是这么做的):否则一根尖峰会把其余全部压平
    double peak = 0.0;
    for (int i = 0; i < 256; i++) { peak = fmax(peak, _pdf[i]); }
    if (peak <= 0.0) { return; }

    [(dark ? [NSColor colorWithWhite:0.75 alpha:0.85]
           : [NSColor colorWithWhite:0.35 alpha:0.85]) setFill];

    CGFloat barW = plot.size.width / 256.0;
    for (int i = 0; i < 256; i++) {
        double v = _pdf[i] / peak;
        if (_logScale && v > 0.0) {
            // log1p 把 0 稳稳地映到 0,不用给零柱做特殊处理
            v = log1p(v * 999.0) / log(1000.0);
        }
        if (v <= 0.0) { continue; }
        CGFloat h = fmax(1.0, v * plot.size.height);
        NSRectFill(NSMakeRect(i * barW, plot.origin.y, fmax(barW, 1.0), h));
    }
}

- (void)drawCurve:(const double *)values inRect:(NSRect)plot color:(NSColor *)color {
    NSBezierPath *path = [NSBezierPath bezierPath];
    for (int i = 0; i < 256; i++) {
        NSPoint p = NSMakePoint(plot.size.width * i / 255.0,
                                plot.origin.y + values[i] * plot.size.height);
        if (i == 0) { [path moveToPoint:p]; } else { [path lineToPoint:p]; }
    }
    [[color colorWithAlphaComponent:0.9] setStroke];
    // 比映射曲线粗:两者重合时(均衡化),蓝线会从黄虚线的缝隙里露出来,
    // 一眼看出"这是两条完全叠在一起的线",而不是"只有一条黄线"
    path.lineWidth = 2.2;
    [path stroke];
}

/// 映射曲线:横轴是输入 r,纵轴是输出 s(都归一到 0~1)
- (void)drawLUTInRect:(NSRect)plot {
    NSBezierPath *path = [NSBezierPath bezierPath];
    for (int i = 0; i < 256; i++) {
        NSPoint p = NSMakePoint(plot.size.width * i / 255.0,
                                plot.origin.y + (_lut[i] / 255.0) * plot.size.height);
        if (i == 0) { [path moveToPoint:p]; } else { [path lineToPoint:p]; }
    }
    [[NSColor systemYellowColor] setStroke];
    path.lineWidth = 1.2;
    // 虚线:均衡化时它会和蓝色 CDF 完全重合,画实线就看不出是两条了
    CGFloat dash[2] = {3.0, 2.0};
    [path setLineDash:dash count:2 phase:0];
    [path stroke];
}

- (void)drawTitlesInRect:(NSRect)b dark:(BOOL)dark {
    NSDictionary *attrs = @{
        NSFontAttributeName: [NSFont systemFontOfSize:9],
        NSForegroundColorAttributeName: dark ? [NSColor colorWithWhite:0.72 alpha:1.0]
                                             : [NSColor colorWithWhite:0.35 alpha:1.0],
    };
    if (self.caption.length) {
        [self.caption drawAtPoint:NSMakePoint(4, b.size.height - kTopInset + 2) withAttributes:attrs];
    }
    if (self.detail.length) {
        NSSize size = [self.detail sizeWithAttributes:attrs];
        [self.detail drawAtPoint:NSMakePoint(b.size.width - size.width - 4,
                                             b.size.height - kTopInset + 2)
                  withAttributes:attrs];
    }
}

@end
