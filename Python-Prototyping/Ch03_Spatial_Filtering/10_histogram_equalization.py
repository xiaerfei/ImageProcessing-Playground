"""第 5 周(3.3 节):直方图处理 —— 10 从零手写直方图均衡化。

对应文档 Documents/03-histogram/histogram-transform.md 第三~六节。

均衡化说白了就一句话:

    新亮度 = 「全图有百分之多少的像素比我暗」× 255

而「有多少比我暗」就是累计分布函数 CDF。它仍然是 01~06 那样的 256 项查表,
只是这张表不是你拧参数拧出来的,而是**图自己统计出来的** —— 换张图,表就变。

验证五件事:
1. 先用教材那张 8 级、100 像素的小图手算一遍,复现文档第四节的表;
   顺带看清「柱子不会真的变平」—— 离散图像根本做不到
2. 手写 LUT 对齐 cv2.equalizeHist:⚠️ 直接 round(cdf × 255) 对不上,
   OpenCV 减掉了最暗那一档的计数(cdf_min 归一化)。在 astronaut 上
   两种写法差到 29 级,差在哪、为什么要减,这一节说清楚
3. 效果与代价:moon.png 标准差 13.3 → 74.0,CDF 离理想直线的平均差距
   从 22.8 个百分点掉到 2.5;代价是用到的灰阶从 178 掉到 49,
   直方图长出梳齿 —— 查表只会合并灰阶,不会凭空造出新的
4. 两个性质:LUT 单调非降(所以不会把明暗顺序搞乱),以及幂等
   (均衡两次 = 均衡一次),这也是「它没有力度旋钮」的另一种说法
5. 三个毛病里最要命的两个:噪声被同步放大(实测放大倍数),
   以及全局统计管不了局部 —— 这就是 CLAHE 存在的理由(见 13 号脚本)

用法:
    .venv/bin/python Ch03_Spatial_Filtering/10_histogram_equalization.py [--show]
    结果图保存到 Assets/results/histogram-equalization-demo.png(原理与效果)
                     Assets/results/equalization-pitfalls-demo.png(两种写法与两个毛病)
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

LEVELS = np.arange(256)


def hr(title: str) -> None:
    print(f"\n{'=' * 66}\n{title}\n{'=' * 66}")


def load_gray(name: str) -> npt.NDArray[np.uint8]:
    path = REPO / "Assets" / "test-images" / name
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise SystemExit(f"读不到 {path}")
    return np.asarray(img, dtype=np.uint8)


def hist_of(img: npt.NDArray[np.uint8]) -> npt.NDArray[np.int64]:
    """256 个桶的直方图。

    用 bincount 而不是 np.histogram/plt.hist:灰度是 0~255 的整数,
    一个值就该占一个桶。np.histogram(bins=256, range=(0,255)) 的桶宽是
    255/256 = 0.996,边界会错位,画出来的柱子高低相间。
    """
    return np.bincount(img.ravel(), minlength=256)


def equalize_lut(img: npt.NDArray[np.uint8], subtract_min: bool = True) -> npt.NDArray[np.uint8]:
    """从图自己的直方图算出 256 项查表。

    subtract_min=False 是教材公式 s = round(255 · cdf(r));
    True 则先减掉最暗那一档的计数再归一化,这是 OpenCV 用的版本,
    区别见第 2 节 —— 前者最暗的像素永远到不了 0。
    """
    hist = hist_of(img).astype(np.float64)
    cdf = np.cumsum(hist)
    if not subtract_min:
        s = cdf / img.size * 255.0
    else:
        first = int(np.nonzero(hist)[0][0])  # 最暗的、真的有像素的那一档
        s = (cdf - hist[first]) * (255.0 / (img.size - hist[first]))
        s[:first] = 0.0  # 空档位随便映射到哪都行,图里根本没有这些值
    return np.clip(np.rint(s), 0, 255).astype(np.uint8)


def equalize(img: npt.NDArray[np.uint8], subtract_min: bool = True) -> npt.NDArray[np.uint8]:
    return np.asarray(cv2.LUT(img, equalize_lut(img, subtract_min)), dtype=np.uint8)


def used_levels(img: npt.NDArray[np.uint8]) -> int:
    """实际用到了多少个灰阶(直方图里有多少根非零的柱子)。"""
    return int(np.count_nonzero(hist_of(img)))


def cdf_gap(img: npt.NDArray[np.uint8]) -> float:
    """离理想均匀分布有多远:CDF 与那条对角线的平均差距,单位是「个百分点」。

    完全均匀时 CDF 就是从 (0,0) 到 (255,1) 的直线,这个数为 0。

    为什么不用「各桶占比的标准差」:那个指标在这里会骗人。均衡化会把多个
    灰阶并成一个,剩下的桶就变得更高,逐桶比较反而看不出改善(moon.png 上
    前后都是 1.35)。而 CDF 是累计量,合并不影响它 —— 它衡量的是
    「像素在 0~255 上摊得均不均」,正是均衡化真正在做的事。
    """
    cdf = np.cumsum(hist_of(img)) / img.size
    return float(np.mean(np.abs(cdf - (LEVELS + 1) / 256.0)) * 100.0)


# ---------------------------------------------------------------- 1
def demo_textbook_table() -> None:
    hr("1. 教材小例子:8 个灰度级、100 个像素,手算一遍")
    counts = np.array([0, 0, 5, 30, 40, 20, 5, 0])
    n, levels = counts.sum(), 8
    cdf = np.cumsum(counts) / n
    s = np.rint(cdf * (levels - 1)).astype(int)

    print("  原亮度 r | 像素数 | 累计比例 | 新亮度 s = round(累计 × 7)")
    for r in range(levels):
        mark = "   ← 挤在一起的三档" if r in (3, 4, 5) else ""
        print(f"      {r}    |  {counts[r]:3d}   |   {cdf[r]:.2f}   |      {s[r]}{mark}")

    print(f"\n  原来 3、4、5 彼此只差 1 → 现在是 {s[3]}、{s[4]}、{s[5]},差 "
          f"{s[4] - s[3]} 和 {s[5] - s[4]},被拉开了")

    after = np.bincount(s, weights=counts, minlength=levels).astype(int)
    print(f"  均衡后每一档的像素数:{after.tolist()}")
    print("  ⚠️ 里面还有一堆 0 —— 离散图像的均衡化永远做不到完全平坦。")
    print("     灰度 4 那 40 个像素原值一样,查表后必然还是一样,不可能拆开分给两档。")
    print("     所以「均衡」是把柱子在 0~7 全程摊得更开,不是把每根柱子削成一样高。")


# ---------------------------------------------------------------- 2
def demo_align_with_opencv() -> None:
    hr("2. 手写 LUT 对齐 cv2.equalizeHist:那个必须减掉的 cdf_min")
    for name in ("moon.png", "camera.png", "astronaut.png"):
        img = load_gray(name)
        ref = np.asarray(cv2.equalizeHist(img), dtype=np.uint8)
        print(f"\n  {name}")
        for label, sub in (("教材式 round(255·cdf)  ", False), ("OpenCV 式(减 cdf_min)", True)):
            out = equalize(img, sub)
            diff = np.abs(out.astype(np.int64) - ref.astype(np.int64))
            print(f"    {label}  与 cv2 最大差 {diff.max():2d},"
                  f"不同像素 {int(np.count_nonzero(diff)):6d}/{img.size},"
                  f"输出范围 [{out.min():3d}, {out.max():3d}]")

    print("\n  两种写法的差别只在最暗那一档:")
    print("    教材式:最暗的像素的累计比例不是 0(它自己也算进去了),所以映射结果 > 0")
    print("    OpenCV:先把这一档的计数减掉,让最暗的像素正好落到 0,输出铺满 [0, 255]")
    img = load_gray("astronaut.png")
    h = hist_of(img)
    print(f"\n  为什么 astronaut 上差到 29:它有 {h[0]} 个纯黑像素"
          f"({h[0] / img.size * 100:.1f}% 的画面是太空背景),")
    print(f"     教材式把这一大坨直接抬到 {equalize_lut(img, False)[0]},整张图都发灰。")
    print("     图里纯黑/纯白占比越大,这个差距越明显 —— camera.png 上两种写法逐像素相同。")


# ---------------------------------------------------------------- 3
def demo_effect_and_cost(img: npt.NDArray[np.uint8]) -> None:
    hr("3. 效果与代价:拉开了对比度,但灰阶只会变少")
    out = equalize(img)
    print(f"    {'':14s}{'标准差':>8s}{'用到的灰阶':>12s}{'CDF 离理想直线':>18s}")
    for label, g in (("均衡前", img), ("均衡后", out)):
        print(f"    {label:14s}{g.std():8.1f}{used_levels(g):12d}{cdf_gap(g):16.1f} 个百分点")
    print("    (CDF 离理想直线 = 像素在 0~255 上摊得均不均,完全均匀是 0.0)")
    print("\n    对比度确实上去了,但用到的灰阶不升反降 —— 查表只会把多个灰阶合并成一个,")
    print("    绝不会凭空造出新的。直方图放大看是一排梳齿:被拉开的档之间是空的。")

    lut = equalize_lut(img)
    merged = 256 - len(np.unique(lut))
    print(f"    这张图的 LUT 里,256 个输入值只映射到 {len(np.unique(lut))} 个不同输出,"
          f"有 {merged} 个灰阶被并掉了。")


# ---------------------------------------------------------------- 4
def demo_properties(img: npt.NDArray[np.uint8]) -> None:
    hr("4. 两个性质:保序,且幂等")
    lut = equalize_lut(img)
    print(f"    LUT 单调非降:{bool(np.all(np.diff(lut) >= 0))}")
    print("      CDF 是累加出来的,只会往上走,所以查表后暗的还是暗、亮的还是亮。")
    print("      这就是「摊开但不能乱摊」那句话的数学保证。")

    once = equalize(img)
    twice = equalize(once)
    diff = np.abs(twice.astype(np.int64) - once.astype(np.int64))
    print(f"\n    均衡两次 vs 均衡一次:最大差 {diff.max()},"
          f"不同像素 {int(np.count_nonzero(diff))}/{img.size}")
    print("      第二次几乎什么都没做 —— 均衡化是幂等的。")
    print("      这正说明它没有「力度」这个旋钮:要么不做,要么做满,想做七成做不到。")
    print("      想要能调力度,得换成 γ 校正(04 号脚本)或者带 clipLimit 的 CLAHE。")


# ---------------------------------------------------------------- 5
def demo_two_flaws(img: npt.NDArray[np.uint8]) -> None:
    hr("5. 两个毛病:噪声被一起放大,以及全局统计管不了局部")
    rng = np.random.default_rng(0)
    sigma = 3.0
    noise = rng.normal(0.0, sigma, img.shape)
    noisy = np.clip(np.rint(img.astype(np.float64) + noise), 0, 255).astype(np.uint8)

    # 同一张 LUT 作用在干净图和带噪图上,差值就是「被放大后的噪声」
    lut = equalize_lut(img)
    clean_eq = np.asarray(cv2.LUT(img, lut), dtype=np.uint8)
    noisy_eq = np.asarray(cv2.LUT(noisy, lut), dtype=np.uint8)
    after = float((noisy_eq.astype(np.float64) - clean_eq.astype(np.float64)).std())
    print(f"    加 σ={sigma:.0f} 的高斯噪声,均衡后噪声标准差变成 {after:.1f},"
          f"放大了 {after / sigma:.1f} 倍")
    print("      原因很直白:均衡化在「人多」的灰度区间把曲线拉得很陡,")
    print("      信号被拉开多少倍,压在上面的噪声就被拉开多少倍 —— 它分不清谁是谁。")
    print("      平坦的天空、墙面这种地方最容易看出来:一片颗粒。")

    page = load_gray("page.png")
    w = page.shape[1] // 2
    glob = np.asarray(cv2.equalizeHist(page), dtype=np.uint8)
    clahe = np.asarray(cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(page),
                       dtype=np.uint8)
    print(f"\n    page.png 左半边 / 右半边受光不均,左右平均亮度:")
    for label, g in (("原图  ", page), ("全局均衡", glob), ("CLAHE ", clahe)):
        print(f"      {label}  左 {g[:, :w].mean():6.1f}  右 {g[:, w:].mean():6.1f}  "
              f"差 {abs(g[:, :w].mean() - g[:, w:].mean()):5.1f}")
    print("      全局均衡化只有一张表,不可能同时照顾亮区和暗区;")
    print("      CLAHE 分块各统计各的,才压得下这个差。拆解见 13_clahe_walkthrough.py。")


# ---------------------------------------------------------------- 图板
def draw_hist(ax, img: npt.NDArray[np.uint8], title: str) -> None:
    """直方图 + CDF 双轴。CDF 画成红线,均衡后应该接近一条对角线。"""
    h = hist_of(img)
    ax.bar(LEVELS, h, width=1.0, color="#4c72b0", linewidth=0)
    ax.set_xlim(0, 255)
    ax.set_xlabel("灰度值")
    ax.set_ylabel("像素数")
    ax.set_title(title, fontsize=10)
    ax2 = ax.twinx()
    ax2.plot(LEVELS, np.cumsum(h) / img.size, color="tab:red", lw=1.6)
    ax2.set_ylim(0, 1.02)
    ax2.set_ylabel("CDF", color="tab:red")
    ax2.tick_params(axis="y", labelcolor="tab:red")


def save_main_figure(out_path: Path, img: npt.NDArray[np.uint8]) -> None:
    """图板一:原图 / 均衡图 / LUT 曲线,以及各自的直方图 + CDF。"""
    out = equalize(img)
    lut = equalize_lut(img)
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))

    axes[0, 0].imshow(img, cmap="gray", vmin=0, vmax=255)
    axes[0, 0].set_title(f"原图 moon.png\n标准差 {img.std():.1f},全挤在中间", fontsize=10)
    axes[0, 1].imshow(out, cmap="gray", vmin=0, vmax=255)
    axes[0, 1].set_title(f"直方图均衡化后\n标准差 {out.std():.1f},没有任何参数", fontsize=10)
    for ax in axes[0, :2]:
        ax.axis("off")

    ax = axes[0, 2]
    ax.plot(LEVELS, lut, color="tab:green", lw=2.0, label="均衡化 LUT(= 255 × CDF)")
    ax.plot(LEVELS, LEVELS, "--", color="gray", lw=1.0, label="恒等(什么都不做)")
    ax.set_xlim(0, 255)
    ax.set_ylim(0, 255)
    ax.set_aspect("equal")
    ax.set_xlabel("输入 r")
    ax.set_ylabel("输出 s")
    ax.set_title("这张表是图自己统计出来的\n陡的地方 = 像素多的地方 = 被拉开", fontsize=10)
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(alpha=0.3)

    draw_hist(axes[1, 0], img, f"原直方图:只用到 {used_levels(img)} 个灰阶\nCDF 中间陡、两头平")
    draw_hist(axes[1, 1], out, f"均衡后:摊到全程,但长出梳齿\n用到 {used_levels(out)} 个灰阶,反而更少")

    ax = axes[1, 2]
    ax.bar(LEVELS, (np.cumsum(hist_of(out)) / out.size - (LEVELS + 1) / 256.0) * 100.0,
           width=1.0, color="#dd8452", linewidth=0)
    ax.set_xlim(0, 255)
    ax.set_xlabel("灰度值")
    ax.set_ylabel("CDF − 理想直线(个百分点)")
    ax.set_title(f"离「完全均匀」还差多少:平均 {cdf_gap(out):.1f} 个百分点\n"
                 f"(原图 {cdf_gap(img):.1f});做不到 0,同值像素没法拆开", fontsize=10)
    ax.grid(alpha=0.3)

    fig.suptitle("直方图均衡化:新亮度 = (有多少比我暗) × 255,表由图自己统计", fontsize=13)
    # 每格标题两行,不留行距会压住上一行
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94), h_pad=3.0)
    fig.savefig(out_path, dpi=110)


def save_pitfalls_figure(out_path: Path) -> None:
    """图板二:两种写法的差别,以及噪声放大与局部失效。"""
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))

    ast = load_gray("astronaut.png")
    book = equalize(ast, subtract_min=False)
    ocv = equalize(ast, subtract_min=True)
    axes[0, 0].imshow(ast, cmap="gray", vmin=0, vmax=255)
    axes[0, 0].set_title(f"astronaut.png 原图\n{hist_of(ast)[0] / ast.size * 100:.1f}% 是纯黑背景",
                         fontsize=10)
    axes[0, 1].imshow(book, cmap="gray", vmin=0, vmax=255)
    axes[0, 1].set_title(f"教材式 round(255·cdf)\n黑场被抬到 {equalize_lut(ast, False)[0]},背景发灰",
                         fontsize=10)
    axes[0, 2].imshow(ocv, cmap="gray", vmin=0, vmax=255)
    axes[0, 2].set_title("OpenCV 式(先减 cdf_min)\n黑场回到 0,与 cv2.equalizeHist 逐像素相同",
                         fontsize=10)
    for ax in axes[0]:
        ax.axis("off")

    page = load_gray("page.png")
    glob = np.asarray(cv2.equalizeHist(page), dtype=np.uint8)
    clahe = np.asarray(cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(page),
                       dtype=np.uint8)
    w = page.shape[1] // 2
    for ax, (g, label) in zip(axes[1], (
            (page, "page.png 原图:左右受光不均"),
            (glob, "全局均衡:一张表顾不了两头"),
            (clahe, "CLAHE:分块各统计各的"))):
        ax.imshow(g, cmap="gray", vmin=0, vmax=255)
        ax.set_title(f"{label}\n左右平均亮度差 {abs(g[:, :w].mean() - g[:, w:].mean()):.1f}",
                     fontsize=10)
        ax.axis("off")

    fig.suptitle("均衡化的两个坑:cdf_min 减不减(上排),以及全局统计管不了局部(下排)",
                 fontsize=13)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94), h_pad=3.0)
    fig.savefig(out_path, dpi=110)


def main() -> None:
    img = load_gray("moon.png")
    print(f"主图 moon.png  shape={img.shape}  "
          f"均值 {img.mean():.1f}  标准差 {img.std():.1f}  —— 典型的低对比度图")

    demo_textbook_table()
    demo_align_with_opencv()
    demo_effect_and_cost(img)
    demo_properties(img)
    demo_two_flaws(img)

    out = REPO / "Assets" / "results" / "histogram-equalization-demo.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    save_main_figure(out, img)
    print(f"\n结果已保存: {out.relative_to(REPO)}")

    pit = out.with_name("equalization-pitfalls-demo.png")
    save_pitfalls_figure(pit)
    print(f"结果已保存: {pit.relative_to(REPO)}")

    if "--show" in sys.argv:
        plt.show()


if __name__ == "__main__":
    main()
