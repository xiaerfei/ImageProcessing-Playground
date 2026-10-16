"""第 11 周前置:35 复变函数第三章「复变函数的积分」的手算复核 ——
配合 Documents/数学基础/复变函数/03-复变函数的积分.md。

笔记按《复变函数与积分变换》(华中科技大学数学系,第 5 版)第 3 章整理。
笔记里的每个数字、每道过关题的答案,都由本脚本重新算一遍;
书上例 3.1~3.12 里能数值验证的也在这里核对过,没有出入。

  1. 复积分 = 数值求和 Σ f(ζ)Δz;例 3.1(路径有关)、例 3.3(路径无关)、例 3.4 估值
  2. ∮ dz/(z-z0)^n:只有 n=1 是 2πi,与圆心半径无关(例 3.2)
  3. 柯西积分定理:解析 → 闭路积分 0;不解析(z̄、1/z)→ 非 0;路径无关;原函数公式(例 3.6、3.8、3.9)
  4. 闭路变形与复合闭路(例 3.7)
  5. 柯西积分公式与平均值公式(例 3.10)
  6. 高阶导数公式(例 3.12)、柯西不等式、最大模原理、刘维尔定理
  7. 习题三的计算题(3.1~3.13)
  + 配图:∮ z^n dz 随 n 变化(只有 n=-1 是 2πi),以及圆周上被积函数的「绕圈累加」

⚠️ 书末「部分习题答案」(印刷页 216 起)我没有读,本脚本的答案是自己算的,没有和书对过。

用法:
    .venv/bin/python Ch04_Frequency_Domain/35_complex_ch3.py
会在 Documents/数学基础/复变函数/images/ 下生成 complex-ch3-contour.png
"""

from __future__ import annotations

import sys
from math import factorial
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import four_questions, use_cjk_font  # noqa: E402

use_cjk_font()
import matplotlib.pyplot as plt  # noqa: E402

I = 1j
PI = np.pi


def head(title: str) -> None:
    print(f"\n{'=' * 8} {title} {'=' * 8}")


def c(z: complex, nd: int = 4) -> str:
    z = complex(z)
    re = 0.0 if abs(z.real) < 10 ** (-nd - 1) else z.real
    im = 0.0 if abs(z.imag) < 10 ** (-nd - 1) else z.imag
    if im == 0:
        return f"{re:.{nd}f}"
    if re == 0:
        return f"{im:.{nd}f}i"
    return f"{re:.{nd}f}{im:+.{nd}f}i"


def line_int(f, a: complex, b: complex, n: int = 200000) -> complex:
    """沿直线段 a→b 的复积分(中点法则)。"""
    t = (np.arange(n) + 0.5) / n
    z = a + (b - a) * t
    return np.sum(f(z)) * (b - a) / n


def poly_int(f, pts: list[complex], n: int = 200000) -> complex:
    return sum(line_int(f, pts[k], pts[k + 1], n) for k in range(len(pts) - 1))


def circ_int(f, z0: complex, r: float, n: int = 200000) -> complex:
    """沿圆周 |z-z0|=r 逆时针一圈的复积分(中点法则)。"""
    th = (np.arange(n) + 0.5) * 2 * PI / n
    z = z0 + r * np.exp(1j * th)
    return np.sum(f(z) * 1j * r * np.exp(1j * th)) * 2 * PI / n


