"""37《理解卷积》(馒头比喻)的配图 —— 配合 Documents/数学基础/快速路线/1.理解卷积.md。

三张图,数字与 36_fast_route_checks.py 第 6 块一致:
 1. conv-shift-add.png   错位相加:每一口的响应各自错开时间,再叠起来
 2. conv-flip-slide.png  翻转滑动:馒头序列翻成 (2,1),在消化序列上一格一格滑
 3. conv-image.png       换成图像:一个亮点被核摊开成核的形状;两个亮点 = 两份核叠加;台阶被抹成斜坡

用法:
    .venv/bin/python Ch04_Frequency_Domain/37_conv_figures.py
会在 Documents/数学基础/快速路线/images/ 下生成三张 png
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import four_questions, use_cjk_font  # noqa: E402

use_cjk_font()
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "Documents" / "数学基础" / "快速路线" / "images"
H = np.array([1, 0.9, 0.5, 0.3, 0])  # 消化序列
X = np.array([1, 2])                 # 馒头序列
Y = np.convolve(X, H)                # (1, 2.9, 2.3, 1.3, 0.6, 0)
BLUE, ORA, GREEN, GRAY = "#2c6fbb", "#d98a14", "#2a8f4a", "#666"


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=130, bbox_inches="tight", facecolor="white")
    print(f"  → Documents/数学基础/快速路线/images/{name}")
    plt.close(fig)


def fmt(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".") if v != int(v) else f"{int(v)}"


# ---------------------------------------------------------------- 1
def fig_shift_add() -> None:
    t = np.arange(1, 7)
    r1 = np.concatenate([X[0] * H, [0]])          # 第 1 刻吃 1 个,从第 1 刻开始
    r2 = np.concatenate([[0], X[1] * H])          # 第 2 刻吃 2 个,从第 2 刻开始
    assert np.allclose(r1 + r2, Y)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    rows = [("① 第 1 刻吃 1 个:响应 = 1 × 消化序列", r1, BLUE, 1),
            ("② 第 2 刻吃 2 个:响应 = 2 × 消化序列,晚一刻开始", r2, ORA, 2)]
    for ax, (title, r, col, start) in zip(axes[:2], rows):
        ax.bar(t, r, color=col, width=0.6)
        for ti, v in zip(t, r):
            if ti >= start:
                ax.text(ti, v + 0.06, fmt(v), ha="center", fontsize=9.5, color=col)
        ax.axvline(start - 0.45, color=col, ls="--", lw=1)
        ax.text(start - 0.4, 2.85, f"第 {start} 刻吃下", color=col, fontsize=9)
        ax.set_title(title, fontsize=10.5, loc="left")
    ax = axes[2]
    ax.bar(t, r1, color=BLUE, width=0.6, label="第 1 口剩下的")
    ax.bar(t, r2, bottom=r1, color=ORA, width=0.6, label="第 2 口剩下的")
    for ti, v in zip(t, Y):
        ax.text(ti, v + 0.06, fmt(v), ha="center", fontsize=10)
    ax.set_title("③ 按时刻对齐叠起来 = 卷积结果", fontsize=10.5, loc="left")
    ax.legend(fontsize=9, loc="upper right")
    for ax in axes:
        ax.set_xticks(t)
        ax.set_xticklabels([f"{i}" for i in t])
        ax.set_xlabel("时刻", fontsize=9)
        ax.set_ylim(0, 3.2)
        ax.tick_params(labelsize=8.5)
    axes[0].set_ylabel("肚子里还剩几个馒头", fontsize=9)
    four_questions(
        fig,
        did="每吃一口,单独画出它之后\n每刻还剩多少,再按时刻\n对齐叠起来",
        gained="(1,2)*(1,0.9,0.5,0.3,0)\n= (1,2.9,2.3,1.3,0.6,0),\n和 np.convolve 完全一致",
        lost="要先画出每一口的整条响应;\n输入很长时(一整行像素)\n手算画不过来",
        limit="成立的前提是线性+时不变:\n消化能力随时间变,或两口\n互相影响,就不能这样叠",
        better="只想要某一个时刻的值,\n用下一张图的翻转滑动",
        y=0.12, bottom=0.27)
    save(fig, "conv-shift-add.png")


# ---------------------------------------------------------------- 2
def fig_flip_slide() -> None:
    fig, axes = plt.subplots(4, 1, figsize=(11, 8.6))
    xr = X[::-1]  # (2, 1)
    for n, ax in enumerate(axes):  # n = 0..3,对应第 1..4 刻
        ax.set_xlim(-2.6, 6.2)
        ax.set_ylim(-0.2, 2.3)
        ax.axis("off")
        ax.text(-2.55, 1.55, "消化序列 h", fontsize=9.5, va="center", color=BLUE)
        ax.text(-2.55, 0.55, "翻转的馒头", fontsize=9.5, va="center", color=ORA)
        for j, v in enumerate(H):
            ax.add_patch(Rectangle((j - 0.4, 1.2), 0.8, 0.7, fc="#eef3f8", ec=BLUE))
            ax.text(j, 1.55, fmt(v), ha="center", va="center", fontsize=11)
            if n == 0:
                ax.text(j, 2.1, f"消化 {j} 拍后", ha="center", fontsize=8, color=GRAY)
        terms = []
        for i, xv in enumerate(xr):  # xr[0]=第 2 口(2 个),放在 n-1;xr[1]=第 1 口(1 个),放在 n
            pos = n - 1 + i
            bite = 2 - i
            hit = 0 <= pos < len(H)
            ax.add_patch(Rectangle((pos - 0.4, 0.2), 0.8, 0.7, fc="#fff3e0" if hit else "#f4f4f4",
                                   ec=ORA if hit else "#bbb"))
            ax.text(pos, 0.55, f"{xv}", ha="center", va="center", fontsize=11, color="#222" if hit else "#aaa")
            ax.text(pos, -0.1, f"第 {bite} 口", ha="center", fontsize=8, color=GRAY)
            if hit:
                ax.text(pos, 1.05, "×", ha="center", va="center", fontsize=10, color=GREEN)
                terms.append(f"{xv}×{fmt(H[pos])}")
        ax.text(5.0, 1.0, f"第 {n + 1} 刻:\n{' + '.join(terms)} = {fmt(Y[n])}",
                fontsize=11, va="center", color=GREEN)
    assert [np.dot(xr, np.concatenate([[0], H, [0]])[n:n + 2]) for n in range(4)] == list(Y[:4])
    fig.suptitle("翻转滑动:馒头序列翻成 (2,1),每往右滑一格就是下一刻;对齐的格子相乘再相加",
                 fontsize=11.5, x=0.02, ha="left", y=0.99)
    four_questions(
        fig,
        did="站在某一刻,找出之前吃的\n每一口,乘上它已消化了\n几拍的剩余比例,再相加",
        gained="直接得到任意一刻的值:\n第 2 刻 = 2×1 + 1×0.9 = 2.9;\n就是 y[n]=Σx[k]h[n-k]",
        lost="翻转这一步不直观,容易\n滑错方向、对错格子",
        limit="翻转馒头还是翻转消化序列\n都对(交换律);但图像库的\nfilter2D 其实不翻转(相关)",
        better="手算对不上时,用上一张图\n的错位相加或多项式乘法验算",
        y=0.06, bottom=0.18)
    save(fig, "conv-flip-slide.png")


# ---------------------------------------------------------------- 3
def conv2_same(a: np.ndarray, k: np.ndarray) -> np.ndarray:
    pad = np.pad(a, 1)
    out = np.zeros_like(a, dtype=float)
    for i in range(3):
        for j in range(3):
            out += k[i, j] * pad[i:i + a.shape[0], j:j + a.shape[1]]
    return out


def fig_image() -> None:
    k1 = np.array([1, 2, 1]) / 4
    k = np.outer(k1, k1)  # 3×3 高斯核,和为 1
    one = np.zeros((9, 9))
    one[4, 4] = 1
    two = np.zeros((9, 9))
    two[3, 2], two[5, 5] = 1, 2
    out1, out2 = conv2_same(one, k), conv2_same(two, k)
    assert np.allclose(out1[3:6, 3:6], k)
    step = np.array([0, 0, 0, 0, 4, 4, 4, 4], float)
    sm = np.convolve(np.pad(step, 1, mode="edge"), k1, mode="valid")  # 两端复制补边,长度不变
    print(f"   单个亮点的输出 3×3 = 核本身(×16):\n{(out1[3:6, 3:6] * 16).astype(int)}")
    print(f"   台阶 {step} * [1,2,1]/4(复制补边)= {sm}")

    fig, axes = plt.subplots(1, 5, figsize=(15, 3.9), gridspec_kw=dict(width_ratios=[1, 1, 1, 1, 1.4]))
    panels = [(one, "① 输入:一个亮点\n(只吃 1 个馒头)"), (out1, "② 输出 = 核本身\n(冲激响应)"),
              (two, "③ 输入:亮度 1 和 2\n的两个亮点"), (out2, "④ 输出 = 两份核\n错位叠加")]
    for ax, (img, title) in zip(axes[:4], panels):
        vmax = 2 if img is two else 1 if img is one else 2 / 4
        ax.imshow(img, cmap="magma", vmin=0, vmax=vmax, interpolation="nearest")
        ax.set_title(title, fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])
    for (r, c) in [(3, 3), (3, 4), (3, 5), (4, 3), (4, 4), (4, 5), (5, 3), (5, 4), (5, 5)]:
        axes[1].text(c, r, f"{int(out1[r, c] * 16)}", ha="center", va="center", fontsize=8,
                     color="white" if out1[r, c] < 0.15 else "black")
    axes[1].text(4, 7.6, "(数字 ×1/16)", ha="center", fontsize=8, color="white")
    ax = axes[4]
    ax.plot(range(len(step)), step, "o-", color=GRAY, label="输入:0 跳到 4 的台阶")
    ax.plot(range(len(sm)), sm, "s-", color=BLUE, label="[1,2,1]/4 卷积后")
    for i, v in enumerate(sm):
        ax.text(i - 0.3, v + 0.15, fmt(v), ha="center", fontsize=9, color=BLUE)
    ax.set_title("⑤ 一行像素:陡台阶被抹成斜坡", fontsize=10)
    ax.set_ylim(-0.5, 5.2)
    ax.set_xlabel("像素位置", fontsize=9)
    ax.legend(fontsize=8.5, loc="upper left")
    ax.tick_params(labelsize=8)
    four_questions(
        fig,
        did="把馒头换成像素:亮点 = 吃\n一个馒头,卷积核 = 消化序列,\n在图上左右上下都错位",
        gained="一个亮点被摊成核的形状;\n两个亮点 = 两份核按亮度\n缩放后叠加(线性+时不变)",
        lost="图变模糊:0 一步跳到 4\n的台阶被抹成 0,1,3,4,\n边缘不再陡",
        limit="图像不讲因果,核以当前\n像素为中心;边界外没有像素,\n要补边(复制、镜像…)",
        better="核大时用频域相乘\n(补零后的 FFT)更快",
        y=0.10, bottom=0.28)
    save(fig, "conv-image.png")


if __name__ == "__main__":
    fig_shift_add()
    fig_flip_slide()
    fig_image()
