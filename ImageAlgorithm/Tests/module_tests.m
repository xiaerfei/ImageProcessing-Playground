//
//  module_tests.m
//  ImageAlgorithm
//
//  模块架构的端到端测试:走 IAModuleRegistry → 基类 → 参数 → processImage 全链路。
//
//      cd ImageAlgorithm
//      clang -fobjc-arc -framework Cocoa \
//            -I ImageAlgorithm/Core -I ImageAlgorithm/Algorithm -I ImageAlgorithm/Modules \
//            -o /tmp/module_tests Tests/module_tests.m \
//            ImageAlgorithm/Core/*.m ImageAlgorithm/Algorithm/*.m ImageAlgorithm/Modules/*.m \
//      && /tmp/module_tests
//

#import <Cocoa/Cocoa.h>
#import "IAAlgorithmModule.h"
#import "IAModuleRegistry.h"
#import "IAIntensityModule.h"
#import "IAHistogramModule.h"
#import "IAHistogram.h"   // IAHistogramTarget 枚举

static int gFail = 0;
static void check(BOOL cond, NSString *msg) {
    printf("%s  %s\n", cond ? "PASS" : "FAIL", msg.UTF8String);
    if (!cond) { gFail++; }
}

static IAImageBuffer *makeRamp(void) {
    IAImageBuffer *b = [IAImageBuffer bufferWithWidth:256 height:4];
    for (NSInteger y = 0; y < 4; y++)
        for (NSInteger x = 0; x < 256; x++) {
            uint8_t *p = b.data + (y * 256 + x) * 4;
            p[0] = p[1] = p[2] = (uint8_t)x; p[3] = 255;
        }
    return b;
}
static uint8_t px(IAImageBuffer *b, NSInteger x, int c) { return b.data[x * 4 + c]; }

