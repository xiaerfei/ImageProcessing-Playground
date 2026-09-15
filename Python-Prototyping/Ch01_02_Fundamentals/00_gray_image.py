"""第 1 周热身:从 RGB 算亮度(Luma Y′),看它长什么样。

验证三件事:
1. 灰度化不是「求平均」,而是按人眼敏感度加权:Y = 0.299R + 0.587G + 0.114B
2. cv2.cvtColor(BGR2GRAY) 用的就是这套 Rec.601 权重、全范围 0~255
3. Y 是 2 维数组,它本身就是一张完整的灰度图(YUV 里那个 Y 就是它,不用算)

用法:
    .venv/bin/python Ch01_02_Fundamentals/00_gray_image.py [--show]
    结果图保存到 Assets/results/week01_gray_image.png
"""

import sys
from pathlib import Path

import cv2
import matplotlib

if "--show" not in sys.argv:
    matplotlib.use("Agg")  # 无窗口环境只保存文件
import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt

REPO = Path(__file__).resolve().parents[2]
matplotlib.rcParams["font.family"] = ["Heiti TC", "Arial Unicode MS", "sans-serif"]


def to_luma(bgr: cv2.typing.MatLike) -> npt.NDArray[np.uint8]:
    """手写 Rec.601 亮度:Y = 0.299R + 0.587G + 0.114B。

    入参用 MatLike(OpenCV 图像的统一类型,cv2.imread 的返回就是它);
    返回值精确标成 uint8 灰度图,方便调用方继续参与 numpy 运算。

    两个坑:OpenCV 读进来是 BGR(拆通道别拿反);
    先 astype(np.float64) 再乘,否则 uint8 直接算会回绕。
    """
    b = bgr[:, :, 0].astype(np.float64)
    g = bgr[:, :, 1].astype(np.float64)
    r = bgr[:, :, 2].astype(np.float64)
    return np.clip(0.299 * r + 0.587 * g + 0.114 * b, 0, 255).astype(np.uint8)


def main() -> None:
    path = REPO / "Assets" / "test-images" / "lenna_s.jpg"
    bgr = cv2.imread(str(path))
    assert bgr is not None, f"读图失败: {path}"

    # --- 1. 同一个 Y,两种算法的对照 ---
    y_cv = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)   # OpenCV:Rec.601 + 全范围
    y_hand = to_luma(bgr)                          # 手写:同一个公式

    diff = np.abs(y_hand.astype(np.int16) - y_cv.astype(np.int16))
    print(f"原图   shape={bgr.shape}  dtype={bgr.dtype}   每像素 3 个数 (B, G, R)")
    print(f"亮度图 shape={y_cv.shape}  dtype={y_cv.dtype}   每像素 1 个数")
    print(f"\n手写 vs cv2.BGR2GRAY:最大差 {diff.max()}  (只差四舍五入 → 同一个 Y)")
    print(f"亮度图统计:均值 {y_cv.mean():.1f}  范围 [{y_cv.min()}, {y_cv.max()}]")

    # --- 2. 出对比图板 ---
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    panels = [
        (cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), "原图 (BGR → RGB)"),
        (y_cv, "亮度 Y′ = 0.299R + 0.587G + 0.114B"),
    ]
    for ax, (img, title) in zip(axes, panels):
        if img.ndim == 2:
            ax.imshow(img, cmap="gray", vmin=0, vmax=255)   # 灰度图必须给 vmin/vmax
        else:
            ax.imshow(img)
        ax.set_title(title, fontsize=11)
        ax.axis("off")
    fig.tight_layout()

    out = REPO / "Assets" / "results" / "week01_gray_image.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=110)
    print(f"\n结果已保存: {out.relative_to(REPO)}")
    if "--show" in sys.argv:
        plt.show()


if __name__ == "__main__":
    main()
