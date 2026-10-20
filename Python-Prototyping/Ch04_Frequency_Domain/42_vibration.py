"""42《振动信号与逆变换》:模拟一段带轴承故障的振动信号,演示「改频谱 + 逆变换」——
配合 Documents/数学基础/快速路线/6.振动信号与逆变换.md。

模拟信号(采样 20 kHz,1 秒):
  转轴 30 Hz(1 倍频)+ 60 Hz(2 倍频)+ 50 Hz 工频干扰 + 白噪声
  + 轴承外圈故障:每秒「磕」107 次,每次激起 3000 Hz 的结构共振,1.5 ms 内衰减掉

演示:
 1. 原始波形里看不出冲击;频谱里能看到 30/50/60 Hz 三根线和 3 kHz 附近一片「鼓包」
 2. 挖掉 50 Hz(陷波)→ 逆变换 → 干净的低频波形
 3. 只留 2.5~3.5 kHz(带通)→ 逆变换 → 冲击一个个露出来;尖峰度大增
 4. 取冲击的外轮廓(包络)再看频谱 → 峰在 107 Hz,就是设定的故障频率
 5. 傅里叶的短板:只响 50 ms 的声音,在整段频谱里被稀释;分段做(短时傅里叶)能看出何时出现

三张图:vib-raw.png、vib-recover.png、vib-stft.png

用法:
    .venv/bin/python Ch04_Frequency_Domain/42_vibration.py
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
FS, T = 20000, 1.0
F_SHAFT, F_MAINS, F_FAULT, F_RES = 30.0, 50.0, 107.0, 3000.0
RNG = np.random.default_rng(7)


def head(title: str) -> None:
    print(f"\n{'=' * 8} {title} {'=' * 8}")


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=130, bbox_inches="tight", facecolor="white")
    print(f"  → Documents/数学基础/快速路线/images/{name}")
    plt.close(fig)


def make_signal():
    t = np.arange(int(FS * T)) / FS
    shaft = 1.0 * np.sin(2 * np.pi * F_SHAFT * t) + 0.4 * np.sin(2 * np.pi * 2 * F_SHAFT * t + 0.7)
    mains = 0.6 * np.sin(2 * np.pi * F_MAINS * t)
    noise = 0.4 * RNG.standard_normal(t.size)
    impacts = np.zeros_like(t)
    hits = np.arange(0.003, T, 1 / F_FAULT)
    for h in hits:
        m = t >= h
        dt = t[m] - h
        impacts[m] += 1.0 * np.exp(-dt / 0.0015) * np.sin(2 * np.pi * F_RES * dt)
    return t, shaft, mains, noise, impacts, hits


def band(x: np.ndarray, lo: float, hi: float, keep: bool = True) -> np.ndarray:
    """频域里只保留(keep=True)或挖掉(keep=False)lo~hi Hz,再逆变换回来。"""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(x.size, 1 / FS)
    m = (f >= lo) & (f <= hi)
    X = X * (m if keep else ~m)
    return np.fft.irfft(X, n=x.size)


def envelope(x: np.ndarray) -> np.ndarray:
    """外轮廓:把负频率去掉、正频率加倍,逆变换后取模(解析信号)。"""
    X = np.fft.fft(x)
    h = np.zeros(x.size)
    h[0] = 1
    h[1:x.size // 2] = 2
    h[x.size // 2] = 1
    return np.abs(np.fft.ifft(X * h))


def kurt(x: np.ndarray) -> float:
    x = x - x.mean()
    return float(np.mean(x ** 4) / np.mean(x ** 2) ** 2)


def amp_at(x: np.ndarray, f0: float) -> float:
    X = np.fft.rfft(x) / x.size * 2
    f = np.fft.rfftfreq(x.size, 1 / FS)
    return float(np.abs(X[np.argmin(np.abs(f - f0))]))


def spectrum(x: np.ndarray):
    return np.fft.rfftfreq(x.size, 1 / FS), np.abs(np.fft.rfft(x)) / x.size * 2


def main() -> None:
    t, shaft, mains, noise, impacts, hits = make_signal()
    x = shaft + mains + noise + impacts

    head("1. 原始信号")
    print(f"  冲击单独的最大幅度 {np.abs(impacts).max():.2f};整段信号的最大幅度 {np.abs(x).max():.2f}")
    print(f"  尖峰度(正态噪声约 3,越大越「尖」):原始 {kurt(x):.2f}")
    for f0 in (F_SHAFT, F_MAINS, 2 * F_SHAFT):
        print(f"  频谱 {f0:.0f} Hz 处幅度 {amp_at(x, f0):.3f}")

    head("2. 挖掉 50 Hz → 逆变换")
    low = band(x, 0, 200)
    clean = band(low, 49, 51, keep=False)
    print(f"  50 Hz 幅度:挖之前 {amp_at(low, F_MAINS):.3f},挖之后 {amp_at(clean, F_MAINS):.1e}")
    ref = band(shaft + noise, 0, 200)
    print(f"  与「没有工频的转轴振动」的 RMS 误差:挖之前 {np.sqrt(np.mean((low - ref) ** 2)):.3f},"
          f"挖之后 {np.sqrt(np.mean((clean - ref) ** 2)):.3f}")
    peak_before, peak_after = np.abs(low).max(), np.abs(clean).max()
    print(f"  峰值读数:挖之前 {peak_before:.3f},挖之后 {peak_after:.3f}(真实转轴峰值 {np.abs(band(shaft, 0, 200)).max():.3f})")

    head("3. 只留 2.5~3.5 kHz → 逆变换:冲击露出来")
    bp = band(x, 2500, 3500)
    print(f"  尖峰度:原始 {kurt(x):.2f} → 带通后 {kurt(bp):.2f}")

    head("4. 包络谱:冲击每秒多少次")
    env = envelope(bp)
    env = env - env.mean()
    f_e, S_e = spectrum(env)
    sel = (f_e > 20) & (f_e < 500)
    f_peak = f_e[sel][np.argmax(S_e[sel])]
    print(f"  包络谱峰值在 {f_peak:.0f} Hz(设定的故障频率 {F_FAULT:.0f} Hz);冲击间隔 {1000 / f_peak:.2f} ms")
    f_r, S_r = spectrum(x)
    sel_r = (f_r > 20) & (f_r < 500)
    print(f"  对比:原始信号的频谱在 0~500 Hz 里最高峰是 {f_r[sel_r][np.argmax(S_r[sel_r])]:.0f} Hz,"
          f"107 Hz 处幅度只有 {amp_at(x, F_FAULT):.3f}")

    # ---------------- 图 1
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.0))
    w = (t >= 0.2) & (t < 0.3)
    ax = axes[0]
    ax.plot(t[w] * 1000, x[w], color="#222", lw=0.6)
    for h in hits[(hits >= 0.2) & (hits < 0.3)]:
        ax.axvline(h * 1000, color=RED, lw=0.6, alpha=0.5)
    ax.set_title("① 原始波形(100 ms):红线是实际冲击时刻,\n波形里完全看不出来", fontsize=10.5, loc="left")
    ax.set_xlabel("时间(ms)", fontsize=9)
    f, S = spectrum(x)
    ax = axes[1]
    ax.plot(f, S, color=BLUE, lw=0.7)
    ax.axvspan(2500, 3500, color=ORA, alpha=0.15)
    ax.text(3700, 0.5, "3 kHz 附近\n一片鼓包:\n结构共振", fontsize=9, color=ORA)
    ax.set_xlim(0, 6000)
    ax.set_ylim(0, 1.15)
    ax.set_xlabel("频率(Hz)", fontsize=9)
    ax.set_title("② 频谱 0~6000 Hz", fontsize=10.5, loc="left")
    ax = axes[2]
    ax.plot(f, S, color=BLUE, lw=1)
    for f0, lab, col in ((F_SHAFT, "30 Hz 转轴", GREEN), (F_MAINS, "50 Hz 工频", RED), (2 * F_SHAFT, "60 Hz 2 倍频", GREEN)):
        ax.annotate(lab, (f0, amp_at(x, f0)), xytext=(f0 + 12, amp_at(x, f0) + 0.06), fontsize=9, color=col)
    ax.annotate(f"107 Hz 故障频率:\n几乎看不见({amp_at(x, F_FAULT):.3f})", (F_FAULT, amp_at(x, F_FAULT)),
                xytext=(125, 0.25), fontsize=9, color=PURPLE, arrowprops=dict(arrowstyle="->", color=PURPLE))
    ax.set_xlim(0, 250)
    ax.set_ylim(0, 1.15)
    ax.set_xlabel("频率(Hz)", fontsize=9)
    ax.set_title("③ 放大 0~250 Hz:三根线清清楚楚", fontsize=10.5, loc="left")
    four_questions(
        fig,
        did="模拟一段振动:转轴、工频、\n噪声,外加每秒 107 次的\n轴承冲击",
        gained="频谱一眼看出 30/50/60 Hz\n和 3 kHz 共振带;\n只做正变换就能判断这些",
        lost="冲击被淹没:波形里看不见,\n频谱里 107 Hz 处也几乎\n没有峰",
        limit="频谱只说「有哪些频率」,\n不说冲击在什么时刻、\n间隔多少",
        better="改频谱再逆变换(下一张图)",
        y=0.08, bottom=0.30)
    save(fig, "vib-raw.png")

    # ---------------- 图 2
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.0))
    ax = axes[0]
    ax.plot(t[w] * 1000, low[w], color=GRAY, lw=1, label=f"挖之前(峰值 {peak_before:.2f})")
    ax.plot(t[w] * 1000, clean[w], color=GREEN, lw=1.5, label=f"挖掉 50 Hz 后(峰值 {peak_after:.2f})")
    ax.set_title("① 陷波去工频 → 逆变换:\n得到干净的转轴振动,峰值读数才可信", fontsize=10.5, loc="left")
    ax.set_xlabel("时间(ms)", fontsize=9)
    ax.set_ylim(-3.2, 3.6)
    ax.legend(fontsize=8.5, loc="upper right")
    ax = axes[1]
    ax.plot(t[w] * 1000, bp[w], color=ORA, lw=0.7)
    for h in hits[(hits >= 0.2) & (hits < 0.3)]:
        ax.axvline(h * 1000, color=RED, lw=0.6, alpha=0.5)
    ax.set_title(f"② 只留 2.5~3.5 kHz → 逆变换:冲击一个个露出来\n尖峰度 {kurt(x):.1f} → {kurt(bp):.1f}", fontsize=10.5, loc="left")
    ax.set_xlabel("时间(ms)", fontsize=9)
    ax = axes[2]
    ax.plot(f_e, S_e, color=PURPLE, lw=1.2)
    for k in (1, 2, 3):
        ax.axvline(F_FAULT * k, color=RED, ls=":", lw=1)
    ax.text(F_FAULT + 25, S_e[sel].max() * 0.75, f"{f_peak:.0f} Hz = 设定的故障频率\n(虚线是它的 1、2、3 倍)", fontsize=9, color=RED)
    ax.set_xlim(0, 400)
    ax.set_xlabel("频率(Hz)", fontsize=9)
    ax.set_title("③ 取冲击的外轮廓(包络)再看频谱:\n峰值就是每秒磕几次", fontsize=10.5, loc="left")
    four_questions(
        fig,
        did="频域里挖掉 50 Hz、或只留\n共振带,再逆变换回时间;\n最后看冲击外轮廓的频谱",
        gained="干净的波形和峰值;被淹没的\n冲击重新可见;包络谱峰值\n107 Hz 对上故障频率",
        lost="带通把转轴振动整个扔掉了;\n挖 50 Hz 也会把真正 50 Hz\n的机械振动一起挖掉",
        limit="共振带要先从频谱里找对;\n转速变化时故障频率会漂,\n峰会变宽",
        better="转速变化时先按转速重采样\n(阶次分析),再做包络",
        y=0.08, bottom=0.30)
    save(fig, "vib-recover.png")

    # ---------------- 图 3 短板
    head("5. 只响 50 ms 的声音:整段频谱 vs 分段频谱")
    y = 0.3 * RNG.standard_normal(t.size) + np.sin(2 * np.pi * F_SHAFT * t)
    burst = (t >= 0.60) & (t < 0.65)
    y[burst] += 1.0 * np.sin(2 * np.pi * 800 * t[burst])
    f, S = spectrum(y)
    a_full = amp_at(y, 800)
    seg = y[burst]
    a_seg = float(np.abs(np.fft.rfft(seg)[np.argmin(np.abs(np.fft.rfftfreq(seg.size, 1 / FS) - 800))]) / seg.size * 2)
    print(f"  800 Hz 只响 50 ms(幅度 1.0):整段 1 秒频谱里幅度 {a_full:.3f};只看那 50 ms 幅度 {a_seg:.3f}")
    nwin, hop = 1024, 256
    win = np.hanning(nwin)
    frames = np.array([np.abs(np.fft.rfft(y[i:i + nwin] * win)) for i in range(0, y.size - nwin, hop)])
    tf = (np.arange(frames.shape[0]) * hop + nwin / 2) / FS
    ff = np.fft.rfftfreq(nwin, 1 / FS)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.0))
    ax = axes[0]
    ax.plot(t * 1000, y, color="#222", lw=0.4)
    ax.axvspan(600, 650, color=ORA, alpha=0.25)
    ax.set_title("① 1 秒的信号,800 Hz 只在\n600~650 ms 响了一下(橙色)", fontsize=10.5, loc="left")
    ax.set_xlabel("时间(ms)", fontsize=9)
    ax = axes[1]
    ax.plot(f, S, color=BLUE, lw=0.8)
    ax.annotate(f"800 Hz:只有 {a_full:.3f}\n(实际幅度 1.0)", (800, a_full), xytext=(1100, 0.35), fontsize=9,
                color=ORA, arrowprops=dict(arrowstyle="->", color=ORA))
    ax.set_xlim(0, 2000)
    ax.set_ylim(0, 1.1)
    ax.set_xlabel("频率(Hz)", fontsize=9)
    ax.set_title("② 整段做一次傅里叶:\n短暂的声音被平均稀释了", fontsize=10.5, loc="left")
    ax = axes[2]
    ax.pcolormesh(tf * 1000, ff, 20 * np.log10(frames.T + 1e-6), shading="auto", cmap="magma")
    ax.set_ylim(0, 2000)
    ax.set_xlabel("时间(ms)", fontsize=9)
    ax.set_ylabel("频率(Hz)", fontsize=9)
    ax.set_title("③ 切成小段各做一次(短时傅里叶):\n看得出何时出现了 800 Hz", fontsize=10.5, loc="left")
    four_questions(
        fig,
        did="同一段信号:整段做一次\n傅里叶,和切成 51 ms 小段\n各做一次排起来",
        gained=f"分段后,800 Hz 在 600~650 ms\n亮起来;只看那 50 ms\n幅度 {a_seg:.2f}",
        lost=f"整段频谱里它只剩 {a_full:.3f},\n且完全不知道发生在\n哪个时刻",
        limit="段切得越短,时刻越准,\n但频率分辨率越差;\n两者不能同时最好",
        better="需要兼顾时就用小波",
        y=0.08, bottom=0.30)
    save(fig, "vib-stft.png")


if __name__ == "__main__":
    main()
