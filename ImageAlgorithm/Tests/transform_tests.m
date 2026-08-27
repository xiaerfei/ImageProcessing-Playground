//
//  transform_tests.m
//  ImageAlgorithm
//
//  几何变换的正确性回归测试(不依赖 XCTest,直接命令行跑):
//
//      cd ImageAlgorithm
//      clang -fobjc-arc -framework Cocoa -I ImageAlgorithm/Algorithm \
//            -o /tmp/transform_tests Tests/transform_tests.m \
//            ImageAlgorithm/Algorithm/IAImageBuffer.m \
//            ImageAlgorithm/Algorithm/IAAffineTransform.m && /tmp/transform_tests
//
#import "IAImageBuffer.h"
#import "IAAffineTransform.h"

static int gFail = 0;
static void check(BOOL cond, NSString *msg) {
    printf("%s  %s\n", cond ? "PASS" : "FAIL", msg.UTF8String);
    if (!cond) { gFail++; }
}

static uint8_t px(IAImageBuffer *b, NSInteger x, NSInteger y, int c) {
    return b.data[(y * b.width + x) * 4 + c];
}

int main(void) { @autoreleasepool {
    // 造一张 8x6 渐变图:R = x*10, G = y*10, B = 200, A = 255
    IAImageBuffer *src = [IAImageBuffer bufferWithWidth:8 height:6];
    for (NSInteger y = 0; y < 6; y++) {
        for (NSInteger x = 0; x < 8; x++) {
            uint8_t *p = src.data + (y * 8 + x) * 4;
            p[0] = (uint8_t)(x * 10); p[1] = (uint8_t)(y * 10); p[2] = 200; p[3] = 255;
        }
    }
    NSSize size = NSMakeSize(8, 6);

    // 1. 单位变换:输出应与输入逐字节相同
    IATransformParams id_ = IATransformParamsDefault();
    IAImageBuffer *r1 = [IAAffineTransform warpImage:src
                                              matrix:[IAAffineTransform matrixWithParams:id_ imageSize:size]
                                       interpolation:IAInterpolationBilinear
                                          canvasMode:IACanvasModeKeepSize];
    check(memcmp(r1.data, src.data, 8 * 6 * 4) == 0, @"单位变换 → 输出逐字节等于输入");

    // 2. 平移 (2, 1):目标 (x,y) 应等于源 (x-2, y-1);左上角空出来的应为透明
    IATransformParams t = IATransformParamsDefault();
    t.translateX = 2; t.translateY = 1;
    IAImageBuffer *r2 = [IAAffineTransform warpImage:src
                                              matrix:[IAAffineTransform matrixWithParams:t imageSize:size]
                                       interpolation:IAInterpolationNearest
                                          canvasMode:IACanvasModeKeepSize];
    check(px(r2, 5, 3, 0) == px(src, 3, 2, 0) && px(r2, 5, 3, 1) == px(src, 3, 2, 1),
          @"平移(2,1) → dst(5,3) == src(3,2)");
    check(px(r2, 0, 0, 3) == 0, @"平移后左上角空出区域为透明");

    // 3. 水平镜像:dst(x,y) == src(W-1-x, y)
    IATransformParams mh = IATransformParamsDefault();
    mh.mirrorHorizontal = YES;
    IAImageBuffer *r3 = [IAAffineTransform warpImage:src
                                              matrix:[IAAffineTransform matrixWithParams:mh imageSize:size]
                                       interpolation:IAInterpolationNearest
                                          canvasMode:IACanvasModeKeepSize];
    BOOL mirrorOK = YES;
    for (NSInteger y = 0; y < 6; y++)
        for (NSInteger x = 0; x < 8; x++)
            if (px(r3, x, y, 0) != px(src, 7 - x, y, 0)) { mirrorOK = NO; }
    check(mirrorOK, @"水平镜像 → dst(x,y) == src(W-1-x, y) 全图成立");

    // 4. 转置 + 自适应画布:8x6 应变成 6x8
    IATransformParams tp = IATransformParamsDefault();
    tp.transpose = YES;
    IAImageBuffer *r4 = [IAAffineTransform warpImage:src
                                              matrix:[IAAffineTransform matrixWithParams:tp imageSize:size]
                                       interpolation:IAInterpolationNearest
                                          canvasMode:IACanvasModeFit];
    check(r4.width == 6 && r4.height == 8,
          ([NSString stringWithFormat:@"转置+自适应 → 8x6 变 6x8 (实际 %ldx%ld)", (long)r4.width, (long)r4.height]));

    // 5. 放大 2 倍 + 自适应:尺寸应约为 16x12
    IATransformParams s2 = IATransformParamsDefault();
    s2.scaleX = 2.0; s2.scaleY = 2.0;
    IAImageBuffer *r5 = [IAAffineTransform warpImage:src
                                              matrix:[IAAffineTransform matrixWithParams:s2 imageSize:size]
                                       interpolation:IAInterpolationBilinear
                                          canvasMode:IACanvasModeFit];
    check(r5.width == 15 && r5.height == 11,
          ([NSString stringWithFormat:@"放大2倍+自适应 → 15x11 (角点跨度 2*(W-1)+1,实际 %ldx%ld)", (long)r5.width, (long)r5.height]));

    // 6. 旋转 360 度应回到原图(检验矩阵复合与求逆的数值稳定性)
    IATransformParams r360 = IATransformParamsDefault();
    r360.rotationDegrees = 360.0;
    IAImageBuffer *r6 = [IAAffineTransform warpImage:src
                                              matrix:[IAAffineTransform matrixWithParams:r360 imageSize:size]
                                       interpolation:IAInterpolationBilinear
                                          canvasMode:IACanvasModeKeepSize];
    int maxDiff = 0;
    for (NSInteger i = 0; i < 8 * 6 * 4; i++) {
        int d = abs((int)r6.data[i] - (int)src.data[i]);
        if (d > maxDiff) { maxDiff = d; }
    }
    check(maxDiff <= 1, ([NSString stringWithFormat:@"旋转360° → 与原图最大误差 %d (≤1)", maxDiff]));

    // 7. 缩放为 0 → 矩阵奇异,应安全返回 nil 而不是崩溃
    IATransformParams zero = IATransformParamsDefault();
    zero.scaleX = 0.0;
    IAImageBuffer *r7 = [IAAffineTransform warpImage:src
                                              matrix:[IAAffineTransform matrixWithParams:zero imageSize:size]
                                       interpolation:IAInterpolationNearest
                                          canvasMode:IACanvasModeKeepSize];
    check(r7 == nil, @"缩放为 0(奇异矩阵)→ 返回 nil,不崩溃");

    printf("\n%s\n", gFail == 0 ? "全部通过 ✅" : "存在失败 ❌");
    return gFail;
}}
