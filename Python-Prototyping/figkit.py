"""文档配图的公共零件。

为什么单独抽出来:
    仓库约定每张配图都要成套回答四问(做了什么 / 得到什么 / 失去什么 / 局限在哪,
    见 Documents/README.md「写作约定」)。那条横幅的画法、中文字体设置、
    保存参数如果每个脚本各抄一份,改一次就要改七八处,迟早走样。

用法(配图脚本放在 Python-Prototyping/<章节目录>/ 下,所以要先把上一级加进 path):

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from figkit import OUT, IMAGES, save, four_questions, show_gray, use_cjk_font
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "Assets" / "results"
IMAGES = REPO / "Assets" / "test-images"


def use_cjk_font() -> None:
    """装上中文字体,并把负号改回 ASCII 的 '-'(默认那个 U+2212 很多字体没有)。

    没有 --show 时切 Agg:无窗口环境(CI、ssh)下 matplotlib 默认后端会直接报错。
    """
    if "--show" not in sys.argv:
        matplotlib.use("Agg")
    matplotlib.rcParams["font.family"] = ["Heiti TC", "Arial Unicode MS", "sans-serif"]
    matplotlib.rcParams["axes.unicode_minus"] = False


def save(fig, name: str) -> None:
    """存到 Assets/results/,并把路径打出来方便对照文档引用。"""
    import matplotlib.pyplot as plt

    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=130, bbox_inches="tight", facecolor="white")
    print(f"  → Assets/results/{name}")
    if "--show" not in sys.argv:
        plt.close(fig)


def show_gray(ax, data, title: str, vmin: float = 0, vmax: float = 255) -> None:
    """画灰度图。

    vmin/vmax 一律显式给 —— 不给的话 matplotlib 会拿这张图自己的 min/max
    去归一化,**悄悄替你拉一次对比度**,你看到的就不是数据本身了。
    """
    ax.imshow(data, cmap="gray", vmin=vmin, vmax=vmax, interpolation="nearest")
    ax.set_title(title, fontsize=10.5)
    ax.axis("off")


def four_questions(fig, did: str, gained: str, lost: str, limit: str, better: str,
                   y: float = 0.0, bottom: float = 0.03) -> None:
    """在图底部贴一条五色横幅,依次回答:
    做了什么 / 得到什么 / 失去什么 / 局限在哪 / 更好的做法。

    这是仓库硬约定(见 Documents/README.md「写作约定」):
    只看效果好的那一面最容易在工程里踩坑,代价和边界必须和收益画在同一张图里,
    不能分成两张。最后一格只**点名**更好的做法,不展开 ——
    读的人知道"还有路可走、该往哪儿查"就够了,展开会喧宾夺主。

    better 是必填的,不是可选项:写不出出路,通常说明「局限」那一格还没想清楚。

    bottom:带折线图的图要调大(0.15 左右),给 x 轴标签留位置,
           否则横幅会压在标签上。
    """
    cells = [("做了什么", did, "#eef3f8", "#2c6fbb"),
             ("得到什么", gained, "#eaf5ec", "#2a8f4a"),
             ("失去什么", lost, "#fdeeea", "#c4442a"),
             ("局限在哪", limit, "#fff6e5", "#a8700a"),
             ("更好的做法", better, "#f2eefb", "#6b4fa8")]
    fig.subplots_adjust(bottom=bottom)
    for i, (head, body, bg, fg) in enumerate(cells):
        # matplotlib 不认 Markdown,** 会被原样印出来,这里统一剥掉
        body = body.replace("**", "")
        fig.text(0.012 + i * 0.197, y, f"{head}\n{body}", fontsize=8.2, va="top", ha="left",
                 color="#222", linespacing=1.5,
                 bbox=dict(boxstyle="round,pad=0.4", fc=bg, ec=fg, lw=1.0))
