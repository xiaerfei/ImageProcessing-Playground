//
//  IAGeometryModule.m
//  ImageAlgorithm
//

#import "IAGeometryModule.h"
#import "IAAffineTransform.h"

static NSString * const kTranslateX   = @"translateX";
static NSString * const kTranslateY   = @"translateY";
static NSString * const kRotation     = @"rotation";
static NSString * const kScaleX       = @"scaleX";
static NSString * const kScaleY       = @"scaleY";
static NSString * const kLockAspect   = @"lockAspect";
static NSString * const kMirrorH      = @"mirrorH";
static NSString * const kMirrorV      = @"mirrorV";
static NSString * const kTranspose    = @"transpose";
static NSString * const kInterpolation = @"interpolation";
static NSString * const kCanvasMode   = @"canvasMode";

@implementation IAGeometryModule

+ (NSString *)title { return @"几何变换"; }
+ (NSString *)subtitle { return @"第 2 章 · 第 3 周"; }
- (NSString *)resultTitle { return @"变换结果"; }

- (void)buildParameters:(IAParameterBuilder *)builder {
    [builder addSection:@"平移 (px)"];
    [builder addSlider:kTranslateX label:@"X" min:-1000 max:1000 value:0 format:@"%.0f"];
    [builder addSlider:kTranslateY label:@"Y" min:-1000 max:1000 value:0 format:@"%.0f"];

    [builder addSeparator];
    [builder addSection:@"旋转 (度,绕图像中心)"];
    [builder addSlider:kRotation label:@"θ" min:-180 max:180 value:0 format:@"%.1f"];

    [builder addSeparator];
    [builder addSection:@"缩放 (倍)"];
    [builder addSlider:kScaleX label:@"X" min:0.1 max:3.0 value:1.0 format:@"%.2f"];
    [builder addSlider:kScaleY label:@"Y" min:0.1 max:3.0 value:1.0 format:@"%.2f"];
    [builder addCheckbox:kLockAspect title:@"锁定 X/Y 比例" value:YES];

    [builder addSeparator];
    [builder addSection:@"翻转"];
    [builder addCheckbox:kMirrorH title:@"水平镜像" value:NO];
    [builder addCheckbox:kMirrorV title:@"垂直镜像" value:NO];
    [builder addCheckbox:kTranspose title:@"转置 (x↔y)" value:NO];

    [builder addSeparator];
    [builder addSection:@"插值方式"];
    [builder addSegmented:kInterpolation items:@[@"最近邻", @"双线性"] value:1];
    [builder addNote:@"反推出的源坐标是小数,最近邻直接取整会出锯齿,双线性按 4 邻点距离加权。"];

    [builder addSection:@"输出画布"];
    [builder addSegmented:kCanvasMode items:@[@"原尺寸", @"自适应"] value:0];
}

- (void)parameterDidChange:(nullable NSString *)key {
    if (![self.parameters boolForKey:kLockAspect]) { return; }
    if ([key isEqualToString:kScaleX]) {
        [self.parameters setDouble:[self.parameters doubleForKey:kScaleX] forKey:kScaleY];
    } else if ([key isEqualToString:kScaleY]) {
        [self.parameters setDouble:[self.parameters doubleForKey:kScaleY] forKey:kScaleX];
    }
}

- (nullable IAImageBuffer *)processImage:(IAImageBuffer *)source {
    IAParameterStore *p = self.parameters;

    IATransformParams params = IATransformParamsDefault();
    params.translateX = round([p doubleForKey:kTranslateX]);
    params.translateY = round([p doubleForKey:kTranslateY]);
    params.rotationDegrees = [p doubleForKey:kRotation];
    params.scaleX = [p doubleForKey:kScaleX];
    params.scaleY = [p doubleForKey:kScaleY];
    params.mirrorHorizontal = [p boolForKey:kMirrorH];
    params.mirrorVertical = [p boolForKey:kMirrorV];
    params.transpose = [p boolForKey:kTranspose];

    NSSize size = NSMakeSize(source.width, source.height);
    simd_double3x3 matrix = [IAAffineTransform matrixWithParams:params imageSize:size];

    return [IAAffineTransform warpImage:source
                                 matrix:matrix
                          interpolation:([p integerForKey:kInterpolation] == 0
                                         ? IAInterpolationNearest : IAInterpolationBilinear)
                             canvasMode:([p integerForKey:kCanvasMode] == 0
                                         ? IACanvasModeKeepSize : IACanvasModeFit)];
}

@end
