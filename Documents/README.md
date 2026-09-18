# Documents

读书笔记、公式推导图解。

> **怎么看**:目录名和文件名前面的两位数字都是**建议的阅读顺序** ——
> 先按目录序号 `00 → 05`,每个目录内再按文件序号 `01 → 0N` 顺着读下去就行。
> 这个序号不是书的章节号(书的章节对应关系写在每篇开头)。
> 配图与笔记放在同一个目录下(`*-images/`)。

```
Documents/
├── 00-roadmap/        学习路线、全书知识地图、参考资料
├── 01-fundamentals/   图像是什么:内存布局、通道顺序、取整与浮点、LUT
├── 02-intensity/      亮度与灰度:取亮度、灰度变换、Luma 与线性光
├── 03-histogram/      直方图与对比度:算法、摄影视角、对比度度量
├── 04-geometry/       几何变换:仿射变换原理与 macOS 实现分析
├── 05-spatial-filtering/  空间滤波:卷积与相关、边界、可分离核、平滑、锐化
└── reference-code/    外部参考代码(《VC++ 图像处理程序设计》配套工程)
```

## 00-roadmap —— 先看这里

| 文档 | 内容 |
| :--- | :--- |
| [01-book-outline.md](00-roadmap/01-book-outline.md) | 全书 12 章知识点地图 + 每章在路线中的定位 |
| [02-数字图像处理自学路线规划.md](00-roadmap/02-数字图像处理自学路线规划.md) | 这个仓库的由来:结合 10 年 iOS/音视频背景定制的冈萨雷斯自学路线(Gemini 对话记录) |
| [03-参考资料.md](00-roadmap/03-参考资料.md) | 外部链接收藏:Imageshop 博客、GIMP 源码等 |

## 01-fundamentals —— 图像是什么

| 文档 | 内容 |
| :--- | :--- |
| [01-week01-image-memory-layout.md](01-fundamentals/01-week01-image-memory-layout.md) | 图像内存布局、BGR/RGB、YUV 三种排布、cv2 的 I420 标准实测 |
| [02-rounding-and-float.md](01-fundamentals/02-rounding-and-float.md) | **取整与浮点**:小数落回 uint8 的三条规矩。截断为什么是单向偏置(实测 20 轮后整图暗 13 个灰阶)、中间结果别落回 uint8(全程 float 偏移为 0)、`astype` 的回绕坑(300 → 44 变黑斑)、银行家舍入、OpenCV 的整数定点 `+32768 >> 16`、什么时候反而该用 floor |
| [03-lut.md](01-fundamentals/03-lut.md) | **LUT(查找表)**:从 3.2 起每篇都在用的那张表。为什么 8 位图能塌缩成 256 项、1080p 上快 **88 倍**的实测、「输出只取决于该像素自己的值」这条判据(均衡化算,模糊和 CLAHE 不算)、1D 与 **3D LUT**(.cube)、`cv2.LUT` 的 8/16 位表长限制、ffmpeg 与显示器里你早就见过的 LUT |

## 02-intensity —— 亮度与灰度

| 文档 | 内容 |
| :--- | :--- |
| [01-intensity-and-grayscale.md](02-intensity/01-intensity-and-grayscale.md) | **原理篇**:线性/对数/幂律为什么这么设计、彼此区别与坑;RGB→灰度加权、各图像类型取亮度、六种亮度定义辨析 |
| [02-gray-transform-tutorial.md](02-intensity/02-gray-transform-tutorial.md) | **图解篇**:七种灰度变换方法的效果图与 OpenCV 代码(反转/对数/幂律/对比度拉伸/灰度级分层/比特平面/阈值化)。改写自知乎文章并修正了几处错误 |
| [03-luma-and-linear-light.md](02-intensity/03-luma-and-linear-light.md) | **亮度的三种含义**:Luminance / Luma / Lightness 到底差在哪;Luma 为什么是「算错了但用了 70 年」的近似(分贝类比 + 高饱和色实测差 70+);**线性光**为什么不能直接存(8bit 的 256 档怎么分配、线性要 16.6bit 才追平、位深一够大家立刻用线性);**YUV**:Y 平面直接就是亮度、limited range 陷阱(ffmpeg 实测白 235 黑 16)、为什么必须先分离亮度才能做色度子采样;**Y 怎么显示回屏幕**(抄三份 R=G=B=Y 就是 U=V=128 的 YUV→RGB 精确解、matplotlib `vmin/vmax` 不给会偷偷拉对比度、线性域算的 Y 直接送显示会偏暗) |

## 03-histogram —— 直方图与对比度

