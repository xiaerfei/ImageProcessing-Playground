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

@interface ViewController ()
@property (nonatomic, strong) NSPopUpButton *modulePopUp;
@property (nonatomic, strong) NSTextField *subtitleLabel;
@property (nonatomic, strong) NSScrollView *parameterScroll;
@property (nonatomic, strong) NSTextField *statusLabel;
@property (nonatomic, strong) NSTextField *resultTitleLabel;
@property (nonatomic, strong) NSImageView *sourceImageView;
@property (nonatomic, strong) NSImageView *resultImageView;

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
    self.statusLabel = [NSTextField wrappingLabelWithString:@""];
    self.statusLabel.font = [NSFont monospacedDigitSystemFontOfSize:10 weight:NSFontWeightRegular];
    self.statusLabel.textColor = NSColor.secondaryLabelColor;

    NSStackView *footer = [NSStackView stackViewWithViews:@[resetButton, self.statusLabel]];
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

    self.sourceImageView = [self makeImageView];
    self.resultImageView = [self makeImageView];

    NSTextField *sourceTitle = [self paneTitleLabel:@"原图"];
    self.resultTitleLabel = [self paneTitleLabel:@"处理结果"];

    [split addArrangedSubview:[self paneWithTitleLabel:sourceTitle imageView:self.sourceImageView]];
    [split addArrangedSubview:[self paneWithTitleLabel:self.resultTitleLabel imageView:self.resultImageView]];
    return split;
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

- (NSImageView *)makeImageView {
    NSImageView *imageView = [[NSImageView alloc] init];
    imageView.imageScaling = NSImageScaleProportionallyDown;   // 只缩不放,免得误以为是算法放大
    imageView.imageAlignment = NSImageAlignCenter;
    imageView.translatesAutoresizingMaskIntoConstraints = NO;
    imageView.wantsLayer = YES;
    imageView.layer.backgroundColor = [NSColor colorWithWhite:0.12 alpha:1.0].CGColor;
    return imageView;
}

- (NSView *)paneWithTitleLabel:(NSTextField *)label imageView:(NSImageView *)imageView {
    NSView *pane = [[NSView alloc] init];
    [pane addSubview:label];
    [pane addSubview:imageView];
    [NSLayoutConstraint activateConstraints:@[
        [label.topAnchor constraintEqualToAnchor:pane.topAnchor constant:6],
        [label.leadingAnchor constraintEqualToAnchor:pane.leadingAnchor constant:10],
        [imageView.topAnchor constraintEqualToAnchor:label.bottomAnchor constant:4],
        [imageView.leadingAnchor constraintEqualToAnchor:pane.leadingAnchor],
        [imageView.trailingAnchor constraintEqualToAnchor:pane.trailingAnchor],
        [imageView.bottomAnchor constraintEqualToAnchor:pane.bottomAnchor],
        [pane.heightAnchor constraintGreaterThanOrEqualToConstant:140],
    ]];
    return pane;
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