# ---------------------------------------------------------------- 1 定义
def step1_definition() -> None:
    head("1 复积分的计算")
    print("定义:∫ f dz = lim Σ f(ζk)Δzk。取 f=z²,直线 0→3+4i,ζk 取每段左端点,分成 n 段求和:")
    a, b = 0j, 3 + 4j
    exact = (b ** 3 - a ** 3) / 3
    for n in (4, 40, 400, 4000):
        zs = a + (b - a) * np.arange(n + 1) / n
        sm = np.sum(zs[:-1] ** 2 * np.diff(zs))
        print(f"   n={n:>4}:Σ f(ζ)Δz = {c(sm, 4)},与精确值差 {abs(sm - exact):.3e}")
    print(f"   精确值 (b³-a³)/3 = {c(exact)}(n 每扩大 10 倍,误差缩小约 10 倍)")
    print(f"例3.3 ∫z dz = ½(3+4i)² = {c(0.5 * (3 + 4j) ** 2)};直线 0→3+4i 数值 {c(line_int(lambda z: z, a, b))};"
          f"折线 0→3→3+4i 数值 {c(poly_int(lambda z: z, [0j, 3 + 0j, 3 + 4j]))}(同一个值,路径无关)")

    zb = np.conj
    r1 = line_int(zb, 1 + 0j, 1j)
    r2 = poly_int(zb, [1 + 0j, 0j, 1j])
    print(f"例3.1 ∫z̄ dz:直线 1→i:{c(r1)}(书上 i);折线 1→0→i:{c(r2)}(书上 0)—— 路径不同,结果不同")
    print(f"      原因:z̄ 不解析。对比解析的 z²:直线 1→i = {c(line_int(lambda z: z ** 2, 1 + 0j, 1j))},"
          f"折线 1→0→i = {c(poly_int(lambda z: z ** 2, [1 + 0j, 0j, 1j]))}(一样)")

    f = lambda z: 1 / (z - 1j)
    val = abs(line_int(f, 0j, 3 + 4j))
    print(f"例3.4 |∫ dz/(z-i)|,C:0→3+4i:实际 {val:.4f},书上给的上界 25/3 = {25 / 3:.4f}(上界 ≥ 实际,成立)")
    print("      估值不等式 |∫f dz| ≤ ML:M = max|1/(z-i)| = 5/3(在 t=4/25 处取到),L = 5")
    ts = np.linspace(0, 1, 100001)
    zz = (3 + 4j) * ts
    print(f"      数值 max|1/(z-i)| = {np.max(1 / abs(zz - 1j)):.4f}(5/3 = {5 / 3:.4f})")

    print("例3.5 lim_{r→0} ∮_{|z|=r} z³/(1+z²) dz = 0:")
    for r in (0.5, 0.2, 0.1, 0.05):
        v = circ_int(lambda z: z ** 3 / (1 + z ** 2), 0, r)
        bound = 2 * PI * r ** 4 / (1 - r ** 2)
        print(f"   r={r:>4}:|积分| = {abs(v):.2e}  ≤ 上界 2πr⁴/(1-r²) = {bound:.2e}")


# ---------------------------------------------------------------- 2 ∮ 1/(z-z0)^n
def step2_powers() -> None:
    head("2 ∮ dz/(z-z0)ⁿ:只有 n=1 非零")
    for z0, r in ((0j, 1.0), (2 + 1j, 0.3), (-1 - 2j, 5.0)):
        row = []
        for n in (-2, -1, 0, 1, 2, 3):
            v = circ_int(lambda z: (z - z0) ** (-n), z0, r)
            row.append(f"n={n:>2}:{c(v, 3)}")
        print(f"   圆心 {c(z0, 1):>8},半径 {r}:" + "  ".join(row))
    print(f"   2πi = {c(2 * PI * 1j)}(n=1 时,与圆心、半径无关)")
    print("   原因:z = z0+re^{iθ},dz = i r e^{iθ} dθ,被积函数变成 (i/r^{n-1}) e^{-i(n-1)θ} dθ;")
    th = (np.arange(1000) + 0.5) * 2 * PI / 1000
    for m in (0, 1, 2, 3):
        print(f"   ∫₀^2π e^(-i·{m}·θ) dθ = {c(np.sum(np.exp(-1j * m * th)) * 2 * PI / 1000)}"
              f"({'= 2π,m=0 即 n=1' if m == 0 else '转满整圈抵消'})")
    print("   ——这和 DFT 里「Σ e^{i2πkm/N} 在 k≠0 时为 0」是同一件事(转满整圈互相抵消)")


