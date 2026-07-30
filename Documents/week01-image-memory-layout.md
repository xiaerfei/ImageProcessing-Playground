# 第 1 周笔记:图像的内存布局

> 配套代码:[00_hello_image.py](../Python-Prototyping/Ch01_02_Fundamentals/00_hello_image.py)、
> [00_yuv_warmup.py](../Python-Prototyping/Ch06_Color_Processing/00_yuv_warmup.py)
> 结果图:`Assets/results/week01_*.png`

## 1. RGB 图像:HWC + 行优先

- numpy 里一张彩色图就是 `(H, W, C)` 的 `uint8` 数组,**行优先**存储。
- 实测 512×512×3 图像的 `strides = (1536, 3, 1)`:跨一行跳 1536 字节(512×3)、跨一列跳 3 字节、跨一通道跳 1 字节 —— 即交错(interleaved)排列 `RGBRGBRGB...`。
- **stride ≠ width×bpp 是常态**:GPU/视频框架常把每行对齐到 16/64 字节(`CVPixelBuffer` 的 `bytesPerRow`、Metal 的 `bytesPerRow`)。逐行拷贝时必须用 stride,不能用 width 算偏移——这是 iOS 视频开发的经典越界/花屏来源。

## 2. BGR vs RGB

- `cv2.imread` 返回 **BGR**(历史原因),matplotlib/绝大多数其他库按 RGB 理解。
- 直接把 BGR 数据丢给 matplotlib,红蓝对调(见 `week01_hello_image.png` 第一格)。
- 教训:跨库传图像时,**先确认通道顺序约定**,和跨系统传 YUV 要先确认 range 一个道理。

## 3. YUV 的三种排布

| 类型 | 例子 | 内存排布 |
| :--- | :--- | :--- |
| 打包/交错 (packed) | YUYV | `Y U Y V Y U Y V ...` 单平面 |
| 平面 (planar) | **I420** (YUV420P) | Y 平面(H×W)+ U 平面(H/2×W/2)+ V 平面(H/2×W/2) |
| 半平面 (semi-planar) | **NV12** | Y 平面(H×W)+ UV 交错平面(`UVUVUV...`,H/2×W) |

- 4:2:0 = 每 2×2 像素块共用一对 UV → 数据量为 4:4:4 的一半(1 + 1/4 + 1/4 = 1.5 字节/像素)。
- iOS 摄像头常给 NV12(`kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange`);ffmpeg/编码器世界常用 I420。两者只差 UV 是否交错。

## 4. 实验结论:OpenCV I420 转换用的是什么标准?

用纯色块探测 `cv2.COLOR_RGB2YUV_I420`(见 `00_yuv_warmup.py`):

| 输入 RGB | Y | U | V | 推断 |
| :--- | :-- | :-- | :-- | :--- |
| 白 (255,255,255) | 235 | 128 | 128 | **video range**(白=235 不是 255) |
| 黑 (0,0,0) | 16 | 128 | 128 | 黑=16,同上 |
| 红 (255,0,0) | 82 | 90 | 240 | Y≈16+219×0.299 → **BT.601** |

- 手写 BT.601 video-range 逆变换与 `cv2.COLOR_YUV2RGB_I420` 对比:**平均误差 0.39,最大误差 1** —— 完全吻合(残差纯属取整),验收通过。
- 故意用 BT.709 解码:平均误差 2.33,肤色/橙色可见偏移(见 `week01_yuv_warmup.png`)。
- 通用逆变换公式(Kr/Kb 参数化,记这个就不用背矩阵):
  - `R = Y' + 2(1−Kr)·Cr'`,`B = Y' + 2(1−Kb)·Cb'`,`G = (Y' − Kr·R − Kb·B) / Kg`
  - video range 归一化:`Y' = (Y−16)/219`,`C' = (C−128)/224`
  - BT.601: Kr=0.299, Kb=0.114;BT.709: Kr=0.2126, Kb=0.0722

## 5. Metal 骨架要点

- `Metal-Implementation/DIPMetalEngine/`:SwiftPM 可执行包,`swift run` 直接跑,无需 xcodeproj。
- 全屏 quad 用 `vertex_id` 生成 4 个角(triangle strip),不需要顶点缓冲;aspect-fit 通过缩放 NDC 坐标实现。
- 纹理加载用了 `.SRGB: false`(按原始字节透传)。第 7 周做模糊时要回头处理 sRGB/线性空间问题(避坑清单 #6)。
- 后续每周的滤镜只需换 fragment 或插 compute pass,这个骨架不用动。

## 遗留问题(带着进第 2 周)

- [ ] `MTKTextureLoader` 加载出的 pixelFormat 是哪个?BGRA 还是 RGBA?(实测 rawValue=80,查表确认)
- [ ] iOS 端拿到 `CVPixelBuffer` 的 NV12 两个平面,bytesPerRow 和 width 差多少?(回工作项目里打印一次)
