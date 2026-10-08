"""第 11 周(数学回血):30 欧拉公式 —— 配合 Documents/数学基础/如何直观理解欧拉公式.md。

那篇文档是一篇外部回答的存档,读的时候有几处跳步、几处笔误,还有一个全文标题级的
结论(e^{iπ}+1=0)从头到尾没被推出来。本脚本把这些地方逐个算一遍,
文档里「补充」「勘误」块里的每个数字都从这里来。

验证十一件事:
1. 乘 i 就是逆时针转 90°:(a+bi)·i = −b+ai,模长不变
2. 单位圆上的向量:增量垂直于原向量,Δy/Δx ≈ i·y,模长 → 1
3. 「沿切线走小步」会走出圆:(1+ix/N)^N → e^{ix},步子越小飘得越少
4. 解微分方程那一步的另一种写法:g = y·e^{−ix} 恒为 1(避开复数对数)
5. 代进去:e^{iπ/2}=i、e^{iπ}=−1、e^{iπ}+1=0
6. 泰勒展开对照:偶数项是 cos、奇数项是 i·sin;x=π 的部分和收敛到 −1
7. ⚠️ 勘误核对:(2+i)² 的模长是平方不是 2 倍;sin x 的分母是 2i 不是 2
8. 2^i 到底等于多少(原文盲猜 cos 2 + i sin 2,是错的)
9. 历史例子:Bombelli 的 x³=15x+4,根号下出现负数,答案却是 4
10. 弹簧振子 ω=√(k/m);三角恒等式用复数一步推出
11. 回到图像处理:卷积核的频率响应 H(ω) = Σ k[n]e^{−iωn},用欧拉公式化成余弦

生成 1 张(写到 Assets/results/):
    euler-taylor-spiral.png     x=π 时泰勒部分和在复平面上逼近 −1 的路径

用法:
    .venv/bin/python Ch04_Frequency_Domain/30_euler_formula.py [--show]
"""

from __future__ import annotations

import sys
from math import factorial
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import four_questions, save, use_cjk_font  # noqa: E402

use_cjk_font()
import matplotlib.pyplot as plt  # noqa: E402

I = 1j


def cplx(z: complex, nd: int = 2) -> str:
    """复数写成 1.00+3.14i 的样子(实部不带正号,比 fmt() 更适合放进图里)。"""
    return f"{z.real:.{nd}f}{z.imag:+.{nd}f}i"


def partial_sum(x: float, n: int) -> complex:
    """e^{ix} 泰勒展开的前 n 项之和。"""
    return sum((I * x) ** k / factorial(k) for k in range(n))


def big_x_cost(x: float, terms: int = 100) -> dict:
    """x 变大时朴素泰勒求和的代价:单项暴涨,要抵消回模长 1,浮点精度被吃掉。

    折回 [−π,π] 是利用 e^{ix} 的周期 2π:先把 x 减掉整圈再展开,单项永远不会太大。
    """
    exact = np.exp(I * x)
    xr = (x + np.pi) % (2 * np.pi) - np.pi
    return {
        "x": x,
        "max_term": max(abs((I * x) ** k / factorial(k)) for k in range(terms)),
        "naive_err": abs(partial_sum(x, terms) - exact),
        "reduced_err": abs(partial_sum(xr, 40) - exact),
    }


