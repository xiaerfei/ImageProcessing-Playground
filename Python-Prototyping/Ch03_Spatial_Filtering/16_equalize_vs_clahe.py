"""第 5 周(3.3 节):直方图处理 —— 16 全局均衡化 vs CLAHE,到底该用哪个。

对应文档 Documents/03-histogram/histogram-transform.md 第六、七节。

10 号脚本写了全局均衡化,13 号脚本拆了 CLAHE 的内部步骤,
这一篇只做一件事:**把两者摆在一起比**,回答「什么时候用哪个」。

一句话区别:

    全局均衡化  = 全图统计出 1 张表,所有像素查同一张
    CLAHE      = 切成 8×8 块,每块统计出自己的表(共 64 张),
                 每张表先被 clipLimit 削掉过高的柱子,再双线性插值过渡

验证五件事:
1. 表的数量:1 张 vs 64 张 —— 把 CLAHE 各块的 LUT 画在一起,一眼看清
2. 三张性格不同的图横着比:低对比度的 moon、光照不均的 page、
   本来就正常的 astronaut。结论不是「CLAHE 永远赢」
3. 「细节看得见」要用**局部对比度**量(分块标准差的均值),
   全局标准差会骗人:全局涨了,局部可能没涨
4. 代价:噪声放大倍数、灰阶合并数、耗时 —— CLAHE 慢但可控
5. CLAHE 本质上就是「带旋钮的均衡化」:clipLimit 推到极大 +
   tileGridSize=(1,1) 会逐像素退化回全局均衡化

用法:
    .venv/bin/python Ch03_Spatial_Filtering/16_equalize_vs_clahe.py [--show]
    结果图保存到 Assets/results/equalize-vs-clahe-demo.png(三张图横向对比)
                     Assets/results/equalize-vs-clahe-curves.png(表、旋钮、直方图)
"""

import sys
import time
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
TILES = 8            # CLAHE 的默认分块数,本文全程用 8×8
CLIP = 2.0           # CLAHE 的默认 clipLimit


def hr(title: str) -> None:
    print(f"\n{'=' * 68}\n{title}\n{'=' * 68}")


def load_gray(name: str) -> npt.NDArray[np.uint8]:
    path = REPO / "Assets" / "test-images" / name
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise SystemExit(f"读不到 {path}")
    return np.asarray(img, dtype=np.uint8)


