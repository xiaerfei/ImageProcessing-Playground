"""第 1 周热身:读图、看内存布局、通道操作。

验证三件事:
1. 图像在 numpy 里就是 (H, W, C) 的 uint8 数组,行优先存储
2. cv2.imread 返回的是 BGR 而不是 RGB(直接给 matplotlib 显示颜色会反)
3. 点操作 = 直接改数组(把某个通道置零)

用法:
    .venv/bin/python Ch01_02_Fundamentals/00_hello_image.py [--show]
    结果图保存到 Assets/results/week01_hello_image.png
"""

import sys
from pathlib import Path

import cv2
import matplotlib

if "--show" not in sys.argv:
    matplotlib.use("Agg")  # 无窗口环境只保存文件
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[2]
matplotlib.rcParams["font.family"] = ["Heiti TC", "Arial Unicode MS", "sans-serif"]


def main() -> None:
    path = REPO / "Assets" / "test-images" / "astronaut.png"
    bgr = cv2.imread(str(path))  # 注意:OpenCV 读进来是 BGR!
    assert bgr is not None, f"读图失败: {path}"

    # --- 1. 内存布局 ---
    print(f"shape = {bgr.shape}  (H, W, C) 行优先")
    print(f"dtype = {bgr.dtype}, 每像素 {bgr.itemsize * bgr.shape[2]} 字节")
    print(f"strides = {bgr.strides}  (跨一行/一列/一通道各要跳多少字节)")
    print(f"像素 [0,0] 的 BGR 值 = {bgr[0, 0]}")

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    # --- 2. 通道分离与置零 ---
    b, g, r = cv2.split(bgr)
    no_red = rgb.copy()
    no_red[:, :, 0] = 0  # RGB 图里把 R 通道置零

    # --- 3. 出对比图板 ---
    fig, axes = plt.subplots(2, 3, figsize=(12, 8))
    panels = [
        (bgr, "BGR 数据直接当 RGB 显示(颜色反了)"),
        (rgb, "转成 RGB 后显示(正确)"),
        (no_red, "R 通道置零"),
        (r, "R 通道(灰度显示)"),
        (g, "G 通道(灰度显示)"),
        (b, "B 通道(灰度显示)"),
    ]
    for ax, (img, title) in zip(axes.flat, panels):
        ax.imshow(img, cmap="gray" if img.ndim == 2 else None)
        ax.set_title(title, fontsize=11)
        ax.axis("off")
    fig.tight_layout()

    out = REPO / "Assets" / "results" / "week01_hello_image.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=110)
    print(f"\n结果已保存: {out.relative_to(REPO)}")
    if "--show" in sys.argv:
        plt.show()


if __name__ == "__main__":
    main()
