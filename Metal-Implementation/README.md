# Metal-Implementation

用 Swift + Metal 将 Python 验证过的算法改写为实时 Shader 渲染,发挥 iOS/macOS 开发优势。

**原则**:Python 是主线,Metal 只挑有实时渲染价值的算法落地,避免"每个算法都 Metal 化"的完美主义。

## 目录

- `DIPMetalEngine/`:Swift 封装的 macOS/iOS Demo App(图像算法实验场)
- `Shaders/`:`.metal` 文件

## 实践任务(按阶段)

- [ ] 阶段 0:最小渲染 App(加载图片/摄像头帧 → MTKView 显示)
- [ ] 阶段 1:sampler linear filtering 缩放,对比手写双线性
- [ ] 阶段 2:通用 3×3 卷积 compute shader
- [ ] 阶段 2:可分离高斯模糊(水平+垂直两 pass),与 `MPSImageGaussianBlur` 对照
- [ ] 阶段 2:Sobel 边缘检测实时滤镜
- [ ] 阶段 3:3D LUT 调色 shader(3D 纹理硬件插值)
- [ ] 阶段 3:饱和度/色温/对比度实时调节
- [ ] 中期项目(第 10 周):实时调色滤镜 App(YUV→RGB + LUT + 实时直方图)
- [ ] 毕业项目(第 18 周):实时绿幕抠图,目标 1080p 60fps

## 避坑

- `_srgb` 纹理采样返回**线性值**;在 gamma 空间做模糊结果会偏暗,滤波前想清楚在哪个空间
- YUV video range(Y: 16~235)与 full range 转换矩阵不同;BT.601/709 系数别混用
- 用 MPS 的现成滤镜(GaussianBlur / Histogram / Sobel)作为自写 shader 的正确性与性能对照基准
