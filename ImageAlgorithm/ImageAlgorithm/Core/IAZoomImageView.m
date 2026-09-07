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
// 与 Photoshop 对齐:放大到 600% 以上画出像素网格
static const double kGridMinScale = 6.0;

// +/- 按钮与 ⌘± 走这套档位,和 PS 一样落在整数百分比上,
// 而不是 1.25 连乘出来的 87%、109% 这种零头。
static const double kZoomStops[] = {
    0.0625, 0.0833, 0.125, 0.1667, 0.25, 0.3333, 0.5, 0.6667,
    1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 12.0, 16.0, 24.0, 32.0, 48.0, 64.0
};
static const size_t kZoomStopCount = sizeof(kZoomStops) / sizeof(kZoomStops[0]);

@implementation IAZoomImageView {
    double  _scale;
    NSPoint _origin;             // 图片左上角在视图中的位置(视图坐标,y 向下)
    BOOL    _didUserZoom;        // 用户手动缩放过 → 不再自动 fit
    BOOL    _applyingSync;       // 正在接收同步,防 A→B→A 递归
    BOOL    _dragging;
    BOOL    _didDrag;            // 本次按下是否真的挪动过 → 挪过就不算双击
    BOOL    _spaceHeld;          // 空格临时抓手(PS 手感)
    BOOL    _didPushCursor;      // mouseDown 压过握拳光标 → mouseUp 才该 pop
    NSPoint _dragStartWindow;    // 拖拽起点:window 坐标 y 向上,与视图相反
    NSPoint _dragStartOrigin;
}

- (instancetype)initWithFrame:(NSRect)frameRect {
    self = [super initWithFrame:frameRect];
    if (self) {
        _scale = 1.0;
        _autoFitsOnResize = YES;
        self.wantsLayer = YES;
        // 背景由 drawRect 的棋盘底负责,并跟随明暗主题 —— 不在这里钉死颜色
        // 关键:图片放大后 _origin 会变成负值(图片画到 view 上方),
        // 不裁剪的话 drawInRect 会越界画到 superview 上,盖住上面的标题栏
        self.clipsToBounds = YES;
    }
    return self;
}

- (BOOL)isFlipped { return YES; }
- (BOOL)acceptsFirstResponder { return YES; }

#pragma mark - 空格抓手(全局)

// PS 里空格是全局临时抓手,不管键盘焦点在哪都生效。
// 所以状态放在类级别、monitor 只装一份:每个实例各装一个的话,
// 先执行的那个吞掉事件,另一个画布就永远收不到空格。
static NSHashTable<IAZoomImageView *> *gLiveViews = nil;
static id gSpaceMonitor = nil;

+ (void)registerView:(IAZoomImageView *)view {
    if (!gLiveViews) { gLiveViews = [NSHashTable weakObjectsHashTable]; }
    [gLiveViews addObject:view];
    if (gSpaceMonitor) { return; }
    gSpaceMonitor = [NSEvent addLocalMonitorForEventsMatchingMask:(NSEventMaskKeyDown | NSEventMaskKeyUp)
                                                          handler:^NSEvent *(NSEvent *e) {
        if (![e.charactersIgnoringModifiers isEqualToString:@" "]) { return e; }
        // 正在文本框里打字时,空格就是空格
        if ([e.window.firstResponder isKindOfClass:NSTextView.class]) { return e; }
        BOOL held = (e.type == NSEventTypeKeyDown);
        BOOL consumed = NO;
        for (IAZoomImageView *v in gLiveViews.allObjects) {
            if (v.window == e.window) { [v setSpaceHeld:held]; consumed = YES; }
        }
        // 吞掉:否则走完 responder chain 没人处理会 beep,
        // 或者误触到当前有焦点的按钮(空格 = 点击)
        return consumed ? nil : e;
    }];
}

+ (void)unregisterView:(IAZoomImageView *)view {
    [gLiveViews removeObject:view];
    if (gLiveViews.allObjects.count == 0 && gSpaceMonitor) {
        [NSEvent removeMonitor:gSpaceMonitor];
        gSpaceMonitor = nil;
    }
}

- (void)viewDidMoveToWindow {
    [super viewDidMoveToWindow];
    if (self.window) { [IAZoomImageView registerView:self]; }
    else             { [IAZoomImageView unregisterView:self]; [self setSpaceHeld:NO]; }
}

- (void)dealloc {
    [IAZoomImageView unregisterView:self];
}

#pragma mark - 主题