# ---------------------------------------------------------------- 3 柯西定理
def step3_cauchy_theorem() -> None:
    head("3 柯西积分定理")
    print("沿 |z|=1 逆时针一圈,解析 → 0,不解析 → 非 0:")
    for name, f in (("z²", lambda z: z ** 2), ("e^z", np.exp), ("sin z", np.sin), ("cos z", np.cos),
                    ("1/(z²+4z+4)(奇点 -2 在圈外)", lambda z: 1 / (z * z + 4 * z + 4)),
                    ("1/cos z(奇点 ±π/2 在圈外)", lambda z: 1 / np.cos(z)),
                    ("z̄", np.conj), ("1/z(奇点 0 在圈内)", lambda z: 1 / z), ("|z|²", lambda z: abs(z) ** 2 + 0j)):
        print(f"   {name:<32} {c(circ_int(f, 0, 1.0), 4)}")
    print(f"   z̄ 的结果 = 2πi·(圆盘面积/π)?∮ z̄ dz = 2i·面积 = {c(2j * PI)}(这里面积 π)——格林公式给的")

    print("路径无关:∫₀^{1+i} z² dz,三条路:")
    f = lambda z: z ** 2
    for name, pts in (("直线", [0j, 1 + 1j]), ("先实轴后垂直", [0j, 1 + 0j, 1 + 1j]), ("先虚轴后水平", [0j, 1j, 1 + 1j])):
        print(f"   {name:<12} {c(poly_int(f, pts))}")
    print(f"   原函数 z³/3:(1+i)³/3 = {c((1 + 1j) ** 3 / 3)}")

    print(f"例3.6 ∫ sin z dz,C 是 |z-1|=1 的上半圆(0→2):换成实轴 0→2:∫sin x dx = 1-cos2 = {1 - np.cos(2):.6f};"
          f"沿上半圆数值 = ", end="")
    th = np.linspace(PI, 0, 400001)
    zc = 1 + np.exp(1j * th)
    dz = np.diff(zc)
    mid = (zc[:-1] + zc[1:]) / 2
    print(c(np.sum(np.sin(mid) * dz), 6))

    print("例3.8 ∫_a^b zⁿ dz = (bⁿ⁺¹ - aⁿ⁺¹)/(n+1):a=1+i,b=2-i,n=3:")
    a, b = 1 + 1j, 2 - 1j
    print(f"   公式 {c((b ** 4 - a ** 4) / 4)};数值(直线)= {c(line_int(lambda z: z ** 3, a, b))}")

    print("例3.9 ∫_C ln(1+z) dz,C:-i→i,书上结果 (-2+ln2+π/2)i:")
    val = line_int(lambda z: np.log(1 + z), -1j, 1j)
    print(f"   数值 {c(val)};公式 {c((-2 + np.log(2) + PI / 2) * 1j)}")


# ---------------------------------------------------------------- 4 闭路变形
def step4_deformation() -> None:
    head("4 闭路变形与复合闭路")
    f = lambda z: 1 / z
    print("闭路变形原理:∮ 1/z dz 沿不同的闭曲线(都绕原点一圈),结果都是 2πi:")
    for name, pts in (("圆 |z|=1", None), ("圆 |z|=3", None)):
        r = 1.0 if "1" in name else 3.0
        print(f"   {name}:{c(circ_int(f, 0, r))}")
    sq = [-2 - 1j, 2 - 1j, 2 + 1j, -2 + 1j, -2 - 1j]
    print(f"   矩形(-2,-1)~(2,1):{c(poly_int(f, sq))}")
    off = [0.5 - 0.5j, 3 - 0.5j, 3 + 2j, 0.5 + 2j, 0.5 - 0.5j]
    print(f"   不绕原点的矩形:{c(poly_int(f, off))}(奇点在圈外,0)")

    g = lambda z: (2 * z - 1) / (z * z - z)
    big = [-2 - 2j, 3 - 2j, 3 + 2j, -2 + 2j, -2 - 2j]
    print(f"例3.7 ∮ (2z-1)/(z²-z) dz,C 是包住 0 和 1 的方框:{c(poly_int(g, big))}(书上 4πi = {c(4j * PI)})")
    print(f"      分解:(2z-1)/(z²-z) = 1/z + 1/(z-1):|z|=½ 圈 0 → {c(circ_int(g, 0, 0.5))};"
          f"|z-1|=½ 圈 1 → {c(circ_int(g, 1, 0.5))};两者之和 {c(circ_int(g, 0, 0.5) + circ_int(g, 1, 0.5))}")
    print(f"      只包 0 的大圈 |z|=0.5:{c(circ_int(g, 0, 0.5))}(= 2πi);只包 1 的 |z-1|=0.5:{c(circ_int(g, 1, 0.5))}")


