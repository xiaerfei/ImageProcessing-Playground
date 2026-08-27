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

    [im.parameters setDouble:1 forKey:@"mode"];              // 反色
    IAImageBuffer *inv = [im processImage:ramp];
    check(px(inv, 0, 0) == 255 && px(inv, 255, 0) == 0 && px(inv, 100, 0) == 155,
          @"反色 s = 255 − r");

    [im.parameters setDouble:3 forKey:@"mode"];              // 幂律
    [im.parameters setDouble:1.0 forKey:@"gamma"];
    IAImageBuffer *g1 = [im processImage:ramp];
    check(px(g1, 77, 0) == 77, @"γ=1 时幂律等于恒等变换");

    [im.parameters setDouble:0.5 forKey:@"gamma"];
    IAImageBuffer *g05 = [im processImage:ramp];
    check(px(g05, 64, 0) > 64, @"γ<1 提亮暗部 (r=64 → 更大)");

    [im.parameters setDouble:4 forKey:@"mode"];              // 分段线性拉伸
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

    printf("\n%s\n", gFail == 0 ? "全部通过 ✅" : "存在失败 ❌");
    return gFail;
}}
