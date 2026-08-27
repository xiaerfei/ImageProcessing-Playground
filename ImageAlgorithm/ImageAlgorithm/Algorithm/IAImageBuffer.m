//
//  IAImageBuffer.m
//  ImageAlgorithm
//

#import "IAImageBuffer.h"

@implementation IAImageBuffer {
    uint8_t *_data;
}

+ (nullable instancetype)bufferWithWidth:(NSInteger)width height:(NSInteger)height {
    if (width <= 0 || height <= 0) { return nil; }
    IAImageBuffer *buffer = [[self alloc] init];
    buffer->_width = width;
    buffer->_height = height;
    buffer->_bytesPerRow = width * 4;
    buffer->_data = calloc((size_t)(width * height * 4), sizeof(uint8_t));
    return buffer->_data ? buffer : nil;
}

+ (nullable instancetype)bufferWithImage:(NSImage *)image {
    CGImageRef cgImage = [image CGImageForProposedRect:NULL context:nil hints:nil];
    if (!cgImage) { return nil; }

    NSInteger width = CGImageGetWidth(cgImage);
    NSInteger height = CGImageGetHeight(cgImage);
    IAImageBuffer *buffer = [self bufferWithWidth:width height:height];
    if (!buffer) { return nil; }

    // 统一重绘到 sRGB + RGBA8,屏蔽掉源图千奇百怪的色彩空间与像素格式
    CGColorSpaceRef space = CGColorSpaceCreateWithName(kCGColorSpaceSRGB);
    CGContextRef ctx = CGBitmapContextCreate(buffer.data, width, height, 8, buffer.bytesPerRow,
                                             space,
                                             kCGImageAlphaPremultipliedLast | kCGBitmapByteOrder32Big);
    CGColorSpaceRelease(space);
    if (!ctx) { return nil; }

    CGContextDrawImage(ctx, CGRectMake(0, 0, width, height), cgImage);
    CGContextRelease(ctx);
    return buffer;
}

- (void)dealloc {
    free(_data);
}

- (uint8_t *)data {
    return _data;
}

- (nullable NSImage *)image {
    CGColorSpaceRef space = CGColorSpaceCreateWithName(kCGColorSpaceSRGB);
    CGContextRef ctx = CGBitmapContextCreate(_data, _width, _height, 8, _bytesPerRow,
                                             space,
                                             kCGImageAlphaPremultipliedLast | kCGBitmapByteOrder32Big);
    CGColorSpaceRelease(space);
    if (!ctx) { return nil; }

    CGImageRef cgImage = CGBitmapContextCreateImage(ctx);
    CGContextRelease(ctx);
    if (!cgImage) { return nil; }

    NSImage *image = [[NSImage alloc] initWithCGImage:cgImage size:NSMakeSize(_width, _height)];
    CGImageRelease(cgImage);
    return image;
}

@end
