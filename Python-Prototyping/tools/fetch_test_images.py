"""生成 Assets/test-images/ 下的标准测试图。

图片来自 scikit-image 内置数据集(公有领域/可自由分发),
避免向公开仓库提交版权不明的教材配图。
每张图的用途对应 ROADMAP 中的具体周任务。

用法:
    .venv/bin/python tools/fetch_test_images.py
"""

from pathlib import Path

import cv2
import numpy as np
from skimage import data

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "Assets" / "test-images"

# (文件名, 图像, 用途说明)
IMAGES = [
    ("camera.png", data.camera(), "512x512 灰度经典图(摄影师),通用"),
    ("astronaut.png", data.astronaut(), "512x512 彩色人像,色彩空间/滤波实验"),
    ("moon.png", data.moon(), "低对比度灰度图,直方图均衡化(第 5 周)"),
    ("coins.png", data.coins(), "硬币,阈值分割/连通分量计数(第 15~16 周)"),
    ("page.png", data.page(), "光照不均文档,自适应阈值(第 16 周)"),
    ("coffee.png", data.coffee(), "彩色静物,插值/几何变换(第 3 周)"),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, img, desc in IMAGES:
        if img.ndim == 3:  # skimage 是 RGB,cv2.imwrite 要 BGR
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(OUT / name), img)
        print(f"{name:16s} {img.shape!s:18s} {desc}")

    # 合成图:水平灰度渐变,量化/伪轮廓实验用(第 2 周)
    ramp = np.tile(np.linspace(0, 255, 512, dtype=np.uint8), (512, 1))
    cv2.imwrite(str(OUT / "gradient.png"), ramp)
    print(f"{'gradient.png':16s} {ramp.shape!s:18s} 合成水平渐变,伪轮廓实验(第 2 周)")


if __name__ == "__main__":
    main()
