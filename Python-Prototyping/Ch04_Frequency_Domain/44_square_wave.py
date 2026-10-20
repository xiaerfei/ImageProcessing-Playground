"""44《知乎傅里叶文章笔记》的配图与数字 —— 配合 Documents/数学基础/快速路线/7.知乎傅里叶文章笔记.md。

 1. 方波叠加:叠 1、2、4、10、100 个正弦,越来越像方波;但直角旁边始终冲过头约 9%(吉布斯现象),
    叠得越多,冲过头只是越挤越靠近直角,高度不降
 2. 「一边离散,另一边就周期」:一个矩形脉冲,不采样时频谱是一条 sinc;
    每隔 T 采一个点之后,频谱变成每隔 1/T 重复一次的周期函数 —— 这就是混叠的根

两张图:square-synthesis.png、sampling-periodic.png

用法:
    .venv/bin/python Ch04_Frequency_Domain/44_square_wave.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import four_questions, use_cjk_font  # noqa: E402

use_cjk_font()
import matplotlib.pyplot as plt  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "Documents" / "数学基础" / "快速路线" / "images"
BLUE, ORA, GREEN, RED, PURPLE, GRAY = "#2c6fbb", "#d98a14", "#2a8f4a", "#c4442a", "#6b4fa8", "#666"
PI = np.pi


def head(title: str) -> None:
    print(f"\n{'=' * 8} {title} {'=' * 8}")


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=130, bbox_inches="tight", facecolor="white")
    print(f"  → Documents/数学基础/快速路线/images/{name}")
    plt.close(fig)


def square_sum(t: np.ndarray, n: int) -> np.ndarray:
    """方波(−1 / +1,周期 2π)的前 n 个非零分量:频率 1、3、5…,振幅 4/π、4/(3π)、4/(5π)…"""
    out = np.zeros_like(t)
    for k in range(1, n + 1):
        m = 2 * k - 1
        out += 4 / PI * np.sin(m * t) / m
    return out


def fig_square() -> None:
    head("1. 方波叠加:冲过头始终约 9%")
    t = np.linspace(-PI, PI, 200001)
    ns = [1, 2, 4, 10, 100]
    rows = []
    for n in ns:
        y = square_sum(t, n)
        right = (t > 0) & (t <= PI / 2)  # 只看 0 处直角右侧(π 处还有另一个直角)
        peak = y[right].max()
        where = t[right][np.argmax(y[right])]
        ov = (peak - 1) / 2 * 100  # 台阶高度是 2(−1 到 +1)
        rows.append((n, ov, where))
        print(f"  叠 {n:3d} 个:最高 {peak:.4f},冲过头 {ov:.2f}%(占台阶高度),出现在离直角 {where:.4f} 处")
    amps = [4 / PI / m for m in (1, 3, 5, 7, 9)]
    print(f"  前 5 个分量的振幅:{', '.join(f'{a:.3f}' for a in amps)}(频率 1、3、5、7、9;偶数倍为 0)")

    fig = plt.figure(figsize=(15.5, 4.3))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.5, 1.1, 1])
    ax = fig.add_subplot(gs[0])
    sq = np.sign(np.sin(t))
    ax.plot(t, sq, color="#bbb", lw=2.5, label="方波")
    cols = [GRAY, BLUE, GREEN, ORA, RED]
    for (n, ov, _), col in zip(rows, cols):
        ax.plot(t, square_sum(t, n), color=col, lw=1.1, label=f"叠 {n} 个")
    ax.set_xlim(-PI, PI)
    ax.set_ylim(-1.45, 1.55)
    ax.set_xticks([-PI, 0, PI])
    ax.set_xticklabels(["−π", "0", "π"])
    ax.set_title("① 正弦一个个叠上去,越来越像方波", fontsize=10.5, loc="left")
    ax.legend(fontsize=8.5, loc="lower right", ncol=2)
    ax = fig.add_subplot(gs[1])
    ax.plot(t, sq, color="#bbb", lw=2.5)
    for (n, ov, _), col in zip(rows[2:], cols[2:]):
        ax.plot(t, square_sum(t, n), color=col, lw=1.3, label=f"叠 {n} 个:冲过头 {ov:.2f}%")
    ax.axhline(1 + 2 * 0.0895, color=RED, ls=":", lw=1)
    ax.set_xlim(-0.05, 0.9)
    ax.set_ylim(0.6, 1.3)
    ax.set_title("② 放大直角:叠多少个都冲过头约 9%,\n只是越挤越靠近直角", fontsize=10.5, loc="left")
    ax.legend(fontsize=8.5, loc="lower right")
    ax = fig.add_subplot(gs[2])
    ms = np.arange(1, 12)
    amp = np.where(ms % 2 == 1, 4 / PI / ms, 0)
    ax.bar(ms, amp, color=[BLUE if m % 2 else "#ddd" for m in ms], width=0.5)
    for m, a in zip(ms, amp):
        if a == 0:
            ax.text(m, 0.03, "0", ha="center", fontsize=8.5, color=GRAY)
    ax.set_xticks(ms)
    ax.set_xlabel("频率(基频的几倍)", fontsize=9)
    ax.set_title("③ 方波的频谱(从侧面看):\n只有奇数倍,偶数倍振幅为 0", fontsize=10.5, loc="left")
    four_questions(
        fig,
        did="按方波的配方,把频率 1、3、5…\n的正弦依次叠加 1、2、4、10、\n100 个",
        gained="越叠越像方波;频谱只有\n奇数倍的竖线,振幅越来越小",
        lost=f"直角永远叠不出来:叠 100 个\n仍冲过头 {rows[-1][1]:.2f}%,只是挤到\n离直角 {rows[-1][2]:.3f} 的地方",
        limit="这就是振铃(吉布斯现象):\n只要截在有限个频率,\n直角旁就有这一下",
        better="不想要冲过头,就让高频\n逐渐变弱而不是一刀切\n(见振铃案例)",
        y=0.08, bottom=0.30)
    save(fig, "square-synthesis.png")


def fig_sampling() -> None:
    head("2. 时间上采样 → 频谱周期重复")
    f = np.linspace(-6, 6, 12001)  # 频率(周期/秒)
    W = 1.0  # 脉冲宽度 1 秒(−0.5~0.5)
    cont = W * np.sinc(f * W)  # 连续矩形脉冲的频谱
    T = 0.25  # 每 0.25 秒采一个点,采样率 4 次/秒
    n = np.arange(-2, 3)  # 落在脉冲里的采样点:t = −0.5、−0.25、0、0.25、0.5 中的前 5 个
    tn = n * T
    vals = np.where(np.abs(tn) < 0.5 + 1e-9, 1.0, 0.0)
    vals[np.abs(np.abs(tn) - 0.5) < 1e-9] = 0.5  # 正好在边缘上的点取一半
    dtft = np.array([np.sum(vals * np.exp(-2j * PI * fr * tn)) * T for fr in f]).real
    per = 1 / T
    i0 = np.argmin(np.abs(f - 0.3))
    i1 = np.argmin(np.abs(f - (0.3 + per)))
    print(f"  每 {T} 秒采一个点(采样率 {per:.0f} 次/秒):采样后频谱在 0.3 与 {0.3 + per:.1f} 处的值 "
          f"{dtft[i0]:.4f}、{dtft[i1]:.4f}(相差 {abs(dtft[i0] - dtft[i1]):.1e},每隔 {per:.0f} 重复一次)")
    print(f"  连续脉冲在 0.3 处的频谱 {cont[i0]:.4f};在 {0.3 + per:.1f} 处 {cont[i1]:.4f}(不重复,越远越小)")

    fig, axes = plt.subplots(2, 2, figsize=(14, 6.2), gridspec_kw=dict(hspace=0.6))
    tt = np.linspace(-1.5, 1.5, 3001)
    ax = axes[0, 0]
    ax.plot(tt, (np.abs(tt) < 0.5).astype(float), color=BLUE, lw=2)
    ax.set_title("① 时域:连续的矩形脉冲", fontsize=10.5, loc="left")
    ax.set_xlabel("时间(秒)", fontsize=9)
    ax.set_ylim(-0.2, 1.3)
    ax = axes[0, 1]
    ax.plot(tt, (np.abs(tt) < 0.5).astype(float), color="#ccc", lw=1.5)
    ax.stem(tn, vals, linefmt=ORA, markerfmt="o", basefmt=" ")
    ax.set_title(f"② 时域:每隔 {T} 秒采一个点(离散)", fontsize=10.5, loc="left")
    ax.set_xlabel("时间(秒)", fontsize=9)
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-0.2, 1.3)
    ax = axes[1, 0]
    ax.plot(f, cont, color=BLUE, lw=1.8)
    ax.axhline(0, color="#999", lw=0.8)
    ax.set_title("③ 频域:一条 sinc,只有一个主峰,越远越小", fontsize=10.5, loc="left")
    ax.set_xlabel("频率(周期/秒)", fontsize=9)
    ax = axes[1, 1]
    ax.plot(f, dtft, color=ORA, lw=1.8)
    for k in (-1, 0, 1):
        ax.axvline(k * per, color=RED, ls=":", lw=1)
    ax.axhline(0, color="#999", lw=0.8)
    ax.set_title(f"④ 频域:每隔 {per:.0f}(采样率)重复一份 —— 变成周期的", fontsize=10.5, loc="left")
    ax.set_xlabel("频率(周期/秒)", fontsize=9)
    four_questions(
        fig,
        did="同一个矩形脉冲:不采样,\n和每 0.25 秒采一个点,\n分别看频谱",
        gained="时域一离散,频域就周期:\n采样后的频谱每隔采样率\n重复一份",
        lost="重复的几份如果叠到一起\n(采样率不够),就分不开\n了 —— 这就是混叠",
        limit="图里只画了实部;\n这个脉冲左右对称,\n虚部为 0",
        better="采样前先低通,让重复的\n各份互不重叠",
        y=0.04, bottom=0.17)
    save(fig, "sampling-periodic.png")


if __name__ == "__main__":
    fig_square()
    fig_sampling()
