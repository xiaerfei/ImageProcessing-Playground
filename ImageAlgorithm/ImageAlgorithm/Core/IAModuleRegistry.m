//
//  IAModuleRegistry.m
//  ImageAlgorithm
//

#import "IAModuleRegistry.h"
#import "IAGeometryModule.h"
#import "IAIntensityModule.h"

@implementation IAModuleRegistry

+ (NSArray<Class> *)moduleClasses {
    // 新增一章算法:实现 IAAlgorithmModule 子类,然后在这里加一行
    return @[
        IAGeometryModule.class,    // 第 3 周
        IAIntensityModule.class,   // 第 4 周
    ];
}

@end