/// 画布是自绘的,拿不到系统控件的自动适配,只能自己问当前外观是明还是暗。
/// 之前颜色全部钉死成近黑,在 light 主题下整块画布突兀,叠在上面的
/// secondaryLabelColor 文字(light 下解析成深灰)更是黑压黑,几乎看不见。
- (BOOL)isDarkAppearance {
    NSAppearanceName name = [self.effectiveAppearance
        bestMatchFromAppearancesWithNames:@[NSAppearanceNameAqua, NSAppearanceNameDarkAqua]];
    return [name isEqualToString:NSAppearanceNameDarkAqua];
}

- (void)viewDidChangeEffectiveAppearance {
    [super viewDidChangeEffectiveAppearance];
    self.needsDisplay = YES;   // 棋盘底与网格线都要按新主题重画
}

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
    // 按 Photoshop 的"适应屏幕":小图也撑大填满窗口。
    // 原来卡在 1.0("只缩不放"),代价是小图的 fit 和 100% 是同一个值 → 双击变死键。
    // 会不会误以为是算法放大?头部的百分比标签已经写着 340%,不至于。
    double fit = fmin(view.width / image.size.width, view.height / image.size.height);
    return fmin(fmax(fit, kMinScale), kMaxScale);
}

/// 与 Photoshop 一致的边界策略:
///   图片某一维比视口小 → 该维强制居中,拖不走(否则画面会莫名其妙地"漂")
///   图片某一维比视口大 → 该维只能在"不露出空边"的范围内拖,到边即停
- (void)clampOrigin {
    NSSize view = self.bounds.size;
    NSSize disp = [self displaySize];
    if (disp.width <= 0 || disp.height <= 0) { return; }

    if (disp.width <= view.width) {
        _origin.x = (view.width - disp.width) * 0.5;
    } else {
        _origin.x = fmin(fmax(_origin.x, view.width - disp.width), 0.0);
    }
    if (disp.height <= view.height) {
        _origin.y = (view.height - disp.height) * 0.5;
    } else {
        _origin.y = fmin(fmax(_origin.y, view.height - disp.height), 0.0);
    }
}

- (void)centerOrigin {
    NSSize view = self.bounds.size;
    NSSize disp = [self displaySize];
    _origin = NSMakePoint((view.width - disp.width) * 0.5, (view.height - disp.height) * 0.5);
}

/// 视口中心此刻落在图像的哪个位置(0~1 归一化)。
/// 同步用它而不是 origin:两边图像尺寸不同也不会错位。
- (NSPoint)normalizedCenter {
    NSSize image = self.image.size;
    if (image.width <= 0 || image.height <= 0) { return NSMakePoint(0.5, 0.5); }
    return NSMakePoint((NSMidX(self.bounds) - _origin.x) / (image.width  * _scale),
                       (NSMidY(self.bounds) - _origin.y) / (image.height * _scale));
}

