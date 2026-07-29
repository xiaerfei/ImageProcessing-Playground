# Python-Prototyping

用 Python + OpenCV 快速验证《数字图像处理》中的算法概念。重点算法用 numpy 手写实现,再与 OpenCV 现成函数对比验证。

## 环境搭建

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 目录(按学习顺序排列)

| 目录 | 阶段 | 对应章节 |
| :--- | :--- | :--- |
| `Ch01_02_Fundamentals/` | 1 | 第 1、2 章:图像基础、插值与几何变换 |
| `Ch03_Spatial_Filtering/` | 2 | 第 3 章:灰度变换与空间滤波 |
| `Ch06_Color_Processing/` | 3 | 第 6 章:彩色图像处理 |
| `Ch04_Frequency_Domain/` | 4 | 第 4 章:频率域滤波 |
| `Ch09_Morphology/` | 5 | 第 9 章:形态学图像处理 |
| `Ch10_Segmentation/` | 5 | 第 10 章:图像分割 |
| `Ch05_Restoration_Denoising/` | 选修 A | 第 5 章:图像复原与去噪 |
| `Ch08_Compression/` | 选修 B | 第 8 章:图像压缩 |

## 通用约定

- 所有像素运算先 `astype(np.float64)`,输出前 `np.clip(x, 0, 255).astype(np.uint8)`
- 与 OpenCV 对比时统一 borderType,否则边缘会有差异
- 测试图统一放 `../Assets/test-images/`,输出效果图存 `../Assets/results/`
