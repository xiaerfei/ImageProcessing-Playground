"""给 01-fundamentals/01-week01-image-memory-layout.md 补配图。

为什么要补:
    「内存布局」是纯抽象的东西 —— 它没有「效果图」可看,全靠脑补一维字节条带。
    这恰恰是最该画出来的:stride 为什么不等于 width×3、NV12 和 I420 到底差在哪,
    画成条带一眼就清楚,读文字要来回倒三遍。

生成 2 张(全部写到 Assets/results/):
    memory-row-major.png  二维图怎么塞进一维内存,以及 stride ≠ width×bpp
    yuv-layouts.png       packed / planar / semi-planar 三种排布,和 4:2:0 省在哪

用法:
    .venv/bin/python Ch01_02_Fundamentals/06_memory_layout_figures.py [--show]
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import IMAGES, four_questions, save, use_cjk_font  # noqa: E402

use_cjk_font()
import cv2  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, Rectangle  # noqa: E402

CH_COLOR = {"R": "#d9534f", "G": "#5cb85c", "B": "#4a7fd4"}
PAD_COLOR = "#cfcfcf"


def cell(ax, x, y, w, h, color, label="", fs=7.5, tc="white"):
    ax.add_patch(Rectangle((x, y), w, h, fc=color, ec="white", lw=0.8))
    if label:
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
                fontsize=fs, color=tc)


# ═══════════════════════════════════ 图 1:行优先与 stride ═══════════════


def fig_row_major() -> None:
    """一维内存怎么装二维图,以及为什么不能用 width×bpp 去算行偏移。

    真实数字取自 01_hello_image.py 实测的 512×512×3:strides = (1536, 3, 1)。
    右边那条是 GPU/视频框架常见的「每行对齐到 64 字节」,stride 被撑到 1600。
    """
    W, H = 4, 3                       # 画一张 4×3 的迷你图,再展开给你看
    bgr = cv2.imread(str(IMAGES / "astronaut.png"))
    real_strides = np.ascontiguousarray(bgr).strides
    align = 64
    # 故意挑一个**不是**对齐粒度整数倍的宽度。
    # 512×3 = 1536 正好是 64 的整数倍,填充为 0 —— 这恰恰是这个坑难查的原因:
    # 在 512、1024 这类 2 的幂尺寸上根本测不出来,一换成裁剪过的奇怪尺寸就炸。
    demo_w = 500
    tight = demo_w * 3
    padded_stride = (tight + align - 1) // align * align

    fig = plt.figure(figsize=(13.4, 5.2))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.25], width_ratios=[1, 2.1],
                          hspace=0.28, wspace=0.16)

    # ── 左上:二维的样子
    ax = fig.add_subplot(gs[0, 0]); ax.axis("off")
    ax.set_title("你眼里的图:二维网格", fontsize=10.5)
    for r in range(H):
        for c in range(W):
            for k, ch in enumerate("RGB"):
                cell(ax, c * 3 + k, (H - 1 - r) * 1.2, 1, 1, CH_COLOR[ch], ch)
            if c == 0:      # 每行只标一次,标多了反而糊成一片
                ax.text(-0.7, (H - 1 - r) * 1.2 + 0.5, f"第 {r} 行",
                        ha="right", va="center", fontsize=7.5, color="#666")
    ax.set_xlim(-3.2, W * 3 + 0.5); ax.set_ylim(-0.4, H * 1.25 + 0.1)
    ax.set_aspect("equal")

    # ── 右上:展开成一条
    ax = fig.add_subplot(gs[0, 1]); ax.axis("off")
    ax.set_title("内存里的样子:一条一维的字节,行接着行(行优先)", fontsize=10.5)
    i = 0
    for r in range(H):
        for c in range(W):
            for ch in "RGB":
                cell(ax, i, 0, 1, 1, CH_COLOR[ch], ch, fs=6.5)
                i += 1
        ax.plot([i, i], [-0.35, 1.35], color="#333", lw=1.6)
        ax.text(i - W * 1.5, 1.55, f"第 {r} 行", ha="center", fontsize=8.5)
    ax.annotate("", xy=(W * 3, -0.75), xytext=(0, -0.75),
                arrowprops=dict(arrowstyle="<->", color="#c4442a", lw=1.4))
    ax.text(W * 1.5, -1.25, f"跨一整行要跳 {W * 3} 字节 = stride",
            ha="center", fontsize=9, color="#c4442a")
    ax.text(W * 3 + 0.4, -1.25, "→ 下一行从这里开始", fontsize=8.6, color="#666")
    ax.set_xlim(-0.5, W * H * 3 + 0.5); ax.set_ylim(-1.7, 2.0)
    ax.set_aspect("equal")

    # ── 下:紧凑 vs 对齐
    ax = fig.add_subplot(gs[1, :]); ax.axis("off")
    ax.set_title(f"真实世界里,stride 常常比 width×3 更大(这里宽 {demo_w})", fontsize=10.5)
    rows = [("numpy / cv2.imread\n(紧凑,无填充)", tight, 0, "#4a7fd4"),
            (f"GPU / CVPixelBuffer\n(每行对齐到 {align} 字节)", tight,
             padded_stride - tight, "#4a7fd4")]
    scale = 9.5 / padded_stride
    for j, (name, data_bytes, pad_bytes, color) in enumerate(rows):
        y = 1 - j * 1.5
        cell(ax, 0, y, data_bytes * scale, 1.0, color,
             f"{data_bytes} 字节的像素数据", fs=9)
        if pad_bytes:
            cell(ax, data_bytes * scale, y, pad_bytes * scale, 1.0, PAD_COLOR,
                 f"填充 {pad_bytes}", fs=8, tc="#333")
        ax.text(-0.25, y + 0.5, name, ha="right", va="center", fontsize=9)
        ax.text((data_bytes + pad_bytes) * scale + 0.45, y + 0.5,
                f"stride = {data_bytes + pad_bytes}", va="center", fontsize=9,
                color="#c4442a" if pad_bytes else "#333")
    ax.text(4.7, -1.45,
            f"拿 width×3 = {tight} 当行偏移去读第二种,每读一行就少走 "
            f"{padded_stride - tight} 字节,画面逐行斜着错开 —— 经典的「花屏」。\n"
            f"注意 512×3 = 1536 正好是 {align} 的整数倍,填充为 0:"
            f"这个 bug 在 2 的幂尺寸上根本测不出来。",
            ha="center", va="top", fontsize=8.8, color="#c4442a")
    ax.set_xlim(-3.4, 11.5); ax.set_ylim(-2.6, 2.4)

    fig.suptitle("图是二维的,内存是一维的 —— 中间靠 stride 这一个数连起来", fontsize=13, y=1.0)
    four_questions(fig,
        "按「行优先」把二维网格\n拉成一条字节:先走完\n第 0 行,再接第 1 行。\n"
        f"实测 512×512×3 的\nstrides = {real_strides}。",
        "只用一个起始地址 +\n一个 stride,就能定位\n任意像素:\n"
        "addr = base + y×stride\n       + x×3 + 通道号",
        "行与行在物理上\n**不一定挨着**。\n一旦有对齐填充,\n「整张图是一块连续内存」\n这个直觉就不成立了。",
        f"用 width×bpp 当行偏移,\n在紧凑内存上跑得好好的,\n换到 GPU 纹理或\nCVPixelBuffer 上就花屏。\n"
        f"更阴的是它**在 512、1024 这类\n2 的幂尺寸上测不出来** ——\n那时 width×3 恰好已经对齐了。",
        "永远从框架问 stride,\n别自己乘:numpy 的 .strides、\nCVPixelBuffer 的\nbytesPerRow、Metal 的\nbytesPerRow。逐行拷贝\n用 memcpy 一行一行走。",
        y=-0.02, bottom=0.05)
    save(fig, "memory-row-major.png")
    print(f"     512×512×3 实测 strides = {real_strides}(1536 已是 {align} 的整数倍,无填充);"
          f"宽 {demo_w} 时 {tight} → 对齐后 {padded_stride},填充 {padded_stride - tight} 字节")


# ═══════════════════════════════════ 图 2:YUV 三种排布 ═════════════════


def fig_yuv_layouts() -> None:
    """同样是 4:2:0,YUYV / I420 / NV12 在内存里长得完全不一样。"""
    W, H = 4, 2                        # 迷你图:4×2 像素,UV 是 2×1
    n_y, n_uv = W * H, (W // 2) * (H // 2)

    fig = plt.figure(figsize=(13.4, 5.2))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.35, 1], width_ratios=[1, 1.25],
                          hspace=0.5, wspace=0.2)

    # ── 左上:4:2:0 是怎么采的
    ax = fig.add_subplot(gs[0, 0]); ax.axis("off")
    ax.set_title("4:2:0 采样:每 2×2 个像素共用一对 UV", fontsize=10.5)
    for r in range(H):
        for c in range(W):
            cell(ax, c, (H - 1 - r) * 1.05, 1, 1, "#777", "Y", fs=9)
    for r in range(H // 2):
        for c in range(W // 2):
            ax.add_patch(Rectangle((c * 2, (H - 2 - r * 2) * 1.05), 2, 2.05,
                                   fill=False, ec="#d9534f", lw=2.2))
            ax.text(c * 2 + 1, -0.75, "1 对 UV", ha="center", fontsize=8.5, color="#d9534f")
    ax.text(W / 2, H * 1.05 + 0.35,
            "亮度每个像素都有,色度四个像素才一份", ha="center", fontsize=9)
    ax.set_xlim(-0.3, W + 0.3); ax.set_ylim(-1.3, H * 1.05 + 0.8)
    ax.set_aspect("equal")

    # ── 右上:三种排布的字节条带
    ax = fig.add_subplot(gs[0, 1]); ax.axis("off")
    ax.set_title("同样这些数据,三种摆法", fontsize=10.5)
    layouts = [
        ("YUYV(打包)", [("Y", "#777")] * 1, "单平面,Y 和 UV 交错着放"),
        ("I420(平面)", None, "Y 一整块 → U 一整块 → V 一整块"),
        ("NV12(半平面)", None, "Y 一整块 → UV 交错的一整块"),
    ]
    seqs = {
        "YUYV(打包)": ["Y", "U", "Y", "V"] * 2,
        "I420(平面)": ["Y"] * n_y + ["U"] * n_uv + ["V"] * n_uv,
        "NV12(半平面)": ["Y"] * n_y + ["U", "V"] * n_uv,
    }
    col = {"Y": "#777", "U": "#4a7fd4", "V": "#d9534f"}
    for j, (name, _, note) in enumerate(layouts):
        y = 2 - j * 1.25
        for i, s in enumerate(seqs[name]):
            cell(ax, i, y, 1, 0.85, col[s], s, fs=7.5)
        ax.text(-0.3, y + 0.42, name, ha="right", va="center", fontsize=9.2)
        ax.text(len(seqs[name]) + 0.3, y + 0.42, note, va="center",
                fontsize=8.4, color="#555")
    ax.set_xlim(-5.2, 22); ax.set_ylim(-0.4, 3.3)

    # ── 下:省了多少
    ax = fig.add_subplot(gs[1, :])
    labels = ["RGB / 4:4:4", "4:2:2", "4:2:0"]
    bpp = [3.0, 2.0, 1.5]
    bars = ax.barh(labels[::-1], bpp[::-1], 0.5,
                   color=["#5cb85c", "#e8a33d", "#4a7fd4"])
    for bar, v in zip(bars, bpp[::-1]):
        ax.text(v + 0.05, bar.get_y() + bar.get_height() / 2,
                f"{v} 字节/像素   1080p 一帧 {v * 1920 * 1080 / 1e6:.1f} MB",
                va="center", fontsize=9)
    ax.set_xlim(0, 4.6); ax.set_xlabel("每个像素要占几个字节")
    ax.set_title("4:2:0 把数据量砍掉一半,而肉眼几乎看不出来", fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)

    fig.suptitle("YUV 的三种内存排布:packed / planar / semi-planar", fontsize=13, y=1.0)
    four_questions(fig,
        "先把亮度和色度拆开,\n再按 2×2 一组丢掉\n四分之三的色度采样。",
        "数据量 3.0 → 1.5 字节/像素,\n**直接砍一半**。\n1080p 一帧从 5.9 MB\n降到 3.0 MB。",
        "色度分辨率。细的\n红蓝边界会发虚、发锯齿 ——\n红色字幕、纯色线条\n最容易看出来。",
        "**RGB 做不到这一步**:\n三个通道里都混着亮度,\n砍哪个都会糊。\n必须先分离出亮度,\n才能只对色度下手。",
        "对色度敏感的场合\n(绿幕抠像、字幕、图形叠加)\n用 4:2:2 甚至 4:4:4;\n专业采集卡和中间码\n(ProRes 422、DNxHR)\n就是为此存在的。",
        y=-0.02, bottom=0.14)
    save(fig, "yuv-layouts.png")
    print(f"     迷你图 {W}×{H}:Y {n_y} 个,UV 各 {n_uv} 个;"
          f"4:2:0 = {(n_y + 2 * n_uv) / n_y:.2f} 字节/像素")


if __name__ == "__main__":
    fig_row_major()
    fig_yuv_layouts()
    if "--show" in sys.argv:
        plt.show()
