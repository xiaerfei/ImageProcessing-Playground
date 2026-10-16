"""第 11 周前置:33 复变函数第一章「复数与复变函数」的手算复核 ——
配合 Documents/数学基础/复变函数/01-复数与复变函数.md。

那篇笔记按《复变函数与积分变换》(华中科技大学数学系,第 5 版)第 1 章整理。
笔记里每一个例子、每一道过关题的数字,都由本脚本重新算一遍;
和书上例题重合的地方(例 1.2~1.8、1.12~1.16 等)也在这里核对过,没有出入。

按笔记的顺序,验证七块:
 1. 四则运算与共轭:乘法公式、除法「上下同乘共轭」、共轭的几条性质
 2. 模与辐角:主辐角的分段公式(含象限的坑)、三角不等式、取等条件
 3. 乘除法 = 旋转 + 伸缩:模相乘角相加;乘 i 转 90°;1/z 的三角式
 4. 乘方与开方:棣莫弗公式、三倍角、z³=2 的三个根、单位根与 DFT 的关系
 5. 点集与曲线:几个常见不等式、参数方程
 6. 复变函数:u、v 拆分;极限与方向有关(z̄/z);arg z 在负实轴上不连续
 7. 习题一里的计算题(1.1、1.3、1.6、1.8)的答案

⚠️ 书末「部分习题答案」(印刷页 216 起)我没有读,本脚本的答案是自己算的,没有和书对过。

用法:
    .venv/bin/python Ch04_Frequency_Domain/33_complex_ch1.py
会在 Documents/数学基础/复变函数/images/ 下生成 complex-ch1-rotate-roots.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import four_questions, use_cjk_font  # noqa: E402

use_cjk_font()
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Arc  # noqa: E402

I = 1j
S3 = np.sqrt(3)
RNG = np.random.default_rng(0)


def head(title: str) -> None:
    print(f"\n{'=' * 8} {title} {'=' * 8}")


def c(z: complex, nd: int = 4) -> str:
    """复数打印成 -0.6000-1.2000i;接近 0 的部分抹掉。"""
    z = complex(z)
    re = 0.0 if abs(z.real) < 10 ** (-nd - 1) else z.real
    im = 0.0 if abs(z.imag) < 10 ** (-nd - 1) else z.imag
    if im == 0:
        return f"{re:.{nd}f}"
    if re == 0:
        return f"{im:.{nd}f}i"
    return f"{re:.{nd}f}{im:+.{nd}f}i"


def polar(z: complex) -> str:
    return f"模 {abs(z):.4f}, 主辐角 {np.angle(z):.4f} rad = {np.angle(z) / np.pi:.4f}π"


# ---------------------------------------------------------------- 1 四则运算
def step1_arithmetic() -> None:
    head("1 四则运算与共轭")
    z1, z2 = 2 - 3 * I, 4 + 5 * I
    re = z1.real * z2.real - z1.imag * z2.imag
    im = z1.real * z2.imag + z2.real * z1.imag
    print(f"(2-3i)(4+5i):实部 2·4-(-3)·5 = {re:.0f},虚部 2·5+4·(-3) = {im:.0f} → {c(z1 * z2, 0)}")
    print(f"i·i = {c(I * I, 0)}")

    a, b = 3 - 2 * I, 2 + 3 * I
    num = a * np.conj(b)
    print(f"(3-2i)/(2+3i):分子乘共轭 (3-2i)(2-3i) = {c(num, 0)},分母 2²+3² = {abs(b) ** 2:.0f}"
          f" → {c(num / abs(b) ** 2, 0)};直接除 = {c(a / b)}")
    print(f"z·z̄ = x²+y²:z=3+4i → {c((3 + 4 * I) * (3 - 4 * I), 0)}")

    # 共轭的性质,随机两个复数各验一次
    p = complex(*RNG.uniform(-3, 3, 2))
    q = complex(*RNG.uniform(-3, 3, 2))
    cj = np.conj
    errs = [
        abs(cj(p + q) - (cj(p) + cj(q))),
        abs(cj(p * q) - cj(p) * cj(q)),
        abs(cj(p / q) - cj(p) / cj(q)),
        abs(p.real - (p + cj(p)).real / 2),
        abs(p.imag - ((p - cj(p)) / (2 * I)).real),
        abs(2 * (p * cj(q)).real - (p * cj(q) + cj(p) * q)),
    ]
    print(f"共轭六条性质(和/积/商/Re/Im/例1.1):随机复数下最大误差 {max(errs):.1e}")


# ---------------------------------------------------------------- 2 模与辐角
def book_arg(z: complex) -> float:
    """书 §1.2.1 的分段公式,原样照写。"""
    x, y = z.real, z.imag
    if x > 0:
        return np.arctan(y / x)
    if x == 0 and y > 0:
        return np.pi / 2
    if x < 0 and y >= 0:
        return np.arctan(y / x) + np.pi
    if x < 0 and y < 0:
        return np.arctan(y / x) - np.pi
    return -np.pi / 2  # x == 0, y < 0


def step2_modulus_arg() -> None:
    head("2 模与辐角")
    pts = [3 + 4 * I, 1 + 1 * I, -1 + 1 * I, -1 - 1 * I, 1 - 1 * I, 2 * I, -2 * I, -3 + 0 * I]
    ok = all(abs(book_arg(z) - np.angle(z)) < 1e-12 for z in pts)
    print(f"书里的分段公式 = np.angle(即 arctan2)? {ok}(共 {len(pts)} 个点,含坐标轴上的)")
    z = -1 - 1 * I
    print(f"象限的坑:z=-1-i,arctan(y/x) = arctan(1) = {np.arctan(1):.4f}(错);"
          f"正确主辐角 = {np.angle(z):.4f} = -3π/4 = {-3 * np.pi / 4:.4f}")
    print(f"负实轴:arg(-3) = {np.angle(-3 + 0 * I):.4f} = π(规定 -π<arg≤π,所以负实轴取 π 而不是 -π)")

    z1, z2 = 3 + 4 * I, 1 - 2 * I
    lo, mid, hi = abs(abs(z1) - abs(z2)), abs(z1 + z2), abs(z1) + abs(z2)
    print(f"三角不等式 z1=3+4i, z2=1-2i:||z1|-|z2|| = {lo:.4f} ≤ |z1+z2| = {mid:.4f} ≤ |z1|+|z2| = {hi:.4f}")
    z1, z2 = 1 + 1 * I, 2 + 2 * I
    print(f"取等:z1=1+i, z2=2+2i 在过原点同一条射线上:|z1+z2| = {abs(z1 + z2):.4f}"
          f" = |z1|+|z2| = {abs(z1) + abs(z2):.4f}")
    z1, z2 = 3 + 4 * I, 1 - 2 * I
    lhs = abs(z1 + z2) ** 2 + abs(z1 - z2) ** 2
    rhs = 2 * (abs(z1) ** 2 + abs(z2) ** 2)
    print(f"平行四边形等式(习题 1.7(2)):|z1+z2|²+|z1-z2|² = {lhs:.0f} = 2(|z1|²+|z2|²) = {rhs:.0f}")
    print(f"|z1-z2| 就是两点距离:3+4i 到 1-2i = {abs(z1 - z2):.4f} = √(2²+6²) = {np.hypot(2, 6):.4f}")


# ---------------------------------------------------------------- 3 乘除法
def step3_mul_div() -> None:
    head("3 乘除法 = 旋转 + 伸缩")
    a, b = 1 + S3 * I, -S3 - 1 * I
    print(f"例1.5:1+√3i → {polar(a)}(π/3 = {np.pi / 3 / np.pi:.4f}π)")
    print(f"       -√3-i → {polar(b)}(-5π/6 = {-5 / 6:.4f}π)")
    print(f"       乘积 {c(a * b)}:模 {abs(a) * abs(b):.0f}=2×2,辐角 {(np.angle(a) + np.angle(b)) / np.pi:.4f}π = π/3+(-5π/6) = -π/2")
    a, b = 2 + 1 * I, 1 - 2 * I
    print(f"例1.6:(2+i)/(1-2i) = {c(a / b)};模比 {abs(a) / abs(b):.4f},辐角差"
          f" {np.arctan(1 / 2) - np.arctan(-2):.4f} = π/2 = {np.pi / 2:.4f}")
    z = 1 + 1 * I
    print(f"乘 i 转 90°:i·(1+i) = {c(I * z, 0)}(1+i 在 45°,结果在 135°);"
          f"乘 -i:-i·(1+i) = {c(-I * z, 0)}(顺时针 90°)")
    z = 3 + 4 * I
    print(f"1/z(例1.4):z=3+4i → 1/z = {c(1 / z, 2)} = z̄/|z|² = {c(np.conj(z) / abs(z) ** 2, 2)};"
          f"模 {abs(1 / z):.2f} = 1/{abs(z):.0f},辐角取负")
    # 复数乘法只有「旋转缩放」这一个效果:对 8 个点验证
    pts = RNG.uniform(-2, 2, 8) + 1j * RNG.uniform(-2, 2, 8)
    w = 0.5 * np.exp(1j * np.pi / 6)
    ok = np.allclose(np.abs(w * pts), 0.5 * np.abs(pts)) and \
         np.allclose(np.angle(w * pts / pts), np.pi / 6)
    print(f"乘 w=0.5·e^(iπ/6):8 个随机点的模全部缩成一半、辐角全部加 π/6? {ok}")


# ---------------------------------------------------------------- 4 乘方开方
def step4_power_root() -> None:
    head("4 乘方与开方")
    z = 1 + S3 * I
    print(f"例1.7:(1+√3i)³ = {c(z ** 3)};三角式 2³(cosπ+i sinπ) = {c(8 * np.exp(1j * np.pi))}")
    th = 0.7
    print(f"三倍角:θ=0.7:cos3θ = {np.cos(3 * th):.6f};cos³θ-3cosθ·sin²θ = "
          f"{np.cos(th) ** 3 - 3 * np.cos(th) * np.sin(th) ** 2:.6f}")
    print(f"           sin3θ = {np.sin(3 * th):.6f};3cos²θ·sinθ-sin³θ = "
          f"{3 * np.cos(th) ** 2 * np.sin(th) - np.sin(th) ** 3:.6f}")

    r = 2 ** (1 / 3)
    roots = [r * np.exp(2j * np.pi * k / 3) for k in range(3)]
    print(f"例1.8:z³=2 的三个根(∛2 = {r:.4f}):")
    for k, w in enumerate(roots):
        print(f"   k={k}: {c(w)};模 {abs(w):.4f},辐角 {np.angle(w) / np.pi:.4f}π;w³ = {c(w ** 3)}")
    print(f"   与书上形式对照:∛2·(-1/2+√3/2 i) = {c(r * (-0.5 + S3 / 2 * I))}")

    for n in (4, 8):
        w = np.exp(2j * np.pi * np.arange(n) / n)
        print(f"{n} 次单位根之和 = {c(w.sum())};每个都满足 w^{n} = 1:{np.allclose(w ** n, 1)}")
    W = np.exp(-2j * np.pi / 4)
    print(f"DFT 的旋转因子 W=e^(-i2π/4) = {c(W, 0)};W 的 0~3 次方 = "
          f"{[c(W ** k, 0) for k in range(4)]}")
    x = np.array([1, 2, 3, 4])
    X1 = sum(x[n] * W ** n for n in range(4))
    print(f"   X[1] = 1·1+2·(-i)+3·(-1)+4·(i) = {c(X1, 0)};np.fft.fft = {c(np.fft.fft(x)[1], 0)}")


# ---------------------------------------------------------------- 5 点集曲线
def step5_sets() -> None:
    head("5 点集与曲线")
    z = RNG.uniform(-2, 2, 6) + 1j * RNG.uniform(-2, 2, 6)
    print("例1.12(1) z+z̄>0 ⇔ Re z>0(6 个随机点逐个对照):",
          all(((z + np.conj(z)).real > 0) == (z.real > 0)))
    z0 = -2 + 1 * I
    tests = [z0, z0 + 1, z0 + 0.5, z0 + 1.5j, 0]
    print("例1.12(2) |z+2-i|≥1 即到 -2+i 的距离≥1(圆周及其外部):")
    for t in tests:
        print(f"   z={c(t, 2):>12}  |z+2-i| = {abs(t + 2 - 1j):.4f}  属于? {abs(t + 2 - 1j) >= 1}")
    print("例1.12(3) 0<arg z<π/3:")
    for t in [1 + 0.5 * I, 1 + 2 * I, 1 + 0 * I, -1 + 0.5 * I]:
        print(f"   z={c(t, 2):>12}  arg/π = {np.angle(t) / np.pi:.4f}  属于? {0 < np.angle(t) < np.pi / 3}")
    z1, z2 = 1 + 1 * I, 3 + 5 * I
    print(f"线段 z1+(z2-z1)t:z1=1+i, z2=3+5i,t=0 → {c(z1 + (z2 - z1) * 0, 0)},t=0.5 → "
          f"{c(z1 + (z2 - z1) * 0.5, 0)}(中点),t=1 → {c(z1 + (z2 - z1) * 1, 0)}")
    a = 2.0
    t = np.linspace(0, 2 * np.pi, 7)
    print(f"圆周 z=a(cos t+i sin t):a=2,各点模都是 {np.round(np.abs(a * (np.cos(t) + 1j * np.sin(t))), 6)}")


# ---------------------------------------------------------------- 6 复变函数
def step6_functions() -> None:
    head("6 复变函数")
    z = 1 + 2 * I
    x, y = z.real, z.imag
    w = z ** 2 + 1
    print(f"例1.13:w=z²+1,z=1+2i → w = {c(w, 0)};u=x²-y²+1 = {x * x - y * y + 1:.0f},v=2xy = {2 * x * y:.0f}")
    print(f"图1.15:z=1/2+i/2 → z² = {c((0.5 + 0.5j) ** 2, 1)}(=i/2)")
    u, v = 2 * x / (x * x + y * y), y / (x * x + y * y)
    print(f"例1.14:z=1+2i:u+iv = {c(u + 1j * v)};3/(2z̄)+1/(2z) = {c(3 / (2 * np.conj(z)) + 1 / (2 * z))}")
    print("例1.15 f(z)=z̄/z 在 0 附近:沿不同方向 θ0 趋近 0,极限 e^(-2iθ0) 不同:")
    for th, name in [(0, "0"), (np.pi / 4, "π/4"), (np.pi / 2, "π/2"), (np.pi, "π")]:
        zz = 1e-6 * np.exp(1j * th)
        print(f"   θ0={name:>3}: f = {c(np.conj(zz) / zz, 3)}")
    up, dn = -1 + 1e-3 * I, -1 - 1e-3 * I
    print(f"例1.16 arg z 在负实轴上跳变:arg(-1+0.001i) = {np.angle(up):.4f},"
          f"arg(-1-0.001i) = {np.angle(dn):.4f}(差 ≈ 2π)")


# ---------------------------------------------------------------- 7 习题一
def step7_exercises() -> None:
    head("7 习题一的计算题")
    print(f"1.1(1) (1+i)-(3-2i) = {c((1 + I) - (3 - 2 * I), 0)}")
    a, b = 2.0, 3.0
    print(f"1.1(2) (a-ib)³ 取 a=2,b=3:{c((a - 1j * b) ** 3, 0)};公式 (a³-3ab²)+i(b³-3a²b) = "
          f"{a ** 3 - 3 * a * b * b:.0f}{b ** 3 - 3 * a * a * b:+.0f}i")
    print(f"1.1(3) i/((i-1)(i-2)) = {c(I / ((I - 1) * (I - 2)), 2)};(i-1)(i-2) = {c((I - 1) * (I - 2), 0)}")
    z = 0.7 - 1.3 * I
    x, y = z.real, z.imag
    print(f"1.1(4) (z-1)/(z+1) 取 z=0.7-1.3i:{c((z - 1) / (z + 1))};"
          f"公式 [(x²+y²-1)+2iy]/[(x+1)²+y²] = "
          f"{c(((x * x + y * y - 1) + 2j * y) / ((x + 1) ** 2 + y * y))}")
    A = np.array([[2, -1], [1 + I, I]])
    rhs = np.array([I, 4 - 3 * I])
    z1, z2 = np.linalg.solve(A, rhs)
    print(f"1.3 方程组 2z1-z2=i,(1+i)z1+iz2=4-3i:z1 = {c(z1)},z2 = {c(z2)};代回:"
          f"{c(2 * z1 - z2)}, {c((1 + I) * z1 + I * z2)}")
    print("1.6 模与主辐角:")
    for z in (S3 + 1 * I, -1 - 1 * I, 2 - 1 * I, -1 + 3 * I):
        print(f"   {c(z, 0):>8}: {polar(z)}")
    print("1.8 三角式:")
    z = -3 + 2 * I
    print(f"   (1) -3+2i:模 √13 = {np.sqrt(13):.4f}(实际 {abs(z):.4f}),主辐角 π-arctan(2/3) = "
          f"{np.pi - np.arctan(2 / 3):.4f}(实际 {np.angle(z):.4f})")
    al = 0.4
    z = np.sin(al) + 1j * np.cos(al)
    print(f"   (2) sinα+i cosα(α=0.4):模 {abs(z):.4f},辐角 {np.angle(z):.4f} = π/2-α = {np.pi / 2 - al:.4f}")
    z = -np.sin(np.pi / 6) - 1j * np.cos(np.pi / 6)
    print(f"   (3) -sin(π/6)-i cos(π/6) = {c(z)}:模 {abs(z):.4f},辐角 {np.angle(z) / np.pi:.4f}π = -2π/3")


# ---------------------------------------------------------------- 图
def arrow(ax, z, color, label=None, lw=2.2, dx=0.0, dy=0.0, ha="left"):
    ax.annotate("", xy=(z.real, z.imag), xytext=(0, 0),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, shrinkA=0, shrinkB=0))
    if label:
        ax.text(z.real + dx, z.imag + dy, label, color=color, fontsize=10.5, ha=ha, va="center")


def setup(ax, lim, title):
    ax.set_xlim(*lim)
    ax.set_ylim(*lim)
    ax.set_aspect("equal")
    ax.axhline(0, color="#999", lw=0.8)
    ax.axvline(0, color="#999", lw=0.8)
    ax.set_xlabel("实轴 Re", fontsize=9)
    ax.set_ylabel("虚轴 Im", fontsize=9)
    ax.set_title(title, fontsize=11.5, loc="left")
    ax.grid(alpha=0.25)
    ax.tick_params(labelsize=8)


def wrap(text: str, n: int = 25) -> str:
    """横幅每格只有约 3 英寸宽,中文按字数硬折行(matplotlib 不会自动换行)。"""
    return "\n".join(text[i:i + n] for i in range(0, len(text), n))


def save_figure() -> None:
    head("图:乘法 = 旋转伸缩 / 开方 = 均分一圈 / 单位根 = DFT 的探针")
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 7.4))
    blue, red, green, ora, gray = "#2c6fbb", "#c4442a", "#2a8f4a", "#d98a14", "#666"
    th = np.linspace(0, 2 * np.pi, 200)

    # ① 乘法:(1+√3i)(-√3-i) = -4i
    ax = axes[0]
    a, b = 1 + S3 * I, -S3 - 1 * I
    p = a * b
    setup(ax, (-4.8, 4.8), "① 乘法:模相乘,角相加")
    ax.plot(2 * np.cos(th), 2 * np.sin(th), color="#bbb", lw=0.9, ls=":")
    ax.plot(4 * np.cos(th), 4 * np.sin(th), color="#bbb", lw=0.9, ls=":")
    arrow(ax, a, blue, "z₁=1+√3i\n模2, 60°", dx=0.15, dy=0.4)
    arrow(ax, b, green, "z₂=-√3-i\n模2, -150°", dx=-0.1, dy=-0.6, ha="right")
    arrow(ax, p, red, "z₁z₂=-4i\n模4, -90°", dx=0.25, dy=0.9)
    ax.add_patch(Arc((0, 0), 1.2, 1.2, theta1=0, theta2=60, color=blue, lw=1.4))
    ax.add_patch(Arc((0, 0), 1.8, 1.8, theta1=-150, theta2=0, color=green, lw=1.4))
    ax.add_patch(Arc((0, 0), 2.6, 2.6, theta1=-90, theta2=0, color=red, lw=1.4, ls="--"))
    ax.text(0.75, 0.12, "60°", color=blue, fontsize=9)
    ax.text(-1.1, 0.25, "-150°", color=green, fontsize=9, ha="right")
    ax.text(1.05, -1.4, "-90°", color=red, fontsize=9)
    ax.text(0, -4.6, "角度:60° + (-150°) = -90°      模:2 × 2 = 4", ha="center", fontsize=9, color=gray)

    # ② 开方:z³=2
    ax = axes[1]
    r = 2 ** (1 / 3)
    roots = [r * np.exp(2j * np.pi * k / 3) for k in range(3)]
    setup(ax, (-1.9, 1.9), "② 开方:n 个根均分一圈")
    ax.plot(r * np.cos(th), r * np.sin(th), color="#bbb", lw=0.9, ls=":")
    poly = roots + [roots[0]]
    ax.plot([w.real for w in poly], [w.imag for w in poly], color=ora, lw=1.4)
    labels = ["k=0\n1.260", "k=1\n-0.630+1.091i", "k=2\n-0.630-1.091i"]
    offs = [(0.12, 0.0, "left"), (-0.1, 0.15, "right"), (-0.1, -0.15, "right")]
    for w, lab, (ox, oy, ha) in zip(roots, labels, offs):
        arrow(ax, w, ora, None, lw=1.8)
        ax.plot(w.real, w.imag, "o", color=ora, ms=6)
        ax.text(w.real + ox, w.imag + oy, lab, color=ora, fontsize=9.5, ha=ha, va="center")
    ax.text(0.05, 0.3, "z³=2\n|z|≈1.260", ha="center", va="center", fontsize=9, color=gray)
    ax.text(0.05, -0.3, "根间隔 120°", ha="center", va="center", fontsize=9, color=gray)

    # ③ 4 次单位根与 DFT
    ax = axes[2]
    setup(ax, (-1.7, 1.7), "③ 4 点 DFT 的探针:W = -i 的幂")
    ax.plot(np.cos(th), np.sin(th), color="#bbb", lw=0.9)
    pw = [(1, "W⁰=1", (0.1, 0.12, "left")), (-1j, "W¹=-i", (0.1, -0.1, "left")),
          (-1, "W²=-1", (-0.1, 0.12, "right")), (1j, "W³=i", (0.1, 0.1, "left"))]
    for z, lab, (ox, oy, ha) in pw:
        arrow(ax, z, blue, None, lw=1.8)
        ax.plot(z.real, z.imag, "o", color=blue, ms=6)
        ax.text(z.real + ox, z.imag + oy, lab, color=blue, fontsize=10, ha=ha, va="center")
    ax.text(0, 1.5, "x=[1,2,3,4] 的 X[1] = Σ xₙ Wⁿ", ha="center", fontsize=9.5, color=gray)
    ax.text(0, 1.3, "= 1×1 + 2×(-i) + 3×(-1) + 4×i = -2+2i", ha="center", fontsize=9.5, color=red)
    ax.text(0, -1.5, "4 个单位根之和 = 0(转满一圈互相抵消)", ha="center", fontsize=9, color=gray)

    four_questions(
        fig,
        did=wrap("把复数写成「模+辐角」(指数式),乘法只剩两件事:模相乘、辐角相加。"
                 "三张图依次是乘、开方、DFT 的探针"),
        gained=wrap("(1+√3i)(-√3-i) 一步得 -4i;z³=2 的三个根一次写全;DFT 的 W 就是 4 次单位根"),
        lost=wrap("加减法反而麻烦:模和辐角不能直接相加,要先拆回 x+iy;辐角不唯一(差 2π 的整数倍)"),
        limit=wrap("0 没有辐角;主辐角在负实轴上会跳变(π 与 -π);手算最容易在象限上写错"),
        better=wrap("加减用 x+iy,乘除乘方开方用指数式,随手切换;细节见欧拉公式那篇"),
        y=0.235, bottom=0.275)
    # 图跟着笔记放(Documents/数学基础/复变函数/images/),文档里的链接就只有一层,预览器不容易丢图
    out = Path(__file__).resolve().parents[2] / "Documents" / "数学基础" / "复变函数" / "images"
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "complex-ch1-rotate-roots.png", dpi=130, bbox_inches="tight", facecolor="white")
    print("  → Documents/数学基础/复变函数/images/complex-ch1-rotate-roots.png")
    plt.close(fig)


def main() -> None:
    step1_arithmetic()
    step2_modulus_arg()
    step3_mul_div()
    step4_power_root()
    step5_sets()
    step6_functions()
    step7_exercises()
    save_figure()


if __name__ == "__main__":
    main()