| 文档 | 内容 |
| :--- | :--- |
| [01-histogram-transform.md](03-histogram/01-histogram-transform.md) | **算法篇**:直方图是什么、均衡化的 CDF 原理与手算实例、为什么柱子不会真的变平、CLAHE、规定化。**深入部分**(七节):直方图/PDF/CDF 三者关系、概率积分变换证明、空间信息丢失实证、gamma 域 vs 线性域、**CLAHE 从零拆解**(全局→AHE→插值→限幅,四种做法并排图;**块间双线性插值写到代码级**:LUT 属于块中心、边界 clamp、台阶 vs 折线、与 `cv2.createCLAHE` 逐像素对齐、OpenCV 的补边怪癖)、规定化手算、分通道均衡的色相偏移实测 |
| [02-histogram-reading.md](03-histogram/02-histogram-reading.md) | **摄影篇**:如何用眼睛读直方图。四种直方图辨析(RGB叠加 vs 明度)、分量图/Waveform、曝光诊断、宽容度与包围曝光、向右曝光 ETTR、影调三维分类(低中高/长中短/软硬)。整理自三篇知乎文章并修正 8 处 |
| [03-contrast.md](03-histogram/03-contrast.md) | **对比度**:和亮度的区别(加法改亮度/乘法改对比度)、直方图宽度、为什么不能用 max−min 统计、标准差与百分位跨度、自动色阶为何扔掉 1%、显示器上三个不同的「对比度」 |
| [04-further-topics.md](03-histogram/04-further-topics.md) | **备忘清单**:直方图还能做什么,只求「知道有这么回事」。规定化、局部统计增强、Otsu、**直方图当特征**(对比四法 / 反向投影 / EMD)、**视频逐帧独立会闪烁**、10bit 与浮点 HDR 下 LUT 走不通、ffmpeg 滤镜对照表 |

## 04-geometry —— 几何变换

| 文档 | 内容 |
| :--- | :--- |
| [01-图像仿射变换原理解析.md](04-geometry/01-图像仿射变换原理解析.md) | **原理篇**:仿射变换的数学基础、基础变换矩阵、复合变换的相乘顺序、重采样、自适应画布、坑点清单与完整参考实现。配套代码 `ImageAlgorithm/Algorithm/IAAffineTransform.m` |
| [02-MacOS-图像仿射变换与采样模块分析.md](04-geometry/02-MacOS-图像仿射变换与采样模块分析.md) | **素材**:围绕 `IAAffineTransform.m` 的逐点答疑原始记录(Gemini 对话),已被上一篇系统整理过 |

## 05-spatial-filtering —— 空间滤波

| 文档 | 内容 |
| :--- | :--- |
| [01-spatial-filtering-basics.md](05-spatial-filtering/01-spatial-filtering-basics.md) | **原理篇(3.4)**:第一个塌缩不成 LUT 的操作。核/模板术语与为什么用奇数边长、**相关 vs 卷积**(用冲激响应分辨,`cv2.filter2D` 做的是相关;对称核无差别,Sobel 一翻就变号;只有卷积有交换律)、**五种补边**实测对照与各自后果(默认 `REFLECT_101` 为什么)、**核的和**决定它是平滑/求导/锐化、线性 vs 非线性的判据、**可分离核**(秩=1,15×15 实测快 **25 倍**;⚠️ `filter2D` 在 k≥9 时改用 DFT,耗时曲线根本不是 k²)、`ddepth` 与溢出(Sobel 在 uint8 下 **45.3% 的像素被截成 0**)、常见坑清单 |
| [02-smoothing.md](05-spatial-filtering/02-smoothing.md) | **平滑篇(3.5)**:模糊 = 每个像素跟邻居商量,四种做法只差在「怎么商量」。盒式把一个点摊成**方块**、高斯摊成**圆**;⚠️ **两次模糊按勾股定理叠加**(σ=3 再 σ=4 等于 σ=5,不是 7);盒式连做 2 次就很像高斯了(中心极限定理);核要取 `6σ+1`(σ=3 配 3×3 会切掉 61.5%);**椒盐用中值**(比高斯高 6 dB,极端值被排序踢出局)、**高斯噪声用高斯/双边**;窗口不是越大越好;代价表 |
| [03-sharpening.md](05-spatial-filtering/03-sharpening.md) | **锐化篇(3.6)**:锐化 = 跟邻居对着干。一阶答「变化多快」、二阶答「变化在哪儿拐弯」;经典锐化核 = **单位核 − 拉普拉斯**(含符号自检);USM 三步与 Photoshop 三个参数的对应;⚠️ **小半径 USM 和拉普拉斯锐化几乎是同一件事**(相关 0.9918);两个代价:**过冲**([50,200] 冲到 [−100,350])和**噪声放大**(拉普拉斯 5.4×、USM 1.86×,所以先降噪再锐化);梯度可省开方(相关 0.9921,45° 最多高估 41%);**Prewitt/Sobel/Scharr 只差在平滑那一列**,方向误差 0.549°/0.275°/0.068° |

## 数学"回血"资源

- 3Blue1Brown《线性代数的本质》—— 矩阵运算直觉
- 3Blue1Brown《傅里叶变换的本质》—— 阶段三开始前观看
- 心法:把书中的公式当作"伪代码",双重求和 = 两层 for 循环或矩阵点乘;按需查找,即用即补
