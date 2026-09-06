//
//  IAZoomImageView.m
//  ImageAlgorithm
//
//  坐标系:本视图 isFlipped = YES,y 轴向下,与位图索引一致,
//  这样 _origin 就是"图片左上角在视图中的位置",不用到处翻 Y。
//
//  缩放的唯一不变量:锚点处的图像坐标不变。
//    缩放前:imagePoint = (anchor - origin) / scale
//    缩放后:origin' = anchor - imagePoint * scale'
//  代入即得"光标指着的那个像素在缩放前后待在原地",这也是所有图像软件的手感。
//

#import "IAZoomImageView.h"

static const double kMinScale = 0.05;
static const double kMaxScale = 64.0;
// 与 Photoshop 对齐:放大到 600% 以上画出像素网格(PS 也是这个量级开始显示)
static const double kGridMinScale = 6.0;

@implementation IAZoomImageView {
    double  _scale;
    NSPoint _origin;             // 图片左上角在视图中的位置(视图坐标,y 向下)
    BOOL    _didUserZoom;        // 用户手动缩放过 → 不再自动 fit
    BOOL    _applyingSync;       // 正在接收同步,防 A→B→A 递归
    BOOL    _dragging;
    NSPoint _dragStartWindow;    // 拖拽起点:window 坐标 y 向上,与视图相反
    NSPoint _dragStartOrigin;
}

- (instancetype)initWithFrame:(NSRect)frameRect {
    self = [super initWithFrame:frameRect];
    if (self) {
        _scale = 1.0;
        _autoFitsOnResize = YES;
        self.wantsLayer = YES;
        self.layer.backgroundColor = [NSColor colorWithWhite:0.12 alpha:1.0].CGColor;
        // 关键:图片放大后 _origin 会变成负值(图片画到 view 上方),
        // 不裁剪的话 drawInRect 会越界画到 superview 上,盖住上面的标题栏
        self.clipsToBounds = YES;
    }
    return self;
}

- (BOOL)isFlipped { return YES; }
- (BOOL)acceptsFirstResponder { return YES; }

#pragma mark - 几何

- (NSSize)displaySize {
    NSImage *image = self.image;
    if (!image) { return NSZeroSize; }
    return NSMakeSize(image.size.width * _scale, image.size.height * _scale);
}

- (double)fitScale {
    NSImage *image = self.image;
    NSSize view = self.bounds.size;
    if (!image || image.size.width <= 0 || image.size.height <= 0) { return 1.0; }
    if (view.width <= 0 || view.height <= 0) { return 1.0; }
    // 沿用原 NSImageView 的"只缩不放":小图不撑大,免得误以为是算法放大
    return fmin(1.0, fmin(view.width / image.size.width, view.height / image.size.height));
}

/// 限制拖动范围:图片至少要有一部分留在视口内,不会被拖到完全看不见
- (void)clampOrigin {
    NSSize view = self.bounds.size;
    NSSize disp = [self displaySize];
    CGFloat marginX = fmin(view.width  * 0.5, disp.width  * 0.25);
    CGFloat marginY = fmin(view.height * 0.5, disp.height * 0.25);
    _origin.x = fmin(fmax(_origin.x, -disp.width  + marginX), view.width  - marginX);
    _origin.y = fmin(fmax(_origin.y, -disp.height + marginY), view.height - marginY);
}

- (void)centerOrigin {
    NSSize view = self.bounds.size;
    NSSize disp = [self displaySize];
    _origin = NSMakePoint((view.width - disp.width) * 0.5, (view.height - disp.height) * 0.5);
}

- (void)setScale:(double)scale anchoredAt:(NSPoint)anchor {
    double s = fmin(fmax(scale, kMinScale), kMaxScale);
    if (fabs(s - _scale) < 1e-9) { return; }

    NSPoint imagePoint = NSMakePoint((anchor.x - _origin.x) / _scale,
                                     (anchor.y - _origin.y) / _scale);
    _scale = s;
    _origin = NSMakePoint(anchor.x - imagePoint.x * _scale,
                          anchor.y - imagePoint.y * _scale);
    [self clampOrigin];
    [self viewDidChange];
}

#pragma mark - 对外操作

