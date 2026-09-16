"""第 4 周(3.2 节):灰度变换 —— 01 图像反转(底片效果)。

灰度变换是「点运算」:新值 s 只取决于当前像素值 r,和邻居无关。
既然输入只有 256 种可能,就犯不着对几十万个像素逐个算 ——
先按公式建一张 256 项的查找表(LUT),再让全图去查表。
反转、对数、伽马、分段拉伸全都是这一套,本文只是开头第一站。

本篇只做 s = 255 - r,验证四件事:
1. LUT 查表 == 直接向量化 == cv2.bitwise_not,三者逐像素完全相同
2. 反转不改变对比度(标准差一字不差),变的只是明暗方向
3. 反转两次回到原图 —— 它是自逆变换
4. 直方图整体左右镜像:hist_inv[i] == hist[255 - i]

彩色图不用另写一套代码:同一张表给 B/G/R 三个通道各查一遍就行。
三个通道用的是同一条映射,所以彩色反转不会偏色。

用法:
    .venv/bin/python Ch01_02_Fundamentals/03_gray-transform.py [--show]
    结果图保存到 Assets/results/gray-inversion.png(主图板)
                     Assets/results/color-negative-cast.png(彩色反转偏色对照)
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
matplotlib.rcParams["axes.unicode_minus"] = False

# 彩色反转对照用的三张图,色调故意选得不一样:
# coffee 明显偏暖、lenna 略暖、page 是纯灰文档(三通道均值完全相同)。
# 偏色方向是不是跟着原图走,看这张对照就一目了然。
COLOR_CASES = ["coffee.png", "lenna_s.jpg", "page.png"]


def negative_lut() -> npt.NDArray[np.uint8]:
    """s = 255 - r 的 256 项查找表。

    这张表就是「变换本身」—— 公式、映射曲线、LUT 是同一个东西的三种写法。
    0↔255、1↔254 全部成对颠倒,所以它是个自逆映射(查两次回到原点)。
    """
    r = np.arange(256, dtype=np.float64)         # 所有可能的输入灰阶
    s = 255.0 - r
    # 虽然这里不会越界,仍按仓库约定走「浮点算 → clip → 转回 uint8」,
    # 后面加对数/伽马时贴同样的出口,不容易漏掉截断。
    return np.clip(s, 0, 255).astype(np.uint8)


def negative(img: cv2.typing.MatLike) -> cv2.typing.MatLike:
    """按 LUT 反转。灰度图(2 维)和彩色图(3 维)都能直接喂进来。

    cv2.LUT 对多通道图的做法是「每个通道各自查同一张表」,
    所以彩色反转 = 三个通道分别反转,等同于底片。
    """
    return cv2.LUT(img, negative_lut())


def histogram(y: cv2.typing.MatLike) -> npt.NDArray[np.int64]:
    """统计 0~255 每个灰阶的像素个数,返回长度恒为 256 的计数数组。

    用 bincount 而不是 np.histogram:后者要分 bin,256 个 bin 铺在 [0,255] 上
    每个宽 255/256,边界会和整数灰阶错位,两端柱子会莫名其妙偏矮。
    """
    return np.bincount(y.ravel(), minlength=256)


def save_color_negative_demo(out_path: Path) -> None:
    """三张色调不同的图各反转一次:偏色方向跟着原图主色调走,纯灰图零偏色。

    对应文档「附:彩色反转为什么会发青蓝」—— 每格标题上的通道均值就是那张表里的数字。
    灰度反转只涉及一个通道,没什么可商量的;彩色反转才暴露出"取反 = 换补色"这件事,
    所以单独出一张对照。
    """
    fig, axes = plt.subplots(2, len(COLOR_CASES), figsize=(12.5, 8.5))

    for col, name in enumerate(COLOR_CASES):
        bgr = cv2.imread(str(REPO / "Assets" / "test-images" / name))
        if bgr is None:
            raise SystemExit(f"读图失败: {name}")

        for row, (img, tag) in enumerate(((bgr, "原图"), (negative(bgr), "255 - r 反转"))):
            # 均值按 B/G/R 顺序打印 —— 哪一路冒头,就说明整张图往哪个方向偏
            mean = np.asarray(img, dtype=np.uint8).reshape(-1, 3).mean(axis=0)
            ax = axes[row, col]
            ax.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            ax.set_title(f"{name} {tag}\nBGR 均值 {mean[0]:.0f} / {mean[1]:.0f} / {mean[2]:.0f}",
                         fontsize=9)
            ax.axis("off")

    fig.suptitle("彩色图反转:青蓝不是加上去的,是原图偏暖被翻了个面", fontsize=12)
    # suptitle 不算在 tight_layout 的布局里,rect 给它留出顶部空间,否则标题会压住第一行
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.955))
    fig.savefig(out_path, dpi=110)


def main() -> None:
    path = REPO / "Assets" / "test-images" / "lenna_s.jpg"
    bgr = cv2.imread(str(path))
    # 用 raise 不用 assert:assert 在 python -O 下会被剥掉,
    # 读图失败就会带着 None 一路跑到 cvtColor 里炸出看不懂的报错。
    if bgr is None:
        raise SystemExit(f"读图失败: {path}")

    # np.asarray 只是把 cv2 的 MatLike 标成精确的 uint8 数组类型,
    # 不复制数据 —— 下面的类型标注才能对上。
    gray = np.asarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), dtype=np.uint8)

    # --- 1. 一个公式,三种写法 ---
    gray_inv = np.asarray(negative(gray), dtype=np.uint8)   # LUT 查表(本篇的主角)
    # 直接向量化:一行搞定。255 减去 uint8 不会出现负数(最大才 255),
    # 但仍按仓库约定 clip 一下,免得以后改成 r+1 之类的公式时静默回绕。
    gray_inv_vec = np.clip(255 - gray, 0, 255).astype(np.uint8)
    gray_inv_cv = cv2.bitwise_not(gray)                     # OpenCV 自带:按位取反

    print(f"原图   {path.name}  shape={bgr.shape}  dtype={bgr.dtype}")
    print(f"灰度图 shape={gray.shape}  dtype={gray.dtype}")

    def max_diff(a: cv2.typing.MatLike, b: cv2.typing.MatLike) -> int:
        # 相减前先升到 int16,否则 uint8 减 uint8 会回绕成 255 这种假差值
        return int(np.abs(a.astype(np.int16) - b.astype(np.int16)).max())

    print("\n三种写法是否一致:")
    print(f"  LUT       vs 255 - img      : 最大差 {max_diff(gray_inv, gray_inv_vec)}")
    print(f"  LUT       vs cv2.bitwise_not: 最大差 {max_diff(gray_inv, gray_inv_cv)}")

    # --- 2. 对比度不变,只是翻了个面 ---
    p1, p99 = np.percentile(gray, [1, 99])
    q1, q99 = np.percentile(gray_inv, [1, 99])
    print("\n反转前后的统计量:")
    print(f"  均值   {gray.mean():6.2f} → {gray_inv.mean():6.2f}"
          f"   (255 - 原均值 = {255 - gray.mean():.2f})")
    print(f"  标准差 {gray.std():6.2f} → {gray_inv.std():6.2f}   ← 一模一样:对比度没变")
    print(f"  1%~99% 跨度 [{p1:.0f}, {p99:.0f}] → [{q1:.0f}, {q99:.0f}]"
          f"   (宽度都是 {p99 - p1:.0f},方向反了)")
    print("  所以反转不是「提亮暗部」,它不改对比度,只是把明暗整个掉个头。")

    # --- 3. 自逆:查两次表回到原图 ---
    restored = negative(negative(gray))
    print(f"\n反转两次复原:逐像素相同 = {np.array_equal(restored, gray)}")

    # --- 4. 直方图左右镜像 ---
    hist = histogram(gray)
    hist_inv = histogram(gray_inv)
    print(f"直方图镜像  hist_inv[i] == hist[255-i] = {np.array_equal(hist_inv, hist[::-1])}")
    peak = int(hist.argmax())
    print(f"  峰值从灰阶 {peak} 挪到 {255 - peak},个数不变"
          f"({int(hist[peak])} 个)—— 同一批像素,只是换了位置")

    # --- 出对比图板 ---
    fig, axes = plt.subplots(2, 3, figsize=(15.5, 9.5))

    panels = [
        (cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), "原图 (RGB)", False),
        (gray, "亮度 Y′ = 0.299R + 0.587G + 0.114B", True),
        (gray_inv, "反转后的 Y′ —— 底片效果", True),
        (cv2.cvtColor(negative(bgr), cv2.COLOR_BGR2RGB),
         "彩色反转(同一张 LUT 扫过 B/G/R 三个通道)", False),
    ]
    # 这里本该用 zip(..., strict=True) 保证两个列表等长,但本仓库的 venv 是
    # Python 3.9,strict 参数 3.10 才有。panels 就在上面几行,长度一目了然。
    for ax, (img, title, is_gray) in zip(axes.flat[:4], panels):
        if is_gray:
            ax.imshow(img, cmap="gray", vmin=0, vmax=255)  # 灰度图必须给死 vmin/vmax
        else:
            ax.imshow(img)
        ax.set_title(title, fontsize=11)
        ax.axis("off")

    # --- 直方图:原图 vs 反转后 vs 反转后再翻回来 ---
    ax = axes.flat[4]
    levels = np.arange(256)
    ax.fill_between(levels, hist, color="0.72", label="原图直方图", zorder=2)
    ax.plot(levels, hist_inv, color="tab:blue", lw=1.3,
            label="反转后的直方图(整体镜像)", zorder=3)
    ax.plot(levels, hist_inv[::-1], color="tab:orange", lw=1.0, ls="--",
            label="镜像后翻回来 → 与原图重合", zorder=4)
    ax.set_xlim(0, 255)
    ax.set_ylim(0, float(hist.max()) * 1.12)
    ax.set_title("直方图:形状不变,只是左右翻面", fontsize=11)
    ax.set_xlabel("灰阶 r / s")
    ax.set_ylabel("像素个数")
    ax.legend(fontsize=8, loc="upper right")

    # --- 映射曲线:s = 255 - r 是一条反斜对角直线 ---
    ax = axes.flat[5]
    ax.plot([0, 255], [0, 255], color="0.78", lw=3.0, label="什么都不做 s = r")
    ax.plot(levels, negative_lut(), color="tab:orange", lw=1.6, label="反转 s = 255 - r")
    ax.plot([0, 255], [255, 0], "o", color="tab:red", ms=5)
    ax.set_xlim(0, 255)
    ax.set_ylim(0, 255)
    ax.set_aspect("equal")   # 正方形,斜率才不会被拉变形
    ax.set_title("映射曲线:直线,斜率 -1,截距 255", fontsize=11)
    ax.set_xlabel("输入灰阶 r")
    ax.set_ylabel("输出灰阶 s")
    ax.legend(fontsize=8, loc="lower left")

    fig.tight_layout()
    out = REPO / "Assets" / "results" / "gray-inversion.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=110)
    print(f"\n结果已保存: {out.relative_to(REPO)}")

    # 第二张图板:彩色反转的偏色对照(文档附录用)
    out_color = out.with_name("color-negative-cast.png")
    save_color_negative_demo(out_color)
    print(f"结果已保存: {out_color.relative_to(REPO)}")

    if "--show" in sys.argv:
        plt.show()


if __name__ == "__main__":
    main()