- (void)setNormalizedCenter:(NSPoint)c {
    NSSize disp = [self displaySize];
    _origin = NSMakePoint(NSMidX(self.bounds) - c.x * disp.width,
                          NSMidY(self.bounds) - c.y * disp.height);
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

/// 找相邻档位。up = YES 取比当前大的第一档。
- (double)nextStopUp:(BOOL)up {
    if (up) {
        for (size_t i = 0; i < kZoomStopCount; i++) {
            if (kZoomStops[i] > _scale * 1.001) { return kZoomStops[i]; }
        }
        return kMaxScale;
    }
    for (size_t i = kZoomStopCount; i > 0; i--) {
        if (kZoomStops[i - 1] < _scale * 0.999) { return kZoomStops[i - 1]; }
    }
    return kMinScale;
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
    // 参数只用来判方向,实际落到标准档位上
    NSPoint center = NSMakePoint(NSMidX(self.bounds), NSMidY(self.bounds));
    _didUserZoom = YES;
    [self setScale:[self nextStopUp:(factor > 1.0)] anchoredAt:center];
}

- (void)applyScale:(double)scale {
    _applyingSync = YES;
    _didUserZoom = YES;
    _scale = fmin(fmax(scale, kMinScale), kMaxScale);
    [self centerOrigin];
    [self viewDidChange];
    _applyingSync = NO;
}

/// 同步的完整形态:缩放 + 视口中心对应的图像归一化坐标。
/// 用归一化坐标而不是 origin,两边图像尺寸不同(几何变换 Fit 模式)也不会错位;
/// 传位置而不是一律居中,才能做到"A 拖到左眼,B 也在左眼"。
- (void)applyScale:(double)scale center:(NSPoint)center {
    _applyingSync = YES;
    _didUserZoom = YES;
    _scale = fmin(fmax(scale, kMinScale), kMaxScale);
    [self setNormalizedCenter:center];
    [self clampOrigin];
    [self viewDidChange];
    _applyingSync = NO;
}

- (void)syncToPartner {
    if (self.syncPartner) {
        [self.syncPartner applyScale:_scale center:[self normalizedCenter]];
    }
}

- (void)viewDidChange {
    self.needsDisplay = YES;
    if (self.onViewDidChange) { self.onViewDidChange(_scale, _origin); }
    if (self.syncPartner && !_applyingSync) {
        [self.syncPartner applyScale:_scale center:[self normalizedCenter]];
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
    self.needsDisplay = YES;
    if (self.onViewDidChange) { self.onViewDidChange(_scale, _origin); }
    // 注意:这里不走 viewDidChange —— 拖分隔条时两个 pane 会一起 resize,
    // 互相同步会打架(A 改完推给 B,B 还没 resize 完又推回 A)
}

#pragma mark - 绘制

- (void)drawRect:(NSRect)dirtyRect {
    [super drawRect:dirtyRect];
    [self drawBackdropInRect:dirtyRect];

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

/// 棋盘底:几何变换后画布外是透明,深色底分不清"透明"和"黑"。
/// 用缓存好的 pattern 一次填充 —— 之前是每帧几千次 NSRectFill,捏合缩放明显掉帧。
- (void)drawBackdropInRect:(NSRect)dirtyRect {
    // 明暗两套各缓存一份:pattern image 是位图,主题切换时得换整张图,不能只改颜色
    static NSColor *darkPattern = nil, *lightPattern = nil;
    BOOL dark = [self isDarkAppearance];
    NSColor *pattern = dark ? darkPattern : lightPattern;
    if (!pattern) {
        const CGFloat kTile = 8.0;
        CGFloat a = dark ? 0.12 : 0.86;   // 深色主题压暗,浅色主题用浅灰,和窗口底色接得上
        CGFloat b = dark ? 0.16 : 0.92;
        NSImage *tile = [NSImage imageWithSize:NSMakeSize(kTile * 2, kTile * 2)
                                       flipped:NO
                                drawingHandler:^BOOL(NSRect rect) {
            [[NSColor colorWithWhite:a alpha:1.0] setFill];
            NSRectFill(rect);
            [[NSColor colorWithWhite:b alpha:1.0] setFill];
            NSRectFill(NSMakeRect(kTile, 0, kTile, kTile));
            NSRectFill(NSMakeRect(0, kTile, kTile, kTile));
            return YES;
        }];
        pattern = [NSColor colorWithPatternImage:tile];
        if (dark) { darkPattern = pattern; } else { lightPattern = pattern; }
    }

    NSGraphicsContext *ctx = NSGraphicsContext.currentContext;
    [ctx saveGraphicsState];
    // pattern 相位是相对 window 的:锁到本视图原点,窗口移动时棋盘才不会跟着滑
    ctx.patternPhase = [self convertPoint:NSZeroPoint toView:nil];
    [pattern setFill];
    NSRectFill(dirtyRect);
    [ctx restoreGraphicsState];
}

- (void)drawPixelGridInRect:(NSRect)rect {
    NSRect vis = NSIntersectionRect(rect, self.bounds);
    if (NSIsEmptyRect(vis)) { return; }

    // 网格线压在图像上,浅色主题下白线等于没画,得换成黑线
    [[NSColor colorWithWhite:([self isDarkAppearance] ? 1.0 : 0.0) alpha:0.10] setStroke];
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

/// 注意方法名:NSResponder 是 scrollWheel:,不是 scrollWheelWithEvent:。
/// 之前写成后者,滚轮的两条路径(⌘缩放 / 平移)从来没被调用过。
- (void)scrollWheel:(NSEvent *)event {
    // 触控板与妙控鼠标给的是像素级增量(一次滑动累计几百),
    // 传统滚轮给的是"行数"(每格 ±1)。同一套系数会让一边飞、一边推不动。
    BOOL precise = event.hasPreciseScrollingDeltas;
    CGFloat dx = event.scrollingDeltaX;
    CGFloat dy = event.scrollingDeltaY;

    if ((event.modifierFlags & NSEventModifierFlagCommand) != 0) {
        NSPoint p = [self convertPoint:event.locationInWindow fromView:nil];
        // 指数映射:同样的滚动量,在任何缩放级别下的"倍率"都一致
        double k = precise ? 0.004 : 0.20;   // 滚轮一格 ≈ exp(0.2) = 1.22 倍
        _didUserZoom = YES;
        [self setScale:_scale * exp(dy * k) anchoredAt:p];
        return;
    }

    if (!precise) { dx *= 16.0; dy *= 16.0; }   // 行 → 像素
    // 内容跟手:视图已翻转(y 向下),自然滚动方向下两个分量都是直接相加
    _origin.x += dx;
    _origin.y += dy;
    [self clampOrigin];
    [self viewDidChange];
}

- (void)mouseDown:(NSEvent *)event {
    // 不 makeFirstResponder 的话,键盘 0/1/+/- 点了也拿不到焦点,等于失效
    [self.window makeFirstResponder:self];
    _didDrag = NO;
    // 按 Photoshop:左键归当前工具,平移要按住空格切临时抓手。
    // 不按空格时左键只用来取焦点和双击。
    _dragging = _spaceHeld;
    if (!_dragging) { return; }
    _dragStartWindow = event.locationInWindow;
    _dragStartOrigin = _origin;
    [NSCursor.closedHandCursor push];
    _didPushCursor = YES;
}

- (void)mouseDragged:(NSEvent *)event {
    if (!_dragging) { return; }
    NSPoint p = event.locationInWindow;
    CGFloat dx = p.x - _dragStartWindow.x;
    CGFloat dy = p.y - _dragStartWindow.y;
    if (!_didDrag && (fabs(dx) > 2.0 || fabs(dy) > 2.0)) { _didDrag = YES; }
    // window 坐标 y 向上,视图 y 向下,所以纵向位移取反
    _origin = NSMakePoint(_dragStartOrigin.x + dx, _dragStartOrigin.y - dy);
    [self clampOrigin];
    [self viewDidChange];
}

- (void)mouseUp:(NSEvent *)event {
    _dragging = NO;
    if (_didPushCursor) { [NSCursor pop]; _didPushCursor = NO; }
    // 拖动过就不算双击 —— 否则"平移完松手"会被误判,画面先移再跳
    if (event.clickCount == 2 && !_didDrag) {
        // 用"是否正停在 fit 上"判断,而不是比大小 —— 小图的 fit 大于 100%,
        // 比大小会让它一直落到 100% 上,双击卡死
        if (fabs(_scale - [self fitScale]) < 1e-6) { [self zoomToActualSize]; }
        else { [self zoomToFit]; }
    }
}

- (void)keyDown:(NSEvent *)event {
    NSString *key = event.charactersIgnoringModifiers;
    if ([key isEqualToString:@"0"])                                        { [self zoomToFit]; }
    else if ([key isEqualToString:@"1"])                                   { [self zoomToActualSize]; }
    else if ([key isEqualToString:@"+"] || [key isEqualToString:@"="])     { [self zoomBy:2.0]; }
    else if ([key isEqualToString:@"-"] || [key isEqualToString:@"_"])     { [self zoomBy:0.5]; }
    else { [super keyDown:event]; }
}

/// ⌘0 / ⌘1 / ⌘+ / ⌘- 走 performKeyEquivalent:带修饰键的按键不会进 keyDown
- (BOOL)performKeyEquivalent:(NSEvent *)event {
    if ((event.modifierFlags & NSEventModifierFlagCommand) == 0) { return NO; }
    if (self.window.firstResponder != self) { return NO; }
    NSString *key = event.charactersIgnoringModifiers;
    if ([key isEqualToString:@"0"])                                    { [self zoomToFit];        return YES; }
    if ([key isEqualToString:@"1"])                                    { [self zoomToActualSize]; return YES; }
    if ([key isEqualToString:@"+"] || [key isEqualToString:@"="])      { [self zoomBy:2.0];       return YES; }
    if ([key isEqualToString:@"-"] || [key isEqualToString:@"_"])      { [self zoomBy:0.5];       return YES; }
    return NO;
}

- (void)setSpaceHeld:(BOOL)held {
    if (_spaceHeld == held) { return; }
    _spaceHeld = held;
    [self.window invalidateCursorRectsForView:self];
}

- (void)resetCursorRects {
    if (!self.image) { return; }
    // 不按空格 → 箭头(左键此刻不平移,光标不该骗人);按住 → 张开手;
    // 真按下去拖的时候由 mouseDown 里 push 的握拳光标接管
    [self addCursorRect:self.bounds cursor:(_spaceHeld ? NSCursor.openHandCursor : NSCursor.arrowCursor)];
}

@end
