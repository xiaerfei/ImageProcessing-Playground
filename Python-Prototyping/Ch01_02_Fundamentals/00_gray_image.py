"""第 1 周热身:从 RGB 算亮度(Luma Y′),看它长什么样。

验证三件事:
1. 灰度化不是「求平均」,而是按人眼敏感度加权:Y = 0.299R + 0.587G + 0.114B
2. cv2.cvtColor(BGR2GRAY) 用的就是这套 Rec.601 权重、全范围 0~255
3. Y 是 2 维数组,它本身就是一张完整的灰度图(YUV 里那个 Y 就是它,不用算)
4. 亮度直方图:这张图的像素在 0~255 上怎么分布,暗/中/亮各占多少

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

    三个坑:OpenCV 读进来是 BGR(拆通道别拿反);
    先 astype(np.float64) 再乘,否则 uint8 直接算会回绕;
    最后必须 np.rint 四舍五入 —— astype(np.uint8) 是向下取整,
    129.9 会变成 129,而 cv2 给的是 130,平均每两个像素就差 1 个灰阶,
    而且永远偏同一个方向(累积起来整张图会发暗)。加上 rint 后误差降到
    ±1 以内且正负抵消。取整规矩详见 Documents/01-fundamentals/rounding-and-float.md。
    """
    b = bgr[:, :, 0].astype(np.float64)
    g = bgr[:, :, 1].astype(np.float64)
    r = bgr[:, :, 2].astype(np.float64)
    y = np.rint(0.299 * r + 0.587 * g + 0.114 * b)
    return np.clip(y, 0, 255).astype(np.uint8)


def luma_histogram(y: npt.NDArray[np.uint8]) -> npt.NDArray[np.int64]:
    """统计 0~255 每个灰阶各有多少个像素,返回长度固定 256 的计数数组。

    用 np.bincount 而不是 np.histogram / plt.hist:后两者要你指定 bins 和
    range,而 256 个 bin 铺在 [0, 255] 上每个 bin 宽 255/256 = 0.996,
    边界会和整数灰阶错位,某些灰阶被并进相邻 bin,直方图两端的柱子莫名其妙
    偏矮。bincount 直接按整数值计数,一个灰阶一个格子,不存在分 bin 的问题。
    minlength=256 保证没出现过的灰阶也留一个 0,输出长度恒定好对齐画图。
    """
    return np.bincount(y.ravel(), minlength=256)


def print_histogram_stats(y: npt.NDArray[np.uint8], hist: npt.NDArray[np.int64]) -> None:
    """把直方图读成几个能下判断的数:集中在哪、够不够宽、两端有没有被削平。"""
    total = y.size
    # 百分位比 min/max 稳:单个噪点就能把 min/max 拉到 0 和 255,
    # 而 1%/99% 跨度反映的是「绝大多数像素」占了多宽,才是有效动态范围。
    p1, p50, p99 = np.percentile(y, [1, 50, 99])
    n_black = int(hist[0])
    n_white = int(hist[255])

    print("\n亮度直方图:")
    print(f"  均值 {y.mean():6.1f}   中位数 {p50:5.1f}   标准差 {y.std():5.1f}(越大对比度越强)")
    print(f"  全范围 [{y.min()}, {y.max()}]   1%~99% 跨度 [{p1:.0f}, {p99:.0f}]"
          f" = {p99 - p1:.0f} 个灰阶(有效动态范围)")
    print(f"  峰值在灰阶 {int(hist.argmax())},占 {100 * hist.max() / total:.2f}%")
    # 只在真的有死黑/死白时才提示,否则「0 个 ← 已丢失细节」读起来自相矛盾。
    clipped = "  ← 死黑/死白,这些像素的细节已经丢了" if (n_black or n_white) else "  ← 两端都没削平"
    print(f"  纯黑(0) {n_black} 个 = {100 * n_black / total:.3f}%   "
          f"纯白(255) {n_white} 个 = {100 * n_white / total:.3f}%{clipped}")

    # 三段占比:粗看影调偏向。分界取 85/170 是把 0~255 三等分,不是什么标准。
    dark, mid, bright = (int(hist[:85].sum()), int(hist[85:170].sum()),
                         int(hist[170:].sum()))
    print(f"  暗部 0~84 {100 * dark / total:5.1f}%   "
          f"中间调 85~169 {100 * mid / total:5.1f}%   "
          f"高光 170~255 {100 * bright / total:5.1f}%")


