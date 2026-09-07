//
//  ViewController.m
//  ImageAlgorithm
//
//  模块宿主。负责所有算法共用的部分:模块切换、图片载入、双图对比、计时与状态。
//  具体算法与参数由 IAAlgorithmModule 子类提供,这里不含任何算法知识。
//
//  布局:左侧(模块选择 + 参数面板 + 状态) | 右侧上下(原图 / 处理结果)
//

#import <QuartzCore/QuartzCore.h>
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>

#import "ViewController.h"
#import "IAAlgorithmModule.h"
#import "IAModuleRegistry.h"
#import "IAZoomImageView.h"

@interface ViewController ()
@property (nonatomic, strong) NSPopUpButton *modulePopUp;
@property (nonatomic, strong) NSTextField *subtitleLabel;
@property (nonatomic, strong) NSScrollView *parameterScroll;
@property (nonatomic, strong) NSTextField *statusLabel;
@property (nonatomic, strong) NSTextField *resultTitleLabel;
@property (nonatomic, strong) IAZoomImageView *sourceImageView;
@property (nonatomic, strong) IAZoomImageView *resultImageView;
@property (nonatomic, strong) NSTextField *sourceZoomLabel;
@property (nonatomic, strong) NSTextField *resultZoomLabel;
@property (nonatomic, strong) NSButton *syncZoomCheckbox;
@property (nonatomic, strong) NSSplitView *previewSplit;
@property (nonatomic) CGFloat lastSplitHeight;
@property (nonatomic) CGFloat splitRatio;

@property (nonatomic, strong) IAImageBuffer *sourceBuffer;
@property (nonatomic, strong) NSMutableDictionary<NSString *, IAAlgorithmModule *> *moduleCache;
@property (nonatomic, strong, nullable) IAAlgorithmModule *currentModule;
@end

@implementation ViewController

- (void)loadView {
    self.view = [[NSView alloc] initWithFrame:NSMakeRect(0, 0, 1100, 760)];
}

- (void)viewDidLoad {
    [super viewDidLoad];
    self.moduleCache = [NSMutableDictionary dictionary];
    [self buildLayout];
    [self selectModuleAtIndex:0];
    [self loadDefaultImage];
}

- (void)viewDidAppear {
    [super viewDidAppear];
    NSWindow *window = self.view.window;
    window.title = @"ImageAlgorithm — 数字图像处理实验场";
    window.minSize = NSMakeSize(900, 620);
    if (window.frame.size.width < 900) {
        [window setFrame:NSMakeRect(window.frame.origin.x, window.frame.origin.y, 1100, 760)
                 display:YES];
        [window center];
    }
}

#pragma mark - 布局

- (void)buildLayout {
    NSSplitView *mainSplit = [[NSSplitView alloc] init];
    mainSplit.vertical = YES;
    mainSplit.dividerStyle = NSSplitViewDividerStyleThin;
    mainSplit.translatesAutoresizingMaskIntoConstraints = NO;

    [mainSplit addArrangedSubview:[self buildLeftColumn]];
    [mainSplit addArrangedSubview:[self buildRightColumn]];
    [mainSplit setHoldingPriority:NSLayoutPriorityDefaultHigh forSubviewAtIndex:0];
    [mainSplit setHoldingPriority:NSLayoutPriorityDefaultLow forSubviewAtIndex:1];

    [self.view addSubview:mainSplit];
    [NSLayoutConstraint activateConstraints:@[
        [mainSplit.topAnchor constraintEqualToAnchor:self.view.topAnchor],
        [mainSplit.bottomAnchor constraintEqualToAnchor:self.view.bottomAnchor],
        [mainSplit.leadingAnchor constraintEqualToAnchor:self.view.leadingAnchor],
        [mainSplit.trailingAnchor constraintEqualToAnchor:self.view.trailingAnchor],
    ]];
}

