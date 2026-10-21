"""45《卷积定理》的配图与数字 —— 配合 Documents/数学基础/快速路线/8.卷积定理.md。

 1. 冲激是拆信号的积木:输入一段方波,切成一根根冲激(每根的大小 = 这一小段的面积),
    每根进系统各自吐出一个冲激响应,错开叠起来;间隔越小,叠出来的越接近真正的卷积
 2. 卷积定理:两个方波卷积成三角波;三角波的频谱 = 两个方波频谱逐点相乘;
    正弦进 LTI 系统,出来还是同频正弦,只被缩放、挪了相位(本征函数)
 3. 应用:视频里的信号 3cos t + 0.3cos5t + 0.15sin7t,频域乘一个高斯 = 时域和高斯卷积

三张图:impulse-train.png、conv-theorem.png、gauss-lowpass.png

用法:
    .venv/bin/python Ch04_Frequency_Domain/45_convolution_theorem.py
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


def h(t: np.ndarray) -> np.ndarray:
    """系统的冲激响应:视频里用的 e^(−t),t<0 时为 0(还没敲,不会有反应)"""
    return np.where(t >= 0, np.exp(-np.clip(t, 0, None)), 0.0)


def fig_impulse_train() -> None:
    head("1. 冲激是拆信号的积木")
    t = np.linspace(-1, 14, 15001)
    L = 6.0  # 输入:0~6 秒、高度 1 的方波
    exact = np.where(t < 0, 0, np.where(t < L, 1 - np.exp(-t), np.exp(-(t - L)) - np.exp(-t)))
    deltas = [2.0, 1.3, 0.9, 0.1]
    errs = {}
    sums = {}
    for d in deltas:
        starts = np.arange(0, L, d)
        widths = np.minimum(starts + d, L) - starts  # 每一小段的宽度 = 这根冲激的大小
        y = sum(w * h(t - s) for s, w in zip(starts, widths))
        sums[d] = (starts, widths, y)
        errs[d] = np.max(np.abs(y - exact))
        print(f"  间隔 {d:>4}:{len(starts):3d} 根冲激,叠出来和真正卷积最多差 {errs[d]:.3f}")
    print(f"  真正卷积的最高点 {exact.max():.4f}(在 t = {t[np.argmax(exact)]:.2f})")

    fig, axes = plt.subplots(2, 3, figsize=(15, 6.8), gridspec_kw=dict(hspace=0.55, wspace=0.22))
    ax = axes[0, 0]
    ax.plot(t, h(t), color=RED, lw=1.8, label="冲激响应")
    ax.annotate("", xy=(0, 1.15), xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=2))
    ax.text(0.25, 1.05, "一下冲激", color=BLUE, fontsize=9)
    ax.set_xlim(-1, 8)
    ax.set_ylim(-0.1, 1.35)
    ax.set_title("① 单个冲激进系统:吐出冲激响应\n(系统的「指纹」)", fontsize=10.5, loc="left")
    ax.legend(fontsize=8.5, loc="upper right")
    for ax, d in zip([axes[0, 1], axes[0, 2], axes[1, 0], axes[1, 1]], deltas):
        starts, widths, y = sums[d]
        if d >= 0.5:
            for s, w in zip(starts, widths):
                ax.plot(t, w * h(t - s), color=RED, lw=0.9, alpha=0.7)
                ax.annotate("", xy=(s, w), xytext=(s, 0),
                            arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=1.4))
        ax.fill_between(t, y, color=PURPLE, alpha=0.25, label="叠加结果")
        ax.plot(t, exact, color="k", ls="--", lw=1.1, label="真正的卷积")
        ax.axvspan(0, L, color="#eee", zorder=0)
        ax.set_xlim(-1, 14)
        ax.set_ylim(-0.1, 2.5)
        ax.set_title(f"{'②③④⑤'[deltas.index(d)]} 每隔 {d:g} 秒一根,共 {len(starts)} 根,最多差 {errs[d]:.2f}",
                     fontsize=10.5, loc="left")
        ax.legend(fontsize=8, loc="upper right")
    ax = axes[1, 2]
    ds = np.array([2.0, 1.5, 1.3, 1.0, 0.9, 0.6, 0.4, 0.2, 0.1, 0.05])
    es = []
    for d in ds:
        starts = np.arange(0, L, d)
        widths = np.minimum(starts + d, L) - starts
        es.append(np.max(np.abs(sum(w * h(t - s) for s, w in zip(starts, widths)) - exact)))
    ax.plot(ds, es, "o-", color=PURPLE)
    ax.invert_xaxis()
    ax.set_xlabel("冲激间隔(越往右越密)", fontsize=9)
    ax.set_title("⑥ 间隔越小,叠加越接近卷积", fontsize=10.5, loc="left")
    four_questions(
        fig,
        did="把 0~6 秒的方波切成一根根\n冲激(大小 = 这一段的面积),\n各自进系统再叠加",
        gained="冲激一密,叠加就连成一片:\n叠加的极限就是卷积;\n系统只要一张「指纹」就够",
        lost="冲激稀时叠出来是锯齿,\n和真结果差得多(间隔 2\n时最多差 " + f"{errs[2.0]:.2f})",
        limit="前提是系统线性、时不变;\n反应会随时间或大小变的\n系统不能这么叠",
        better="实际计算直接卷积,或者\n用卷积定理到频域去乘",
        y=0.04, bottom=0.17)
    save(fig, "impulse-train.png")


def fig_conv_theorem() -> None:
    head("2. 卷积定理:时域卷积 = 频域相乘")
    dt = 0.001
    t = np.arange(-3, 3, dt)
    rect = (np.abs(t) < 0.5).astype(float)
    tri = np.convolve(rect, rect, mode="same") * dt
    print(f"  两个宽 1、高 1 的方波卷积:三角波最高 {tri.max():.4f},宽 {np.sum(tri > 1e-9) * dt:.2f}")
    # 离散验证:直接卷积 vs 变到频域相乘再变回来
    rng = np.random.default_rng(0)
    a, b = rng.normal(size=300), rng.normal(size=200)
    direct = np.convolve(a, b)
    n = len(a) + len(b) - 1
    via_f = np.fft.ifft(np.fft.fft(a, n) * np.fft.fft(b, n)).real
    print(f"  随机两串数:直接卷积 vs 频域相乘再变回,最大差 {np.max(np.abs(direct - via_f)):.1e}")
    f = np.linspace(-4, 4, 1601)
    sinc = np.sinc(f)
    tri_ft = np.array([np.sum(tri * np.cos(2 * PI * fr * t)) * dt for fr in f])
    i = np.argmin(np.abs(f - 0.3))
    print(f"  频率 0.3 处:方波频谱 {sinc[i]:.4f},平方 {sinc[i] ** 2:.4f},三角波频谱实算 {tri_ft[i]:.4f}")
    print(f"  全频段最大差 {np.max(np.abs(tri_ft - sinc ** 2)):.1e}")
    # 本征函数:cos2t 进 h = e^(−t)
    dt2 = 0.001
    t2 = np.arange(0, 40, dt2)
    x = np.cos(2 * t2)
    y = np.convolve(x, h(t2))[: len(t2)] * dt2
    m = t2 > 30
    A = np.vstack([np.cos(2 * t2[m]), np.sin(2 * t2[m])]).T
    c, s = np.linalg.lstsq(A, y[m], rcond=None)[0]
    amp, ph = np.hypot(c, s), np.degrees(np.arctan2(-s, c))
    fit_res = np.max(np.abs(A @ [c, s] - y[m]))
    print(f"  cos2t 进系统:出来仍是频率 2 的余弦(拟合残差 {fit_res:.1e}),振幅 {amp:.4f},相位 {ph:.1f}°")
    print(f"  理论:振幅 1/√5 = {1 / np.sqrt(5):.4f},相位 −arctan2 = {-np.degrees(np.arctan(2)):.1f}°")
    for w in (0.5, 2, 8):
        print(f"    频率 {w}:系统把振幅乘上 {1 / np.hypot(1, w):.3f}")

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.3), gridspec_kw=dict(wspace=0.25))
    ax = axes[0]
    ax.plot(t, rect, color=BLUE, lw=1.8, label="方波")
    ax.plot(t, tri, color=PURPLE, lw=2, label="方波 * 方波")
    ax.set_xlim(-1.6, 1.6)
    ax.set_ylim(-0.1, 1.3)
    ax.set_title("① 时域:两个方波卷积,成了三角波", fontsize=10.5, loc="left")
    ax.legend(fontsize=8.5)
    ax.set_xlabel("时间(秒)", fontsize=9)
    ax = axes[1]
    ax.plot(f, sinc, color=BLUE, lw=1.5, label="方波的频谱")
    ax.plot(f, sinc ** 2, color=ORA, lw=3.5, alpha=0.6, label="方波频谱 × 方波频谱")
    ax.plot(f, tri_ft, color=PURPLE, lw=1.2, ls="--", label="三角波的频谱(实算)")
    ax.axhline(0, color="#999", lw=0.8)
    ax.set_title("② 频域:三角波的频谱 = 两份方波频谱相乘", fontsize=10.5, loc="left")
    ax.legend(fontsize=8.5)
    ax.set_xlabel("频率(周期/秒)", fontsize=9)
    ax = axes[2]
    show = (t2 > 30) & (t2 < 36)
    ax.plot(t2[show], x[show], color=BLUE, lw=1.6, label="进:cos2t")
    ax.plot(t2[show], y[show], color=RED, lw=1.8, label=f"出:振幅 {amp:.3f},晚 {-ph:.1f}°")
    ax.set_ylim(-1.3, 1.6)
    ax.set_title("③ 正弦进系统,出来还是同频正弦\n只被缩小、挪后", fontsize=10.5, loc="left")
    ax.legend(fontsize=8.5, loc="upper right", ncol=2)
    ax.set_xlabel("时间(秒)", fontsize=9)
    four_questions(
        fig,
        did="两个方波做卷积,对比三角\n波的频谱和两份方波频谱\n的乘积;cos2t 进 e^(−t)",
        gained="时域卷积 = 频域相乘;\n正弦出来频率不变,系统\n只管乘一个数(本征函数)",
        lost="频域里乘出来是 0 的频率,\n回到时域就彻底没了,\n再也找不回",
        limit="电脑里的 FFT 是循环的:\n不补零会首尾绕回\n(脚本里的验证已补零)",
        better="长核卷积改用 FFT 相乘,\n比逐点滑动快得多",
        y=0.08, bottom=0.30)
    save(fig, "conv-theorem.png")


def fig_lowpass() -> None:
    head("3. 应用:频域乘高斯 = 时域和高斯卷积")
    N, L = 8192, 2 * PI * 32  # 32 个基波周期,整数频率正好落在频率格子上
    dt = L / N
    t = np.arange(N) * dt
    f = 3 * np.cos(t) + 0.3 * np.cos(5 * t) + 0.15 * np.sin(7 * t)
    w = 2 * PI * np.fft.fftfreq(N, dt)  # 角频率(和视频一样,cos5t 的频率记作 5)
    sig = 2.0
    H = np.exp(-w ** 2 / (2 * sig ** 2))
    F = np.fft.fft(f)
    g_freq = np.fft.ifft(F * H).real
    # 时域:和面积为 1、宽度 1/sig 的高斯做(循环)卷积
    st = 1 / sig
    tt = np.where(t < L / 2, t, t - L)
    kern = np.exp(-tt ** 2 / (2 * st ** 2)) / (np.sqrt(2 * PI) * st) * dt
    g_time = np.fft.ifft(np.fft.fft(f) * np.fft.fft(kern)).real
    g_direct = np.array([np.sum(f * np.roll(kern[::-1], k + 1)) for k in range(0, N, 64)])
    amp = lambda X: np.abs(X) * 2 / N  # noqa: E731
    k = {m: int(round(m * L / (2 * PI))) for m in (1, 5, 7)}
    for m in (1, 5, 7):
        print(f"  频率 {m}:高斯在这里是 {H[k[m]]:.4f};振幅 {amp(F)[k[m]]:.3f} → {amp(np.fft.fft(g_freq))[k[m]]:.4f}")
    print(f"  频域相乘 vs 时域卷积(高斯宽 {st}):最大差 {np.max(np.abs(g_freq - g_time)):.1e};"
          f"抽查逐点滑动 {np.max(np.abs(g_direct - g_freq[::64])):.1e}")
    print(f"  滤完和纯 {3 * H[k[1]]:.3f}cos t 的最大差 {np.max(np.abs(g_freq - 3 * H[k[1]] * np.cos(t))):.1e}")

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.3), gridspec_kw=dict(wspace=0.25, width_ratios=[1.3, 1, 1]))
    ax = axes[0]
    show = t < 4 * PI
    ax.plot(t[show], f[show], color=BLUE, lw=1.3, label="原信号")
    ax.plot(t[show], g_freq[show], color=RED, lw=1.8, label="频域乘高斯后")
    ax.plot(t[show], g_time[show], color="k", ls=":", lw=1.4, label="时域和高斯卷积")
    ax.set_ylim(-4, 5.2)
    ax.set_title("① 时域:毛刺没了,主波形留下", fontsize=10.5, loc="left")
    ax.legend(fontsize=8.5, loc="upper right", ncol=3)
    ax.set_xlabel("时间", fontsize=9)
    order = np.argsort(w)
    for ax, X, title in ((axes[1], F, "② 原频谱和高斯(虚线)"), (axes[2], np.fft.fft(g_freq), "③ 相乘后:5、7 几乎压没")):
        ax.plot(w[order], amp(X)[order], color=BLUE if X is F else RED, lw=1.5)
        for m in (1, 5, 7):
            ax.text(m, amp(X)[k[m]] + 0.08, f"{amp(X)[k[m]]:.3g}", ha="center", fontsize=8.5)
        if X is F:
            ax.plot(w[order], 3 * H[order], color=GREEN, ls="--", lw=1.2)
        ax.set_xlim(-0.5, 9)
        ax.set_ylim(0, 3.5)
        ax.set_title(title, fontsize=10.5, loc="left")
        ax.set_xlabel("频率", fontsize=9)
    four_questions(
        fig,
        did="频域里把频谱乘上一个高斯\n(宽 2),再变回时域;\n对照时域和高斯卷积",
        gained=f"5、7 的分量缩到原来的\n{H[k[5]]:.3f}、{H[k[7]]:.4f},波形变平滑;\n两种做法结果一样",
        lost=f"主频 1 也被压了一点:\n振幅 3 → {3 * H[k[1]]:.2f}",
        limit="噪声和信号频率重叠时,\n压噪声也会压掉信号",
        better="保住主频就把高斯放宽,\n或者只在 5、7 处陷波",
        y=0.08, bottom=0.30)
    save(fig, "gauss-lowpass.png")


if __name__ == "__main__":
    fig_impulse_train()
    fig_conv_theorem()
    fig_lowpass()
