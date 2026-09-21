"""梯度方向到底指向哪 —— 配合 03-sharpening.md 第七节与 04-edge-detection.md 第 2 步。

为什么单独做一份:
    「梯度方向垂直于边的走向」是理解非极大值抑制(NMS)的钥匙 ——
    NMS 沿梯度方向前后比较,正是因为那个方向恰好是边的**横截面**。
    这条结论两篇文档里都只有一句话,没有图也没有实测,等于要人凭空想象。

本脚本做两件事:
  1. 造一批**走向已知**的边,量出梯度方向,验证夹角恒为 90°
  2. 把「灰度当海拔」这个比方画出来,并演示不筛幅值时方向全是噪声

生成 1 张(写到 Assets/results/):
    gradient-direction.png

用法:
    .venv/bin/python Ch03_Spatial_Filtering/25_gradient_direction.py [--show]
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import IMAGES, four_questions, save, use_cjk_font  # noqa: E402

use_cjk_font()
import cv2  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402


def sobel_grad(img):
    """返回 (gx, gy, 幅值, 方向角度)。方向用 atan2(gy, gx),单位是度。"""
    gx = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=3)
    return gx, gy, np.hypot(gx, gy), np.rad2deg(np.arctan2(gy, gx))


def edge_at(angle_deg, size=201, softness=1.5):
    """造一条沿 angle_deg 方向延伸的明暗分界线(软边,避免锯齿污染梯度)。"""
    yy, xx = np.mgrid[0:size, 0:size].astype(float)
    c = (size - 1) / 2
    t = np.deg2rad(angle_deg)
    d = -(xx - c) * np.sin(t) + (yy - c) * np.cos(t)      # 到那条直线的带符号距离
    return np.clip(128 + 60 * np.tanh(d / softness), 0, 255)


def mean_direction(ang_deg, mask):
    """方向的平均不能直接算术平均(±180 处会绕回),要先化成单位向量再平均。"""
    a = np.deg2rad(ang_deg[mask])
    return np.rad2deg(np.arctan2(np.sin(a).mean(), np.cos(a).mean()))


def measure(angles=(0, 30, 45, 90, 135)):
    rows = []
    for a in angles:
        img = edge_at(a)
        _, _, mag, ang = sobel_grad(img)
        m = mag > mag.max() * 0.5          # 只看边上那一圈强梯度点
        g = mean_direction(ang, m)
        gap = abs((g - a + 90) % 180 - 90)  # 折算到 0~90
        rows.append((a, g, gap))
    return rows


def main() -> None:
    rows = measure()

    fig = plt.figure(figsize=(13.4, 4.6))
    gs = fig.add_gridspec(1, 4, width_ratios=[1, 1, 1.05, 1.1], wspace=0.28)

    # ── (a) 灰度当海拔:一个小山包 + 梯度箭头
    ax = fig.add_subplot(gs[0])
    n = 61
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    hill = 255 * np.exp(-((xx - 30) ** 2 + (yy - 30) ** 2) / (2 * 14.0 ** 2))
    gx, gy, mag, _ = sobel_grad(hill)
    ax.imshow(hill, cmap="gray", vmin=0, vmax=255)
    s = 7
    sub = (slice(None, None, s), slice(None, None, s))
    # 只画山腰:山顶和山脚的梯度都接近 0,画出来是一堆看不清的小点
    strong = mag[sub] > mag.max() * 0.25
    ax.quiver(xx[sub][strong], yy[sub][strong], gx[sub][strong], gy[sub][strong],
              color="#d95f02", scale=2200, width=0.010)
    ax.set_title("把亮度当海拔\n箭头 = 上坡最陡的方向", fontsize=10.5)
    ax.axis("off")
    ax.text(30, 30, "山顶", color="#2c6fbb", fontsize=9, ha="center", va="center")

    # ── (b) 一条 30° 的边:梯度垂直于它
    ax = fig.add_subplot(gs[1])
    a0 = 30
    img = edge_at(a0, size=121)
    gx, gy, mag, ang = sobel_grad(img)
    ax.imshow(img, cmap="gray", vmin=0, vmax=255)
    c = 60
    th = np.deg2rad(a0)
    # 沿这条边均匀取 7 个点,而不是按光栅顺序取 —— 否则箭头全挤在左上角
    ts = np.linspace(-45, 45, 7)
    px = np.clip(c + ts * np.cos(th), 1, img.shape[1] - 2).astype(int)
    py = np.clip(c + ts * np.sin(th), 1, img.shape[0] - 2).astype(int)
    ax.quiver(px, py, gx[py, px], gy[py, px],
              color="#d95f02", scale=1800, width=0.012)
    t = th
    ax.plot([c - 55 * np.cos(t), c + 55 * np.cos(t)],
            [c - 55 * np.sin(t), c + 55 * np.sin(t)],
            color="#2c6fbb", lw=2, ls="--")
    ax.set_title(f"边沿 {a0}° 延伸(蓝虚线)\n梯度(橙箭头)横着扎出去", fontsize=10.5)
    ax.axis("off")

    # ── (c) 五个角度的验证
    ax = fig.add_subplot(gs[2])
    xs_ = np.arange(len(rows))
    ax.bar(xs_, [r[2] for r in rows], 0.5, color="#2a8f4a")
    ax.axhline(90, color="#c4442a", ls="--", lw=1.4)
    ax.text(-0.45, 92.5, "90°", color="#c4442a", fontsize=9, ha="left")
    for i, (a, g, gap) in enumerate(rows):
        ax.text(i, gap + 2.5, f"{gap:.1f}°", ha="center", fontsize=8.8, color="#2a8f4a")
    ax.set_xticks(xs_)
    ax.set_xticklabels([f"{r[0]}°" for r in rows])
    ax.set_ylim(0, 105)
    ax.set_xlabel("边的走向")
    ax.set_ylabel("边与梯度方向的夹角")
    ax.set_title("换五个角度试\n夹角恒为 90°,没有例外", fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)

    # ── (d) 真实照片:不筛幅值的话,方向全是噪声
    real = cv2.imread(str(IMAGES / "camera.png"), cv2.IMREAD_GRAYSCALE).astype(float)
    gx, gy, mag, ang = sobel_grad(real)
    flat = (mag < 10).mean()
    # 用色相编码方向,亮度编码「是否够强」
    hue = ((ang % 180) / 180 * 179).astype(np.uint8)
    sat = np.full_like(hue, 255)
    raw = cv2.cvtColor(np.dstack([hue, sat, np.full_like(hue, 255)]), cv2.COLOR_HSV2RGB)
    val = np.clip(mag / np.percentile(mag, 99) * 255, 0, 255).astype(np.uint8)
    gated = cv2.cvtColor(np.dstack([hue, sat, val]), cv2.COLOR_HSV2RGB)

    ax = fig.add_subplot(gs[3])
    ax.imshow(np.hstack([raw, np.full((raw.shape[0], 8, 3), 255, np.uint8), gated]))
    ax.set_title(f"颜色 = 梯度方向\n左:不筛幅值({flat:.0%} 是平坦区,纯噪声)  右:按幅值加权",
                 fontsize=9.6)
    ax.axis("off")

    fig.suptitle("梯度方向:上坡最陡的那一边 —— 而它永远垂直于边的走向", fontsize=13, y=1.03)
    four_questions(fig,
        "每个像素只测两个数:\ngx(横向变化率)、\ngy(纵向变化率),\n"
        "再合成一个箭头:\n幅值 √(gx²+gy²)、\n方向 atan2(gy, gx)。",
        "一个箭头同时回答了\n「变化多剧烈」和\n「朝哪儿变最快」。\n"
        "而且方向垂直于边 ——\n于是有了边的**横截面**,\nNMS 才知道该沿哪个方向削。",
        f"平坦区的方向没有意义。\n实测 camera.png 有 {flat:.0%} 的\n像素幅值 < 10,那里 gx、gy\n"
        "都接近 0,角度完全由噪声决定\n(左图那片彩色雪花)。",
        "方向有 180° 的二义性:\n从暗到亮和从亮到暗\n差整整半圈。做边缘检测时\n"
        "通常只关心「轴向」,\n要先折算到 0~180°。\n另外图像 y 轴向下,\n视觉上的旋向是反的。",
        "先用幅值筛一遍再谈方向;\n要更准的方向用 Scharr\n(方向误差 0.068° vs Sobel 0.275°);\n"
        "要亚像素精度的朝向,\n查结构张量(structure tensor)\n或 HOG 那套方向直方图。",
        y=-0.03, bottom=0.14)
    save(fig, "gradient-direction.png")

    print("  边走向 → 梯度方向 → 夹角")
    for a, g, gap in rows:
        print(f"    {a:>5}°  →  {g:>7.1f}°  →  {gap:>5.1f}°")
    print(f"  camera.png 平坦区(幅值<10)占比 {flat:.1%}")


if __name__ == "__main__":
    main()
    if "--show" in sys.argv:
        plt.show()
