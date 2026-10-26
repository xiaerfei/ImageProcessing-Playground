"""46《探针为什么反向转》的数字与配图 —— 配合 Documents/数学基础/快速路线/9.探针为什么反向转.md。

数字(文中每个数都从这里来):
 1. 不同频率相乘积分为 0:sin(2π·2t)·sin(2π·3t) 在 [0,1] 上积出 0;sin²(2π·2t) 积出 0.5
 2. 相位一来单探针就瞎:x(t)=cos(2πt+φ),只用 cos 探针得 0.5cosφ、只用 sin 探针得 −0.5sinφ;
    φ=90° 时 cos 探针给 0,但模始终是 0.5
 3. 两个坐标反推角度:实部 0.4330、虚部 0.25 → atan2 得 30°,模 0.5
 4. 4 点手算:z=[1, j, −1, −j],负号探针 k=1 得 4(半径 4/4=1);正号探针 k=1 得 0、k=3 得 4
 5. 本轮:正方形 64 点,按振幅取前 K 项重建,K 越大越准

一张图:probe-sign.png(四格)

用法:
    .venv/bin/python Ch04_Frequency_Domain/46_fourier_probe.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import use_cjk_font  # noqa: E402

use_cjk_font()
import matplotlib.pyplot as plt  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "Documents" / "数学基础" / "快速路线" / "images"
BLUE, RED, GREEN, ORA, GRAY = "#2c6fbb", "#c4442a", "#2a8f4a", "#d95f02", "#666"


def head(title: str) -> None:
    print(f"\n{'=' * 8} {title} {'=' * 8}")


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=130, bbox_inches="tight", facecolor="white")
    print(f"  → Documents/数学基础/快速路线/images/{name}")
    plt.close(fig)


def quad(f, a: float = 0.0, b: float = 1.0, n: int = 200001) -> float:
    """[a,b] 上的梯形积分(自己写,免得踩 numpy 版本对 trapz 的改名)。"""
    t = np.linspace(a, b, n)
    y = f(t)
    return float(np.sum((y[1:] + y[:-1]) * 0.5 * (t[1] - t[0])))


def numbers() -> dict:
    two_pi = 2 * np.pi

    head("1. 相乘之后,不同频率为 0、同频率留下常数")
    diff = quad(lambda t: np.sin(two_pi * 2 * t) * np.sin(two_pi * 3 * t))
    same = quad(lambda t: np.sin(two_pi * 2 * t) ** 2)
    print(f"  2Hz × 3Hz 积分 = {diff:.2e}(应为 0)")
    print(f"  2Hz × 2Hz 积分 = {same:.6f}(应为 1/2,这就是那个「多出来的直流」)")

    head("2~3. 相位来了:两个探针各量一半")
    rows = {}
    for phi_deg in (0, 30, 90):
        phi = np.radians(phi_deg)
        x = lambda t, phi=phi: np.cos(two_pi * t + phi)  # noqa: E731
        a = quad(lambda t, x=x: x(t) * np.cos(two_pi * t))       # cos 探针 → 实部
        b = -quad(lambda t, x=x: x(t) * np.sin(two_pi * t))      # e^{-iωt} 的虚部
        rows[phi_deg] = (a, b)
        print(f"  φ={phi_deg:>3}°: 实部 {a:+.4f}(0.5cosφ={0.5 * np.cos(phi):+.4f})  "
              f"虚部 {b:+.4f}(0.5sinφ={0.5 * np.sin(phi):+.4f})  "
              f"模 {np.hypot(a, b):.4f}  辐角 {np.degrees(np.arctan2(b, a)):+.1f}°")
    print("  φ=90° 时实部正好是 0 —— 只用一根探针就全瞎了,但模一点没少")

    head("4. 四个点手算 DFT")
    z = np.array([1, 1j, -1, -1j])
    n = z.size
    for sign, tag in ((-1, "负号 e^{-i2πkt/N}(正变换)"), (+1, "正号 e^{+i2πkt/N}(逆变换用的那个)")):
        coef = [np.sum(z * np.exp(sign * 2j * np.pi * k * np.arange(n) / n)) for k in range(n)]
        got = ", ".join(f"{c.real:+.0f}{c.imag:+.0f}i" for c in coef)
        print(f"  {tag}: [{got}]")
        if sign < 0:
            minus = coef
            print(f"    k=1 得 {coef[1].real:.0f};半径 = 累加值 / N = {coef[1].real:.0f} / {n} = "
                  f"{coef[1].real / n:.0f}(和输入的圆半径 1 对上了)")
        else:
            print(f"    k=1 得 {coef[1].real:.0f}(抓不到),k=3 得 {coef[3].real:.0f} —— "
                  f"逆时针转速 1 被读成了顺时针转速 1")
    print(f"  numpy 对答案:np.fft.fft(z) = {np.fft.fft(z)}")

    head("5. 本轮:项数越多越准(正方形 64 点)")
    corners = np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j])
    ns = 64
    per = np.empty(ns, complex)
    side = np.linspace(0, 1, ns // 4 + 1)[:-1]
    for i in range(4):
        seg = corners[i] + (corners[(i + 1) % 4] - corners[i]) * side
        per[i * (ns // 4):(i + 1) * (ns // 4)] = seg
    X = np.fft.fft(per) / ns
    order = np.argsort(-np.abs(X))
    t = np.arange(ns) / ns
    errs = {}
    for k in (1, 3, 9, 33, 64):
        idx = order[:k]
        recon = np.zeros(ns, complex)
        for j in idx:
            recon = recon + X[j] * np.exp(2j * np.pi * j * t)
        errs[k] = float(np.max(np.abs(recon - per)))
        print(f"  前 {k:>2} 项:最大偏差 {errs[k]:.6f}")
    print(f"  前 5 名的频率编号 {[int(j) for j in order[:5]]}(成对出现:1 与 61 就是 +1 与 −1)")
    print(f"  前 5 名的半径     {[round(float(abs(X[j])), 4) for j in order[:5]]}")
    print("  33 项就已经是 0:正方形的偶数频率全是 0,非零的只有 32 个")
    return dict(diff=diff, same=same, rows=rows, minus=minus, per=per, X=X, order=order, errs=errs)


def figures(d: dict) -> None:
    fig, ax = plt.subplots(2, 2, figsize=(11.5, 7.8))
    two_pi = 2 * np.pi
    tt = np.linspace(0, 1, 2001)

    # ① 不同频率相乘 → 正负抵消;同频率 → 留下直流
    a0 = ax[0, 0]
    p_diff = np.sin(two_pi * 2 * tt) * np.sin(two_pi * 3 * tt)
    p_same = np.sin(two_pi * 2 * tt) ** 2
    a0.fill_between(tt, 0, p_diff, color=BLUE, alpha=0.25)
    a0.plot(tt, p_diff, color=BLUE, lw=1.2, label="2Hz × 3Hz → 积分 0")
    a0.plot(tt, p_same, color=RED, lw=1.6, label="2Hz × 2Hz → 积分 0.5")
    a0.axhline(0, color=GRAY, lw=0.8)
    a0.legend(fontsize=9, loc="upper right")
    a0.set_title("① 频率不同:正负面积刚好抵消", fontsize=11)
    a0.set_xlabel("t / 秒")
    a0.set_ylabel("相乘的结果")

    # ② 相位扫描:两根探针此消彼长,模不变
    a1 = ax[0, 1]
    phi = np.linspace(0, 2 * np.pi, 361)
    a1.plot(np.degrees(phi), 0.5 * np.cos(phi), color=BLUE, lw=2, label="cos 探针(实部)")
    a1.plot(np.degrees(phi), 0.5 * np.sin(phi), color=RED, lw=2, label="sin 探针(虚部)")
    a1.plot(np.degrees(phi), np.full_like(phi, 0.5), color=GREEN, lw=1.4, ls="--", label="模 = 0.5(不变)")
    a1.axhline(0, color=GRAY, lw=0.8)
    a1.plot([90], [0.5], "o", color=GREEN, ms=6)
    a1.annotate("φ=90°:一根给 0,\n另一根顶满", xy=(90, 0.5), xytext=(150, 0.42),
                fontsize=9, color=GREEN, arrowprops=dict(arrowstyle="->", color=GREEN, lw=1))
    a1.legend(fontsize=9, loc="upper right")
    a1.set_title("② 相位怎么晃,两根探针合起来都不丢", fontsize=11)
    a1.set_xlabel("信号相位 φ / 度")
    a1.set_ylabel("探针量出来的值")
    a1.set_xlim(0, 360)

    # ③ 4 点圆:负号探针 vs 正号探针
    a2 = ax[1, 0]
    z = np.array([1, 1j, -1, -1j])
    n = z.size
    ks = np.arange(n)
    minus = np.array([abs(np.sum(z * np.exp(-2j * np.pi * k * np.arange(n) / n))) for k in ks])
    plus = np.array([abs(np.sum(z * np.exp(+2j * np.pi * k * np.arange(n) / n))) for k in ks])
    w = 0.38
    a2.bar(ks - w / 2, minus, w, color=BLUE, label="负号探针(正变换)")
    a2.bar(ks + w / 2, plus, w, color=ORA, label="正号探针")
    a2.set_xticks(ks)
    a2.set_xticklabels([f"k={k}" for k in ks])
    a2.legend(fontsize=9)
    a2.set_title("③ 同一个圆,探针带不带负号,峰落在不同的 k", fontsize=11)
    a2.set_ylabel("|X_k|")

    # ④ 本轮:项数越多越像
    a3 = ax[1, 1]
    per, X, order = d["per"], d["X"], d["order"]
    ns = per.size
    t = np.arange(ns) / ns
    a3.plot(per.real, per.imag, color=GRAY, lw=1.6, ls="--", label="原始正方形")
    for k, c in ((1, ORA), (3, GREEN), (9, BLUE), (33, RED)):
        recon = np.zeros(ns, complex)
        for j in order[:k]:
            recon = recon + X[j] * np.exp(2j * np.pi * j * t)
        recon = np.append(recon, recon[0])
        a3.plot(recon.real, recon.imag, color=c, lw=1.6,
                label=f"前 {k} 项(最大偏差 {d['errs'][k]:.2f})")
    a3.set_aspect("equal")
    a3.legend(fontsize=8.5, loc="upper right")
    a3.set_title("④ 本轮:圆盘越多,描出来的边越像", fontsize=11)
    a3.set_xlabel("x")
    a3.set_ylabel("y")

    fig.suptitle("探针为什么反向转:从「相乘等于 0」到本轮", fontsize=13)
    fig.tight_layout()
    save(fig, "probe-sign.png")


if __name__ == "__main__":
    data = numbers()
    figures(data)
