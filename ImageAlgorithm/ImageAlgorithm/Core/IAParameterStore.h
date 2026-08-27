//
//  IAParameterStore.h
//  ImageAlgorithm
//
//  参数值的统一读写入口。控件本身就是唯一数据源,store 只是按 key 转发,
//  这样不用在每个模块里维护一份"控件 ↔ 变量"的同步代码。
//

#import <Cocoa/Cocoa.h>

NS_ASSUME_NONNULL_BEGIN

@interface IAParameterStore : NSObject

- (double)doubleForKey:(NSString *)key;
- (NSInteger)integerForKey:(NSString *)key;
- (BOOL)boolForKey:(NSString *)key;

/// 供模块做参数联动(例如"锁定 X/Y 比例"时把 Y 跟着 X 一起改)
- (void)setDouble:(double)value forKey:(NSString *)key;
- (void)setBool:(BOOL)value forKey:(NSString *)key;

/// 全部恢复到注册时的默认值
- (void)resetAll;

#pragma mark - 供 IAParameterBuilder 调用

- (void)registerControl:(NSControl *)control
                 forKey:(NSString *)key
           defaultValue:(double)defaultValue;
- (nullable NSControl *)controlForKey:(NSString *)key;
- (NSArray<NSString *> *)allKeys;

@end

NS_ASSUME_NONNULL_END