/// 左列:固定的头部(模块选择/打开图片)+ 可滚动的参数区 + 固定的底部(重置/状态)
- (NSView *)buildLeftColumn {
    NSView *column = [[NSView alloc] init];
    [column.widthAnchor constraintGreaterThanOrEqualToConstant:250].active = YES;
    [column.widthAnchor constraintLessThanOrEqualToConstant:360].active = YES;

    self.modulePopUp = [NSPopUpButton buttonWithTitle:@""
                                               target:self action:@selector(moduleChanged:)];
    for (Class moduleClass in IAModuleRegistry.moduleClasses) {
        [self.modulePopUp addItemWithTitle:[moduleClass title]];
    }

    self.subtitleLabel = [NSTextField labelWithString:@""];
    self.subtitleLabel.font = [NSFont systemFontOfSize:10];
    self.subtitleLabel.textColor = NSColor.tertiaryLabelColor;

    NSButton *openButton = [NSButton buttonWithTitle:@"打开图片…"
                                              target:self action:@selector(openImageClicked:)];

    NSStackView *header = [NSStackView stackViewWithViews:@[self.modulePopUp, self.subtitleLabel, openButton]];
    header.orientation = NSUserInterfaceLayoutOrientationVertical;
    header.alignment = NSLayoutAttributeLeading;
    header.spacing = 6.0;
    header.edgeInsets = NSEdgeInsetsMake(14, 16, 10, 16);
    header.translatesAutoresizingMaskIntoConstraints = NO;

    self.parameterScroll = [[NSScrollView alloc] init];
    self.parameterScroll.hasVerticalScroller = YES;
    self.parameterScroll.drawsBackground = NO;
    self.parameterScroll.translatesAutoresizingMaskIntoConstraints = NO;

    NSButton *resetButton = [NSButton buttonWithTitle:@"重置参数"
                                               target:self action:@selector(resetClicked:)];
    self.syncZoomCheckbox = [NSButton checkboxWithTitle:@"同步两图缩放" target:self action:@selector(syncZoomToggled:)];
    self.syncZoomCheckbox.state = NSControlStateValueOff;
    self.syncZoomCheckbox.toolTip = @"开启后,原图与结果图共用同一缩放比例(各自居中),便于对比大小关系";
    self.statusLabel = [NSTextField wrappingLabelWithString:@""];
    self.statusLabel.font = [NSFont monospacedDigitSystemFontOfSize:10 weight:NSFontWeightRegular];
    self.statusLabel.textColor = NSColor.secondaryLabelColor;

    NSStackView *footer = [NSStackView stackViewWithViews:@[resetButton, self.syncZoomCheckbox, self.statusLabel]];
    footer.orientation = NSUserInterfaceLayoutOrientationVertical;
    footer.alignment = NSLayoutAttributeLeading;
    footer.spacing = 6.0;
    footer.edgeInsets = NSEdgeInsetsMake(10, 16, 14, 16);
    footer.translatesAutoresizingMaskIntoConstraints = NO;

    NSBox *topLine = [self horizontalLine];
    NSBox *bottomLine = [self horizontalLine];
    for (NSView *v in @[header, topLine, self.parameterScroll, bottomLine, footer]) {
        [column addSubview:v];
    }

    [NSLayoutConstraint activateConstraints:@[
        [header.topAnchor constraintEqualToAnchor:column.topAnchor],
        [header.leadingAnchor constraintEqualToAnchor:column.leadingAnchor],
        [header.trailingAnchor constraintEqualToAnchor:column.trailingAnchor],

        [topLine.topAnchor constraintEqualToAnchor:header.bottomAnchor],
        [topLine.leadingAnchor constraintEqualToAnchor:column.leadingAnchor],
        [topLine.trailingAnchor constraintEqualToAnchor:column.trailingAnchor],

        [self.parameterScroll.topAnchor constraintEqualToAnchor:topLine.bottomAnchor],
        [self.parameterScroll.leadingAnchor constraintEqualToAnchor:column.leadingAnchor],
        [self.parameterScroll.trailingAnchor constraintEqualToAnchor:column.trailingAnchor],
        [self.parameterScroll.bottomAnchor constraintEqualToAnchor:bottomLine.topAnchor],

        [bottomLine.leadingAnchor constraintEqualToAnchor:column.leadingAnchor],
        [bottomLine.trailingAnchor constraintEqualToAnchor:column.trailingAnchor],
        [bottomLine.bottomAnchor constraintEqualToAnchor:footer.topAnchor],

        [footer.leadingAnchor constraintEqualToAnchor:column.leadingAnchor],
        [footer.trailingAnchor constraintEqualToAnchor:column.trailingAnchor],
        [footer.bottomAnchor constraintEqualToAnchor:column.bottomAnchor],
        [self.statusLabel.widthAnchor constraintEqualToAnchor:footer.widthAnchor constant:-32],
    ]];
    return column;
}

