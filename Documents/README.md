# Documents

读书笔记、公式推导图解。按主题分目录,目录名前缀的数字是**建议的阅读顺序**,
不是书的章节号。配图与笔记放在同一个目录下(`*-images/`)。

```
Documents/
├── 00-roadmap/        学习路线、全书知识地图、参考资料
├── 01-fundamentals/   图像是什么:内存布局、通道顺序、取整与浮点
├── 02-intensity/      亮度与灰度:取亮度、灰度变换、Luma 与线性光
├── 03-histogram/      直方图与对比度:算法、摄影视角、对比度度量
├── 04-geometry/       几何变换:仿射变换原理与 macOS 实现分析
└── reference-code/    外部参考代码(《VC++ 图像处理程序设计》配套工程)
```

## 00-roadmap —— 先看这里

| 文档 | 内容 |
| :--- | :--- |
| [book-outline.md](00-roadmap/book-outline.md) | 全书 12 章知识点地图 + 每章在路线中的定位 |
| [数字图像处理自学路线规划.md](00-roadmap/数字图像处理自学路线规划.md) | 这个仓库的由来:结合 10 年 iOS/音视频背景定制的冈萨雷斯自学路线(Gemini 对话记录) |
| [参考资料.md](00-roadmap/参考资料.md) | 外部链接收藏:Imageshop 博客、GIMP 源码等 |

## 01-fundamentals —— 图像是什么

| 文档 | 内容 |
| :--- | :--- |
| [week01-image-memory-layout.md](01-fundamentals/week01-image-memory-layout.md) | 图像内存布局、BGR/RGB、YUV 三种排布、cv2 的 I420 标准实测 |
| [rounding-and-float.md](01-fundamentals/rounding-and-float.md) | **取整与浮点**:小数落回 uint8 的三条规矩。截断为什么是单向偏置(实测 20 轮后整图暗 13 个灰阶)、中间结果别落回 uint8(全程 float 偏移为 0)、`astype` 的回绕坑(300 → 44 变黑斑)、银行家舍入、OpenCV 的整数定点 `+32768 >> 16`、什么时候反而该用 floor |

## 02-intensity —— 亮度与灰度

| 文档 | 内容 |
| :--- | :--- |
| [intensity-and-grayscale.md](02-intensity/intensity-and-grayscale.md) | **原理篇**:线性/对数/幂律为什么这么设计、彼此区别与坑;RGB→灰度加权、各图像类型取亮度、六种亮度定义辨析 |
| [gray-transform-tutorial.md](02-intensity/gray-transform-tutorial.md) | **图解篇**:七种灰度变换方法的效果图与 OpenCV 代码(反转/对数/幂律/对比度拉伸/灰度级分层/比特平面/阈值化)。改写自知乎文章并修正了几处错误 |
| [luma-and-linear-light.md](02-intensity/luma-and-linear-light.md) | **亮度的三种含义**:Luminance / Luma / Lightness 到底差在哪;Luma 为什么是「算错了但用了 70 年」的近似(分贝类比 + 高饱和色实测差 70+);**线性光**为什么不能直接存(8bit 的 256 档怎么分配、线性要 16.6bit 才追平、位深一够大家立刻用线性);**YUV**:Y 平面直接就是亮度、limited range 陷阱(ffmpeg 实测白 235 黑 16)、为什么必须先分离亮度才能做色度子采样;**Y 怎么显示回屏幕**(抄三份 R=G=B=Y 就是 U=V=128 的 YUV→RGB 精确解、matplotlib `vmin/vmax` 不给会偷偷拉对比度、线性域算的 Y 直接送显示会偏暗) |

## 03-histogram —— 直方图与对比度

| 文档 | 内容 |
| :--- | :--- |
| [histogram-transform.md](03-histogram/histogram-transform.md) | **算法篇**:直方图是什么、均衡化的 CDF 原理与手算实例、为什么柱子不会真的变平、CLAHE、规定化。**深入部分**(七节):直方图/PDF/CDF 三者关系、概率积分变换证明、空间信息丢失实证、gamma 域 vs 线性域、**CLAHE 从零拆解**(全局→AHE→插值→限幅,四种做法并排图)、规定化手算、分通道均衡的色相偏移实测 |
| [histogram-reading.md](03-histogram/histogram-reading.md) | **摄影篇**:如何用眼睛读直方图。四种直方图辨析(RGB叠加 vs 明度)、分量图/Waveform、曝光诊断、宽容度与包围曝光、向右曝光 ETTR、影调三维分类(低中高/长中短/软硬)。整理自三篇知乎文章并修正 8 处 |
| [contrast.md](03-histogram/contrast.md) | **对比度**:和亮度的区别(加法改亮度/乘法改对比度)、直方图宽度、为什么不能用 max−min 统计、标准差与百分位跨度、自动色阶为何扔掉 1%、显示器上三个不同的「对比度」 |

## 04-geometry —— 几何变换

| 文档 | 内容 |
| :--- | :--- |
| [图像仿射变换原理解析.md](04-geometry/图像仿射变换原理解析.md) | **原理篇**:仿射变换的数学基础、基础变换矩阵、复合变换的相乘顺序、重采样、自适应画布、坑点清单与完整参考实现。配套代码 `ImageAlgorithm/Algorithm/IAAffineTransform.m` |
| [MacOS-图像仿射变换与采样模块分析.md](04-geometry/MacOS-图像仿射变换与采样模块分析.md) | **素材**:围绕 `IAAffineTransform.m` 的逐点答疑原始记录(Gemini 对话),已被上一篇系统整理过 |

## 数学"回血"资源

- 3Blue1Brown《线性代数的本质》—— 矩阵运算直觉
- 3Blue1Brown《傅里叶变换的本质》—— 阶段三开始前观看
- 心法:把书中的公式当作"伪代码",双重求和 = 两层 for 循环或矩阵点乘;按需查找,即用即补