# ---------------------------------------------------------------- 5 积分公式
def step5_formula() -> None:
    head("5 柯西积分公式与平均值公式")
    print("f(z0) = (1/2πi)∮ f(z)/(z-z0) dz:")
    for name, f, z0, r in (("e^z,z0=0.3+0.2i,|z|=2", np.exp, 0.3 + 0.2j, 2.0),
                           ("z³+2z,z0=-0.5+0.7i,|z|=2", lambda z: z ** 3 + 2 * z, -0.5 + 0.7j, 2.0),
                           ("sin z,z0=0.1,|z|=1", np.sin, 0.1 + 0j, 1.0)):
        val = circ_int(lambda z: f(z) / (z - z0), 0, r) / (2j * PI)
        print(f"   {name:<28} 积分/(2πi) = {c(val, 6)};f(z0) = {c(f(z0), 6)}")
    print("   z0 在圈外 → 0:e^z/(z-5),|z|=2:", c(circ_int(lambda z: np.exp(z) / (z - 5), 0, 2.0)))

    print("平均值公式 f(z0) = (1/2π)∫ f(z0+Re^{iθ}) dθ(圆周上的平均就是圆心的值):")
    th = (np.arange(100000) + 0.5) * 2 * PI / 100000
    for name, f, z0, R in (("e^z", np.exp, 0.3 + 0.2j, 1.5), ("z²+1", lambda z: z ** 2 + 1, 1 - 1j, 0.7)):
        print(f"   {name:<8} 平均 = {c(np.mean(f(z0 + R * np.exp(1j * th))), 6)};f(z0) = {c(f(z0), 6)}")
    print("   对照 |z|²:圆心 z0=1 半径 0.5:平均 =", f"{np.mean(abs(1 + 0.5 * np.exp(1j * th)) ** 2):.4f}", "≠ |1|²=1(不满足,因为 |z|² 不调和)")

    print("例3.10 (1) ∮_{|z|=2} sin z/z dz = 2πi·sin 0 =", c(circ_int(lambda z: np.sin(z) / z, 0, 2.0)))
    print(f"       (2) ∮_{{|z|=2}} z/((9-z²)(z+i)) dz = 2πi·[z/(9-z²)]_{{z=-i}} = π/5 = {PI / 5:.4f};数值 "
          f"{c(circ_int(lambda z: z / ((9 - z * z) * (z + 1j)), 0, 2.0))}")


# ---------------------------------------------------------------- 6 高阶、不等式
def step6_high_order() -> None:
    head("6 高阶导数公式、柯西不等式、最大模、刘维尔")
    z0 = 0.3 + 0.2j
    print("f^(n)(z0) = n!/(2πi)∮ f(ζ)/(ζ-z0)^{n+1} dζ,f=e^z(所有阶导数都是 e^z):")
    for n in (0, 1, 2, 3, 5):
        val = factorial(n) / (2j * PI) * circ_int(lambda z: np.exp(z) / (z - z0) ** (n + 1), z0, 1.0)
        print(f"   n={n}:{c(val, 6)};e^z0 = {c(np.exp(z0), 6)}")
    z0 = 0.5
    val = factorial(3) / (2j * PI) * circ_int(lambda z: np.sin(z) / (z - z0) ** 4, z0, 1.0)
    print(f"   sin z 的三阶导数 -cos z0 在 z0=0.5:{c(val, 6)};-cos(0.5) = {-np.cos(0.5):.6f}")

    print("例3.12 (1) ∮_{|z-i|=1} cos z/(z-i)³ dz = -(πi/2)(e+e^{-1}) = ", end="")
    print(f"{c(-PI * 1j / 2 * (np.e + 1 / np.e))};数值 {c(circ_int(lambda z: np.cos(z) / (z - 1j) ** 3, 1j, 1.0))}")
    print("       (2) ∮_{|z|=4} e^z/(z²(z-1)²) dz = 2π(3-e)i =", c(2 * PI * (3 - np.e) * 1j),
          ";数值", c(circ_int(lambda z: np.exp(z) / (z ** 2 * (z - 1) ** 2), 0, 4.0)))

    print("柯西不等式 |f^(n)(z0)| ≤ n!M/Rⁿ:f=e^z,z0=0,R=1:M=max|e^z|=e:")
    for n in (1, 2, 3, 5):
        print(f"   n={n}:|f^(n)(0)| = 1 ≤ n!M/Rⁿ = {factorial(n) * np.e:.4f}")
    print("   取 R=2:M=e²,n=1:1 ≤ M/R =", f"{np.e ** 2 / 2:.4f}", ";R 越大上界越松,所以有界整函数的导数被压成 0(刘维尔)")

    print("最大模原理:|f| 在圆盘内部取不到最大值,只能在边界:f=z²+z,|z|≤1:")
    rr = np.linspace(0, 1, 201)
    th = np.linspace(0, 2 * PI, 721)
    R, T = np.meshgrid(rr, th)
    Z = R * np.exp(1j * T)
    F = abs(Z ** 2 + Z)
    i, j = np.unravel_index(np.argmax(F), F.shape)
    print(f"   最大 |f| = {F.max():.4f} 在 |z| = {R[i, j]:.2f}(边界),z = {c(Z[i, j], 3)};内部 |z|=0.5 的最大 {F[:, 100].max():.4f}")
    print("   最小模原理(习题3.12):f 非常数且无零点 → |f| 在内部取不到最小:f=z+2,|z|≤1:最小 |f| 在边界",
          f"{abs(Z + 2).min():.4f}(在 z=-1)")