def eq(img: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
    return np.asarray(cv2.equalizeHist(img), dtype=np.uint8)


def clahe(img: npt.NDArray[np.uint8], clip: float = CLIP,
          tiles: int = TILES) -> npt.NDArray[np.uint8]:
    op = cv2.createCLAHE(clipLimit=clip, tileGridSize=(tiles, tiles))
    return np.asarray(op.apply(img), dtype=np.uint8)


def local_contrast(img: npt.NDArray[np.uint8], tiles: int = TILES) -> float:
    """分块标准差的均值 —— 「局部细节看不看得见」的量化指标。

    为什么不看全局标准差:全局标准差只要把暗区压得更暗、亮区拉得更亮就能涨,
    但那不叫细节变清楚了。人眼看细节看的是**一小片区域内部**的差异,
    所以要先切块、块内各算各的标准差,再平均。
    """
    h, w = img.shape
    v = img.astype(np.float64)
    stds = []
    for i in range(tiles):
        for j in range(tiles):
            block = v[i * h // tiles:(i + 1) * h // tiles,
                      j * w // tiles:(j + 1) * w // tiles]
            stds.append(block.std())
    return float(np.mean(stds))


def halves_gap(img: npt.NDArray[np.uint8]) -> float:
    """左右半边的平均亮度差 —— 衡量光照不均有没有被改善。"""
    w = img.shape[1] // 2
    return float(abs(img[:, :w].mean() - img[:, w:].mean()))


def used_levels(img: npt.NDArray[np.uint8]) -> int:
    return int(np.count_nonzero(np.bincount(img.ravel(), minlength=256)))


def tile_lut(block: npt.NDArray[np.uint8], clip: float = CLIP) -> npt.NDArray[np.float64]:
    """按 CLAHE 的规则算一个小块自己的映射表(削顶 → 均分回填 → CDF)。

    这是为了**把表画出来**看的简化版:OpenCV 不暴露内部的 64 张表,
    而且真正的 CLAHE 还要在块之间做双线性插值,这里不做插值。
    """
    hist = np.bincount(block.ravel(), minlength=256).astype(np.float64)
    limit = clip * block.size / 256.0
    excess = float(np.maximum(hist - limit, 0.0).sum())
    hist = np.minimum(hist, limit) + excess / 256.0  # 削下来的总量均分回填,总数守恒
    return np.cumsum(hist) / hist.sum() * 255.0


def noise_gain(img: npt.NDArray[np.uint8], method: str, sigma: float = 3.0,
               clip: float = CLIP) -> float:
    """给图加噪声,看这个算法把噪声放大了几倍。

    干净图和带噪图各走一遍同一个算法,两者之差就是「被处理过的噪声」。
    """
    rng = np.random.default_rng(0)
    noisy = np.clip(np.rint(img.astype(np.float64) + rng.normal(0.0, sigma, img.shape)),
                    0, 255).astype(np.uint8)
    def fn(x: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
        return eq(x) if method == "eq" else clahe(x, clip=clip)

    d = fn(noisy).astype(np.float64) - fn(img).astype(np.float64)
    return float(d.std() / sigma)


# ---------------------------------------------------------------- 1
def demo_one_table_vs_many(img: npt.NDArray[np.uint8]) -> None:
    hr("1. 一张表 vs 64 张表")
    print(f"  全局均衡化:全图 {img.size} 个像素统计出 1 张 256 项的表,所有像素共用")
    print(f"  CLAHE     :切成 {TILES}×{TILES} = {TILES * TILES} 块,每块 "
          f"{img.shape[0] // TILES}×{img.shape[1] // TILES} 个像素,各统计各的表")

    h, w = img.shape
    luts = [tile_lut(img[i * h // TILES:(i + 1) * h // TILES,
                         j * w // TILES:(j + 1) * w // TILES])
            for i in range(TILES) for j in range(TILES)]
    arr = np.array(luts)
    spread = arr.max(axis=0) - arr.min(axis=0)
    print(f"\n  这 {len(luts)} 张表差别有多大:在输入 r={int(spread.argmax())} 处,"
          f"最亮的块和最暗的块把它映射到 {arr[:, spread.argmax()].min():.0f} 和 "
          f"{arr[:, spread.argmax()].max():.0f},差 {spread.max():.0f} 级")
    print("  同一个灰度值,在不同位置被映射到完全不同的地方 —— 这就是「自适应」三个字的含义,")
    print("  也是为什么 CLAHE 不再是点运算:结果取决于像素在哪儿,不只取决于它的值。")


# ---------------------------------------------------------------- 2
def demo_three_images() -> None:
    hr("2. 三张性格不同的图:结论不是「CLAHE 永远赢」")
    print(f"  {'图':<16s}{'做法':<12s}{'全局标准差':>11s}{'局部对比度':>11s}{'左右亮度差':>11s}")
    for name, note in (("moon.png", "整体灰蒙蒙"),
                       ("page.png", "左右受光不均"),
                       ("astronaut.png", "本来就正常")):
        img = load_gray(name)
        print(f"  ── {name}({note})")
        for label, v in (("原图", img), ("全局均衡化", eq(img)), ("CLAHE", clahe(img))):
            print(f"  {'':<16s}{label:<12s}{v.std():11.1f}{local_contrast(v):11.1f}"
                  f"{halves_gap(v):11.1f}")

    print("\n  怎么读这张表:")
    print("    moon —— 整体低对比度,两个都能救,全局均衡化下手更猛(标准差更高)")
    print("    page —— 全局均衡化把左右亮度差做得更糟,CLAHE 才压得下去")
    print("    astronaut —— 原图本来就跨满 0~255,全局均衡化提升有限还会翻噪声,")
    print("                 CLAHE 提的是局部对比度(细节),两者目标不一样")
    print("  ⚠️ 「左右亮度差」这一列只对 page.png 有意义 —— 另外两张本来就不是左右不均,")
    print("     那个数字上下浮动不说明好坏。指标要挑对图看。")
    print("\n  一句话:全局均衡化管「整张图的分布」,CLAHE 管「每一小片里看不看得清」。")


# ---------------------------------------------------------------- 3
def demo_global_vs_local_metric(img: npt.NDArray[np.uint8]) -> None:
    hr("3. 为什么必须看局部对比度 —— 全局标准差会骗人")
    print(f"  拿 astronaut.png(原图已经跨满 0~255)比:\n")
    print(f"  {'':<14s}{'全局标准差':>11s}{'局部对比度':>11s}")
    for label, v in (("原图", img), ("全局均衡化", eq(img)), ("CLAHE", clahe(img))):
        print(f"  {label:<14s}{v.std():11.1f}{local_contrast(v):11.1f}")
    print("\n  全局标准差:全局均衡化涨得多 —— 它就是奔着「把分布摊满」去的")
    print("  局部对比度:CLAHE 涨得多 —— 每块按自己的情况拉,暗角里的细节才浮出来")
    print("  两个指标各自回答不同的问题,别用一个数字下结论。")


# ---------------------------------------------------------------- 4
def demo_cost(img: npt.NDArray[np.uint8]) -> None:
    hr("4. 代价:噪声、灰阶、耗时")
    print(f"  {'':<14s}{'噪声放大':>10s}{'用到的灰阶':>12s}{'耗时':>10s}")
    for label, fn in (("全局均衡化", eq), ("CLAHE", clahe)):
        out = fn(img)
        t0 = time.perf_counter()
        for _ in range(20):
            fn(img)
        ms = (time.perf_counter() - t0) / 20 * 1000
        g = noise_gain(img, "eq" if label == "全局均衡化" else "clahe")
        print(f"  {label:<14s}{g:9.1f}×{used_levels(out):12d}{ms:9.2f} ms")
    print(f"  (原图用到 {used_levels(img)} 个灰阶;σ=3 的高斯噪声)")
    print("\n  全局均衡化便宜:两遍扫描,一张表,可以整帧向量化。")
    print("  CLAHE 贵在 64 次统计 + 双线性插值,但噪声被 clipLimit 摁住了 —— 这就是那点钱买的东西。")


# ---------------------------------------------------------------- 5
def demo_clahe_is_equalize_with_knobs(img: npt.NDArray[np.uint8]) -> None:
    hr("5. CLAHE 是「带旋钮的均衡化」")
    degenerate = clahe(img, clip=40.0, tiles=1)
    diff = int(np.abs(degenerate.astype(np.int64) - eq(img).astype(np.int64)).max())
    print(f"  tileGridSize=(1,1) + clipLimit=40 与 cv2.equalizeHist 最大差 {diff} 级")
    print("  → 不分块、不限幅,CLAHE 就是全局均衡化本身。两个旋钮都拧到底 = 退化。\n")

    print(f"  {'clipLimit':>10s}{'全局标准差':>12s}{'局部对比度':>12s}{'噪声放大':>11s}")
    for c in (1.0, 2.0, 4.0, 8.0, 40.0):
        v = clahe(img, clip=c)
        g = noise_gain(img, "clahe", 3.0, clip=c)
        print(f"  {c:10.1f}{v.std():12.1f}{local_contrast(v):12.1f}{g:10.1f}×")
    print("\n  clipLimit 越大越猛,噪声也越明显;2.0 是个稳妥起点。")
    print("  这正是全局均衡化欠缺的东西 —— 它幂等、没有力度可调,要么不做要么做满。")


# ---------------------------------------------------------------- 图板
def save_compare_figure(out_path: Path) -> None:
    """图板一:三张性格不同的图 × 原图 / 全局均衡化 / CLAHE。"""
    rows = (("moon.png", "整体灰蒙蒙"),
            ("page.png", "左右受光不均"),
            ("astronaut.png", "本来就正常"))
    fig, axes = plt.subplots(3, 3, figsize=(15, 13.5))
    for r, (name, note) in enumerate(rows):
        img = load_gray(name)
        for ax, (label, v) in zip(axes[r], (
                (f"{name}\n{note}", img),
                ("全局均衡化", eq(img)),
                (f"CLAHE(clip={CLIP}, {TILES}×{TILES})", clahe(img)))):
            ax.imshow(v, cmap="gray", vmin=0, vmax=255)
            ax.set_title(f"{label}\n全局 σ {v.std():.1f} / 局部对比度 {local_contrast(v):.1f}"
                         f" / 左右差 {halves_gap(v):.1f}", fontsize=9)
            ax.axis("off")
    fig.suptitle("全局均衡化 vs CLAHE:全局管分布,CLAHE 管每一小片看不看得清", fontsize=13)
    # 每格标题两行,不留行距会压住上一行的图
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.95), h_pad=2.5)
    fig.savefig(out_path, dpi=110)


def save_curves_figure(out_path: Path, img: npt.NDArray[np.uint8]) -> None:
    """图板二:1 张表 vs 64 张表、clipLimit 旋钮、三条直方图。"""
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.4))

    # (a) 表的数量
    ax = axes[0]
    h, w = img.shape
    for i in range(TILES):
        for j in range(TILES):
            lut = tile_lut(img[i * h // TILES:(i + 1) * h // TILES,
                               j * w // TILES:(j + 1) * w // TILES])
            ax.plot(LEVELS, lut, color="tab:orange", lw=0.6, alpha=0.45)
    ax.plot([], [], color="tab:orange", lw=1.2, label=f"CLAHE:{TILES * TILES} 张块内表")
    lut_eq = np.cumsum(np.bincount(img.ravel(), minlength=256)) / img.size * 255.0
    ax.plot(LEVELS, lut_eq, color="tab:blue", lw=2.4, label="全局均衡化:全图共 1 张表")
    ax.plot(LEVELS, LEVELS, "--", color="gray", lw=1.0, label="恒等")
    ax.set_xlim(0, 255); ax.set_ylim(0, 255); ax.set_aspect("equal")
    ax.set_xlabel("输入 r"); ax.set_ylabel("输出 s")
    ax.set_title("同一个灰度值,在不同块里去向完全不同\n这就是「自适应」,也是它不再是点运算的原因",
                 fontsize=10)
    ax.legend(fontsize=8, loc="lower right"); ax.grid(alpha=0.3)

    # (b) clipLimit 旋钮
    ax = axes[1]
    clips = [0.5, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 20.0, 40.0]
    outs = [clahe(img, clip=c) for c in clips]
    ax.plot(clips, [local_contrast(v) for v in outs], "o-", color="tab:orange",
            lw=1.8, ms=4, label="局部对比度")
    ax.axhline(local_contrast(eq(img)), color="tab:blue", ls="--", lw=1.4,
               label="全局均衡化(没有旋钮可拧)")
    ax.axhline(local_contrast(img), color="gray", ls=":", lw=1.2, label="原图")
    ax.axvline(CLIP, color="tab:red", lw=1.0, alpha=0.6)
    ax.annotate("默认 2.0", xy=(CLIP, local_contrast(outs[2])), xytext=(4.5, local_contrast(img)),
                fontsize=9, color="tab:red",
                arrowprops=dict(arrowstyle="->", color="tab:red", lw=1.0))
    ax.set_xscale("log"); ax.set_xticks(clips)
    ax.set_xticklabels([str(c) for c in clips], fontsize=7)
    ax.set_xlabel("clipLimit(对数轴)"); ax.set_ylabel("局部对比度")
    ax.set_title("CLAHE 有力度旋钮,均衡化没有\nclipLimit 越大越猛,噪声也跟着上来", fontsize=10)
    ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # (c) 三条直方图
    ax = axes[2]
    for label, v, color in (("原图", img, "gray"),
                            ("全局均衡化", eq(img), "tab:blue"),
                            ("CLAHE", clahe(img), "tab:orange")):
        ax.plot(LEVELS, np.bincount(v.ravel(), minlength=256), color=color, lw=1.2, label=label)
    ax.set_xlim(0, 255)
    ax.set_xlabel("灰度值"); ax.set_ylabel("像素数")
    ax.set_title("直方图:全局均衡化摊成梳齿状\nCLAHE 只是把峰压扁,形状还认得出来", fontsize=10)
    ax.legend(fontsize=8); ax.grid(alpha=0.3)

    fig.suptitle(f"两者的三处关键差别(主图 {'moon.png'})", fontsize=13)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.90), h_pad=2.0)
    fig.savefig(out_path, dpi=110)


def main() -> None:
    img = load_gray("moon.png")
    print(f"主图 moon.png  shape={img.shape}  标准差 {img.std():.1f}  "
          f"局部对比度 {local_contrast(img):.1f}")

    demo_one_table_vs_many(img)
    demo_three_images()
    demo_global_vs_local_metric(load_gray("astronaut.png"))
    demo_cost(img)
    demo_clahe_is_equalize_with_knobs(img)

    out = REPO / "Assets" / "results" / "equalize-vs-clahe-demo.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    save_compare_figure(out)
    print(f"\n结果已保存: {out.relative_to(REPO)}")

    curves = out.with_name("equalize-vs-clahe-curves.png")
    save_curves_figure(curves, img)
    print(f"结果已保存: {curves.relative_to(REPO)}")

    if "--show" in sys.argv:
        plt.show()


if __name__ == "__main__":
    main()
