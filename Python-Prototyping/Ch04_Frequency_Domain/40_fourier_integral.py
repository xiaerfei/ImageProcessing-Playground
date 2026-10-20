"""40《理解傅里叶积分》的数字与配图 —— 配合 Documents/数学基础/快速路线/4.理解傅里叶积分.md。

数字:
 1. 离散点乘 [1,2,3,4]·b1 = −2;细切求和逼近积分
 2. 同频相乘恒 ≥ 0:∫₀^{2π} cos3t·cos3t dt = π;不同频正负抵消:∫ cos3t·cos5t dt = 0
 3. 矩形脉冲(−1≤t≤1 为 1):F(ω) = 2 sinω/ω,在 0、π/2、π、3π/2、2π 处的值
 4. 周期 T 的谱线间隔 2π/T:T 越大越密
 5. 逆变换:由 X = [10, −2+2i, −2, −2−2i] 按 x[n] = (1/N)ΣX[k]e^{+i2πkn/N} 拼回 [1,2,3,4]

配图:fourier-integral.png

用法:
    .venv/bin/python Ch04_Frequency_Domain/40_fourier_integral.py
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
BLUE, ORA, GREEN, RED, GRAY = "#2c6fbb", "#d98a14", "#2a8f4a", "#c4442a", "#666"
PI = np.pi


def head(title: str) -> None:
    print(f"\n{'=' * 8} {title} {'=' * 8}")


def integ(f, a: float, b: float, n: int = 200000) -> complex:
    """中点求和逼近积分:切成 n 条竖条,每条高 × 宽。"""
    dt = (b - a) / n
    t = a + (np.arange(n) + 0.5) * dt
    return complex(np.sum(f(t)) * dt)


def pulse_F(w: float) -> float:
    return 2.0 if w == 0 else 2 * np.sin(w) / w


def numbers() -> None:
    head("1. 离散点乘 → 积分")
    x = np.array([1, 2, 3, 4])
    b1 = np.array([1, 0, -1, 0])
    print(f"  [1,2,3,4]·[1,0,-1,0] = {x @ b1}")
    for n in (4, 40, 4000):
        print(f"  ∫₀^π sin t dt 切 {n:5d} 条:{integ(np.sin, 0, PI, n).real:.6f}(精确值 2)")

    head("2. 同频恒正、不同频抵消")
    same = integ(lambda t: np.cos(3 * t) ** 2, 0, 2 * PI).real
    diff = integ(lambda t: np.cos(3 * t) * np.cos(5 * t), 0, 2 * PI).real
    print(f"  ∫ cos3t·cos3t = {same:.6f}(π = {PI:.6f});最小值 {np.min(np.cos(3 * np.linspace(0, 2 * PI, 9999)) ** 2):.3f}")
    print(f"  ∫ cos3t·cos5t = {diff:.1e}")

    head("3. 矩形脉冲 F(ω) = 2 sinω/ω")
    for w, name in ((0, "0"), (PI / 2, "π/2"), (PI, "π"), (1.5 * PI, "3π/2"), (2 * PI, "2π")):
        num = integ(lambda t: np.exp(-1j * w * t), -1, 1)
        print(f"  ω={name:5s} 数值积分 {num.real:+.4f}{num.imag:+.1e}i,公式 {pulse_F(w):+.4f}")

    head("4. 谱线间隔 2π/T")
    for T in (2 * PI, 20 * PI, 200 * PI):
        print(f"  T = {T / PI:.0f}π:间隔 {2 * PI / T:.3f}")

    head("5. 逆变换拼回 [1,2,3,4]")
    X = np.array([10, -2 + 2j, -2, -2 - 2j])
    N = 4
    for n in range(N):
        terms = X * np.exp(1j * 2 * PI * np.arange(N) * n / N)
        print(f"  x[{n}] = (1/4)·({' + '.join(f'{t.real:+.0f}{t.imag:+.0f}i' for t in np.round(terms, 9))}) = {terms.sum().real / N:.4f}")
    print(f"  np.fft.ifft:{np.fft.ifft(X).real}")


def fig() -> None:
    t = np.linspace(0, 2 * PI, 2001)
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.2))
    for ax, (g, title, total, col) in zip(axes[:2], [
            (np.cos(3 * t) ** 2, "① 同频率:cos3t × cos3t\n乘出来永远 ≥ 0,越积越多", PI, GREEN),
            (np.cos(3 * t) * np.cos(5 * t), "② 不同频率:cos3t × cos5t\n正负面积相等,互相抵消", 0.0, RED)]):
        ax.plot(t, g, color="#222", lw=1.2)
        ax.fill_between(t, g, 0, where=g >= 0, color=GREEN, alpha=0.35, label="正面积")
        ax.fill_between(t, g, 0, where=g < 0, color=RED, alpha=0.35, label="负面积")
        ax.axhline(0, color="#999", lw=0.8)
        ax.text(0.05, 0.93, f"积分 = {total:.4f}" if total else "积分 = 0", transform=ax.transAxes,
                fontsize=10, color=col)
        ax.set_title(title, fontsize=10.5, loc="left")
        ax.set_xticks([0, PI, 2 * PI])
        ax.set_xticklabels(["0", "π", "2π"])
        ax.set_ylim(-1.15, 1.3)
        ax.legend(fontsize=8.5, loc="upper right")
    ax = axes[2]
    w = np.linspace(-4 * PI, 4 * PI, 2001)
    Fw = np.where(w == 0, 2.0, 2 * np.sin(w) / np.where(w == 0, 1, w))
    ax.plot(w, Fw, color=BLUE, lw=2)
    ax.axhline(0, color="#999", lw=0.8)
    for wv, name in ((0, "0"), (PI / 2, "π/2"), (PI, "π"), (1.5 * PI, "3π/2"), (2 * PI, "2π")):
        v = round(pulse_F(wv), 9) + 0.0  # 去掉 -0.00
        ax.plot([wv], [v], "o", color=ORA, ms=5)
        ax.annotate(f"{name}:{v:.2f}", (wv, v), xytext=(wv + 0.4, v + (0.25 if v >= 0 else -0.35)), fontsize=8.5, color=ORA)
    ax.set_xticks([-4 * PI, -2 * PI, 0, 2 * PI, 4 * PI])
    ax.set_xticklabels(["−4π", "−2π", "0", "2π", "4π"])
    ax.set_xlabel("探针频率 ω", fontsize=9)
    ax.set_ylim(-0.8, 2.5)
    ax.set_title("③ 矩形脉冲(−1~1 为 1)的频谱\nF(ω) = 2 sinω / ω,在 π 的整数倍处为 0", fontsize=10.5, loc="left")
    four_questions(
        fig,
        did="把「探针 × 信号」画出来,\n看正负面积;再对矩形脉冲\n逐个 ω 做积分",
        gained="同频乘积恒正、积出 π;\n不同频正负抵消、积出 0;\n脉冲的频谱是 2 sinω/ω",
        lost="积分只告诉你「有多少」,\n不直接告诉你这个频率出现在\n哪一段时间(藏在相位里)",
        limit="要从 −∞ 积到 +∞:\n信号两头不衰减到 0 时\n(如 cos t),积分不收敛",
        better="想知道「何时出现哪个频率」,\n看短时傅里叶变换或小波",
        y=0.08, bottom=0.30)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "fourier-integral.png", dpi=130, bbox_inches="tight", facecolor="white")
    print("  → Documents/数学基础/快速路线/images/fourier-integral.png")
    plt.close(fig)


if __name__ == "__main__":
    numbers()
    fig()
