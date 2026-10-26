# 《The Scientist and Engineer's Guide to Digital Signal Processing》目录中译

> 原书：上一级目录 `Documents/数学基础/` 下的 `The Scientist and Engineer Guide to Digital Signal Processing.pdf`，对应 PDF 第 2～8 页（罗马页码 v～xi）。
> 页码保留原书页码。专业名词第一次出现时在括号里附上英文。

---

## 目录概览（Contents at a Glance）

**基础（FOUNDATIONS）**
- 第 1 章　数字信号处理(DSP)的广度与深度 …… 1
- 第 2 章　统计、概率与噪声 …… 11
- 第 3 章　模数转换与数模转换(ADC and DAC) …… 35
- 第 4 章　DSP 软件 …… 67

**核心原理（FUNDAMENTALS）**
- 第 5 章　线性系统(Linear Systems) …… 87
- 第 6 章　卷积(Convolution) …… 107
- 第 7 章　卷积的性质 …… 123
- 第 8 章　离散傅里叶变换(DFT) …… 141
- 第 9 章　DFT 的应用 …… 169
- 第 10 章　傅里叶变换的性质 …… 185
- 第 11 章　傅里叶变换对(Fourier Transform Pairs) …… 209
- 第 12 章　快速傅里叶变换(FFT) …… 225
- 第 13 章　连续信号处理 …… 243

**数字滤波器（DIGITAL FILTERS）**
- 第 14 章　数字滤波器入门 …… 261
- 第 15 章　移动平均滤波器(Moving Average Filters) …… 277
- 第 16 章　加窗 sinc 滤波器(Windowed-Sinc Filters) …… 285
- 第 17 章　自定义滤波器 …… 297
- 第 18 章　FFT 卷积 …… 311
- 第 19 章　递归滤波器(Recursive Filters) …… 319
- 第 20 章　切比雪夫滤波器(Chebyshev Filters) …… 333
- 第 21 章　滤波器对比 …… 343

**应用（APPLICATIONS）**
- 第 22 章　音频处理 …… 351
- 第 23 章　图像的形成与显示 …… 373
- 第 24 章　线性图像处理 …… 397
- 第 25 章　特殊成像技术 …… 423
- 第 26 章　神经网络（及其他！） …… 451
- 第 27 章　数据压缩 …… 481
- 第 28 章　数字信号处理器(Digital Signal Processors) …… 503
- 第 29 章　DSP 上手实践 …… 535

**复数技术（COMPLEX TECHNIQUES）**
- 第 30 章　复数(Complex Numbers) …… 551
- 第 31 章　复数傅里叶变换 …… 567
- 第 32 章　拉普拉斯变换(Laplace Transform) …… 581
- 第 33 章　z 变换(z-Transform) …… 605

- 术语表(Glossary) …… 631
- 索引(Index) …… 643

---

## 详细目录（Table of Contents）

### 基础

**第 1 章　DSP 的广度与深度 …… 1**
- DSP 的起源 1
- 电信 4
- 音频处理 5
- 回声定位(Echo Location) 7
- 图像处理 9

**第 2 章　统计、概率与噪声 …… 11**
- 信号与图表的术语 11
- 均值(Mean)与标准差(Standard Deviation) 13
- 信号与其背后的过程(Underlying Process) 17
- 直方图(Histogram)、概率质量函数(pmf)与概率密度函数(pdf) 19
- 正态分布(Normal Distribution) 26
- 用数字方式生成噪声 29
- 精密度(Precision)与准确度(Accuracy) 32

**第 3 章　ADC 与 DAC …… 35**
- 量化(Quantization) 35
- 采样定理(Sampling Theorem) 39
- 数模转换 44
- 用于数据转换的模拟滤波器 48
- 如何选择抗混叠滤波器(Antialias Filter) 55
- 多速率(Multirate)数据转换 58
- 单比特(Single Bit)数据转换 60

**第 4 章　DSP 软件 …… 67**
- 计算机里的数 67
- 定点数（整数）(Fixed Point) 68
- 浮点数（实数）(Floating Point) 70
- 数值精度 72
- 运行速度：编程语言 76
- 运行速度：硬件 80
- 运行速度：编程技巧 84

