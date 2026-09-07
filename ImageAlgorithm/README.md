# ImageAlgorithm

macOS 图像算法实验场。每章算法是一个独立模块,共用同一套界面(左侧参数 / 右上原图 / 右下结果)。

```bash
xcodegen generate && open ImageAlgorithm.xcodeproj
```

## 架构

```
ImageAlgorithm/
├── Core/                     宿主框架,与具体算法无关
│   ├── IAAlgorithmModule     模块基类:子类只管参数声明与算法本体
│   ├── IAParameterStore      参数读写(控件即数据源,不维护镜像变量)
│   ├── IAParameterBuilder    声明式参数面板,模块不碰 Auto Layout
│   ├── IAModuleRegistry      模块清单
│   └── IAZoomImageView       可缩放/可平移画布(放大看像素)
├── Algorithm/                可复用的算法原语
│   ├── IAImageBuffer         RGBA8 像素缓冲(预乘 alpha)
│   └── IAAffineTransform     3×3 齐次矩阵 + 反向映射(矩阵运算用 simd)
├── Modules/                  每章一个模块
│   ├── IAGeometryModule      几何变换(第 3 周)
│   └── IAIntensityModule     灰度变换(第 4 周)
└── ViewController            宿主:模块切换、图片载入、计时、双图对比
```

宿主不含任何算法知识,模块不含任何布局代码 —— 加一章算法不需要改宿主。

## 新增一章算法

**1. 写模块**(`Modules/IAYourModule.m`),最少重写三个方法:

```objc
@implementation IAYourModule

+ (NSString *)title { return @"空间滤波"; }
+ (NSString *)subtitle { return @"第 3 章 · 第 6 周"; }

- (void)buildParameters:(IAParameterBuilder *)builder {
    [builder addSection:@"高斯核"];
    [builder addSlider:@"sigma" label:@"σ" min:0.5 max:10 value:1.5 format:@"%.1f"];
    [builder addSegmented:@"border" items:@[@"补零", @"复制", @"镜像"] value:2];
    [builder addNote:@"核尺寸取 6σ 向上取奇数。"];
}

- (IAImageBuffer *)processImage:(IAImageBuffer *)source {
    double sigma = [self.parameters doubleForKey:@"sigma"];
    // …算法本体,返回新的 IAImageBuffer
}

@end
```

**2. 注册**(`Core/IAModuleRegistry.m` 加一行):

```objc
IAYourModule.class,   // 第 6 周
```

完成。切换菜单、参数联动、重置、计时、状态栏都是白送的。

### 可选重写

| 方法 | 用途 |
| :--- | :--- |
| `-parameterDidChange:` | 参数联动(如"锁定 X/Y 比例"、保证 低<高) |
| `-resultTitle` | 结果面板标题,如 `@"梯度幅值图"` |
| `-extraStatus` | 状态栏追加一行,如算出的 Otsu 阈值 |

### 参数面板可用元素

`addSection:` `addSeparator` `addNote:` `addSlider:label:min:max:value:format:`
`addCheckbox:title:value:` `addSegmented:items:value:` `addButton:action:`

## 查看与缩放

两个画布(原图 / 结果)都是 `IAZoomImageView`:

交互对齐 Photoshop:

| 操作 | 效果 |
| :--- | :--- |
| 捏合 / ⌘+滚轮 | 以光标为锚点缩放 |
| 滚轮 | 平移 |
| **空格 + 拖拽** | 平移(空格是全局临时抓手,与 PS 一致) |
| 双击 | 适应窗口 ↔ 1:1 |
| 面板 `−` `+` `1:1` `适应` | 按钮缩放,`±` 走标准档位 |
| 键盘 `0` / `1` / `+` `−`(可带 ⌘) | 同上 |

- 放大到 ≥100% 时**关闭插值**,看到的是真实像素;≥600% 再叠一层像素网格(与 Photoshop 的阈值一致) ——
  最近邻的锯齿与双线性的过渡,只有这时才分得出来
- 「适应窗口」会把小图放大填满窗口(PS 的适应屏幕),不卡在 100%
- 边界策略同 PS:图小于视口则居中锁死,大于视口则拖到边即停,不会拖出空边
- `±` 落在 6.25% / 12.5% / 25% / 50% / 100% / 200% … 这套档位上,而不是 1.25 连乘出来的零头
- 画布外(几何变换空出来的区域)画棋盘底,透明与纯黑一眼可分;
  棋盘底、像素网格线都跟随系统明暗主题
- 「同步两图缩放」默认关闭,开启后同步的是缩放比例 **+ 视口中心的归一化坐标** ——
  A 拖到哪 B 跟到哪;用归一化坐标而非 origin,两边图像尺寸不同也不会错位
- 调参数时只要输出尺寸没变,视角保持不变,不会跳回"适应"

> 空格被画布全局捕获(否则键盘焦点不在画布上时按空格无效),
> 代价是焦点落在复选框上时空格不再切换它 —— PS 语义的直接后果。

## 测试

不依赖 XCTest,命令行直接跑(文件头有完整命令):

```bash
clang -fobjc-arc -framework Cocoa -I ImageAlgorithm/Algorithm \
      -o /tmp/tt Tests/transform_tests.m ImageAlgorithm/Algorithm/*.m && /tmp/tt
```

- `Tests/transform_tests.m` — 几何变换正确性(单位变换/平移/镜像/转置/旋转 360°/奇异矩阵)
- `Tests/module_tests.m` — 模块架构端到端 + 灰度变换 LUT 正确性

## 矩阵运算

用 Apple 的 **simd**(`<simd/simd.h>`,系统框架,零依赖):`simd_mul` / `simd_inverse` /
`simd_determinant`,构造用 `simd_matrix_from_rows` 按课本行布局书写。它也是 Metal 的矩阵类型,
以后算法搬到 shader 可直接复用。

选型实测(Apple Silicon,3×3 double):

| 操作 | 手写 | simd | Accelerate LAPACK |
| :--- | ---: | ---: | ---: |
| 求逆(每次变换一次) | 6.9 ns | 15.9 ns | 392 ns |
| 矩阵×向量(每像素) | 7.8 ms/1080p | **6.0 ms** | — |

两个函数的快慢方向相反,原因在于**是否内联**:

- `simd_mul` 的实现就写在头文件里,完全内联 → 热循环里比手写快 1.3 倍,这是采用 simd 的实际收益。
- `simd_inverse` 只是个壳,转发给 libsystem_m 里的外部符号 `__invert_d3`(`nm -u` 可见)。
  跨库调用意味着 96 字节的矩阵要经内存按指针传参;反汇编可见它内部同样是标量代数余子式展开,
  算完 9 个余子式后先写回内存、再以 `q` 寄存器读出来乘 1/det —— 多了一趟内存往返。
  内联的手写版全程待在寄存器里,所以更快。
- 但求逆每次变换只调一次,9 ns 的差距对上毫秒级的 warp 可以忽略,不值得为此保留手写代码。

LAPACK 是给大矩阵用的,3×3 上比 simd 慢 25 倍,不要用。Accelerate 的价值在别处 ——
vImage/vDSP 的卷积与 FFT 可以做后续章节的对照基准。

## 已知约束

- 处理在主线程同步执行。测试图(600×400)双线性约 9ms;换成 4K 图会卡顿,届时需要挪到后台队列。
- `IAImageBuffer` 是预乘 alpha。对不透明图无影响;将来处理带透明度的图,点运算前需先反预乘。
