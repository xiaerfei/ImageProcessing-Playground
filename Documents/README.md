# Documents

读书笔记、公式推导图解。

建议按章节组织,例如 `Ch03-notes.md`、`Ch04-fourier-intuition.md`。

## 现有笔记

| 文档 | 内容 |
| :--- | :--- |
| [book-outline.md](book-outline.md) | 全书 12 章知识点地图 + 每章在路线中的定位 |
| [week01-image-memory-layout.md](week01-image-memory-layout.md) | 图像内存布局、BGR/RGB、YUV 三种排布、cv2 的 I420 标准实测 |
| [intensity-and-grayscale.md](intensity-and-grayscale.md) | **原理篇**:线性/对数/幂律为什么这么设计、彼此区别与坑;RGB→灰度加权、各图像类型取亮度、六种亮度定义辨析 |
| [gray-transform-tutorial.md](gray-transform-tutorial.md) | **图解篇**:七种灰度变换方法的效果图与 OpenCV 代码(反转/对数/幂律/对比度拉伸/灰度级分层/比特平面/阈值化)。改写自知乎文章并修正了几处错误 |
| [histogram-transform.md](histogram-transform.md) | **算法篇**:直方图是什么、均衡化的 CDF 原理与手算实例、为什么柱子不会真的变平、CLAHE、规定化。**深入部分**:概率积分变换证明、空间信息丢失实证、gamma 域 vs 线性域、clip 削顶数字、分通道均衡的色相偏移实测 |
| [histogram-reading.md](histogram-reading.md) | **摄影篇**:如何用眼睛读直方图。四种直方图辨析(RGB叠加 vs 明度)、分量图/Waveform、曝光诊断、宽容度与包围曝光、向右曝光 ETTR、影调三维分类(低中高/长中短/软硬)。整理自三篇知乎文章并修正 8 处 |

## 数学"回血"资源

- 3Blue1Brown《线性代数的本质》—— 矩阵运算直觉
- 3Blue1Brown《傅里叶变换的本质》—— 阶段三开始前观看
- 心法:把书中的公式当作"伪代码",双重求和 = 两层 for 循环或矩阵点乘;按需查找,即用即补