### 核心原理

**第 5 章　线性系统 …… 87**
- 信号与系统 87
- 线性的条件 89
- 静态线性(Static Linearity)与正弦保真性(Sinusoidal Fidelity) 92
- 线性与非线性系统的例子 94
- 线性的特殊性质 96
- 叠加(Superposition)：DSP 的基石 98
- 常见的分解方式(Decompositions) 100
- 线性之外的替代方案 104

**第 6 章　卷积 …… 107**
- 冲激函数(Delta Function)与冲激响应(Impulse Response) 107
- 卷积 108
- 输入端算法(Input Side Algorithm) 112
- 输出端算法(Output Side Algorithm) 116
- 输入的加权求和 122

**第 7 章　卷积的性质 …… 123**
- 常见的冲激响应 123
- 数学性质 132
- 相关(Correlation) 136
- 速度 140

**第 8 章　离散傅里叶变换 …… 141**
- 傅里叶变换家族 141
- 实数 DFT 的记号与格式 146
- 频域的自变量 148
- DFT 的基函数(Basis Functions) 150
- 合成(Synthesis)：计算逆 DFT 152
- 分析(Analysis)：计算 DFT 156
- 对偶性(Duality) 161
- 极坐标表示(Polar Notation) 161
- 极坐标表示的麻烦之处 164

**第 9 章　DFT 的应用 …… 169**
- 信号的频谱分析(Spectral Analysis) 169
- 系统的频率响应(Frequency Response) 177
- 借助频域做卷积 180

