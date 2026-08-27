//
//  IAModuleRegistry.h
//  ImageAlgorithm
//
//  模块清单。新增一章算法时,在 .m 里加一行即可。
//

#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

@interface IAModuleRegistry : NSObject
/// 按学习顺序排列的模块类(均为 IAAlgorithmModule 子类)
+ (NSArray<Class> *)moduleClasses;
@end

NS_ASSUME_NONNULL_END
