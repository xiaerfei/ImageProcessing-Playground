"""38《理解傅里叶变换》(李永乐老师科普视频笔记)的配图与数字 ——
配合 Documents/数学基础/快速路线/2.理解傅里叶变换.md。

三张图:
 1. ft-series.png   周期信号 = 三个正弦相加;时域看是一条线,频域看是三根竖线(振幅)+ 相位
 2. ft-probe.png    用转圈探针做内积:含这个频率 → 非零,不含 → 0;
                    平移只改实部虚部,不改模(订正视频「实部=振幅、虚部=相位」)
 3. ft-lowpass.png  图像去高频 = 磨皮;去太多眼睛鼻子也没了;保边滤波做对比

用法:
    .venv/bin/python Ch04_Frequency_Domain/38_fourier_figures.py
会在 Documents/数学基础/快速路线/images/ 下生成三张 png,并打印文中用到的数字
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
BLUE, ORA, GREEN, RED, GRAY = "#2c6fbb", "#d98a14", "#2a8f4a", "#c4442a", "#666"
# 三个分量:频率倍数、振幅、相位(弧度),仿视频黑板上「ω 小、2ω 大、3ω 很小」
PARTS = [(1, 0.6, 0.0), (2, 1.0, np.pi / 2), (3, 0.25, np.pi)]


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=130, bbox_inches="tight", facecolor="white")
    print(f"  → Documents/数学基础/快速路线/images/{name}")
    plt.close(fig)


def head(title: str) -> None:
    print(f"\n{'=' * 8} {title} {'=' * 8}")


# ---------------------------------------------------------------- 1
def fig_series() -> None:
    head("1. 周期信号 = 三个正弦相加")
    N = 512
    t = np.arange(N) / N * 2 * np.pi  # 正好一个基本周期
    comps = [a * np.sin(k * t + p) for k, a, p in PARTS]
    f = sum(comps)
    # 用 DFT 把振幅、相位读回来(sin(kt+p) 的复系数 = A/2 · e^{i(p-π/2)})
    F = np.fft.fft(f) / (N / 2)
    for k, a, p in PARTS:
        amp, ph = abs(F[k]), np.angle(F[k]) + np.pi / 2
        ph = (ph + np.pi) % (2 * np.pi) - np.pi
        print(f"  {k}ω:设定振幅 {a},读回 {amp:.4f};设定相位 {p:.4f},读回 {abs(ph) if abs(abs(ph) - np.pi) < 1e-9 else ph:.4f}")
    others = np.abs(F[4:N // 2]).max()
    print(f"  其余频率读回的最大振幅 {others:.1e}(只有三根竖线)")
    rebuilt = np.fft.ifft(F * (N / 2)).real
    print(f"  逆变换拼回与原信号最大差 {np.abs(rebuilt - f).max():.1e}")

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.0), gridspec_kw=dict(width_ratios=[1.6, 1, 1]))
    ax = axes[0]
    cols = [BLUE, ORA, GREEN]
    for (k, a, p), c, col in zip(PARTS, comps, cols):
        ax.plot(t, c - 2.4 * (PARTS.index((k, a, p)) + 1), color=col, lw=1.4)
        ax.text(0.05, -2.4 * (PARTS.index((k, a, p)) + 1) + a + 0.15, f"{k}ω,振幅 {a}", fontsize=9, color=col)
    ax.plot(t, f + 1.2, color="#222", lw=2)
    ax.text(0.05, 2.3, "三个相加 = 原信号", fontsize=9)
    ax.set_xlim(0, 2 * np.pi)
    ax.set_yticks([])
    ax.set_xticks([0, np.pi, 2 * np.pi])
    ax.set_xticklabels(["0", "半个周期", "一个周期"], fontsize=8.5)
    ax.set_title("① 时域:一条弯曲的线,其实是三个正弦叠起来", fontsize=10.5, loc="left")
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax = axes[1]
    ks = [k for k, _, _ in PARTS]
    ax.bar(ks, [a for _, a, _ in PARTS], color=cols, width=0.35)
    for k, a, _ in PARTS:
        ax.text(k, a + 0.03, f"{a}", ha="center", fontsize=9.5)
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.set_xticklabels(["ω", "2ω", "3ω", "4ω", "5ω"])
    ax.set_ylim(0, 1.2)
    ax.set_title("② 频域:每个频率的振幅(一根根竖线)", fontsize=10.5, loc="left")
    ax.set_xlabel("频率", fontsize=9)
    ax = axes[2]
    ax.bar(ks, [p for _, _, p in PARTS], color=cols, width=0.35)
    for k, _, p in PARTS:
        ax.text(k, p + 0.08, ["0", "π/2", "π"][ks.index(k)], ha="center", fontsize=9.5)
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.set_xticklabels(["ω", "2ω", "3ω", "4ω", "5ω"])
    ax.set_ylim(0, 3.8)
    ax.set_title("③ 频域:每个频率的相位(从哪起步)", fontsize=10.5, loc="left")
    ax.set_xlabel("频率", fontsize=9)
    four_questions(
        fig,
        did="把一个周期信号拆成 ω、2ω、\n3ω 三个正弦,分别记下\n振幅和相位",
        gained="三样信息(频率、振幅、相位)\n就能逆变换拼回原信号,\n最大差 6.9e-16",
        lost="只看振幅图(②)会丢掉\n相位,单凭振幅拼不回原样",
        limit="只适用于周期信号;\n非周期信号要用连续傅里叶\n变换,频谱变成连续的",
        better="计算机里用 DFT/FFT,\n把积分换成 N 项求和",
        y=0.08, bottom=0.30)
    save(fig, "ft-series.png")


# ---------------------------------------------------------------- 2
def fig_probe() -> None:
    head("2. 转圈探针做内积;平移只改实部虚部,不改模")
    dt = 0.001
    t = np.arange(-10, 10, dt)
    env = np.exp(-t ** 2 / 8)  # 非周期:两头衰减到 0
    sig = env * (np.cos(3 * t) + 0.5 * np.cos(7 * t))
    ws = np.linspace(0, 10, 501)
    F = np.array([np.sum(sig * np.exp(-1j * w * t)) * dt for w in ws])
    for w in (3, 5, 7):
        val = np.sum(sig * np.exp(-1j * w * t)) * dt
        print(f"  探针 ω={w}:|F| = {abs(val):.4f}")
    # 平移:cos(3(t-d)) 的 F(3) 实部虚部随 d 变,模不变
    rows = []
    for d in (0.0, 0.25, 0.5):
        s = np.exp(-(t - d) ** 2 / 8) * np.cos(3 * (t - d))
        v = np.sum(s * np.exp(-1j * 3 * t)) * dt
        rows.append((d, v))
        print(f"  平移 {d}:F(3) = {v.real:+.4f}{v.imag:+.4f}i,模 {abs(v):.4f},辐角 {np.angle(v):+.4f}(理论 −3·d = {-3 * d:+.4f})")

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.0))
    ax = axes[0]
    ax.plot(t, sig, color="#222", lw=1.2)
    ax.set_xlim(-8, 8)
    ax.set_title("① 非周期信号:两头衰减到 0", fontsize=10.5, loc="left")
    ax.set_xlabel("时间 t", fontsize=9)
    ax = axes[1]
    ax.plot(ws, np.abs(F), color=BLUE, lw=2)
    for w in (3, 5, 7):
        val = abs(F[np.argmin(np.abs(ws - w))])
        ax.plot([w], [val], "o", color=RED if w == 5 else GREEN, ms=6)
        ax.annotate(f"ω={w}:{val:.2f}", (w, val), xytext=(w - 0.9, val + 0.35 if w != 5 else 0.7), fontsize=9,
                    color=RED if w == 5 else GREEN)
    ax.set_title("② 每个 ω 用探针做一次内积:\n含 3、7 → 非零;不含 5 → 约 0", fontsize=10.5, loc="left")
    ax.set_xlabel("探针频率 ω", fontsize=9)
    ax.set_ylabel("|F(ω)|", fontsize=9)
    ax.set_ylim(0, 4.6)
    ax = axes[2]
    ax.add_patch(plt.Circle((0, 0), abs(rows[0][1]), fill=False, ls="--", color="#bbb"))
    for (d, v), col in zip(rows, [BLUE, ORA, GREEN]):
        ax.annotate("", (v.real, v.imag), (0, 0), arrowprops=dict(arrowstyle="->", color=col, lw=2))
        ax.text(v.real * 1.08, v.imag * 1.08 + 0.12, f"平移 {d}\n实 {v.real:.2f} 虚 {v.imag:.2f}", fontsize=8.5, color=col)
    ax.axhline(0, color="#ccc", lw=0.8)
    ax.axvline(0, color="#ccc", lw=0.8)
    ax.set_xlim(-1.5, 4.8)
    ax.set_ylim(-4.2, 1.6)
    ax.set_aspect("equal")
    ax.set_title("③ 同一分量平移:实部虚部都变,\n箭头长度(模 = 振幅)不变,只转角度(相位)", fontsize=10.5, loc="left")
    ax.set_xlabel("实部", fontsize=9)
    ax.set_ylabel("虚部", fontsize=9)
    four_questions(
        fig,
        did="对每个 ω,用顺时针转的\n探针 e^(-iωt) 乘信号再积分,\n得到复数 F(ω)",
        gained="信号里有的频率(3、7)冒出峰,\n没有的(5)几乎为 0;\n频谱是连续的",
        lost="F(ω) 是复数,要拆成\n模(振幅)和辐角(相位)\n两张图才看得懂",
        limit="实部、虚部不是振幅和相位:\n平移后实部虚部都变,\n只有模不变",
        better="想看相位就画 arg F(ω);\n离散信号用 np.fft",
        y=0.08, bottom=0.30)
    save(fig, "ft-probe.png")


# ---------------------------------------------------------------- 3
def lowpass(img: np.ndarray, r: int) -> tuple[np.ndarray, float]:
    F = np.fft.fftshift(np.fft.fft2(img))
    h, w = img.shape
    yy, xx = np.ogrid[:h, :w]
    mask = (yy - h // 2) ** 2 + (xx - w // 2) ** 2 <= r * r
    kept = (np.abs(F[mask]) ** 2).sum() / (np.abs(F) ** 2).sum()
    out = np.fft.ifft2(np.fft.ifftshift(F * mask)).real
    return np.clip(out, 0, 255), kept


def fig_lowpass() -> None:
    head("3. 图像去高频 = 磨皮")
    img = cv2.imread(str(IMAGES / "astronaut.png"), cv2.IMREAD_GRAYSCALE)
    img = cv2.resize(img, (256, 256), interpolation=cv2.INTER_AREA).astype(float)
    spec = np.log1p(np.abs(np.fft.fftshift(np.fft.fft2(img))))
    lp1, k1 = lowpass(img, 40)
    lp2, k2 = lowpass(img, 10)
    bil = cv2.bilateralFilter(img.astype(np.uint8), 9, 40, 9).astype(float)
    area1 = np.pi * 40 ** 2 / 256 ** 2
    area2 = np.pi * 10 ** 2 / 256 ** 2
    print(f"  半径 40:保留 {area1 * 100:.1f}% 的频率点,{k1 * 100:.2f}% 的能量")
    print(f"  半径 10:保留 {area2 * 100:.2f}% 的频率点,{k2 * 100:.2f}% 的能量")

    fig, axes = plt.subplots(1, 5, figsize=(16, 4.0))
    panels = [(img, "① 原图"), (spec, "② 频谱(中心低频,外圈高频)"),
              (lp1, f"③ 只留中心半径 40\n({area1 * 100:.1f}% 的点,{k1 * 100:.1f}% 能量)"),
              (lp2, f"④ 只留半径 10:轮廓还在,\n五官糊了({k2 * 100:.1f}% 能量)"),
              (bil, "⑤ 保边滤波(双边):\n抹平细纹,边缘还在")]
    for ax, (im, title) in zip(axes, panels):
        if im is spec:
            ax.imshow(im, cmap="magma")
            for r, col in ((40, GREEN), (10, ORA)):
                ax.add_patch(plt.Circle((128, 128), r, fill=False, color=col, lw=1.4))
        else:
            ax.imshow(im, cmap="gray", vmin=0, vmax=255)
        ax.set_title(title, fontsize=10)
        ax.axis("off")
    four_questions(
        fig,
        did="对图像做二维傅里叶变换,\n只保留中心一小圈低频,\n再逆变换回来",
        gained="斑点、细纹这类高频细节\n消失,画面变光滑;\n只用很少的频率点",
        lost="边缘也是高频:去得越多,\n眼睛、鼻子的轮廓越糊,\n还会出现一圈圈振铃",
        limit="低通分不清「斑点」和\n「五官边缘」,两者都是高频,\n一起被抹掉",
        better="真正的磨皮用保边滤波\n(双边、导向滤波)",
        y=0.06, bottom=0.30)
    save(fig, "ft-lowpass.png")


if __name__ == "__main__":
    fig_series()
    fig_probe()
    fig_lowpass()
