"""39《正交基与相位》的数字与配图 —— 配合 Documents/数学基础/快速路线/3.正交基与相位.md。

数字(文中每个数都从这里来):
 1. 不正交的零件量不准:u=[1,0]、v=[1,1] 拼 [3,1],点乘量出 3 而不是 2
 2. 正交零件一次量准:[1,1]/√2、[1,-1]/√2 量 [3,1] 得 2√2、√2
 3. 4 点「波形零件」两两正交;[1,2,3,4] = 2.5·b0 − b1 − b2 − 0.5·b3;与 DFT 的对应
 4. 相位:[1,0,-1,0] 与 [0,1,0,-1] 振幅相同;冲激改相位 [1,i,1,-i] → [0.5,-0.5,0.5,0.5]
 5. 32 点:所有频率相位对齐 → 冲激;相位打乱 → 散开(振幅谱完全一样)
 6. 图像:camera 的幅度 + coins 的相位,像谁

两张图:basis-orthogonal.png、phase-matters.png

用法:
    .venv/bin/python Ch04_Frequency_Domain/39_basis_phase.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import IMAGES, four_questions, use_cjk_font  # noqa: E402

use_cjk_font()
import matplotlib.pyplot as plt  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "Documents" / "数学基础" / "快速路线" / "images"
BLUE, ORA, GREEN, RED, PURPLE, GRAY = "#2c6fbb", "#d98a14", "#2a8f4a", "#c4442a", "#6b4fa8", "#666"
B = np.array([[1, 1, 1, 1], [1, 0, -1, 0], [0, 1, 0, -1], [1, -1, 1, -1]], float)
NAMES = ["b0 直流", "b1 cos", "b2 sin", "b3 最高频"]


def head(title: str) -> None:
    print(f"\n{'=' * 8} {title} {'=' * 8}")


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=130, bbox_inches="tight", facecolor="white")
    print(f"  → Documents/数学基础/快速路线/images/{name}")
    plt.close(fig)


def numbers() -> dict:
    head("1~2. 不正交量不准,正交一次量准")
    a = np.array([3.0, 1.0])
    u, v = np.array([1.0, 0.0]), np.array([1.0, 1.0])
    true = np.linalg.solve(np.column_stack([u, v]), a)
    print(f"  u·v = {u @ v:.0f}(不正交);真实系数 {true}(2u + 1v);点乘去量 u 得 {a @ u:.0f}")
    e1, e2 = np.array([1, 1]) / np.sqrt(2), np.array([1, -1]) / np.sqrt(2)
    print(f"  正交零件:e1·e2 = {e1 @ e2:.0f};量得 {a @ e1:.4f}(2√2 = {2 * np.sqrt(2):.4f})、{a @ e2:.4f}(√2)")

    head("3. 4 点波形零件")
    print(f"  两两点乘(对角线是长度²):\n{(B @ B.T).astype(int)}")
    x = np.array([1, 2, 3, 4], float)
    c = B @ x / np.sum(B * B, 1)
    print(f"  [1,2,3,4] 的系数 {c};拼回 {c @ B}")
    X = np.fft.fft(x)
    print(f"  DFT {np.round(X, 4)};X[1] = (x·b1) − i(x·b2) = {x @ B[1]:.0f} − i·({x @ B[2]:.0f})")

    head("4. 相位")
    for s in ([1, 0, -1, 0], [0, 1, 0, -1], [1, 0, 0, 0]):
        Y = np.fft.fft(s)
        print(f"  {s}: DFT {np.round(Y, 4)},模 {np.round(np.abs(Y), 4)}")
    y = np.fft.ifft([1, 1j, 1, -1j]).real
    print(f"  振幅全 1、相位改成 [1,i,1,-i]:逆变换 {y}")
    return dict(c=c, y=y)


def fig_basis(c: np.ndarray) -> None:
    fig = plt.figure(figsize=(14, 4.6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1.5])
    # ① 不正交
    ax = fig.add_subplot(gs[0])
    a = np.array([3, 1])
    for vec, col, lab in (([1, 0], BLUE, "u=[1,0]"), ([1, 1], ORA, "v=[1,1]")):
        ax.annotate("", vec, (0, 0), arrowprops=dict(arrowstyle="->", color=col, lw=2))
        ax.text(vec[0] + 0.05, vec[1] + 0.1, lab, color=col, fontsize=9.5)
    ax.annotate("", a, (0, 0), arrowprops=dict(arrowstyle="->", color="#222", lw=2))
    ax.text(3.05, 1.05, "[3,1]", fontsize=10)
    ax.plot([2, 3], [0, 1], color=ORA, ls="--", lw=1.2)
    ax.plot([3, 3], [0, 1], color=GRAY, ls=":", lw=1.2)
    ax.text(1.0, -0.38, "拼法:2 个 u + 1 个 v", color=BLUE, fontsize=9)
    ax.text(3.1, 0.3, "点乘量 u\n得 3,\n不是 2", color=RED, fontsize=9)
    ax.set_xlim(-0.3, 4.0)
    ax.set_ylim(-0.6, 2.0)
    ax.set_aspect("equal")
    ax.grid(alpha=0.25)
    ax.set_title("① 零件不正交:\n量 u 时把 v 的那份也量进去了", fontsize=10.5, loc="left")
    # ② 正交
    ax = fig.add_subplot(gs[1])
    e1, e2 = np.array([1, 1]) / np.sqrt(2), np.array([1, -1]) / np.sqrt(2)
    for vec, col, lab in ((e1, BLUE, "[1,1]/√2"), (e2, ORA, "[1,-1]/√2")):
        ax.annotate("", vec, (0, 0), arrowprops=dict(arrowstyle="->", color=col, lw=2))
        ax.text(vec[0] + 0.05, vec[1] + (0.1 if vec[1] > 0 else -0.3), lab, color=col, fontsize=9.5)
    ax.annotate("", a, (0, 0), arrowprops=dict(arrowstyle="->", color="#222", lw=2))
    ax.text(3.05, 1.05, "[3,1]", fontsize=10)
    p1 = (a @ e1) * e1
    ax.plot([a[0], p1[0]], [a[1], p1[1]], color=GRAY, ls=":", lw=1.2)
    ax.plot(*p1, "o", color=BLUE, ms=5)
    ax.text(p1[0] - 0.4, p1[1] + 0.25, "投影 2√2", color=BLUE, fontsize=9)
    ax.set_xlim(-0.3, 4.0)
    ax.set_ylim(-1.6, 2.6)
    ax.set_aspect("equal")
    ax.grid(alpha=0.25)
    ax.set_title("② 零件正交(互相垂直):\n各量各的,点乘一次得 2√2 和 √2", fontsize=10.5, loc="left")
    # ③ 4 点波形零件
    ax = fig.add_subplot(gs[2])
    n = np.arange(4)
    cols = [GRAY, BLUE, ORA, GREEN]
    for i in range(4):
        off = -2.6 * i
        ax.plot(n, B[i] + off, "o-", color=cols[i], lw=1.4)
        ax.text(-0.35, off, f"{NAMES[i]}\n× {c[i]:g}", ha="right", va="center", fontsize=9, color=cols[i])
    x = c @ B
    ax.plot(n, x * 0.6 + 2.2, "s-", color="#222", lw=2)
    ax.text(-0.35, 2.2 + 1.2, "相加 =\n[1,2,3,4]", ha="right", va="center", fontsize=9.5)
    for ni, xv in zip(n, x):
        ax.text(ni, xv * 0.6 + 2.5, f"{xv:g}", ha="center", fontsize=9)
    ax.set_xlim(-1.6, 3.4)
    ax.set_xticks(n)
    ax.set_yticks([])
    ax.set_xlabel("采样点 n", fontsize=9)
    ax.set_title("③ 四个波形零件两两正交,各量一次就拼回 [1,2,3,4]", fontsize=10.5, loc="left")
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    four_questions(
        fig,
        did="同一个向量,分别用不正交\n和正交的零件去拆;再用 4 个\n波形零件拆 [1,2,3,4]",
        gained="正交零件:每个系数点乘一次\n就得到(2.5、−1、−1、−0.5),\n不用解方程",
        lost="不正交时点乘量出来的数\n(3)不是真系数(2),\n只能解方程组",
        limit="零件长度不是 1 时,\n点乘完要再除以长度²\n(b0、b3 除 4,b1、b2 除 2)",
        better="N 点信号用 N 个转圈零件,\n就是 DFT;交给 np.fft",
        y=0.08, bottom=0.30)
    save(fig, "basis-orthogonal.png")


def fig_phase(y4: np.ndarray) -> None:
    head("5~6. 相位对齐 → 尖峰;相位打乱 → 散开;图像交换")
    N = 32
    rng = np.random.default_rng(3)
    imp = np.zeros(N)
    imp[N // 2] = 1
    F = np.fft.fft(imp)
    ph = rng.uniform(-np.pi, np.pi, N)
    G = np.abs(F) * np.exp(1j * ph)
    G[0] = abs(F[0])
    G[N // 2] = abs(F[N // 2])
    G[N // 2 + 1:] = np.conj(G[1:N // 2][::-1])  # 共轭对称,保证逆变换是实数
    scr = np.fft.ifft(G)
    assert np.abs(scr.imag).max() < 1e-12
    scr = scr.real
    print(f"  32 点冲激:振幅谱全是 {np.abs(F)[0]:.0f};打乱相位后振幅谱最大差 {np.abs(np.abs(G) - np.abs(F)).max():.1e}")
    print(f"  冲激的最大值 {imp.max():.3f};打乱后最大值 {np.abs(scr).max():.3f}(能量都是 {np.sum(imp ** 2):.3f} vs {np.sum(scr ** 2):.3f})")

    cam = cv2.resize(cv2.imread(str(IMAGES / "camera.png"), 0), (256, 256), interpolation=cv2.INTER_AREA).astype(float)
    coin = cv2.resize(cv2.imread(str(IMAGES / "coins.png"), 0), (256, 256), interpolation=cv2.INTER_AREA).astype(float)
    Fa, Fb = np.fft.fft2(cam), np.fft.fft2(coin)
    mix = np.fft.ifft2(np.abs(Fa) * np.exp(1j * np.angle(Fb))).real
    r_coin = np.corrcoef(mix.ravel(), coin.ravel())[0, 1]
    r_cam = np.corrcoef(mix.ravel(), cam.ravel())[0, 1]
    print(f"  camera 幅度 + coins 相位:与 coins 相关 {r_coin:.3f},与 camera 相关 {r_cam:.3f}")

    fig, axes = plt.subplots(1, 5, figsize=(16, 4.0), gridspec_kw=dict(width_ratios=[1, 1, 1.3, 1, 1]))
    ax = axes[0]
    n = np.arange(4)
    ax.plot(n, [1, 0, -1, 0], "o-", color=BLUE, label="[1,0,−1,0]")
    ax.plot(n, [0, 1, 0, -1], "s--", color=ORA, label="[0,1,0,−1]")
    ax.set_title("① 振幅谱都是 [0,2,0,2],\n差别全在相位:右移了一格", fontsize=10, loc="left")
    ax.legend(fontsize=8.5, loc="lower left")
    ax.set_xticks(n)
    ax.set_ylim(-1.5, 1.6)
    ax = axes[1]
    ax.stem(n, [1, 0, 0, 0], linefmt=BLUE, markerfmt="o", basefmt=" ", label="[1,0,0,0]")
    ax.plot(n + 0.12, y4, "s", color=ORA, label="[0.5,−0.5,0.5,0.5]")
    ax.set_title("② 振幅全是 1,只改相位\n冲激就变成另一个信号", fontsize=10, loc="left")
    ax.legend(fontsize=8.5, loc="upper right")
    ax.set_xticks(n)
    ax.set_ylim(-0.8, 1.3)
    ax = axes[2]
    k = np.arange(N)
    ax.plot(k, imp, color=BLUE, lw=2, label="相位对齐:冲激")
    ax.plot(k, scr, color=ORA, lw=1.5, label="相位打乱:散开")
    ax.set_title("③ 32 点:振幅谱完全相同,\n波峰对齐才叠出尖峰", fontsize=10, loc="left")
    ax.legend(fontsize=8.5, loc="upper left")
    ax.set_ylim(-0.6, 1.3)
    ax.set_xlabel("采样点", fontsize=9)
    for a_, im, t in ((axes[3], cam, "④ camera 原图"), (axes[4], mix, f"⑤ camera 幅度 + coins 相位\n像 coins(相关 {r_coin:.3f})")):
        a_.imshow(im, cmap="gray", vmin=0 if im is cam else im.min(), vmax=255 if im is cam else im.max())
        a_.set_title(t, fontsize=10)
        a_.axis("off")
    four_questions(
        fig,
        did="保持振幅谱不变,只改相位,\n看信号和图像变成什么",
        gained="相位决定「东西在哪」:\n平移、尖峰、边缘、图像结构\n都由相位决定",
        lost="只保存振幅会丢掉位置:\n同一张振幅谱可以对应\n完全不同的信号",
        limit="⑤ 的相关是 0.574 不是 1:\n振幅也有用,它决定每种\n纹理有多强",
        better="频域滤波用零相移滤波器\n(实数、对称),只改振幅、\n不动相位",
        y=0.06, bottom=0.30)
    save(fig, "phase-matters.png")


if __name__ == "__main__":
    d = numbers()
    fig_basis(d["c"])
    fig_phase(d["y"])