- (void)setImage:(NSImage *)image {
    BOOL sizeChanged = (_image == nil) || (image == nil) || !NSEqualSizes(_image.size, image.size);
    _image = image;
    if (!image) { self.needsDisplay = YES; return; }

    if (!_didUserZoom || sizeChanged) {
        // 首次出图,或输出尺寸变了(几何变换的自适应画布)→ 重新适应
        [self zoomToFit];
    } else {
        // 尺寸没变就保持当前视角:放大看细节时拖参数,画面不该跳回去
        self.needsDisplay = YES;
        if (self.onViewDidChange) { self.onViewDidChange(_scale, _origin); }
    }
}

- (void)zoomToFit {
    _scale = [self fitScale];
    _didUserZoom = NO;
    [self centerOrigin];
    [self viewDidChange];
}

- (void)zoomToActualSize {
    NSPoint center = NSMakePoint(NSMidX(self.bounds), NSMidY(self.bounds));
    _didUserZoom = YES;
    [self setScale:1.0 anchoredAt:center];
}

- (void)zoomBy:(double)factor {
    NSPoint center = NSMakePoint(NSMidX(self.bounds), NSMidY(self.bounds));
    _didUserZoom = YES;
    [self setScale:_scale * factor anchoredAt:center];
}

- (void)applyScale:(double)scale {
    // 同步只传 scale,不传 origin:让接收方按自己的图像尺寸与视图尺寸重新居中,
    // 避免两边图片尺寸不同(例如几何变换 Fit 模式下输出尺寸变化)时 origin 错位
    // 导致图片被 clipsToBounds 裁光。
    _applyingSync = YES;
    _didUserZoom = YES;
    _scale = fmin(fmax(scale, kMinScale), kMaxScale);
    [self centerOrigin];
    [self viewDidChange];
    _applyingSync = NO;
}

- (void)syncToPartner {
    if (self.syncPartner) { [self.syncPartner applyScale:_scale]; }
}

- (void)viewDidChange {
    self.needsDisplay = YES;
    if (self.onViewDidChange) { self.onViewDidChange(_scale, _origin); }
    if (self.syncPartner && !_applyingSync) {
        [self.syncPartner applyScale:_scale];
    }
}

#pragma mark - 尺寸变化

- (void)setFrameSize:(NSSize)newSize {
    NSSize old = self.frame.size;
    [super setFrameSize:newSize];
    if (old.width <= 0 || old.height <= 0) { [self zoomToFit]; return; }
    if (_autoFitsOnResize && !_didUserZoom) { [self zoomToFit]; return; }

    // 保持画面中心不动:视口宽高各变了多少,图片就跟着挪一半
    _origin.x += (newSize.width  - old.width)  * 0.5;
    _origin.y += (newSize.height - old.height) * 0.5;
    [self clampOrigin];
    [self viewDidChange];
}

#pragma mark - 绘制

- (void)drawRect:(NSRect)dirtyRect {
    [super drawRect:dirtyRect];
    [self drawBackdrop];

    NSImage *image = self.image;
    if (!image) { return; }

    NSSize disp = [self displaySize];
    NSRect dest = NSMakeRect(_origin.x, _origin.y, disp.width, disp.height);

    NSGraphicsContext *ctx = NSGraphicsContext.currentContext;
    // 放大时关插值:要看真实像素网格(最近邻的锯齿、双线性的过渡全靠这个才看得见);
    // 缩小时用高质量,避免大图缩略出现摩尔纹
    ctx.imageInterpolation = (_scale >= 1.0) ? NSImageInterpolationNone : NSImageInterpolationHigh;

    [image drawInRect:dest
             fromRect:NSZeroRect
            operation:NSCompositingOperationSourceOver
             fraction:1.0];

    if (_scale >= kGridMinScale) { [self drawPixelGridInRect:dest]; }
}

/// 棋盘底:几何变换后画布外是透明,深色底分不清"透明"和"黑"
- (void)drawBackdrop {
    const CGFloat kTile = 8.0;
    NSColor *dark  = [NSColor colorWithWhite:0.12 alpha:1.0];
    NSColor *light = [NSColor colorWithWhite:0.16 alpha:1.0];
    NSRect bounds = self.bounds;
    for (CGFloat y = 0; y < bounds.size.height; y += kTile) {
        for (CGFloat x = 0; x < bounds.size.width; x += kTile) {
            BOOL odd = (((NSInteger)(x / kTile) + (NSInteger)(y / kTile)) & 1);
            [(odd ? light : dark) setFill];
            NSRectFill(NSMakeRect(x, y, kTile, kTile));
        }
    }
}