- (NSView *)buildRightColumn {
    NSSplitView *split = [[NSSplitView alloc] init];
    split.vertical = NO;
    split.dividerStyle = NSSplitViewDividerStyleThin;
    split.translatesAutoresizingMaskIntoConstraints = NO;
    self.previewSplit = split;

    self.sourceImageView = [self makeZoomViewWithTag:0];
    self.resultImageView = [self makeZoomViewWithTag:1];
    // 注意:不在这里设 syncPartner —— 同步只由左下角 checkbox 控制,
    // 默认关闭,避免两个视图在启动/换图阶段相互干扰(曾经的错位 bug 根源)

    self.sourceZoomLabel = [self zoomPercentLabel];
    self.resultZoomLabel = [self zoomPercentLabel];

    NSTextField *sourceTitle = [self paneTitleLabel:@"原图"];
    self.resultTitleLabel = [self paneTitleLabel:@"处理结果"];

    [split addArrangedSubview:[self paneWithTitleLabel:sourceTitle
                                             zoomView:self.sourceImageView
                                            zoomLabel:self.sourceZoomLabel
                                                  tag:0]];
    [split addArrangedSubview:[self paneWithTitleLabel:self.resultTitleLabel
                                             zoomView:self.resultImageView
                                            zoomLabel:self.resultZoomLabel
                                                  tag:1]];
    return split;
}

/// 两个 pane 只有"最小高度 140"这一个约束,没有任何等高倾向,
/// AppKit 会把多余空间全塞给其中一个(一边占满、另一边被压成一条)。
///
/// 光在首次布局摆正一次不够 —— 窗口之后每 resize 一次,增量又会被全塞给一边。
/// 所以这里维护一个比例:高度变了就按比例重设分隔条,高度没变(说明是用户
/// 拖了分隔条)就把新比例记下来。用户的手动调整因此能在缩放窗口后保持。
- (void)viewDidLayout {
    [super viewDidLayout];
    NSSplitView *split = self.previewSplit;
    CGFloat h = split.bounds.size.height;
    if (h < 2 * 140) { return; }   // 还没排完版,或者窗口太矮,等下一轮

    if (fabs(h - self.lastSplitHeight) < 0.5) {
        NSView *top = split.arrangedSubviews.firstObject;
        CGFloat topH = top.frame.size.height;
        if (topH > 0) { self.splitRatio = topH / h; }
        return;
    }
    self.lastSplitHeight = h;
    if (self.splitRatio <= 0.01 || self.splitRatio >= 0.99) { self.splitRatio = 0.5; }
    [split setPosition:(h - split.dividerThickness) * self.splitRatio ofDividerAtIndex:0];
}

- (NSBox *)horizontalLine {
    NSBox *box = [[NSBox alloc] init];
    box.boxType = NSBoxSeparator;
    box.translatesAutoresizingMaskIntoConstraints = NO;
    return box;
}

- (NSTextField *)paneTitleLabel:(NSString *)text {
    NSTextField *label = [NSTextField labelWithString:text];
    label.font = [NSFont boldSystemFontOfSize:11];
    label.textColor = NSColor.secondaryLabelColor;
    label.translatesAutoresizingMaskIntoConstraints = NO;
    return label;
}

- (IAZoomImageView *)makeZoomViewWithTag:(NSInteger)tag {
    IAZoomImageView *view = [[IAZoomImageView alloc] init];
    view.translatesAutoresizingMaskIntoConstraints = NO;
    __weak typeof(self) weakSelf = self;
    view.onViewDidChange = ^(double scale, NSPoint origin) {
        __strong typeof(weakSelf) self = weakSelf;
        if (!self) { return; }
        NSTextField *label = (tag == 0) ? self.sourceZoomLabel : self.resultZoomLabel;
        label.stringValue = [NSString stringWithFormat:@"%.0f%%", scale * 100.0];
    };
    return view;
}

- (NSTextField *)zoomPercentLabel {
    NSTextField *label = [NSTextField labelWithString:@"100%"];
    label.font = [NSFont monospacedDigitSystemFontOfSize:10 weight:NSFontWeightRegular];
    label.textColor = NSColor.secondaryLabelColor;
    label.translatesAutoresizingMaskIntoConstraints = NO;
    return label;
}

