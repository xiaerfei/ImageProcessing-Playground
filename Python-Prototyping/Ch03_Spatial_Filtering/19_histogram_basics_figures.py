"""给 03-histogram/01-histogram-basics.md 补配图 —— 全篇讲了三个概念,却只有一张图。

为什么要补:
    「直方图 / PDF / CDF 是同一批数字的三种写法」这句话,用表格讲要来回对照三遍,
    画成三格一眼就懂。而「横轴在哪个域」那节更是非画不可 ——
    同一批像素在两个域里画出来的直方图形状完全是两回事,光看中位数的数字没有冲击力。

生成 2 张(全部写到 Assets/results/):
    histogram-three-forms.png  直方图怎么数出来的 → PDF → CDF,以及「柱子高 = 增益大」那条链子
    histogram-which-domain.png 同一批像素,线性域和 gamma 域画出来的直方图差多远

用法:
    .venv/bin/python Ch03_Spatial_Filtering/19_histogram_basics_figures.py [--show]
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import IMAGES, four_questions, save, show_gray, use_cjk_font  # noqa: E402

use_cjk_font()
import cv2  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402


def to_linear(c):
    """sRGB 编码值(0~1)→ 线性光。和 Ch06 那两个脚本用的是同一套分段函数。"""
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(v):
    return np.where(v <= 0.0031308, v * 12.92, 1.055 * np.maximum(v, 0) ** (1 / 2.4) - 0.055)


# ═══════════════════════════════ 图 1:三种形态 ═════════════════════════


def fig_three_forms() -> None:
    """直方图 → PDF → CDF,用文档里那张 8 灰度级、100 像素的小图,数字能对上。

    第四格是全章的枢纽:柱子高 → CDF 涨得陡 → 映射表斜率大 → 对比度增益大。
    后面 CLAHE 的 clipLimit 削的就是这条链子的最左端。
    """
    counts = np.array([0, 0, 5, 30, 40, 20, 5, 0], np.int64)
    L, N = len(counts), int(counts.sum())
    pdf = counts / N
    cdf = np.cumsum(pdf)
    x = np.arange(L)

    fig = plt.figure(figsize=(13.4, 4.2))
    gs = fig.add_gridspec(1, 4, wspace=0.32)

    ax = fig.add_subplot(gs[0])
    ax.bar(x, counts, 0.66, color="#777")
    for r, c in zip(x, counts):
        if c:
            ax.text(r, c + 1.2, str(c), ha="center", fontsize=8.6)
    ax.set_xlabel("灰度"); ax.set_ylabel("有几个像素")
    ax.set_ylim(0, 48)
    ax.set_title(f"① 直方图\n准备 {L} 个桶,数一遍({N} 个像素)", fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)

    ax = fig.add_subplot(gs[1])
    ax.bar(x, pdf * 100, 0.66, color="#2c6fbb")
    ax.set_xlabel("灰度"); ax.set_ylabel("占全图的百分之几")
    ax.set_ylim(0, 48)
    ax.set_title(f"② PDF\n每个数除以 {N} —— 这一步就叫归一化", fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.annotate("", xy=(-0.12, 0.5), xytext=(-0.42, 0.5), xycoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", lw=1.6, color="#c4442a"))

    ax = fig.add_subplot(gs[2])
    ax.step(x, cdf, where="mid", lw=2, color="#2a8f4a")
    ax.plot(x, cdf, "o", color="#2a8f4a", ms=5)
    for r in (3, 4, 5):
        ax.annotate(f"{cdf[r]:.2f}", (r, cdf[r]), textcoords="offset points",
                    xytext=(-2, 8), ha="center", fontsize=8.4, color="#2a8f4a")
    ax.set_xlabel("灰度"); ax.set_ylabel("累计比例")
    ax.set_ylim(-0.05, 1.15)
    ax.set_title("③ CDF\n从左往右一个个加起来", fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.annotate("", xy=(-0.12, 0.5), xytext=(-0.42, 0.5), xycoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", lw=1.6, color="#c4442a"))

    # ── 第四格:那条链子
    ax = fig.add_subplot(gs[3]); ax.axis("off")
    ax.set_title("为什么非要认识 CDF", fontsize=10.5)
    ax.text(0.5, 0.96,
            "CDF 是 PDF 的累加,\n反过来 PDF 是 CDF 的斜率。\n\n"
            "于是有了这条链子:\n\n"
            "  某段灰度像素多\n"
            "        ↓\n"
            "  PDF 那里高\n"
            "        ↓\n"
            "  CDF 那里涨得陡\n"
            "        ↓\n"
            "  映射表斜率大\n"
            "        ↓\n"
            "  那段的对比度增益大\n\n"
            "CLAHE 的 clipLimit\n削的就是最左端(柱子高度),\n管的是最右端(增益上限)。",
            ha="center", va="top", fontsize=9.2, linespacing=1.55,
            bbox=dict(boxstyle="round,pad=0.5", fc="#eef3f8", ec="#2c6fbb"))

    fig.suptitle("直方图 / PDF / CDF —— 同一批数字的三种写法,你已经会前两种了",
                 fontsize=13, y=1.03)
    four_questions(fig,
        "数一遍每个灰度有几个\n像素(①),除以总数(②),\n再逐项累加(③)。",
        "一张几百万像素的图\n被压成 256 个数,\n而且和图多大无关 ——\n归一化之后能跨尺寸比较。",
        "**全部空间信息**。\n哪个像素在哪儿、\n谁挨着谁,一点都不剩。\n打乱像素后直方图逐桶相同。",
        "所以任何基于直方图的\n算法都**看不见结构** ——\n分不出天空和人脸,\n也分不出纹理和噪声。",
        "要保留位置就别只看\n全图一张直方图:分块统计\n(CLAHE)、局部统计量\n(均值/方差图),或者\n干脆换成看邻居的空间滤波。",
        y=-0.03, bottom=0.14)
    save(fig, "histogram-three-forms.png")
    print(f"     小图:counts={counts.tolist()}  PDF={np.round(pdf, 2).tolist()}  "
          f"CDF={np.round(cdf, 2).tolist()}")


# ═══════════════════════════════ 图 2:哪个域 ═══════════════════════════


def fig_which_domain() -> None:
    """同一批像素,在线性光域和 sRGB 编码域各画一次直方图。

    数字要和文档那张表对上:线性域中位数 0.053、最暗 1/16 区间占 54.2%;
    sRGB 域中位数 0.255、最暗区间占 13.5%。
    """
    # 和 15_histogram_deep_dive.py 的 demo_which_domain() 用**同一个分布同一个种子**,
    # 否则图上的数字会和文档那张表对不上(我第一版随手换了分布,13.5% 变成了 5.2%)。
    rng = np.random.default_rng(2)
    lin = rng.beta(0.6, 6.0, 500_000)      # 线性反射率,自然场景常态:大量暗像素
    srgb = to_srgb(lin)

    def stats(v):
        first16 = (v < 1 / 16).mean()
        return np.median(v), first16

    m_lin, f_lin = stats(lin)
    m_srgb, f_srgb = stats(srgb)

    fig = plt.figure(figsize=(13.4, 4.4))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1.15], wspace=0.28)

    for i, (v, name, color, m, f) in enumerate([
            (lin, "线性光域(真实光强)", "#c4442a", m_lin, f_lin),
            (srgb, "sRGB 编码域(你看到的直方图)", "#2c6fbb", m_srgb, f_srgb)]):
        ax = fig.add_subplot(gs[i])
        ax.hist(v, bins=64, range=(0, 1), color=color)
        ax.axvline(m, color="#222", ls="--", lw=1.4)
        ax.axvspan(0, 1 / 16, color="#000", alpha=0.10)
        ax.text(m + 0.02, ax.get_ylim()[1] * 0.85, f"中位数 {m:.3f}", fontsize=9)
        ax.text(1 / 16 + 0.02, ax.get_ylim()[1] * 0.6,
                f"最暗的 1/16 区间\n塞了 {f:.1%} 的像素", fontsize=8.8, color="#333")
        ax.set_xlabel("值"); ax.set_ylabel("像素数")
        ax.set_title(name, fontsize=10.5)
        ax.spines[["top", "right"]].set_visible(False)

    # ── 右:一句话判据
    ax = fig.add_subplot(gs[2]); ax.axis("off")
    ax.set_title("怎么判断该用哪个域", fontsize=10.5)
    ax.text(0.5, 0.97,
            "同一批像素,同一张照片,\n画出来完全是两回事。\n\n"
            "gamma 编码把暗部那一大坨\n「撑开」了 —— 这正是它的设计目的。\n\n"
            "───────────────\n\n"
            "只要你要做「加法」或「平均」\n"
            "(曝光融合、缩放、模糊)\n"
            "→ 先转回线性域\n\n"
            "只要你是在「迎合人眼」\n"
            "(增强、均衡化、调曲线)\n"
            "→ 留在 gamma 域\n\n"
            "───────────────\n\n"
            "好消息:后者是常态,\n所以平时不用特意做什么。",
            ha="center", va="top", fontsize=9.2, linespacing=1.5,
            bbox=dict(boxstyle="round,pad=0.5", fc="#fff6e5", ec="#a8700a"))

    fig.suptitle("一个没人明说的隐藏前提:你的直方图画在哪个域", fontsize=13, y=1.03)
    four_questions(fig,
        "存图前先做 gamma 编码,\n于是直方图的横轴\n是「编码值」,不是光强。",
        "256 个格子花在了\n人眼最挑剔的暗部。\n看曝光、做增强时,\n这个域天然贴合视觉。",
        f"横轴不再正比于光强。\n编码值 128 对应的光强\n只有满格的 21.6% ——\n"
        "「128 是一半亮」是错觉。",
        f"在这个域里做加法和平均\n**在物理上是错的**。\n缩小图片时最常见:\n"
        "大部分软件直接在编码域\n平均,结果**偏暗一点点**。",
        "要物理正确:先转线性、\n算完再编码回来。\nPhotoshop 有「以线性方式\n混合颜色」的开关,\n渲染和合成软件内部\n本来就全程线性。",
        y=-0.03, bottom=0.14)
    save(fig, "histogram-which-domain.png")
    print(f"     线性域 中位数 {m_lin:.3f},最暗 1/16 占 {f_lin:.1%};"
          f"sRGB 域 中位数 {m_srgb:.3f},占 {f_srgb:.1%}")


if __name__ == "__main__":
    fig_three_forms()
    fig_which_domain()
    if "--show" in sys.argv:
        plt.show()