def main() -> None:
    path = REPO / "Assets" / "test-images" / "lenna_s.jpg"
    bgr = cv2.imread(str(path))
    # 用 raise 不用 assert:assert 在 python -O 下会被整条剥掉,
    # 读图失败就会带着 None 一路跑到 cvtColor 里炸出看不懂的报错。
    if bgr is None:
        raise SystemExit(f"读图失败: {path}")

    # --- 1. 同一个 Y,两种算法的对照 ---
    y_cv = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)   # OpenCV:Rec.601 + 全范围
    y_hand = to_luma(bgr)                          # 手写:同一个公式

    diff = np.abs(y_hand.astype(np.int16) - y_cv.astype(np.int16))
    n_diff = int(np.count_nonzero(diff))
    print(f"原图   shape={bgr.shape}  dtype={bgr.dtype}   每像素 3 个数 (B, G, R)")
    print(f"亮度图 shape={y_cv.shape}  dtype={y_cv.dtype}   每像素 1 个数")
    # cv2 内部走的是整数定点 + SIMD,取整细节和 numpy 浮点不完全同步,
    # 所以只保证 ±1 以内,不保证逐像素相同(这张照片碰巧是 0)。
    print(f"\n手写 vs cv2.BGR2GRAY:最大差 {diff.max()},不一致 {n_diff} 个像素 → 同一个 Y")
    print(f"亮度图统计:均值 {y_cv.mean():.1f}  范围 [{y_cv.min()}, {y_cv.max()}]")

    # --- 2. 亮度直方图 ---
    hist = luma_histogram(y_cv)
    print_histogram_stats(y_cv, hist)

    # --- 3. 出对比图板:原图 / 亮度图 / 亮度直方图 ---
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    panels = [
        (cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), "原图 (BGR → RGB)"),
        (y_cv, "亮度 Y′ = 0.299R + 0.587G + 0.114B"),
    ]
    # 这里想用 zip(..., strict=True) 保证两个列表等长,但本仓库的 venv 是
    # Python 3.9,strict 参数 3.10 才有,3.9 下会直接 TypeError。
    # panels 就在上面几行写死,长度一目了然,直接 zip 即可。
    for ax, (img, title) in zip(axes[:2], panels):
        if img.ndim == 2:
            ax.imshow(img, cmap="gray", vmin=0, vmax=255)   # 灰度图必须给 vmin/vmax
        else:
            ax.imshow(img)
        ax.set_title(title, fontsize=11)
        ax.axis("off")

    ax = axes[2]
    levels = np.arange(256)
    # 用 bar 而不是 plot:直方图是 256 个离散计数,不是连续曲线,
    # 折线会在空灰阶处画出并不存在的斜坡。width=1 让柱子严丝合缝排满。
    ax.bar(levels, hist, width=1.0, color="#444444", zorder=2)
    # 底色铺一条由黑到白的渐变,一眼能看出横轴每个位置对应多亮,
    # 不用去数刻度。extent 的 y 上界跟着柱高走,渐变条才不会挡住柱子。
    ax.imshow(levels.reshape(1, -1), cmap="gray", vmin=0, vmax=255, aspect="auto",
              extent=(0.0, 255.0, 0.0, float(hist.max()) * 0.06), zorder=1)
    ax.set_xlim(0, 255)
    ax.set_ylim(0, float(hist.max()) * 1.05)
    ax.set_title("亮度直方图(横轴 0~255,纵轴 像素个数)", fontsize=11)
    ax.set_xlabel("灰阶")
    ax.set_ylabel("像素个数")
    fig.tight_layout()

    out = REPO / "Assets" / "results" / "week01_gray_image.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=110)
    print(f"\n结果已保存: {out.relative_to(REPO)}")
    if "--show" in sys.argv:
        plt.show()


if __name__ == "__main__":
    main()