**第 10 章　傅里叶变换的性质 …… 185**
- 傅里叶变换的线性 185
- 相位的特性 188
- DFT 的周期性 194
- 压缩与拉伸、多速率方法 200
- 信号相乘（幅度调制(Amplitude Modulation)） 204
- 离散时间傅里叶变换(DTFT) 206
- 帕塞瓦尔定理(Parseval's Relation) 208

**第 11 章　傅里叶变换对 …… 209**
- 冲激函数的变换对 209
- sinc 函数 212
- 其他变换对 215
- 吉布斯效应(Gibbs Effect) 218
- 谐波(Harmonics) 220
- 啁啾信号(Chirp Signals) 222

**第 12 章　快速傅里叶变换 …… 225**
- 用复数 DFT 计算实数 DFT 225
- FFT 的工作原理 228
- FFT 程序 233
- 速度与精度对比 237
- 进一步提速 238

**第 13 章　连续信号处理 …… 243**
- 冲激函数 243
- 卷积 246
- 傅里叶变换 252
- 傅里叶级数(Fourier Series) 255

### 数字滤波器

**第 14 章　数字滤波器入门 …… 261**
- 滤波器基础 261
- 信号中的信息是如何表示的 265
- 时域参数 266
- 频域参数 268
- 高通(High-Pass)、带通(Band-Pass)与带阻(Band-Reject)滤波器 271
- 滤波器的分类 274

**第 15 章　移动平均滤波器 …… 277**
- 用卷积实现 277
- 降噪与阶跃响应(Step Response)的取舍 278
- 频率响应 280
- 移动平均滤波器的亲戚们 280
- 递归实现 282

**第 16 章　加窗 sinc 滤波器 …… 285**
- 加窗 sinc 的思路 285
- 设计滤波器 288
- 加窗 sinc 滤波器示例 292
- 推到极限 293

**第 17 章　自定义滤波器 …… 297**
- 任意频率响应 297
- 反卷积(Deconvolution) 300
- 最优滤波器(Optimal Filters) 307

**第 18 章　FFT 卷积 …… 311**
- 重叠相加法(Overlap-Add Method) 311
- FFT 卷积 312
- 速度改进 316

**第 19 章　递归滤波器 …… 319**
- 递归方法 319
- 单极点(Single Pole)递归滤波器 322
- 窄带滤波器 326
- 相位响应(Phase Response) 328
- 用整数实现 332

**第 20 章　切比雪夫滤波器 …… 333**
- 切比雪夫响应与巴特沃斯(Butterworth)响应 333
- 设计滤波器 334
- 阶跃响应的过冲(Overshoot) 338
- 稳定性 339

**第 21 章　滤波器对比 …… 343**
- 第 1 场：模拟滤波器 vs. 数字滤波器 343
- 第 2 场：加窗 sinc vs. 切比雪夫 346
- 第 3 场：移动平均 vs. 单极点 348

### 应用

**第 22 章　音频处理 …… 351**
- 人的听觉 351
- 音色(Timbre) 355
- 音质与数据率的取舍 358
- 高保真(High Fidelity)音频 359
- 压扩(Companding) 362
- 语音合成与识别 364
- 非线性音频处理 368

**第 23 章　图像的形成与显示 …… 373**
- 数字图像的结构 373
- 相机与眼睛 376
- 电视视频信号 384
- 其他图像采集与显示方式 386
- 亮度与对比度调整 387
- 灰度变换(Grayscale Transforms) 390
- 图像变形(Warping) 394

**第 24 章　线性图像处理 …… 397**
- 卷积 397
- 3×3 边缘修饰 402
- 利用可分离性(Separability)做卷积 404
- 大尺寸点扩散函数(PSF)的例子：光照平场化(Illumination Flattening) 407
- 傅里叶图像分析 410
- FFT 卷积 416
- 细看图像卷积 418

**第 25 章　特殊成像技术 …… 423**
- 空间分辨率(Spatial Resolution) 423
- 采样间距与采样孔径(Sampling Aperture) 430
- 信噪比(SNR) 432
- 形态学图像处理(Morphological Image Processing) 436
- 计算机断层成像(Computed Tomography, CT) 442

**第 26 章　神经网络（及其他！） …… 451**
- 目标检测 451
- 神经网络的结构 458
- 它为什么有效？ 463
- 训练神经网络 465
- 评估结果 473
- 递归滤波器设计 476

**第 27 章　数据压缩 …… 481**
- 数据压缩的策略 481
- 游程编码(Run-Length Encoding) 483
- 霍夫曼编码(Huffman Encoding) 484
- 差分编码(Delta Encoding) 486
- LZW 压缩 488
- JPEG（变换压缩(Transform Compression)） 494
- MPEG 501

**第 28 章　数字信号处理器 …… 503**
- DSP 芯片有何不同 503
- 环形缓冲(Circular Buffering) 506
- 数字信号处理器的架构 509
- 定点 vs. 浮点 514
- C 语言 vs. 汇编 520
- DSP 芯片有多快？ 526
- 数字信号处理器市场 531

**第 29 章　DSP 上手实践 …… 535**
- ADSP-2106x 系列 535
- SHARC EZ-KIT Lite 开发板 537
- 设计示例：一个 FIR 音频滤波器 538
- DSP 系统上的模拟测量 542
- 再谈定点 vs. 浮点 544
- 高级软件工具 546

### 复数技术

**第 30 章　复数 …… 551**
- 复数系统 551
- 极坐标表示 555
- 用代换法使用复数 557
- 正弦波的复数表示 559
- 系统的复数表示 561
- 电路分析 563

**第 31 章　复数傅里叶变换 …… 567**
- 实数 DFT 567
- 数学上的等价性 569
- 复数 DFT 570
- 傅里叶变换家族 575
- 为什么要用复数傅里叶变换 577

**第 32 章　拉普拉斯变换 …… 581**
- s 域(s-Domain)的本质 581
- 拉普拉斯变换的思路 588
- 电路分析 592
- 极点(Poles)与零点(Zeros)的重要性 597
- 在 s 域中设计滤波器 600

**第 33 章　z 变换 …… 605**
- z 域的本质 605
- 递归系统的分析 610
- 级联(Cascade)与并联(Parallel)结构 616
- 频谱反转(Spectral Inversion) 619
- 增益调整 621
- 切比雪夫-巴特沃斯滤波器设计 623
- DSP 的最好与最坏之处 630

**术语表 …… 631**
**索引 …… 643**
