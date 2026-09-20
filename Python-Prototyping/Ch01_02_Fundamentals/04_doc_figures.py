"""给 01-fundamentals 那两篇补配图 —— LUT 和「取整与浮点」原先一张图都没有。

为什么要补:
    这两篇是后面每一篇的地基(从 3.2 起每篇都在说「建一张 LUT」),但通篇是文字
    加表格。「建表 → 查表」「截断会累积成偏置」「astype 会回绕」这三件事,
    看一眼图就懂,读三段文字反而容易走神。

生成 5 张(全部写到 Assets/results/):
    lut-how-it-works.png       LUT 三步:建表(只算 256 次)→ 表长什么样 → 全图查表
    lut-speedup.png            1080p 伽马校正的四种做法耗时对比(实测,不是写死的)
    lut-1d-vs-3d.png           1D LUT 为什么表达不了「通道互相影响」,3D LUT 怎么补
    rounding-truncation-drift.png  20 轮往返:截断 / 四舍五入 / 全程 float 的漂移
    rounding-wraparound.png    astype 取模回绕:300 → 44,过曝处长出黑斑

用法:
    .venv/bin/python Ch01_02_Fundamentals/04_doc_figures.py [--show]

注意:本脚本会覆盖上述 5 个文件,文档正文引用的就是它们。
耗时数字每次跑都会略有不同,改完记得同步文档里那张表。
"""

import sys
import time
from pathlib import Path

import cv2
import matplotlib