# ---------------------------------------------------------------- 7 习题
def step7_exercises() -> None:
    head("7 习题三的计算题")
    f31 = lambda z: (z.real - z.imag) + 1j * z.real ** 2
    print("3.1 ∫₀^{1+i}[(x-y)+ix²]dz,三条路径(f 不解析,结果因路径而异):")
    r_a = line_int(f31, 0j, 1 + 1j)
    r_b = poly_int(f31, [0j, 1 + 0j, 1 + 1j])
    r_c = poly_int(f31, [0j, 1j, 1 + 1j])
    print(f"   (1) 直线:{c(r_a)}   (2) 先实轴后垂直:{c(r_b)}   (3) 先虚轴后水平:{c(r_c)}")
    print(f"   手算核对 (1):x=y=t,dz=(1+i)dt:∫(0+it²)(1+i)dt = (1+i)i/3 = {c((1 + 1j) * 1j / 3)}")

    print("3.2 ∮ z̄/|z| dz:在圆上 z̄/|z| = e^(-iθ),dz = i r e^(iθ)dθ,被积 = i r dθ,积分 = 2πi·r:")
    for r in (2.0, 4.0):
        print(f"   |z|={r:.0f}:数值 {c(circ_int(lambda z: np.conj(z) / abs(z), 0, r))};2πi·r = {c(2j * PI * r)}")

    print("3.3 |∫ dz/z²| ≤ π/4,C:1-i → 1:")
    val = line_int(lambda z: 1 / z ** 2, 1 - 1j, 1 + 0j)
    print(f"   实际 {c(val)};|·| = {abs(val):.4f} ≤ π/4 = {PI / 4:.4f};"
          f"(其实原函数 -1/z:-1/1 + 1/(1-i) = {c(-1 + 1 / (1 - 1j))})")

    print("3.4 观察法,|z|=1:(1) 1/(z²+4z+4) 奇点 z=-2 在圈外 → 0;(2) 1/cos z 奇点 ±π/2 在圈外 → 0;(3) 1/(z-½) → 2πi")
    print(f"   数值:(1) {c(circ_int(lambda z: 1 / (z * z + 4 * z + 4), 0, 1.0))};(2) {c(circ_int(lambda z: 1 / np.cos(z), 0, 1.0))};"
          f"(3) {c(circ_int(lambda z: 1 / (z - 0.5), 0, 1.0))}")

    print("3.5 ∫ e^z/z dz,C = 正向 |z|=2 与负向 |z|=1 组成(即圆环边界):")
    v = circ_int(lambda z: np.exp(z) / z, 0, 2.0) - circ_int(lambda z: np.exp(z) / z, 0, 1.0)
    print(f"   {c(v)}(两圈都等于 2πi,相减为 0:e^z/z 在圆环里解析)")

    print("3.6 ∮_{|z|=2} 1/(z²-z) dz = 1/(z-1) - 1/z:两个奇点都在圈内:", c(circ_int(lambda z: 1 / (z * z - z), 0, 2.0)),
          "(= 2πi·(1) + 2πi·(-1) = 0)")
    print("3.7 ∮_{|z|=3} 1/((z-i)(z+2)) dz = (1/(i+2))·... 部分分式:",
          c(circ_int(lambda z: 1 / ((z - 1j) * (z + 2)), 0, 3.0)), ";= 0(1/(z-i)(z+2) 两个留数 ±1/(2+i) 相消)")

    print("3.8 ∫ sin z dz(0→πi)、∫ z e^z dz(1→1+i)、∫(3e^z+2z) dz(0→i):")
    print(f"   (1) -cos(πi)+1 = 1 - cosh π = {c(1 - np.cosh(PI))};数值 {c(line_int(np.sin, 0j, PI * 1j))}")
    g = lambda z: z * np.exp(z) - np.exp(z)
    print(f"   (2) [(z-1)e^z]₁^{{1+i}} = i·e^{{1+i}} = {c(1j * np.exp(1 + 1j))};数值 {c(line_int(lambda z: z * np.exp(z), 1 + 0j, 1 + 1j))};原函数验算 {c(g(1 + 1j) - g(1))}")
    print(f"   (3) 3e^i - 3 + i² = 3e^i - 4 = {c(3 * np.exp(1j) - 3 + (1j) ** 2)};数值 {c(line_int(lambda z: 3 * np.exp(z) + 2 * z, 0j, 1j))}")

    print(f"3.9 ∫ 1/z² dz,C 是 |z+i|=2 的右半周,-3i→i:原函数 -1/z:-1/i - (-1/(-3i)) = {c(-1 / 1j - (-1 / (-3j)))}"
          f"(i 与 -3i 都在圆上,圆心 -i,半径 2)")
    th = np.linspace(-PI / 2, PI / 2, 400001)
    zc = -1j + 2 * np.exp(1j * th)
    dz = np.diff(zc)
    print(f"       沿右半周数值 {c(np.sum(1 / ((zc[:-1] + zc[1:]) / 2) ** 2 * dz))};起点 {c(zc[0])},终点 {c(zc[-1])}")

    print("3.10 ∮ f/(z-z0) 型:")
    print(f"   (1) ∮_{{|z-2|=1}} e^z/(z-2) dz = 2πi e² = {c(2j * PI * np.exp(2))};数值 {c(circ_int(lambda z: np.exp(z) / (z - 2), 2 + 0j, 1.0))}")
    print(f"   (2) ∮_{{|z|=2}} (2z²-z+1)/(z-1) dz = 2πi·f(1) = 2πi·2 = {c(4j * PI)};数值 {c(circ_int(lambda z: (2 * z * z - z + 1) / (z - 1), 0, 2.0))}")
    print("   (4) ∮_{|z|=r} dz/(z-1)^n:r<1 → 0(1 在圈外);r>1 → n=1 时 2πi,n≠1 时 0:")
    for r in (0.5, 2.0):
        print("       r=" + str(r) + ":" + ",".join(f"n={n}:{c(circ_int(lambda z: 1 / (z - 1) ** n, 0, r), 3)}" for n in (1, 2, 3)))

    print("3.11 I = ∮ z/((2z+1)(z-2)) dz,奇点 z=-½、z=2:")
    g = lambda z: z / ((2 * z + 1) * (z - 2))
    for name, z0, r in (("(1) |z|=1(含 -½)", 0j, 1.0), ("(2) |z-2|=1(含 2)", 2 + 0j, 1.0),
                        ("(3) |z-1|=½(都不含)", 1 + 0j, 0.5), ("(4) |z|=3(都含)", 0j, 3.0)):
        print(f"   {name}:{c(circ_int(g, z0, r))}")
    print(f"       公式:含 -½:2πi·[z/(2(z-2))]_{{z=-½}} = 2πi·(-½)/(2·(-5/2)) = {c(2j * PI * (-0.5) / (2 * -2.5))};"
          f"含 2:2πi·[z/(2z+1)]_{{z=2}} = 2πi·2/5 = {c(2j * PI * 2 / 5)};两者之和 = {c(2j * PI * (-0.5) / (2 * -2.5) + 2j * PI * 2 / 5)}")

    print("3.13 ∮ 型(高阶导数公式):")
    v1 = circ_int(lambda z: np.exp(z) / z ** 100, 0, 1.0)
    print(f"   (1) ∮_{{|z|=1}} e^z/z^100 dz = 2πi/99! = {c(2j * PI / factorial(99))};数值 {c(v1)}")
    v2 = circ_int(lambda z: np.sin(z) / (z - PI / 2) ** 2, 0, 2.0)
    print(f"   (2) ∮_{{|z|=2}} sin z/(z-π/2)² dz = 2πi·cos(π/2) = {c(2j * PI * np.cos(PI / 2))};数值 {c(v2)}")
    v3 = circ_int(lambda z: np.cos(z) / z ** 3, 0, 3.0) + circ_int(lambda z: np.cos(z) / z ** 3, 0, 2.0)
    print(f"   (3) ∮_{{C1+C2}} cos z/z³ dz(C1:|z|=2,C2:|z|=3,都正向):2×(2πi/2!)·(cos)''(0) = 2×(-πi) = {c(-2j * PI)};数值 {c(v3)}")

    print("3.14 f 在 |z|≤1 解析,|z|=1 上 |f(z)-z|<|z|,试证 |f'(1/2)| ≤ 8:")
    print("   在圆上 |f| ≤ |f-z| + |z| < 2|z| = 2,所以 M=2;柯西公式 f'(½) = (1/2πi)∮ f/(z-½)² dz,")
    print("   |z|=1 上 |z-½| ≥ ½,所以 |f'(½)| ≤ (1/2π)·M/(½)²·L,L=2π → 4M = 8")
    f_ex = lambda z: z * 1.9                      # |f-z| = 0.9|z| < |z|
    d = (f_ex(0.5 + 1e-6) - f_ex(0.5 - 1e-6)) / 2e-6
    print(f"   例:f(z)=1.9z 满足 |f-z|=0.9|z|<|z|:|f'(½)| = {abs(d):.4f} ≤ 8 ✓")

    print("3.12 非常数解析 f 在 G 内无零点 ⇒ 不能取最小模(考虑 1/f):f=e^z,圆盘 |z|≤1:|f| 最小 = e^{-1}")
    print(f"   在边界 z=-1 取到:{np.exp(-1):.6f};内部 |z|=0.5 的最小 {np.exp(-0.5):.6f} > 边界最小 ✓")


