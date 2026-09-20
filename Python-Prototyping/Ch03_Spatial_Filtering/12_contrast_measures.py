"""对比度的三种度量方式对照 —— 配合 Documents/03-histogram/03-contrast.md。

  1. 亮度和对比度是两件独立的事:加法改亮度,乘法改对比度
  2. max-min 的致命弱点:两个极端像素就能骗过它
  3. 三种度量在真实照片上的表现
  4. 自动色阶为什么要故意扔掉 1%

同时把上面四条画成 3 张配图(文档正文引用的就是它们),按仓库约定
每张成套回答四问:做了什么 / 得到什么 / 失去什么 / 局限在哪。
数字和图出自同一次计算,不会对不上。

    contrast-brightness-vs-contrast.png  加法改亮度、乘法改对比度,互不干扰
    contrast-metrics-fooled.png          两个像素就能骗过 max−min
    contrast-autolevels.png              自动色阶为什么扔掉 1%

用法:
    .venv/bin/python Ch03_Spatial_Filtering/12_contrast_measures.py [--show]
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import IMAGES, four_questions, save, show_gray, use_cjk_font  # noqa: E402

use_cjk_font()
import cv2  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
SRC = IMAGES / "astronaut.png"


def hr(title: str) -> None:
    print(f"\n{'=' * 64}\n{title}\n{'=' * 64}")


def span(v: np.ndarray) -> float:
    """跨度:最亮减最暗。最直觉,但一个坏点就毁掉它。"""
    return float(v.max() - v.min())


def rms_contrast(v: np.ndarray) -> float:
    """RMS 对比度:亮度的标准差。每个像素都参与,极端值被稀释。"""
    return float(v.std())


def percentile_span(v: np.ndarray, lo: float = 1.0, hi: float = 99.0) -> float:
    """百分位跨度:扔掉最极端的那一小撮再算。工程上最实用。"""
    a, b = np.percentile(v, [lo, hi])
    return float(b - a)


def report(name: str, v: np.ndarray) -> None:
    print(f"  {name:22s} 跨度={span(v):6.1f}   标准差={rms_contrast(v):6.2f}   "
          f"1~99%跨度={percentile_span(v):6.1f}")


# ---------------------------------------------------------------- 1
def demo_brightness_vs_contrast() -> None:
    hr("1. 亮度和对比度是两件独立的事")
    a = np.array([100.0, 110, 120, 130, 140])  # 挤在中间
    b = np.array([20.0, 70, 120, 170, 220])    # 铺得开

    for name, v in (("A 低对比度", a), ("B 高对比度", b)):
        vals = str(v.astype(int).tolist())
        print(f"  {name}: {vals:26s}  平均={v.mean():.0f}  "
              f"跨度={span(v):.0f}  标准差={v.std():.1f}")

    print("\n  → 平均值都是 120(一样亮),但 B 的差距是 A 的 5 倍\n")

    plus = a + 100                      # 加法
    times = (a - 120) * 5 + 120         # 乘法(以 120 为中心)
    print(f"  A 整体 +100      : {plus.astype(int).tolist()}"
          f"  平均={plus.mean():.0f}  跨度={span(plus):.0f}  标准差={plus.std():.1f}")
    print(f"  A 以120为中心 ×5 : {times.astype(int).tolist()}"
          f"  平均={times.mean():.0f}  跨度={span(times):.0f}  标准差={times.std():.1f}")
    print("\n  → 加法只动平均值(亮度),乘法只动跨度(对比度)。互不干扰。")


# ---------------------------------------------------------------- 2
def demo_outlier_breaks_span() -> None:
    hr("2. max-min 的致命弱点:两个像素就能骗过它")
    n = 10000
    fake = np.full(n, 120.0)     # 一整块均匀的灰板
    fake[0], fake[1] = 0, 255    # 只掺 2 个极端像素(占 0.02%)
    real = np.linspace(0, 255, n)

    report("纯灰 + 2个极端点", fake)
    report("真·高对比度渐变", real)
    report("纯灰(无极端点)", np.full(n, 120.0))

    print("\n  → 跨度对前两者都报 255,完全分不出来")
    print("  → 标准差 1.81 vs 73.62,差 40 倍;1~99% 跨度 0.0 vs 249.9,判断正确")


# ---------------------------------------------------------------- 3
def demo_real_photo() -> None:
    hr("3. 真实照片:原图 / 压低对比度 / 拉高对比度")
    g = cv2.imread(str(SRC), cv2.IMREAD_GRAYSCALE).astype(float)
    mean = g.mean()
    for name, a in (("原图 (a=1.0)", 1.0), ("压低 (a=0.4)", 0.4), ("拉高 (a=2.0)", 2.0)):
        v = np.clip((g - mean) * a + mean, 0, 255)
        report(name, v)
    print("\n  注意 a=2.0 那行:跨度还是 255(本来就顶满),")
    print("  但标准差明显变大 —— 只有标准差反映出了真实变化。")


# ---------------------------------------------------------------- 4
def demo_autolevels() -> None:
    hr("4. 自动色阶为什么要故意扔掉 1%")
    # 造一张真实场景:隔着雾/玻璃拍的低对比度照片,再掺一个镜面反光坏点
    g = cv2.imread(str(SRC), cv2.IMREAD_GRAYSCALE).astype(float)
    hazy = g * 0.3 + 90          # 压成 90~166 的窄区间,灰蒙蒙
    hazy[0, 0] = 255             # 一个反光高光
    hazy[0, 1] = 0               # 一个暗坏点

    naive = (hazy - hazy.min()) / (hazy.max() - hazy.min()) * 255
    lo, hi = np.percentile(hazy, [0.5, 99.5])
    smart = np.clip((hazy - lo) / (hi - lo) * 255, 0, 255)

    report("原图(灰蒙蒙+坏点)", hazy)
    report("按 min/max 拉伸", naive)
    report("按 0.5~99.5% 拉伸", smart)
    print(f"\n  min/max 方案:坏点已经占住 0 和 255,算法以为'已经铺满了',白做一场")
    print(f"    标准差 {hazy.std():.2f} → {naive.std():.2f}(几乎没变)")
    print(f"  百分位方案:坏点被当成那 1% 扔掉,真正把有效区间铺开")
    print(f"    标准差 {hazy.std():.2f} → {smart.std():.2f}(涨了 {smart.std()/hazy.std():.1f} 倍)")


# ================================================================ 配图 ====


def fig_brightness_vs_contrast() -> None:
    """加法只动平均值,乘法只动跨度 —— 在五个点上看,再在真实照片上看。"""
    a = np.array([100.0, 110, 120, 130, 140])
    plus = a + 100
    times = (a - 120) * 5 + 120
    g = cv2.imread(str(SRC), cv2.IMREAD_GRAYSCALE).astype(float)
    m = g.mean()
    bright = np.clip(g + 60, 0, 255)                 # 加法
    contrast = np.clip((g - m) * 1.8 + m, 0, 255)    # 乘法

    fig = plt.figure(figsize=(13.4, 4.4))
    gs = fig.add_gridspec(1, 5, width_ratios=[1.35, 1, 1, 1, 1.3], wspace=0.26)

    ax = fig.add_subplot(gs[0])
    for y, (v, label, color) in enumerate([(a, "原始", "#999"),
                                           (plus, "+100(加法)", "#2c6fbb"),
                                           (times, "×5(乘法,以 120 为心)", "#c4442a")]):
        ax.scatter(v, [y] * len(v), s=90, color=color, zorder=3)
        ax.plot([v.min(), v.max()], [y, y], color=color, lw=1.4, alpha=0.5)
        ax.scatter([v.mean()], [y], s=180, marker="|", color="#222", zorder=4)
        ax.text(262, y, f"{label}\n平均 {v.mean():.0f} · 跨度 {span(v):.0f}",
                fontsize=8.6, va="center", color=color)
    ax.set_yticks([]); ax.set_xlim(-8, 262); ax.set_ylim(-0.6, 2.6)
    ax.set_xlabel("亮度值")
    ax.set_title("五个像素,两种操作\n竖线 = 平均值", fontsize=10.5)
    ax.spines[["top", "right", "left"]].set_visible(False)

    for i, (data, title) in enumerate([
            (g, f"原图\n平均 {g.mean():.0f} · σ {g.std():.1f}"),
            (bright, f"+60(加法)\n平均 {bright.mean():.0f} ↑ · σ {bright.std():.1f}"),
            (contrast, f"×1.8(乘法)\n平均 {contrast.mean():.0f} · σ {contrast.std():.1f} ↑")]):
        show_gray(fig.add_subplot(gs[i + 1]), data, title)

    ax = fig.add_subplot(gs[4])
    for data, label, color in [(g, "原图", "#999"), (bright, "+60", "#2c6fbb"),
                               (contrast, "×1.8", "#c4442a")]:
        ax.hist(data.ravel(), bins=128, range=(0, 255), histtype="step", lw=1.8,
                color=color, label=label)
    ax.set_xlim(0, 255); ax.set_xlabel("亮度"); ax.set_ylabel("像素数")
    ax.legend(fontsize=8.6)
    ax.set_title("直方图:一个整体右移\n一个原地摊开", fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)

    fig.suptitle("加法改亮度,乘法改对比度 —— 这就是 s = a·r + b 里两个旋钮的分工",
                 fontsize=13, y=1.03)
    four_questions(fig,
        "对每个像素做 s = a·r + b。\nb 是加法项,a 是乘法项。",
        f"两个旋钮互不干扰:\n+60 只把平均从 {g.mean():.0f} 推到 {bright.mean():.0f},\n"
        f"σ 几乎不动;×1.8 平均不动,\nσ 从 {g.std():.1f} 涨到 {contrast.std():.1f}。",
        "两头都会被削平。\n"
        f"×1.8 之后有 {(((g - m) * 1.8 + m) > 255).mean() * 100:.1f}% 的像素\n"
        f"顶到 255、{(((g - m) * 1.8 + m) < 0).mean() * 100:.1f}% 掉到 0,\n"
        "那部分层次是**真的没了**,\n调回去也救不回来。",
        "它是条直线,做不到\n「暗部陡、亮部平」——\n想分区间区别对待得用\n分段线性或伽马;\n想让图自己决定力度\n得用直方图均衡化。",
        y=-0.03, bottom=0.14)
    save(fig, "contrast-brightness-vs-contrast.png")


def fig_metrics_fooled() -> None:
    """两个像素就能让 max−min 彻底瞎掉。"""
    n = 10000
    side = 100
    fake = np.full(n, 120.0); fake[0], fake[1] = 0, 255
    real = np.linspace(0, 255, n)
    plain = np.full(n, 120.0)
    sets = [("纯灰 + 2 个极端点\n(占 0.02%)", fake), ("真·高对比度渐变", real), ("纯灰(无极端点)", plain)]

    fig = plt.figure(figsize=(13.4, 4.4))
    gs = fig.add_gridspec(1, 4, width_ratios=[1, 1, 1, 1.5], wspace=0.24)
    for i, (title, v) in enumerate(sets):
        show_gray(fig.add_subplot(gs[i]), v.reshape(side, side),
                  f"{title}\n跨度 {span(v):.0f} · σ {rms_contrast(v):.2f} · "
                  f"1~99% {percentile_span(v):.1f}")

    ax = fig.add_subplot(gs[3])
    labels = ["跨度\nmax−min", "标准差\nRMS", "1~99%\n百分位跨度"]
    x = np.arange(3)
    for j, (title, v) in enumerate(sets):
        vals = [span(v), rms_contrast(v), percentile_span(v)]
        ax.bar(x + (j - 1) * 0.27, vals, 0.27,
               color=["#c4442a", "#2c6fbb", "#999"][j], label=title.split("\n")[0])
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("度量值")
    ax.legend(fontsize=8.4)
    ax.set_title("同一批数据,三种度量\n第一组柱子里,前两张图一模一样", fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)

    fig.suptitle("max − min 会被两个像素骗过 —— 所以工程上根本不用它", fontsize=13, y=1.03)
    four_questions(fig,
        "换一种统计口径:\n标准差让**每个像素**都参与;\n百分位跨度先把最极端的\n那一小撮扔掉再算。",
        f"骗不过去了。同样两张图,\n跨度都报 255 分不出来,\n"
        f"标准差 {rms_contrast(fake):.2f} vs {rms_contrast(real):.2f}(差 40 倍),\n"
        f"百分位跨度 {percentile_span(fake):.1f} vs {percentile_span(real):.1f}。",
        "标准差对**分布形状**不敏感:\n双峰和均匀分布可能\n算出同一个标准差。\n百分位跨度则要你\n自己选一个阈值。",
        "这三个量的都是\n「全图整体拉得开不开」。\n一张左暗右亮的图\n整体标准差可能很大,\n但每个局部都灰蒙蒙 ——\n那要用局部对比度去量。",
        y=-0.03, bottom=0.12)
    save(fig, "contrast-metrics-fooled.png")


def fig_autolevels() -> None:
    """一个太阳的反光就能让自动增强整个失效。"""
    g = cv2.imread(str(SRC), cv2.IMREAD_GRAYSCALE).astype(float)
    hazy = g * 0.3 + 90
    hazy[0, 0] = 255
    hazy[0, 1] = 0
    naive = (hazy - hazy.min()) / (hazy.max() - hazy.min()) * 255
    lo, hi = np.percentile(hazy, [0.5, 99.5])
    smart = np.clip((hazy - lo) / (hi - lo) * 255, 0, 255)
    clipped = ((hazy < lo) | (hazy > hi)).mean()

    fig = plt.figure(figsize=(13.4, 4.4))
    gs = fig.add_gridspec(1, 4, width_ratios=[1, 1, 1, 1.5], wspace=0.24)
    show_gray(fig.add_subplot(gs[0]), hazy, f"原图:灰蒙蒙 + 2 个坏点\nσ {hazy.std():.2f}")
    show_gray(fig.add_subplot(gs[1]), naive,
              f"按 min/max 拉伸\nσ {naive.std():.2f} —— 等于没做")
    show_gray(fig.add_subplot(gs[2]), smart,
              f"按 0.5~99.5% 拉伸\nσ {smart.std():.2f} —— 涨了 {smart.std() / hazy.std():.1f} 倍")

    ax = fig.add_subplot(gs[3])
    ax.hist(hazy.ravel(), bins=256, range=(0, 255), color="#999", label="原图")
    ax.hist(smart.ravel(), bins=256, range=(0, 255), color="#2c6fbb", alpha=0.6,
            label="百分位拉伸后")
    ax.axvline(lo, color="#c4442a", ls="--", lw=1.4)
    ax.axvline(hi, color="#c4442a", ls="--", lw=1.4)
    ax.text(hi + 3, ax.get_ylim()[1] * 0.75, f"P0.5={lo:.0f}\nP99.5={hi:.0f}",
            fontsize=8.6, color="#c4442a")
    ax.set_xlim(0, 255); ax.set_xlabel("亮度"); ax.set_ylabel("像素数")
    ax.legend(fontsize=8.6)
    ax.set_title("原图那一坨全挤在 90~166\n而 0 和 255 上各趴着一个坏点", fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)

    fig.suptitle("自动色阶为什么要故意扔掉 1%", fontsize=13, y=1.03)
    four_questions(fig,
        "不找 min/max,改找\n第 0.5% 和 99.5% 分位,\n把这两个值拉到 0 和 255,\n超出的直接裁掉。",
        f"σ {hazy.std():.2f} → {smart.std():.2f},\n涨了 {smart.std() / hazy.std():.1f} 倍。\n"
        "而 min/max 方案纹丝不动 ——\n坏点已经占住 0 和 255,\n算法以为「已经铺满了」。",
        f"真的裁掉了 {clipped * 100:.1f}% 的像素。\n"
        "被裁的那部分变成死黑或死白,\n层次不可恢复。反光、镜面、\n真实的高光细节也会一起没。",
        "阈值得看图选。0.5% 对\n普通照片合适;星空、\n医学影像这类「极端值\n本身就是信息」的图,\n扔 0.5% 可能正好把\n要找的目标扔了。",
        y=-0.03, bottom=0.12)
    save(fig, "contrast-autolevels.png")


if __name__ == "__main__":
    for fn in (demo_brightness_vs_contrast, demo_outlier_breaks_span,
               demo_real_photo, demo_autolevels):
        fn()
    print()
    for fn in (fig_brightness_vs_contrast, fig_metrics_fooled, fig_autolevels):
        fn()
    if "--show" in sys.argv:
        plt.show()