if "--show" not in sys.argv:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Rectangle

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "Assets" / "results"
IMAGES = REPO / "Assets" / "test-images"
matplotlib.rcParams["font.family"] = ["Heiti TC", "Arial Unicode MS", "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False

LEVELS = np.arange(256)
GAMMA = 1 / 2.2


def save(fig, name: str) -> None:
    fig.savefig(OUT / name, dpi=130, bbox_inches="tight", facecolor="white")
    print(f"  → Assets/results/{name}")
    if "--show" not in sys.argv:
        plt.close(fig)


def gamma_lut() -> np.ndarray:
    return np.clip(np.rint(255.0 * (LEVELS / 255.0) ** GAMMA), 0, 255).astype(np.uint8)


# ═══════════════════════════════════════════════════ 图 1:LUT 三步 ══════


def fig_how_it_works() -> None:
    """把「建表 → 表 → 查表」画成一条从左到右的流水线。

    要让人看明白的就一件事:公式只在最左边跑了 256 次,右边那几百万个像素
    走的是查表,一次算术都没有。
    """
    img = cv2.imread(str(IMAGES / "moon.png"), cv2.IMREAD_GRAYSCALE)
    lut = gamma_lut()
    out = lut[img]

    fig = plt.figure(figsize=(13, 4.4))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1.15, 1.5], wspace=0.32)

    # ── (a) 建表:曲线上只有 256 个点
    ax = fig.add_subplot(gs[0])
    ax.plot(LEVELS, lut, lw=2, color="#2c6fbb")
    step = LEVELS[::16]
    ax.plot(step, lut[step], "o", ms=4.5, color="#d95f02", zorder=3)
    ax.plot([0, 255], [0, 255], "--", lw=1, color="#999")
    ax.set_xlim(0, 255)
    ax.set_ylim(0, 255)
    ax.set_xlabel("输入 r(下标)")
    ax.set_ylabel("输出 s(表里的值)")
    ax.set_title("① 建表\n公式 $s=255(r/255)^{1/2.2}$ 只跑 256 次", fontsize=11)
    ax.text(130, 40, "虚线 = 什么都不做\n实线 = 这张表干的事",
            fontsize=9, color="#555", ha="center")

    # ── (b) 表本身:上色带是下标,下色带是表里的值
    ax = fig.add_subplot(gs[1])
    ax.imshow(LEVELS[None, :], cmap="gray", aspect="auto",
              extent=(0, 256, 1.15, 2.0), vmin=0, vmax=255)
    ax.imshow(lut[None, :], cmap="gray", aspect="auto",
              extent=(0, 256, 0.0, 0.85), vmin=0, vmax=255)
    for r in (0, 64, 128, 192, 255):
        ax.annotate("", xy=(r + 0.5, 0.88), xytext=(r + 0.5, 1.12),
                    arrowprops=dict(arrowstyle="-|>", lw=1.1, color="#d95f02"))
        ax.text(r + 0.5, 2.10, str(r), ha="center", fontsize=8.5, color="#333")
        ax.text(r + 0.5, -0.22, str(int(lut[r])), ha="center", fontsize=8.5, color="#d95f02")
    ax.text(128, 2.55, "下标:像素原来的值", ha="center", fontsize=10)
    ax.text(128, -0.62, "值:它应该变成什么", ha="center", fontsize=10, color="#d95f02")
    ax.set_xlim(-6, 262)
    ax.set_ylim(-0.95, 2.9)
    ax.axis("off")
    ax.set_title("② 这张表\n256 项,一共 256 字节", fontsize=11)

    # ── (c) 查表:一行代码走完全图
    ax = fig.add_subplot(gs[2])
    ax.axis("off")
    ax.set_title("③ 查表\n每个像素一次数组访问,没有算术", fontsize=11)
    ax.imshow(np.hstack([img, np.full((img.shape[0], 18), 255, np.uint8), out]),
              cmap="gray", vmin=0, vmax=255)
    h, w = img.shape
    ax.text(w / 2, h + 26, "原图", ha="center", fontsize=10)
    ax.text(w + 18 + w / 2, h + 26, "查完表", ha="center", fontsize=10)
    ax.text(w + 9, h / 2, "lut[img]", ha="center", va="center", fontsize=10,
            rotation=90, color="#d95f02",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#d95f02", lw=1))

    fig.suptitle("LUT 的全部内容:公式只算 256 次,剩下几百万个像素全靠查",
                 fontsize=13, y=1.04)
    save(fig, "lut-how-it-works.png")


# ═══════════════════════════════════════════════════ 图 2:快多少 ════════


def fig_speedup() -> None:
    """实测四种做法在 1080p 上的耗时。

    数字每次跑略有出入,所以图上直接打印本次实测值,不引用文档里的旧数。
    """
    rng = np.random.default_rng(0)
    img = rng.integers(0, 256, (1080, 1920), dtype=np.uint8)
    lut = gamma_lut()

    def bench(fn, rounds: int = 20) -> float:
        fn()                                   # 预热,把首次分配和缓存冷启动摘掉
        t0 = time.perf_counter()
        for _ in range(rounds):
            fn()
        return (time.perf_counter() - t0) / rounds * 1000

    ms = {
        "逐像素算 pow()\n(已经是 numpy 向量化)": bench(
            lambda: np.clip(np.rint(255.0 * (img / 255.0) ** GAMMA), 0, 255).astype(np.uint8)),
        "lut[img]\n(numpy 花式索引)": bench(lambda: lut[img]),
        "cv2.LUT(img, lut)\n(SIMD + L1 缓存)": bench(lambda: cv2.LUT(img, lut)),
        "建表本身\n(256 次 pow,一次性)": bench(lambda: gamma_lut(), rounds=200),
    }
    slowest = max(ms.values())
    build_key = next(k for k in ms if k.startswith("建表"))

    fig, ax = plt.subplots(figsize=(9.5, 3.8))
    names = list(ms)[::-1]
    vals = [ms[n] for n in names]
    colors = ["#999", "#2c6fbb", "#2c6fbb", "#c44"][::-1]
    bars = ax.barh(names, vals, color=colors, height=0.6)
    for bar, name, v in zip(bars, names, vals):
        # 建表不是「另一种做法」,是一次性开销,标倍数没有意义
        if name == build_key:
            note = f"{v:.3f} ms   只占查表耗时的 {v / ms['cv2.LUT(img, lut)\n(SIMD + L1 缓存)'] * 100:.0f}%"
        elif v == slowest:
            note = f"{v:.2f} ms"
        else:
            note = f"{v:.2f} ms   快 {slowest / v:.0f}×"
        ax.text(v + slowest * 0.015, bar.get_y() + bar.get_height() / 2,
                note, va="center", fontsize=10)
    ax.set_xlim(0, slowest * 1.32)
    ax.set_xlabel("耗时(毫秒,1920×1080 灰度图,20 次平均)")
    ax.set_title("同一个伽马校正,四种做法\n建表的开销小到可以忽略 —— 而且是一次性的",
                 fontsize=12)
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "lut-speedup.png")
    print("     本次实测:" + "  ".join(f"{k.splitlines()[0]}={v:.2f}ms" for k, v in ms.items()))


# ═══════════════════════════════════════════════════ 图 3:1D vs 3D ══════


