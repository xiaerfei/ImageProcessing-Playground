//
//  IAImageBuffer.h
//  ImageAlgorithm
//
//  RGBA8 像素缓冲:算法层只跟裸字节打交道,不依赖 NSImage / CGImage。
//

#import <Cocoa/Cocoa.h>

NS_ASSUME_NONNULL_BEGIN

/// 行优先(row-major)存储的 RGBA8 位图,alpha 为预乘。
///
/// 预乘的原因:插值会对相邻像素做加权平均,若 alpha 不预乘,
/// 半透明边缘会把背景色"拖"进来产生黑边/白边(halo)。
@interface IAImageBuffer : NSObject

@property (nonatomic, readonly) NSInteger width;
@property (nonatomic, readonly) NSInteger height;
/// 每行字节数,等于 width * 4(本类不做行对齐,便于逐像素索引)
@property (nonatomic, readonly) NSInteger bytesPerRow;
@property (nonatomic, readonly) uint8_t *data NS_RETURNS_INNER_POINTER;

+ (nullable instancetype)bufferWithImage:(NSImage *)image;
/// 新建全透明缓冲
+ (nullable instancetype)bufferWithWidth:(NSInteger)width height:(NSInteger)height;

- (nullable NSImage *)image;

@end

NS_ASSUME_NONNULL_END