int main(void) { @autoreleasepool {
    [NSApplication sharedApplication];   // 参数面板要创建 NSView

    // --- 架构层面 ---
    NSArray<Class> *classes = IAModuleRegistry.moduleClasses;
    check(classes.count >= 2, ([NSString stringWithFormat:@"注册表含 %lu 个模块", (unsigned long)classes.count]));

    BOOL allConform = YES, allTitled = YES, allBuildPanel = YES;
    for (Class c in classes) {
        if (![c isSubclassOfClass:IAAlgorithmModule.class]) { allConform = NO; }
        if ([[c title] length] == 0) { allTitled = NO; }
        IAAlgorithmModule *m = [[c alloc] init];
        if (!m.parameterView || m.parameters.allKeys.count == 0) { allBuildPanel = NO; }
    }
    check(allConform, @"所有注册模块都是 IAAlgorithmModule 子类");
    check(allTitled, @"所有模块都提供了非空 +title");
    check(allBuildPanel, @"所有模块都能构建出参数面板且注册了参数");

    // 每个模块都能在不改宿主代码的前提下跑通
    IAImageBuffer *ramp = makeRamp();
    BOOL allRun = YES;
    for (Class c in classes) {
        IAAlgorithmModule *m = [[c alloc] init];
        (void)m.parameterView;
        IAImageBuffer *out = [m processImage:ramp];
        if (!out || out.width == 0) { allRun = NO; printf("     ↑ %s 返回空\n", [[c title] UTF8String]); }
    }
    check(allRun, @"所有模块用默认参数都能产出结果");

    // 参数重置后回到默认值
    IAAlgorithmModule *geo = [[classes[0] alloc] init];
    (void)geo.parameterView;
    [geo.parameters setDouble:123 forKey:geo.parameters.allKeys.firstObject];
    [geo.parameters resetAll];
    check([geo.parameters doubleForKey:geo.parameters.allKeys.firstObject] == 0,
          @"resetAll 能把参数恢复默认值");

    // --- 灰度模块的算法正确性 ---
    IAIntensityModule *im = [[IAIntensityModule alloc] init];
    (void)im.parameterView;

    [im.parameters setDouble:IAIntensityModeInvert forKey:@"mode"];
    IAImageBuffer *inv = [im processImage:ramp];
    check(px(inv, 0, 0) == 255 && px(inv, 255, 0) == 0 && px(inv, 100, 0) == 155,
          @"反色 s = 255 − r");

    [im.parameters setDouble:IAIntensityModeGamma forKey:@"mode"];
    [im.parameters setDouble:1.0 forKey:@"gamma"];
    IAImageBuffer *g1 = [im processImage:ramp];
    check(px(g1, 77, 0) == 77, @"γ=1 时幂律等于恒等变换");

    [im.parameters setDouble:0.5 forKey:@"gamma"];
    IAImageBuffer *g05 = [im processImage:ramp];
    check(px(g05, 64, 0) > 64, @"γ<1 提亮暗部 (r=64 → 更大)");

    // 线性 s = a·r + b
    [im.parameters setDouble:IAIntensityModeLinear forKey:@"mode"];
    [im.parameters setDouble:1.0 forKey:@"slope"];
    [im.parameters setDouble:0.0 forKey:@"intercept"];
    check(px([im processImage:ramp], 137, 0) == 137, @"线性 a=1,b=0 等于恒等");

    [im.parameters setDouble:1.0 forKey:@"slope"];
    [im.parameters setDouble:60.0 forKey:@"intercept"];
    IAImageBuffer *lin = [im processImage:ramp];
    check(px(lin, 100, 0) == 160 && px(lin, 250, 0) == 255,
          @"线性 b=+60 整体提亮,超出部分截断到 255");

    [im.parameters setDouble:-1.0 forKey:@"slope"];
    [im.parameters setDouble:255.0 forKey:@"intercept"];
    IAImageBuffer *negLin = [im processImage:ramp];
    check(px(negLin, 40, 0) == 215 && px(negLin, 200, 0) == 55,
          @"线性 a=-1,b=255 等价于反色");

    // 截断统计
    [im.parameters setDouble:2.0 forKey:@"slope"];
    [im.parameters setDouble:0.0 forKey:@"intercept"];
    (void)[im processImage:ramp];
    check([im.extraStatus containsString:@"截断"], @"a=2 时状态栏报告截断比例");

    [im.parameters setDouble:IAIntensityModeStretch forKey:@"mode"];
    [im.parameters setDouble:50 forKey:@"lowIn"];
    [im.parameters setDouble:200 forKey:@"highIn"];
    IAImageBuffer *st = [im processImage:ramp];
    check(px(st, 50, 0) == 0 && px(st, 200, 0) == 255 && px(st, 20, 0) == 0,
          @"拉伸 [50,200] → [0,255],区间外截断");

    // 低 >= 高 的联动保护
    [im.parameters setDouble:240 forKey:@"lowIn"];
    [im parameterDidChange:@"lowIn"];
    check([im.parameters doubleForKey:@"highIn"] > [im.parameters doubleForKey:@"lowIn"],
          @"低值超过高值时自动顶开,避免除零");

    // --- 直方图模块的算法正确性 ---
    IAHistogramModule *hm = [[IAHistogramModule alloc] init];
    (void)hm.parameterView;

    // 挤在 100~140 的窄区间:均衡化应当把它摊开
    IAImageBuffer *narrow = [IAImageBuffer bufferWithWidth:200 height:20];
    for (NSInteger i = 0; i < 200 * 20; i++) {
        uint8_t *p = narrow.data + i * 4;
        p[0] = p[1] = p[2] = (uint8_t)(100 + (i % 41)); p[3] = 255;
    }
    double (^stdev)(IAImageBuffer *) = ^double(IAImageBuffer *b) {
        NSInteger n = b.width * b.height;
        double mean = 0, var = 0;
        for (NSInteger i = 0; i < n; i++) { mean += b.data[i * 4]; }
        mean /= n;
        for (NSInteger i = 0; i < n; i++) { double d = b.data[i * 4] - mean; var += d * d; }
        return sqrt(var / n);
    };

    [hm.parameters setDouble:IAHistogramModeIdentity forKey:@"mode"];
    IAImageBuffer *same = [hm processImage:narrow];
    check(fabs(stdev(same) - stdev(narrow)) < 0.01, @"原图模式不改动像素");

    [hm.parameters setDouble:IAHistogramModeEqualize forKey:@"mode"];
    IAImageBuffer *eq = [hm processImage:narrow];
    check(stdev(eq) > stdev(narrow) * 4.0,
          ([NSString stringWithFormat:@"均衡化摊开窄区间:σ %.1f → %.1f", stdev(narrow), stdev(eq)]));

    // 规定化到"均匀"应当与均衡化一致 —— 两者同源
    [hm.parameters setDouble:IAHistogramModeSpecify forKey:@"mode"];
    [hm.parameters setDouble:IAHistogramTargetUniform forKey:@"target"];
    IAImageBuffer *spec = [hm processImage:narrow];
    int maxDiff = 0;
    for (NSInteger i = 0; i < 200 * 20; i++) {
        maxDiff = MAX(maxDiff, abs(spec.data[i * 4] - eq.data[i * 4]));
    }
    check(maxDiff <= 1,
          ([NSString stringWithFormat:@"规定化到均匀 == 全局均衡化(最大偏差 %d)", maxDiff]));

    // 彩色图:只动亮度不该偏色,分通道必然偏色
    IAImageBuffer *color = [IAImageBuffer bufferWithWidth:64 height:8];
    for (NSInteger i = 0; i < 64 * 8; i++) {
        uint8_t *p = color.data + i * 4;
        // 偏暖的一片:R 始终大于 B,三个通道的分布宽度各不相同
        p[0] = (uint8_t)(90 + (i % 60));
        p[1] = (uint8_t)(70 + (i % 40));
        p[2] = (uint8_t)(50 + (i % 20));
        p[3] = 255;
    }
    double (^warmth)(IAImageBuffer *) = ^double(IAImageBuffer *b) {
        NSInteger n = b.width * b.height;
        double sum = 0;
        for (NSInteger i = 0; i < n; i++) { sum += (double)b.data[i * 4] - b.data[i * 4 + 2]; }
        return sum / n;   // 平均 R−B,衡量色偏
    };

    [hm.parameters setDouble:IAHistogramModeEqualize forKey:@"mode"];
    [hm.parameters setDouble:IAHistogramColorModeLuma forKey:@"colorMode"];
    IAImageBuffer *lumaEq = [hm processImage:color];
    [hm.parameters setDouble:IAHistogramColorModePerChannel forKey:@"colorMode"];
    IAImageBuffer *chEq = [hm processImage:color];
    check(warmth(chEq) < warmth(color) * 0.5,
          ([NSString stringWithFormat:@"分通道均衡化把暖色洗掉:R−B %.1f → %.1f",
            warmth(color), warmth(chEq)]));
    check(fabs(warmth(lumaEq) - warmth(color)) < fabs(warmth(chEq) - warmth(color)),
          ([NSString stringWithFormat:@"只动亮度更好地保住色偏:R−B %.1f(原图 %.1f)",
            warmth(lumaEq), warmth(color)]));

    // CLAHE 走得通,且和全局均衡化的结果不同
    [hm.parameters setDouble:IAHistogramModeCLAHE forKey:@"mode"];
    [hm.parameters setDouble:IAHistogramColorModeGray forKey:@"colorMode"];
    [hm.parameters setDouble:4 forKey:@"tiles"];
    [hm.parameters setDouble:2.0 forKey:@"clipLimit"];
    IAImageBuffer *clahe = [hm processImage:narrow];
    check(clahe != nil && clahe.width == narrow.width, @"CLAHE 能产出结果");
    int diffFromGlobal = 0;
    for (NSInteger i = 0; i < 200 * 20; i++) {
        diffFromGlobal = MAX(diffFromGlobal, abs(clahe.data[i * 4] - eq.data[i * 4]));
    }
    check(diffFromGlobal > 5,
          ([NSString stringWithFormat:@"CLAHE 与全局均衡化结果不同(最大差 %d)", diffFromGlobal]));

    // 状态栏有话说
    check(hm.extraStatus.length > 0, @"模块向状态栏报告了当前用的方式");

    printf("\n%s\n", gFail == 0 ? "全部通过 ✅" : "存在失败 ❌");
    return gFail;
}}