def fig_1d_vs_3d() -> None:
    """1D LUT 的根本限制:输出的 R 只能由输入的 R 决定。

    左边画三条互不相干的曲线,右边画立方体网格 —— 一眼能看出
    「一条线」和「一个空间」的差别,以及为什么 3D LUT 非配插值不可。
    """
    fig = plt.figure(figsize=(12, 4.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.05], wspace=0.25)

    # ── 左:1D LUT × 3
    ax = fig.add_subplot(gs[0])
    for ch, color, g in [("R", "#d62728", 0.75), ("G", "#2ca02c", 1.0), ("B", "#1f77b4", 1.35)]:
        ax.plot(LEVELS, 255 * (LEVELS / 255) ** g, lw=2, color=color, label=f"{ch} 用的表")
    ax.set_xlim(0, 255)
    ax.set_ylim(0, 255)
    ax.legend(fontsize=9, loc="lower right")
    ax.set_xlabel("输入")
    ax.set_ylabel("输出")
    ax.set_title("1D LUT × 3:三条互不相干的曲线\n输出的 R 只看输入的 R,跟 G、B 无关",
                 fontsize=11)
    ax.text(12, 232, "表达不了「红一高就把绿压一点」这类联动",
            fontsize=9.5, color="#c44")

    # ── 右:3D LUT 的稀疏网格
    ax = fig.add_subplot(gs[1], projection="3d")
    n = 5                                        # 画 5³ 意思一下;实际常见 17³/33³/65³
    g = np.linspace(0, 1, n)
    G1, G2, G3 = np.meshgrid(g, g, g, indexing="ij")
    ax.scatter(G1, G2, G3, s=14, c=np.stack([G1, G2, G3], -1).reshape(-1, 3), depthshade=False)
    q = (0.62, 0.38, 0.55)                       # 一个落在格子中间的查询点
    ax.scatter(*q, s=150, marker="*", color="#d95f02", depthshade=False, zorder=5)
    ax.text(q[0] - 0.55, q[1], q[2] + 0.42, "想查的颜色落在格子中间\n→ 三线性插值",
            fontsize=9, color="#d95f02")
    ax.set_xlabel("R", labelpad=-8)
    ax.set_ylabel("G", labelpad=-8)
    ax.set_zlabel("B", labelpad=-8)
    ax.set_xticklabels([]); ax.set_yticklabels([]); ax.set_zticklabels([])
    ax.set_title("3D LUT:表从一条线变成一个立方体\n输入 3 个数、输出 3 个数,通道之间能互相影响",
                 fontsize=11)

    fig.suptitle("彩色图的两种查表方式", fontsize=13, y=1.02)
    save(fig, "lut-1d-vs-3d.png")


# ═══════════════════════════════════ 图 4:截断会攒成偏置 ═════════════════