- (void)drawPixelGridInRect:(NSRect)rect {
    NSRect vis = NSIntersectionRect(rect, self.bounds);
    if (NSIsEmptyRect(vis)) { return; }

    [[NSColor colorWithWhite:1.0 alpha:0.07] setStroke];
    NSBezierPath *path = [NSBezierPath bezierPath];
    // 只画可见范围内的网格线,大图放大时不会去画几千条看不见的线
    double startX = rect.origin.x + floor((NSMinX(vis) - rect.origin.x) / _scale) * _scale;
    for (double x = startX; x <= NSMaxX(vis); x += _scale) {
        [path moveToPoint:NSMakePoint(x, NSMinY(vis))];
        [path lineToPoint:NSMakePoint(x, NSMaxY(vis))];
    }
    double startY = rect.origin.y + floor((NSMinY(vis) - rect.origin.y) / _scale) * _scale;
    for (double y = startY; y <= NSMaxY(vis); y += _scale) {
        [path moveToPoint:NSMakePoint(NSMinX(vis), y)];
        [path lineToPoint:NSMakePoint(NSMaxX(vis), y)];
    }
    path.lineWidth = 0.5;
    [path stroke];
}

#pragma mark - 事件

- (void)magnifyWithEvent:(NSEvent *)event {
    NSPoint p = [self convertPoint:event.locationInWindow fromView:nil];
    _didUserZoom = YES;
    [self setScale:_scale * (1.0 + event.magnification) anchoredAt:p];
}

- (void)scrollWheelWithEvent:(NSEvent *)event {
    if ((event.modifierFlags & NSEventModifierFlagCommand) != 0) {
        NSPoint p = [self convertPoint:event.locationInWindow fromView:nil];
        // 上滚 → deltaY 为正 → 放大;指数映射保证每次滚轮的缩放步长一致
        [self setScale:_scale * exp(event.scrollingDeltaY * 0.01) anchoredAt:p];
        _didUserZoom = YES;
        return;
    }
    // 普通滚轮平移:图片跟着内容走,方向与系统滚动一致(视图已翻转,y 取反)
    _origin.x -= event.scrollingDeltaX;
    _origin.y += event.scrollingDeltaY;
    [self clampOrigin];
    [self viewDidChange];
}

- (void)mouseDown:(NSEvent *)event {
    _dragging = YES;
    _dragStartWindow = event.locationInWindow;
    _dragStartOrigin = _origin;
}

- (void)mouseDragged:(NSEvent *)event {
    if (!_dragging) { return; }
    NSPoint p = event.locationInWindow;
    // window 坐标 y 向上,视图 y 向下,所以纵向位移取反
    _origin = NSMakePoint(_dragStartOrigin.x + (p.x - _dragStartWindow.x),
                          _dragStartOrigin.y - (p.y - _dragStartWindow.y));
    [self clampOrigin];
    [self viewDidChange];
}

- (void)mouseUp:(NSEvent *)event {
    _dragging = NO;
    if (event.clickCount == 2) {
        if (_scale > [self fitScale] + 1e-6) { [self zoomToFit]; }
        else { [self zoomToActualSize]; }
    }
}

- (void)keyDown:(NSEvent *)event {
    NSString *key = event.charactersIgnoringModifiers;
    if ([key isEqualToString:@"0"])                                        { [self zoomToFit]; }
    else if ([key isEqualToString:@"1"])                                   { [self zoomToActualSize]; }
    else if ([key isEqualToString:@"+"] || [key isEqualToString:@"="])     { [self zoomBy:1.25]; }
    else if ([key isEqualToString:@"-"])                                   { [self zoomBy:1.0 / 1.25]; }
    else { [super keyDown:event]; }
}

- (void)resetCursorRects {
    if (self.image) { [self addCursorRect:self.bounds cursor:NSCursor.openHandCursor]; }
}

@end