# ---------------------------------------------------------------- 图
def save_figure() -> None:
    head("图:∮ zⁿ dz 随 n 的变化;一圈里「谁被抵消」")
    ns = np.arange(-5, 4)
    r = 1.0
    vals = [circ_int(lambda z, n=n: z ** n, 0, r) for n in ns]
    for n, v in zip(ns, vals):
        print(f"   n={n:>2}:{c(v, 3)}")

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 6.6))
    blue, red, green, ora, gray = "#2c6fbb", "#c4442a", "#2a8f4a", "#d98a14", "#666"

    # ① 柱状:∮ zⁿ dz 的虚部
    ax = axes[0]
    ax.bar(ns, [v.imag for v in vals], color=[red if n == -1 else blue for n in ns], width=0.7)
    ax.axhline(0, color="#999", lw=0.8)
    ax.axhline(2 * PI, color=red, lw=0.8, ls="--")
    ax.text(3.3, 2 * PI + 0.15, "2π", color=red, fontsize=9, ha="right")
    ax.set_xticks(ns)
    ax.set_xlabel("n(被积函数是 zⁿ)", fontsize=9)
    ax.set_ylabel("∮ zⁿ dz 的虚部(实部都是 0)", fontsize=9)
    ax.set_title("① 沿单位圆绕一圈:只有 n=-1 非零", fontsize=11.5, loc="left")
    ax.set_ylim(-1, 7.5)
    ax.set_box_aspect(1)
    ax.tick_params(labelsize=8)

    # ② 累加:一小段一小段首尾相接,看终点回不回得到起点
    ax = axes[1]
    th = np.linspace(0, 2 * PI, 2001)
    z = np.exp(1j * th)
    for name, f, col in (("1/z  (n=-1)", lambda z: 1 / z, red), ("1/z²  (n=-2)", lambda z: 1 / z ** 2, blue),
                         ("z²  (n=2)", lambda z: z ** 2, green)):
        dz = np.diff(z)
        mid = (z[:-1] + z[1:]) / 2
        acc = np.concatenate([[0], np.cumsum(f(mid) * dz)])
        ax.plot(acc.real, acc.imag, color=col, lw=2, label=name)
        ax.plot([acc[-1].real], [acc[-1].imag], "o", color=col, ms=6)
        print(f"   累加到终点:{name} → {c(acc[-1], 3)}")
    ax.plot([0], [0], "k+", ms=11)
    ax.annotate("起点 0", (0, 0), xytext=(0.35, -0.55), fontsize=9, color=gray)
    ax.annotate("1/z 一路向上:\n终点 2πi=6.28i", (0, 6.28), xytext=(0.5, 5.2), fontsize=9, color=red)
    ax.annotate("另外两条各绕一个圈,\n又回到起点 0", (0.6, 0.9), xytext=(0.9, 1.7), fontsize=9, color=gray)
    ax.set_xlim(-3.2, 3.4)
    ax.set_ylim(-1.2, 7.0)
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_box_aspect(1)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=9, loc="center left")
    ax.set_title("② 沿单位圆一路累加 Σ f(z)Δz", fontsize=11.5, loc="left")
    ax.set_xlabel("累加值的实部", fontsize=9)
    ax.set_ylabel("累加值的虚部", fontsize=9)
    ax.tick_params(labelsize=8)

    # ③ 路径无关:z² 从 0 到 1+i 三条路径,累加终点相同;z̄ 不同
    ax = axes[2]
    paths = {"直线": [0j, 1 + 1j], "先横后竖": [0j, 1 + 0j, 1 + 1j], "先竖后横": [0j, 1j, 1 + 1j]}
    cols = [blue, green, ora]
    xs_ = []
    for (name, pts), col in zip(paths.items(), cols):
        a = poly_int(lambda z: z ** 2, pts, 20000)
        b = poly_int(np.conj, pts, 20000)
        xs_.append((name, a, b))
    names = [x[0] for x in xs_]
    ax.bar(np.arange(3) - 0.18, [abs(x[1]) for x in xs_], width=0.34, color=blue, label="解析的 z²:路径无关")
    ax.bar(np.arange(3) + 0.18, [abs(x[2]) for x in xs_], width=0.34, color=red, label="不解析的 z̄:路径有关")
    for k, (name, a, b) in enumerate(xs_):
        ax.text(k - 0.18, abs(a) + 0.02, f"{abs(a):.3f}", ha="center", fontsize=8.5, color=blue)
        ax.text(k + 0.18, abs(b) + 0.02, f"{abs(b):.3f}", ha="center", fontsize=8.5, color=red)
    ax.set_xticks(range(3))
    ax.set_xticklabels(names, fontsize=9)
    ax.set_ylabel("|积分值|(0 → 1+i)", fontsize=9)
    ax.set_title("③ 同一起点终点,三条路径", fontsize=11.5, loc="left")
    ax.legend(fontsize=9, loc="upper left")
    ax.set_ylim(0, 1.7)
    ax.set_box_aspect(1)
    ax.tick_params(labelsize=8)
    for x in xs_:
        print(f"   路径 {x[0]}:∫z² dz = {c(x[1], 4)}(|·|={abs(x[1]):.4f});∫z̄ dz = {c(x[2], 4)}(|·|={abs(x[2]):.4f})")

    four_questions(
        fig,
        did="把「沿圆周绕一圈的复积分」\n和「换路径」两件事,都用数值\n求和直接算出来",
        gained="∮ zⁿ dz 只有 n=-1 非零,\n等于 2πi(6.283);解析的 z²\n换路径结果不变,z̄ 会变",
        lost="数值只是逼近:被积函数\n数值极小时(如 e^z/z¹⁰⁰),\n公式比数值求和更可靠",
        limit="奇点在圈外时整圈是 0\n(如 1/(z+2) 绕单位圆),\n所以关键是「圈里有没有奇点」",
        better="想一次算出圈内所有奇点的\n贡献,看第 5 章留数",
        y=0.17, bottom=0.27)
    out = Path(__file__).resolve().parents[2] / "Documents" / "数学基础" / "复变函数" / "images"
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "complex-ch3-contour.png", dpi=130, bbox_inches="tight", facecolor="white")
    print("  → Documents/数学基础/复变函数/images/complex-ch3-contour.png")
    plt.close(fig)


def main() -> None:
    step1_definition()
    step2_powers()
    step3_cauchy_theorem()
    step4_deformation()
    step5_formula()
    step6_high_order()
    step7_exercises()
    save_figure()


if __name__ == "__main__":
    main()
