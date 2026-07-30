# ImageProcessing-Playground

图像处理学习 —— 冈萨雷斯《数字图像处理》(第4版) 自学工程。

**路线**:代码先行、理论跟进、按需补数学。Python/OpenCV 为主线验证概念,Swift/Metal 挑有实时价值的算法落地。

📍 **详细计划见 [ROADMAP.md](ROADMAP.md)**(18 周逐周计划:阅读小节、代码任务、验收问题)。
🗺️ **全书章节知识点地图见 [Documents/book-outline.md](Documents/book-outline.md)**(12 章知识版图 + 每章在路线中的定位)。

## 仓库结构

```text
ImageProcessing-Playground/
├── ROADMAP.md                 # 详细学习路线图
├── Python-Prototyping/        # 主线:Python/OpenCV 手写验证算法
│   ├── Ch01_02_Fundamentals/  # 阶段 1:采样量化、插值、几何变换
│   ├── Ch03_Spatial_Filtering/# 阶段 2:灰度变换、直方图、空间滤波
│   ├── Ch06_Color_Processing/ # 阶段 3:彩色处理 + 视频色彩工程
│   ├── Ch04_Frequency_Domain/ # 阶段 4:频域处理与傅里叶变换
│   ├── Ch09_Morphology/       # 阶段 5:形态学
│   ├── Ch10_Segmentation/     # 阶段 5:图像分割
│   ├── Ch05_Restoration_Denoising/ # 选修 A:噪声模型与去噪
│   └── Ch08_Compression/      # 选修 B:图像压缩(DCT/JPEG/运动补偿)
├── Metal-Implementation/      # iOS/macOS 原生 Metal Shader 实现
│   ├── DIPMetalEngine/        # Swift 封装的 Demo App
│   └── Shaders/               # .metal 文件
├── Documents/                 # 读书笔记、公式推导图解
└── Assets/                    # 测试图片与处理效果对比(GIF/截图)
```

## 学习进度

- [ ] **阶段 0**(第 1 周):环境搭建 + YUV→RGB 热身
- [ ] **阶段 1**(第 2~3 周):第 1、2 章 —— 采样量化、插值、几何变换
- [ ] **阶段 2**(第 4~7 周):第 3 章 —— 灰度变换与空间滤波(全书核心)
- [ ] **阶段 3**(第 8~9 周):第 6 章 —— 彩色图像处理 + 视频色彩补充
- [ ] **缓冲周**(第 10 周):补欠账 + 中期项目「实时调色滤镜 App」
- [ ] **阶段 4**(第 11~14 周):第 4 章 —— 数学回血 + 频域处理
- [ ] **阶段 5**(第 15~17 周):第 9、10 章 —— 形态学与图像分割
- [ ] **毕业项目**(第 18 周):实时绿幕抠图(Python 原型 + Metal 1080p 60fps)

### 选修(主线毕业后)

- [ ] 选修 A:第 5 章 去噪(双边滤波 / 视频降噪延伸)
- [ ] 选修 B:第 8 章 图像压缩 —— 推流开发者价值最高
- [ ] 选修 C:第 12 章 神经网络与深度学习入门

各阶段的细分任务清单在对应章节目录的 README 中打卡。