- (NSView *)paneWithTitleLabel:(NSTextField *)label
                      zoomView:(IAZoomImageView *)zoomView
                     zoomLabel:(NSTextField *)zoomLabel
                           tag:(NSInteger)tag {
    // ── 布局思路 ────────────────────────────────────────────────────────
    // header 高度固定为 26pt,zoomView 用显式 top/bottom 填满剩余空间。
    // 不用 NSStackView:IAZoomImageView 没有实现 intrinsicContentSize,
    // stack 对其高度分配在两个 pane 上可能不一致,这是"修好下面坏上面"的根源。
    // 全部锚点都是 pane 的固定几何,任意 pane 高度下都无歧义:头必在上。
    NSView *pane = [[NSView alloc] init];

    NSSegmentedControl *zoomSeg =
        [NSSegmentedControl segmentedControlWithLabels:@[@"−", @"+", @"1:1", @"适应"]
                                         trackingMode:NSSegmentSwitchTrackingMomentary
                                               target:self
                                               action:@selector(zoomAction:)];
    zoomSeg.tag = tag;
    zoomSeg.font = [NSFont systemFontOfSize:10];
    zoomSeg.toolTip = @"缩放;⌘+滚轮 / 捏合 缩放,空格+拖拽 平移,双击 切换适应/1:1";

    NSStackView *tools = [NSStackView stackViewWithViews:@[zoomLabel, zoomSeg]];
    tools.orientation = NSUserInterfaceLayoutOrientationHorizontal;
    tools.spacing = 6.0;
    tools.translatesAutoresizingMaskIntoConstraints = NO;

    // 用系统材质而不是自画深色底:标题与百分比用的是 secondaryLabelColor 这类
    // 语义色,它们在 light 外观下解析成深灰 —— 压在钉死的近黑底上就是黑压黑,
    // 缩放百分比几乎读不出来。交给 NSVisualEffectView,明暗两套自动对得上。
    NSVisualEffectView *header = [[NSVisualEffectView alloc] init];
    header.material = NSVisualEffectMaterialHeaderView;
    header.blendingMode = NSVisualEffectBlendingModeWithinWindow;
    header.state = NSVisualEffectStateActive;
    header.wantsLayer = YES;
    header.layer.cornerRadius = 4.0;
    header.translatesAutoresizingMaskIntoConstraints = NO;
    [header addSubview:label];
    [header addSubview:tools];

    [pane addSubview:header];
    [pane addSubview:zoomView];

    [NSLayoutConstraint activateConstraints:@[
        // header:顶部贴 pane(留 4pt),高度固定 26,不再随内容浮动
        [header.topAnchor      constraintEqualToAnchor:pane.topAnchor      constant:4],
        [header.leadingAnchor  constraintEqualToAnchor:pane.leadingAnchor  constant:6],
        [header.trailingAnchor constraintEqualToAnchor:pane.trailingAnchor constant:-6],
        [header.heightAnchor   constraintEqualToConstant:26],

        // header 内部:标题左对齐,工具右对齐,纵向居中
        [label.leadingAnchor   constraintEqualToAnchor:header.leadingAnchor  constant:8],
        [label.centerYAnchor   constraintEqualToAnchor:header.centerYAnchor],
        [tools.trailingAnchor  constraintEqualToAnchor:header.trailingAnchor constant:-8],
        [tools.centerYAnchor   constraintEqualToAnchor:header.centerYAnchor],

        // zoomView:从 header 底部下方 6pt 起,一直延伸到 pane 底部 → 头/底顺序固定
        [zoomView.topAnchor      constraintEqualToAnchor:header.bottomAnchor constant:6],
        [zoomView.leadingAnchor  constraintEqualToAnchor:pane.leadingAnchor],
        [zoomView.trailingAnchor constraintEqualToAnchor:pane.trailingAnchor],
        [zoomView.bottomAnchor   constraintEqualToAnchor:pane.bottomAnchor],

        [pane.heightAnchor constraintGreaterThanOrEqualToConstant:140],
    ]];
    return pane;
}

#pragma mark - 缩放

- (void)zoomAction:(NSSegmentedControl *)sender {
    IAZoomImageView *view = (sender.tag == 0) ? self.sourceImageView : self.resultImageView;
    switch (sender.selectedSegment) {
        case 0: [view zoomBy:1.0 / 1.25]; break;
        case 1: [view zoomBy:1.25];       break;
        case 2: [view zoomToActualSize];  break;
        case 3: [view zoomToFit];         break;
        default: break;
    }
}