def fig_truncation_drift() -> None:
    """20 轮「×1.1 再 ÷1.1」,理论上原样返回,实际三种做法分道扬镳。

    这张图要说的是方向,不是大小:截断的误差**永远同号**,所以是条一路向下的斜线;
    四舍五入正负抵消,曲线基本贴着 0;全程 float 则严格是 0。
    """
    base = np.arange(256, dtype=np.float64)
    rounds = 20
    trunc = base.copy()
    rint = base.copy()
    flt = base.copy()
    drift = {"每步截断落回 uint8": [], "每步四舍五入落回 uint8": [], "全程 float,最后落一次": []}

    for _ in range(rounds):
        trunc = np.clip(trunc * 1.1, 0, 255).astype(np.uint8)
        trunc = np.clip(trunc / 1.1, 0, 255).astype(np.uint8).astype(np.float64)
        rint = np.clip(np.rint(rint * 1.1), 0, 255).astype(np.uint8)
        rint = np.clip(np.rint(rint / 1.1), 0, 255).astype(np.uint8).astype(np.float64)
        flt = flt * 1.1 / 1.1
        drift["每步截断落回 uint8"].append((trunc - base).mean())
        drift["每步四舍五入落回 uint8"].append((rint - base).mean())
        drift["全程 float,最后落一次"].append(
            (np.clip(np.rint(flt), 0, 255).astype(np.uint8).astype(np.float64) - base).mean())

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(12, 4.2),
                                  gridspec_kw={"width_ratios": [1.25, 1], "wspace": 0.28})
    x = np.arange(1, rounds + 1)
    for (label, ys), color, style in zip(drift.items(),
                                         ["#c44", "#d95f02", "#2c6fbb"], ["-", "-", "-"]):
        ax.plot(x, ys, style, lw=2, color=color, marker="o", ms=3.5, label=label)
        ax.annotate(f"{ys[-1]:+.2f}", (x[-1], ys[-1]), textcoords="offset points",
                    xytext=(6, -3), fontsize=9.5, color=color)
    ax.axhline(0, color="#999", lw=1, ls="--")
    ax.set_xlabel("做了几轮「×1.1 再 ÷1.1」")
    ax.set_ylabel("整图平均偏移(灰阶)")
    ax.set_xlim(0.5, rounds + 2.6)
    ax.legend(fontsize=9, loc="lower left")
    ax.set_title("误差的方向比大小要命\n截断永远少一点点,20 轮攒成肉眼可见的发暗", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)

    # ── 右:一步之内误差的分布,解释上面那条斜线为什么一路向下
    rng = np.random.default_rng(1)
    vals = rng.uniform(0, 255, 200_000)
    ax2.hist(np.floor(vals) - vals, bins=60, color="#c44", alpha=0.75, label="截断")
    ax2.hist(np.rint(vals) - vals, bins=60, color="#2c6fbb", alpha=0.6, label="四舍五入")
    ax2.axvline(0, color="#333", lw=1)
    ax2.set_xlabel("单次取整的误差(灰阶)")
    ax2.set_ylabel("像素个数")
    ax2.legend(fontsize=9)
    ax2.set_title("为什么会一路向下\n截断的误差全落在 0 左边,平均 −0.5;四舍五入正负各一半",
                  fontsize=11)
    ax2.spines[["top", "right"]].set_visible(False)

    save(fig, "rounding-truncation-drift.png")
    for k, v in drift.items():
        print(f"     {k}: 20 轮后平均偏移 {v[-1]:+.2f}")


# ═══════════════════════════════════ 图 5:回绕 ═══════════════════════════


def fig_wraparound() -> None:
    """astype 对越界值取模,300 → 44。过曝处不是变白,是长出黑斑。"""
    img = cv2.imread(str(IMAGES / "moon.png"), cv2.IMREAD_GRAYSCALE)
    boosted = img.astype(np.int16) + 120
    wrapped = boosted.astype(np.uint8)                       # 回绕:越界取模
    saturated = np.clip(boosted, 0, 255).astype(np.uint8)    # 饱和:夹回边界

    fig = plt.figure(figsize=(12.5, 4.5))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 1, 1], wspace=0.2)

    # ── 左:输入 → 输出的折线,锯齿一眼可见
    ax = fig.add_subplot(gs[0])
    v = np.arange(-60, 460)
    ax.plot(v, np.mod(v, 256), lw=2, color="#c44", label="astype:取模回绕")
    ax.plot(v, np.clip(v, 0, 255), lw=2, color="#2c6fbb", ls="--", label="clip 之后:饱和")
    ax.plot([300], [44], "o", ms=8, color="#c44", zorder=4)
    ax.annotate("300 → 44", (300, 44), textcoords="offset points", xytext=(10, 14),
                fontsize=10, color="#c44",
                arrowprops=dict(arrowstyle="->", color="#c44"))
    ax.set_xlabel("算出来的值(可能越界)")
    ax.set_ylabel("落回 uint8 之后")
    ax.legend(fontsize=9, loc="upper left")
    ax.set_title("越界了会怎样\nnumpy 取模,不是夹到边界", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)

    for i, (data, title) in enumerate([
            (wrapped, f"直接 astype:整体 +120\n过曝处翻黑,{(boosted > 255).mean():.1%} 的像素中招"),
            (saturated, "先 clip 再 astype\n过曝处顶格变白,符合直觉")]):
        ax = fig.add_subplot(gs[i + 1])
        ax.imshow(data, cmap="gray", vmin=0, vmax=255)
        ax.set_title(title, fontsize=11)
        ax.axis("off")

    fig.suptitle("clip 一定要在 astype 之前 —— 顺序反了就救不回来", fontsize=13, y=1.02)
    save(fig, "rounding-wraparound.png")
    print(f"     越界像素占比 {(boosted > 255).mean():.1%}")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    print("LUT:")
    fig_how_it_works()
    fig_speedup()
    fig_1d_vs_3d()
    print("取整与浮点:")
    fig_truncation_drift()
    fig_wraparound()
    if "--show" in sys.argv:
        plt.show()