def hr(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def fmt(z: complex, nd: int = 4) -> str:
    """复数打印成 a+bi 的样子;实部虚部都带符号,对齐好读。"""
    return f"{z.real:+.{nd}f}{z.imag:+.{nd}f}i"


# ------------------------------------------------------------------ 1
def demo_times_i() -> None:
    hr("1. 乘 i 就是逆时针转 90°")
    z = 2 + 1j
    print(f"  (2+i)·i 展开:2i + i² = 2i − 1 = {fmt(z * I, 0)}   (numpy 算:{z * I})")
    print("  一般地 (a+bi)·i = ai + bi² = −b + ai,即坐标 (a,b) → (−b,a):")
    for a, b in ((2, 1), (3, 0), (0, 2), (1, 1)):
        w = (a + b * 1j) * I
        ang = np.degrees(np.angle(w) - np.angle(a + b * 1j))
        print(f"    ({a},{b}) → ({w.real:+.0f},{w.imag:+.0f})   "
              f"转了 {ang % 360:.1f}°   模长 {abs(a + b * 1j):.4f} → {abs(w):.4f}")


# ------------------------------------------------------------------ 2
def demo_increment_is_perpendicular() -> None:
    hr("2. 单位圆上:增量垂直于原向量,而且 |Δy| = Δx")
    x, dx = 0.5, 1e-6
    y = np.cos(x) + I * np.sin(x)
    dy = (np.cos(x + dx) + I * np.sin(x + dx)) - y
    print(f"  x = {x},y = cos x + i·sin x = {fmt(y, 6)},|y| = {abs(y):.12f}")
    print(f"  Δx = {dx:g}  →  Δy = {fmt(dy, 9)}")
    dot = y.real * dy.real + y.imag * dy.imag
    print(f"  y 与 Δy 的点积(=0 就是垂直)= {dot:.3e}     |Δy| / Δx = {abs(dy) / dx:.9f}")
    print(f"  Δy/Δx = {fmt(dy / dx, 6)},   i·y = {fmt(I * y, 6)},   差 {abs(dy / dx - I * y):.2e}")
    print("  为什么:模长恒为 1 → 增量只能沿切线;切线垂直半径;弧长 = 半径 × 角度 = 1 × Δx。")

    print("\n  Δx 取不同大小,误差怎么变(应该随 Δx 线性变小):")
    for d in (1e-1, 1e-2, 1e-3, 1e-4):
        d_y = (np.cos(x + d) + I * np.sin(x + d) - y) / d
        print(f"    Δx = {d:<7g}  |Δy/Δx − i·y| = {abs(d_y - I * y):.3e}")


# ------------------------------------------------------------------ 3
def demo_euler_polyline() -> None:
    hr("3. 每步沿切线走一小步 → 会走出圆;步子越小飘得越少")
    x = np.pi
    print("  从 y(0)=1 出发,每步 y ← y·(1 + i·Δx),走到 x = π(Δx = π/N):")
    print(f"  {'N':>9} | {'终点':>20} | {'|终点|':>9} | {'离 −1 有多远':>12}")
    for n in (10, 100, 1000, 10 ** 6):
        y = (1 + I * x / n) ** n
        print(f"  {n:>9} | {fmt(y, 5):>20} | {abs(y):>9.6f} | {abs(y + 1):>12.3e}")
    print("  每一步 |1+iΔx| = √(1+Δx²) > 1(勾股:切线垂直半径,所以斜边比半径长),")
    print("  所以折线总是略微向外飘;N → ∞ 时飘出的部分 → 0,终点 → e^{iπ} = −1。")


# ------------------------------------------------------------------ 4
def demo_g_is_constant() -> None:
    hr("4. 另一种写法:g(x) = y(x)·e^{−ix} 恒为 1(不用复数对数)")
    print("  y' = iy 时,g' = y'e^{−ix} − iy·e^{−ix} = (y' − iy)e^{−ix} = 0,")
    print("  所以 g 是常数,g(0) = 1·1 = 1,于是 y = e^{ix}。数值上看 g:")
    for x in (0.0, 0.5, 1.0, 2.0, np.pi, 5.0):
        y = np.cos(x) + I * np.sin(x)
        g = y * np.exp(-I * x)
        print(f"    x = {x:.4f}   g = {fmt(g, 12)}")


# ------------------------------------------------------------------ 5
def demo_plug_in() -> None:
    hr("5. 把特殊值代进去:公式的标题结论 e^{iπ}+1=0 是这样来的")
    print(f"  {'x':>8} | {'cos x':>9} | {'sin x':>9} | {'e^{ix}':>20} | 它在复平面上哪儿")
    where = {0.0: "实轴正方向(起点)", np.pi / 2: "虚轴正方向 = i(转了 90°)",
             np.pi: "实轴负方向 = −1(转了半圈)", 3 * np.pi / 2: "虚轴负方向 = −i",
             2 * np.pi: "回到起点 = 1(转了一圈)"}
    for x, w in where.items():
        z = np.exp(I * x)
        print(f"  {x:8.4f} | {np.cos(x):+9.4f} | {np.sin(x):+9.4f} | {fmt(z, 4):>20} | {w}")
    r = np.exp(I * np.pi) + 1
    print(f"\n  e^{{iπ}} + 1 = {r.real:+.3e}{r.imag:+.3e}i   (浮点误差量级,即 0)")
    print("  推导只有两行:代入 x=π → e^{iπ} = cos π + i·sin π = −1 + 0·i = −1 → 移项。")


# ------------------------------------------------------------------ 6
def demo_taylor() -> None:
    hr("6. 泰勒展开对照:e^{ix} = Σ (ix)^n / n!")
    print("  i 的幂循环:i⁰=1, i¹=i, i²=−1, i³=−i, i⁴=1 ... 偶数项全是实数、奇数项全带 i:")
    x = 1.3
    n_terms = 30
    even = sum((-1) ** k * x ** (2 * k) / factorial(2 * k) for k in range(n_terms))
    odd = sum((-1) ** k * x ** (2 * k + 1) / factorial(2 * k + 1) for k in range(n_terms))
    print(f"  x = {x}:偶数项之和 = {even:.12f}   cos x = {np.cos(x):.12f}   差 {abs(even - np.cos(x)):.1e}")
    print(f"         奇数项之和 = {odd:.12f}   sin x = {np.sin(x):.12f}   差 {abs(odd - np.sin(x)):.1e}")

    print("\n  x = π 时前 N 项的部分和怎么逼近 −1(复平面上的落点):")
    print(f"  {'N':>3} | {'部分和':>22} | {'离 −1 有多远':>12}")
    for n in (2, 4, 6, 8, 12, 16, 20, 24):
        s = partial_sum(np.pi, n)
        print(f"  {n:>3} | {fmt(s, 6):>22} | {abs(s + 1):>12.3e}")

    print("\n  路径为什么是直角折线:第 n 项 = 第 n−1 项 × (iπ/n)。")
    print("  乘 i 是转 90°(逆时针),再缩放 π/n —— 每一步都在上一步的基础上「转 90° 并缩放」:")
    print(f"  {'n':>3} | {'这一步的长度 π^n/n!':>20} | {'方向':>6} | 相对上一步")
    names = {1: "上", 2: "左", 3: "下", 0: "右"}
    for n in range(1, 8):
        step = np.pi ** n / factorial(n)
        trend = f"× π/{n} = ×{np.pi / n:.3f}  {'变长' if np.pi / n > 1 else '变短'}"
        print(f"  {n:>3} | {step:>20.4f} | {names[n % 4]:>6} | {trend}")
    print("  π/n > 1 只到 n=3:前三步越走越长(3.14 → 4.93 → 5.17),从第 4 步起越走越短 —— 这就是「先冲出去再收回来」。")

    path = [partial_sum(np.pi, n) for n in range(1, 31)]
    far = int(np.argmax([abs(z) for z in path])) + 1
    print(f"\n  路径一度冲到离原点 {abs(path[far - 1]):.3f} 远(N={far}),是单位圆半径的 {abs(path[far - 1]):.1f} 倍 ——")
    print("  部分和根本不沿圆走;它能算出 −1,却看不出「为什么在转」。")
    n17 = next(n for n in range(1, 60) if abs(partial_sum(np.pi, n) + 1) < 1e-6)
    print(f"  x=π 时误差降到 1e−6 以下需要 N={n17} 项。")

    print("\n  x 变大时朴素求和的代价(同样 100 项;右列先折回 [−π,π] 再算):")
    print(f"  {'x':>6} | {'最大单项':>10} | {'朴素求和误差':>12} | {'折回后误差':>10}")
    for x in (np.pi, 10, 20, 30):
        c = big_x_cost(x)
        print(f"  {c['x']:6.2f} | {c['max_term']:10.3g} | {c['naive_err']:12.2e} | {c['reduced_err']:10.2e}")
    print("  单项最大到 7.8e11,却要加减抵消回模长 1,双精度只有 ~16 位有效数字,")
    print("  所以误差从 3e−16 涨到 2e−4。折回之后单项永远不超过 ~5,误差回到 1e−15 量级。")


# ------------------------------------------------------------------ 7
def demo_errata() -> None:
    hr("7. ⚠️ 勘误核对:原文有两处写错")
    z = 2 + 1j
    z2 = z ** 2
    print(f"  (2+i)² = {z2}   (原文写 3+4i,对)")
    print(f"  模长:|2+i| = {abs(z):.4f}  →  |(2+i)²| = {abs(z2):.4f}")
    print(f"        原文说「模长放大到 2 倍」应是 {2 * abs(z):.4f},而实际是 {abs(z2):.4f} = {abs(z):.4f}²")
    print(f"        所以模长是**平方**,不是 2 倍。  √5 → 5(因为 (√5)² = 5)")
    print(f"  辐角:{np.degrees(np.angle(z)):.3f}° → {np.degrees(np.angle(z2)):.3f}°,"
          f"确实放大到 2 倍(原文这半句对)")

    x = 0.7
    a = (np.exp(I * x) - np.exp(-I * x)) / 2
    b = (np.exp(I * x) - np.exp(-I * x)) / (2 * I)
    print(f"\n  x = {x}:sin x = {np.sin(x):.6f}")
    print(f"    (e^(ix) − e^(−ix)) / 2   = {fmt(a, 6)}   ← 原文的写法,是 i·sin x,不是 sin x")
    print(f"    (e^(ix) − e^(−ix)) / 2i  = {fmt(b, 6)}   ← 分母要带 i")
    c = (np.exp(I * x) + np.exp(-I * x)) / 2
    print(f"    cos x = (e^(ix) + e^(−ix)) / 2 = {fmt(c, 6)}  (cos x = {np.cos(x):.6f},这条原文是对的)")

    print("\n  「数字的扩充」那组里,第 4 条(虚数)写成「从有理数扩充到无理数」,与第 3 条一字不差,是抄重了。")
    print("  虚数把范围从**实数**扩充到**复数**。(这条是文字问题,无需计算。)")


# ------------------------------------------------------------------ 8
def demo_two_to_the_i() -> None:
    hr("8. 2^i 到底等于多少")
    guess = np.cos(2) + I * np.sin(2)
    true = np.exp(I * np.log(2))
    print(f"  原文盲猜:2^i ≈ cos 2 + i·sin 2 = {fmt(guess, 4)}   (转了 2 弧度)")
    print(f"  真值:    2^i = e^(i·ln 2) = cos(ln 2) + i·sin(ln 2) = {fmt(true, 4)}   (转了 ln 2 = {np.log(2):.4f} 弧度)")
    print(f"  numpy 直接算 2**1j = {fmt(2 ** 1j, 4)}   与真值差 {abs(2 ** 1j - true):.1e}")
    print("  做法:先把底换成 e —— 2 = e^(ln 2),所以 2^i = (e^(ln 2))^i = e^(i·ln 2),再用欧拉公式。")
    print(f"  模长 = {abs(true):.6f}(恒为 1:纯虚数指数只转不缩)")

    print("\n  指数律还成立吗(a^b·a^c = a^(b+c))?")
    print(f"    2^i · 2^i  = {fmt(2 ** 1j * 2 ** 1j, 6)}      2^(2i)   = {fmt(2 ** 2j, 6)}")
    print(f"    2^i · 2^(−i) = {fmt(2 ** 1j * 2 ** -1j, 6)}   2^0      = 1")
    print(f"    2^(1+i)    = {fmt(2 ** (1 + 1j), 6)}   = 2 · 2^i = {fmt(2 * 2 ** 1j, 6)}")
    print("  都成立 —— 这就是「把幂运算补全到复数」想要的结果:旧规则一条不丢。")


# ------------------------------------------------------------------ 9
def demo_bombelli() -> None:
    hr("9. 历史例子:根号下出现负数,答案却是实数")
    print("  Bombelli 的例子 x³ = 15x + 4(p=15, q=4):")
    p, q = 15, 4
    disc = (q / 2) ** 2 - (p / 3) ** 3
    print(f"    Cardano 公式根号里:(q/2)² − (p/3)³ = {(q / 2) ** 2:.0f} − {(p / 3) ** 3:.0f} = {disc:.0f}  < 0")
    print(f"    √{disc:.0f} = {np.sqrt(complex(disc)).imag:.0f}i,所以 x = ∛(2+11i) + ∛(2−11i)")
    print(f"    (2+i)³ = {(2 + 1j) ** 3},(2−i)³ = {(2 - 1j) ** 3}  → 立方根分别是 2+i 和 2−i")
    x = (2 + 1j) + (2 - 1j)
    print(f"    x = (2+i) + (2−i) = {x.real:.0f}    验:{x.real:.0f}³ = {x.real ** 3:.0f},"
          f"15·{x.real:.0f}+4 = {15 * x.real + 4:.0f}  ✓")

    z = 5 + 1j * np.sqrt(2)
    t1, t2 = z ** (1 / 3), np.conj(z) ** (1 / 3)
    print(f"\n  原文那个 x = ∛(5+√−2) + ∛(5−√−2):两项互为共轭,虚部抵消:")
    print(f"    ∛(5+√−2) = {fmt(t1, 6)}   ∛(5−√−2) = {fmt(t2, 6)}   和 = {fmt(t1 + t2, 6)}(虚部 = 0)")


# ------------------------------------------------------------------ 10
def demo_spring_and_identities() -> None:
    hr("10. 弹簧振子的 ω;三角恒等式用复数一步推出")
    k, m, a, phi = 4.0, 1.0, 0.7, 0.3
    omega = np.sqrt(k / m)
    t = np.linspace(0, 6, 7)
    h = 1e-3
    xt = lambda tt: a * np.sin(omega * tt + phi)
    acc = (xt(t + h) - 2 * xt(t) + xt(t - h)) / h ** 2
    res = np.abs(-k * xt(t) - m * acc).max()
    print(f"  −kx = m·x'' 的解 x = A·sin(ωt+φ),代回去要求 ω² = k/m,即 ω = √(k/m)。")
    print(f"  取 k={k:g}, m={m:g} → ω = {omega:g};用二阶差分算 x'',残差 max|−kx − m·x''| = {res:.2e}")
    omega_bad = 1.5
    xb = lambda tt: a * np.sin(omega_bad * tt + phi)
    accb = (xb(t + h) - 2 * xb(t) + xb(t - h)) / h ** 2
    print(f"  换个错的 ω={omega_bad}:残差 {np.abs(-k * xb(t) - m * accb).max():.2f}(远大于 0,不是解)")

    print("\n  电势那一节的符号(原文 E、F 前后含义对调):令 k·q₁·q₂ = 1,在 x = 2 处:")
    u = lambda xx: 1.0 / xx                    # 势能 U = kq₁q₂/x
    e = lambda xx: -1.0 / xx                   # 原文最后的 E = −kq₁q₂/x
    dx = 1e-6
    print(f"    力 F = kq₁q₂/x² = {1 / 4:.4f}")
    print(f"    −dU/dx = {-(u(2 + dx) - u(2 - dx)) / (2 * dx):.4f}   (U = kq₁q₂/x,通常约定 F = −dU/dx)")
    print(f"    +dE/dx = {(e(2 + dx) - e(2 - dx)) / (2 * dx):.4f}   (原文的 E = −kq₁q₂/x = −U,所以是 +dE/dx)")

    x, y = 0.9, 0.4
    prod = np.exp(I * x) * np.exp(I * y)
    print(f"\n  cos(x+y) = Re(e^(ix)·e^(iy)):x={x}, y={y}")
    print(f"    直接算 cos(x+y)                 = {np.cos(x + y):.12f}")
    print(f"    Re(e^(ix)·e^(iy))               = {prod.real:.12f}")
    print(f"    cos x·cos y − sin x·sin y       = {np.cos(x) * np.cos(y) - np.sin(x) * np.sin(y):.12f}")
    print(f"    Im(e^(ix)·e^(iy)) = sin(x+y)    = {prod.imag:.12f}  (sin(x+y) = {np.sin(x + y):.12f})")
    print("    展开 (cos x + i sin x)(cos y + i sin y),实部是 cos x cos y − sin x sin y,"
          "虚部是 sin x cos y + cos x sin y。")


# ------------------------------------------------------------------ 11
def demo_kernel_frequency_response() -> None:
    hr("11. 回到图像处理:卷积核的频率响应 H(ω) = Σ k[n]·e^(−iωn)")
    print("  [1,2,1]/4 把中心放在 n=0(两边 n=±1):")
    print("    H(ω) = (e^(iω) + 2 + e^(−iω)) / 4 = (2 + 2cos ω) / 4 = (1 + cos ω) / 2")
    print("  这一步用的就是 e^(iω)+e^(−iω) = 2cos ω(上一节验过的 cos 公式)。")
    n = 8
    k = np.zeros(n); k[0], k[1], k[-1] = 0.5, 0.25, 0.25
    h = np.fft.fft(k)
    print(f"\n  {'ω':>10} | {'(1+cos ω)/2':>12} | {'np.fft.fft':>12} | 含义")
    meaning = {0: "零频 = 核的和 = 1(亮度不变)", n // 4: "中频,幅度减半", n // 2: "最高频(棋盘格)被完全抹掉"}
    for j in (0, n // 4, n // 2):
        w = 2 * np.pi * j / n
        print(f"  {w:>10.4f} | {(1 + np.cos(w)) / 2:>12.6f} | {h[j].real:>12.6f} | {meaning[j]}")

    print("\n  03-sharpening 第六节用的锐化核 [[0,−1,0],[−1,5,−1],[0,−1,0]]:")
    print("    H(ωx,ωy) = 5 − (e^(iωx)+e^(−iωx)) − (e^(iωy)+e^(−iωy)) = 5 − 2cos ωx − 2cos ωy")
    k2 = np.zeros((n, n))
    k2[0, 0] = 5; k2[0, 1] = k2[1, 0] = k2[0, -1] = k2[-1, 0] = -1
    h2 = np.fft.fft2(k2)
    print(f"  {'(ωx,ωy)':>12} | {'5−2cosωx−2cosωy':>16} | {'np.fft.fft2':>12}")
    for jx, jy in ((0, 0), (n // 2, 0), (n // 2, n // 2)):
        wx, wy = 2 * np.pi * jx / n, 2 * np.pi * jy / n
        label = f"({jx * 180 // (n // 2)}°,{jy * 180 // (n // 2)}°)"
        print(f"  {label:>12} | {5 - 2 * np.cos(wx) - 2 * np.cos(wy):>16.6f} | {h2[jx, jy].real:>12.6f}")
    print("  零频 1、最高频 9 —— 正是 03-sharpening 里「核的和 = 1 / 最高频增益 9」的来历。")


# ------------------------------------------------------------------ 图
def save_taylor_spiral_figure() -> None:
    """x=π 时泰勒部分和 S_N 在复平面上怎么逼近 −1。

    为什么要画:文档里那张表给了 N=2…24 的部分和与误差,数字都对,
    可看表看不出「它在平面上是怎么走的」—— 前几项乱跳、甚至越走越远,
    到 N=12 才贴住 −1。画出来一眼就看懂了。
    """
    x, n_max = np.pi, 30
    pts = np.array([partial_sum(x, n) for n in range(1, n_max + 1)])   # S_1 … S_30
    err = np.maximum(np.abs(pts + 1), 1e-17)
    far = int(np.argmax(np.abs(pts)))
    c30, c_pi = big_x_cost(30.0), big_x_cost(np.pi)
    table_n = (2, 4, 8, 12, 16, 20, 24)           # 与文档里那张表同一组 N

    fig = plt.figure(figsize=(15.2, 6.6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 1.0, 1.0], wspace=0.24,
                          left=0.045, right=0.985, top=0.885, bottom=0.40)

    th = np.linspace(0, 2 * np.pi, 400)
    cmap = plt.get_cmap("viridis")

    # ① 全貌
    ax = fig.add_subplot(gs[0])
    ax.plot(np.cos(th), np.sin(th), "--", color="#2c6fbb", lw=1.2, label="单位圆(e^(ix) 真正走的路)")
    ax.plot(pts.real, pts.imag, "-", color="#9aa5b1", lw=1.0, zorder=1)
    sc = ax.scatter(pts.real, pts.imag, c=np.arange(1, n_max + 1), cmap=cmap, s=34, zorder=3)
    ax.scatter([-1], [0], marker="*", s=260, color="#c4442a", zorder=4, label="目标 −1")
    for n in (1, 2, 3, 4, 5):
        z = pts[n - 1]
        ax.annotate(f"N={n}", (z.real, z.imag), xytext=(7, 6), textcoords="offset points", fontsize=8.6)
    # 放大窗口的位置
    wx, wy = (-1.4, 0.35), (-0.25, 0.65)
    ax.add_patch(plt.Rectangle((wx[0], wy[0]), wx[1] - wx[0], wy[1] - wy[0],
                               fill=False, ec="#a8700a", lw=1.4, ls=":"))
    ax.set_aspect("equal")
    ax.set_xlim(-4.9, 2.0)
    ax.set_ylim(-3.1, 3.9)
    ax.axhline(0, color="#ccd3da", lw=0.8); ax.axvline(0, color="#ccd3da", lw=0.8)
    ax.set_xlabel("实部"); ax.set_ylabel("虚部")
    ax.set_title(f"全貌:直角折线(每项只沿实轴或虚轴走),前 {n_max} 项", fontsize=10.5)
    ax.legend(loc="lower left", fontsize=8.2, framealpha=0.92)
    cb = fig.colorbar(sc, ax=ax, fraction=0.04, pad=0.02)
    cb.set_label("N(项数)", fontsize=9)

    # ② −1 附近放大
    ax2 = fig.add_subplot(gs[1])
    ax2.plot(np.cos(th), np.sin(th), "--", color="#2c6fbb", lw=1.2)
    sel = pts[5:]                                  # 从 N=6 起
    ax2.plot(sel.real, sel.imag, "-", color="#9aa5b1", lw=1.0, zorder=1)
    ax2.scatter(sel.real, sel.imag, c=np.arange(6, n_max + 1), cmap=cmap, vmin=1, vmax=n_max, s=40, zorder=3)
    ax2.scatter([-1], [0], marker="*", s=260, color="#c4442a", zorder=4)
    for n, off in ((6, (8, 6)), (7, (8, 6)), (8, (-26, -14)), (9, (8, -14)), (10, (8, 8)), (12, (-34, 10))):
        z = pts[n - 1]
        ax2.annotate(f"N={n}", (z.real, z.imag), xytext=off, textcoords="offset points", fontsize=8.6)
    ax2.set_aspect("equal")
    ax2.set_xlim(*wx); ax2.set_ylim(*wy)
    ax2.axhline(0, color="#ccd3da", lw=0.8)
    ax2.set_xlabel("实部")
    ax2.set_anchor("N")
    ax2.set_title("放大(左图虚线框):N=12 起贴住 −1", fontsize=11)
    for sp in ax2.spines.values():
        sp.set_edgecolor("#a8700a"); sp.set_linestyle(":"); sp.set_linewidth(1.4)

    # ③ 离 −1 的距离
    ax3 = fig.add_subplot(gs[2])
    ns = np.arange(1, n_max + 1)
    ax3.semilogy(ns, err, "o-", color="#6b4fa8", ms=4.5, lw=1.4)
    for n in table_n:
        if n < 8:                       # N=2、N=4 的值挤在曲线顶端,标出来会叠成一团
            continue
        ax3.annotate(f"{err[n - 1]:.1e}", (n, err[n - 1]), xytext=(5, 7), textcoords="offset points",
                     fontsize=8.0, color="#6b4fa8")
    ax3.axhline(1e-6, color="#2a8f4a", ls="--", lw=1.1)
    ax3.text(1.0, 1.6e-6, "误差 < 1e−6", color="#2a8f4a", fontsize=8.6)
    ax3.set_xlim(0, n_max + 1)
    ax3.set_ylim(5e-17, 2e1)
    ax3.set_xlabel("N(项数)"); ax3.set_ylabel("|S_N − (−1)|")
    ax3.set_title("离 −1 有多远(对数轴):越往后降得越快", fontsize=10.5)
    ax3.grid(alpha=0.25, which="both")

    fig.suptitle("泰勒部分和在复平面上逼近 e^(iπ) = −1:先乱跳,再贴住", fontsize=13, y=0.965)
    four_questions(fig,
        "把 e^(iπ) = Σ(iπ)ⁿ/n! 的\n前 N 项部分和,逐项画在\n复平面上(左);\n"
        "中间放大 −1 附近,\n右边看离 −1 的距离。",
        f"看见级数怎么落到 −1:\n前几项乱跳(N=2 在 {cplx(pts[1])}、\n"
        f"N=4 在 {cplx(pts[3])}),\nN=12 起贴住,\nN=20 误差 {err[19]:.1e}。",
        f"过程**不沿圆走**:路径一度\n冲到离原点 {abs(pts[far]):.2f} 远(N={far + 1},\n"
        f"单位圆的 {abs(pts[far]):.0f} 倍)。能算出 −1,\n却看不出「为什么在转」。",
        f"x 一大就崩:x=30 时单项\n最大到 {c30['max_term']:.1e},要抵消\n回模长 1,误差 {c30['naive_err']:.1e}\n"
        f"(x=π 时是 {c_pi['naive_err']:.0e})。",
        f"先把 x 折回 [−π,π](周期\n2π)再展开,误差回到\n{c30['reduced_err']:.0e};库函数的 sin/cos\n"
        "都先做范围缩减 ——\n查 range reduction、CORDIC。",
        y=0.295, bottom=0.40)
    save(fig, "euler-taylor-spiral.png")


def main() -> None:
    demo_times_i()
    demo_increment_is_perpendicular()
    demo_euler_polyline()
    demo_g_is_constant()
    demo_plug_in()
    demo_taylor()
    demo_errata()
    demo_two_to_the_i()
    demo_bombelli()
    demo_spring_and_identities()
    demo_kernel_frequency_response()
    print()
    save_taylor_spiral_figure()


if __name__ == "__main__":
    main()