- (void)syncZoomToggled:(NSButton *)sender {
    BOOL on = (sender.state == NSControlStateValueOn);
    self.sourceImageView.syncPartner = on ? self.resultImageView : nil;
    self.resultImageView.syncPartner = on ? self.sourceImageView : nil;
    if (on) { [self.sourceImageView syncToPartner]; }
}

#pragma mark - 模块切换

- (void)selectModuleAtIndex:(NSInteger)index {
    NSArray<Class> *classes = IAModuleRegistry.moduleClasses;
    if (index < 0 || index >= (NSInteger)classes.count) { return; }

    Class moduleClass = classes[index];
    NSString *cacheKey = NSStringFromClass(moduleClass);

    // 缓存实例,切回来时参数还在
    IAAlgorithmModule *module = self.moduleCache[cacheKey];
    if (!module) {
        module = [[moduleClass alloc] init];
        __weak typeof(self) weakSelf = self;
        module.onNeedsReprocess = ^{ [weakSelf runCurrentModule]; };
        self.moduleCache[cacheKey] = module;
    }
    self.currentModule = module;
    // 程序化切换时下拉框不会自己动,这里同步一下(用户手动选时是幂等的)
    if (self.modulePopUp.indexOfSelectedItem != index) {
        [self.modulePopUp selectItemAtIndex:index];
    }

    NSString *subtitle = [moduleClass subtitle];
    self.subtitleLabel.stringValue = subtitle ?: @"";
    self.resultTitleLabel.stringValue = module.resultTitle ?: @"处理结果";

    NSView *paramView = module.parameterView;
    self.parameterScroll.documentView = paramView;
    [NSLayoutConstraint activateConstraints:@[
        [paramView.widthAnchor constraintEqualToAnchor:self.parameterScroll.widthAnchor],
    ]];

    [self runCurrentModule];
}

- (void)moduleChanged:(NSPopUpButton *)sender {
    [self selectModuleAtIndex:sender.indexOfSelectedItem];
}

- (void)resetClicked:(id)sender {
    [self.currentModule resetParameters];
}

#pragma mark - 图片

- (void)loadDefaultImage {
    NSURL *url = [NSBundle.mainBundle URLForResource:@"coffee" withExtension:@"png"];
    NSImage *image = url ? [[NSImage alloc] initWithContentsOfURL:url] : nil;
    if (image) {
        [self setSourceImage:image];
    } else {
        self.statusLabel.stringValue = @"未找到内置测试图,请点「打开图片…」";
    }
}

- (void)openImageClicked:(id)sender {
    NSOpenPanel *openPanel = [NSOpenPanel openPanel];
    openPanel.allowedContentTypes = @[UTTypeImage];
    openPanel.allowsMultipleSelection = NO;
    [openPanel beginSheetModalForWindow:self.view.window completionHandler:^(NSModalResponse result) {
        if (result != NSModalResponseOK || !openPanel.URL) { return; }
        NSImage *image = [[NSImage alloc] initWithContentsOfURL:openPanel.URL];
        if (image) { [self setSourceImage:image]; }
    }];
}

- (void)setSourceImage:(NSImage *)image {
    self.sourceBuffer = [IAImageBuffer bufferWithImage:image];
    self.sourceImageView.image = self.sourceBuffer.image;
    [self runCurrentModule];
}

#pragma mark - 执行

- (void)runCurrentModule {
    IAAlgorithmModule *module = self.currentModule;
    IAImageBuffer *src = self.sourceBuffer;
    if (!module || !src) { return; }

    NSTimeInterval start = CACurrentMediaTime();
    IAImageBuffer *result = [module processImage:src];
    NSTimeInterval elapsed = (CACurrentMediaTime() - start) * 1000.0;

    if (!result) {
        self.statusLabel.stringValue = @"当前参数下无法处理(矩阵不可逆或输出过大)";
        return;
    }

    self.resultImageView.image = result.image;
    self.resultTitleLabel.stringValue = module.resultTitle ?: @"处理结果";

    NSMutableArray<NSString *> *lines = [NSMutableArray array];
    [lines addObject:[NSString stringWithFormat:@"源 %ld×%ld → 出 %ld×%ld",
                      (long)src.width, (long)src.height, (long)result.width, (long)result.height]];
    [lines addObject:[NSString stringWithFormat:@"耗时 %.1f ms", elapsed]];
    NSString *extra = module.extraStatus;
    if (extra.length > 0) { [lines addObject:extra]; }
    self.statusLabel.stringValue = [lines componentsJoinedByString:@"\n"];
}

@end
