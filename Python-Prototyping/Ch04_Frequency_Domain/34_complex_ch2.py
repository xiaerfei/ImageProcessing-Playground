"""第 11 周前置:34 复变函数第二章「解析函数」的手算复核 ——
配合 Documents/数学基础/复变函数/02-解析函数.md。

笔记按《复变函数与积分变换》(华中科技大学数学系,第 5 版)第 2 章整理。
笔记里的每个数字、每道过关题的答案,都由本脚本重新算一遍;
和书上例题重合的地方(例 2.1~2.13)也在这里核对过,没有出入。

按笔记的顺序,验证八块:
 1. 导数:差商沿不同方向趋近,可导 ⇔ 方向无关(例 2.1、2.2)
 2. C-R 方程:数值残差;反例 u=v=xy/(x²+y²);f'(z) 的几个公式
 3. 调和函数:离散拉普拉斯算子;偏积分法(例 2.6~2.8);习题 2.5、2.7、2.9
 4. 指数函数:周期、模、辐角;例 2.9、2.10
 5. 对数函数:多值、主值、分支;例 2.11~2.13;Ln z² ≠ 2Ln z
 6. 幂函数:i^i、2^(1+i);z^(p/q) 有 q 个值
 7. 三角函数与双曲函数:无界、sin²z 可以是负数;习题 2.14、2.15
 8. 习题二里的计算题(2.1~2.3、2.9、2.13、2.14、2.18)
 + 配图:同一张方格网送进「解析」和「不解析」两个函数

⚠️ 书末「部分习题答案」(印刷页 216 起)我没有读,本脚本的答案是自己算的,没有和书对过。

用法:
    .venv/bin/python Ch04_Frequency_Domain/34_complex_ch2.py
会在 Documents/数学基础/复变函数/images/ 下生成 complex-ch2-conformal.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import four_questions, use_cjk_font  # noqa: E402

use_cjk_font()
import matplotlib.pyplot as plt  # noqa: E402

I = 1j
PI = np.pi
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


def partials(f, z: complex, h: float = 1e-6) -> tuple[float, float, float, float]:
    """u_x, u_y, v_x, v_y(中心差分)。"""
    fx = (f(z + h) - f(z - h)) / (2 * h)
    fy = (f(z + I * h) - f(z - I * h)) / (2 * h)
    return fx.real, fy.real, fx.imag, fy.imag


def cr_residual(f, z: complex) -> tuple[float, float]:
    """C-R 方程两个等式的残差:u_x - v_y、u_y + v_x(都为 0 才满足)。"""
    ux, uy, vx, vy = partials(f, z)
    return ux - vy, uy + vx


def lap(f, x: float, y: float, h: float = 1.0) -> float:
    """二维离散拉普拉斯(5 点模板 [[0,1,0],[1,-4,1],[0,1,0]]),f 是 (x,y)→实数。"""
    return f(x + h, y) + f(x - h, y) + f(x, y + h) + f(x, y - h) - 4 * f(x, y)


# ---------------------------------------------------------------- 1 导数
def step1_derivative() -> None:
    head("1 导数:差商沿不同方向趋近")
    f = lambda z: abs(z) ** 2
    print("例2.1 f=|z|² 在 z0=0:差商 = z̄,沿各方向都趋于 0,所以 f'(0)=0")
    for th in (0, PI / 3, PI / 2):
        h = 1e-6 * np.exp(I * th)
        print(f"   方向 {th / PI:.3f}π:差商 = {c((f(0 + h) - f(0)) / h, 6)}")
    z0 = 1 + 1j
    print(f"       |z|² 在 z0=1+i:差商 = z̄0 + z0·e^(-2iθ) + h̄,与方向有关")
    for th in (0, PI / 2):
        h = 1e-7 * np.exp(I * th)
        print(f"   方向 {th / PI:.1f}π:差商 = {c((f(z0 + h) - f(z0)) / h, 3)}"
              f"(公式 {c(np.conj(z0) + z0 * np.exp(-2j * th), 3)})")

    g = lambda z: z.real
    print("例2.2 f=Re z 处处不可导:沿实轴差商 1,沿虚轴差商 0")
    z0 = 0.3 + 0.7j
    for th, name in ((0, "实轴方向"), (PI / 2, "虚轴方向")):
        h = 1e-6 * np.exp(I * th)
        print(f"   {name}:差商 = {c((g(z0 + h) - g(z0)) / h, 4)}")

    print("对照:f=z² 在 z0=1+0.5i,差商沿四个方向都是 2z0 =", c(2 * (1 + 0.5j), 3))
    z0 = 1 + 0.5j
    for th in (0, PI / 4, PI / 2, PI):
        h = 1e-6 * np.exp(I * th)
        print(f"   方向 {th / PI:.2f}π:{c(((z0 + h) ** 2 - z0 ** 2) / h, 4)}")


# ---------------------------------------------------------------- 2 C-R
def step2_cauchy_riemann() -> None:
    head("2 柯西-黎曼方程")
    zs = [0.7 - 0.4j, 1.2 + 0.9j, -0.5 + 1.1j]
    tests = [("z²", lambda z: z ** 2), ("e^z", np.exp), ("sin z", np.sin), ("1/z", lambda z: 1 / z),
             ("z̄", np.conj), ("|z|²", lambda z: abs(z) ** 2 + 0j), ("Re z", lambda z: z.real + 0j)]
    print("C-R 残差 (u_x - v_y, u_y + v_x),取 3 个点的最大绝对值:")
    for name, f in tests:
        worst = max(max(abs(a), abs(b)) for a, b in (cr_residual(f, z) for z in zs))
        print(f"   {name:<6} {worst:.2e}" + ("   ← 满足" if worst < 1e-6 else "   ← 不满足"))
    r0 = cr_residual(lambda z: abs(z) ** 2 + 0j, 0j)
    r1 = cr_residual(lambda z: abs(z) ** 2 + 0j, 1 + 1j)
    print(f"例2.4(2) |z|² 的 C-R 方程只在原点成立:z=0 残差 ({r0[0]:.1e}, {r0[1]:.1e}),"
          f"z=1+i 残差 ({r1[0]:.1f}, {r1[1]:.1f})")

    # e^z:u=e^x cos y,v=e^x sin y
    z = 0.7 - 0.4j
    ux, uy, vx, vy = partials(np.exp, z)
    print(f"例2.4(3) e^z 在 z={c(z, 1)}:u_x + i v_x = {c(ux + 1j * vx)},e^z = {c(np.exp(z))};"
          f"v_y - i u_y = {c(vy - 1j * uy)}")

    # 反例:u=v=xy/(x²+y²)
    def bad(z: complex) -> complex:
        x, y = z.real, z.imag
        d = x * x + y * y
        return 0j if d == 0 else (1 + 1j) * x * y / d
    print("反例 u=v=xy/(x²+y²)(u(0,0)=0):原点处 4 个偏导数都是 0,C-R 方程成立,但函数在原点不连续:")
    print(f"   沿实轴趋近:f(t) = {c(bad(1e-3 + 0j), 3)};沿 y=x 趋近:f(t) = {c(bad(1e-3 * (1 + 1j)), 3)}"
          f"(= (1+i)/2)")
    bu = [(bad(1e-6) - bad(-1e-6)) / 2e-6, (bad(1e-6 * I) - bad(-1e-6 * I)) / 2e-6]
    print(f"   f 在原点沿 x、y 方向的导数:{c(bu[0], 3)}、{c(bu[1], 3)}(全为 0)")


# ---------------------------------------------------------------- 3 调和函数
def step3_harmonic() -> None:
    head("3 调和函数")
    u = lambda x, y: x ** 3 - 3 * x * y ** 2
    v = lambda x, y: 3 * x ** 2 * y - y ** 3
    pts = [(0, 0), (2, 3), (-4, 1), (5, -2)]
    print("例2.6 u=x³-3xy²,v=3x²y-y³:5 点离散拉普拉斯(h=1)")
    for x, y in pts:
        print(f"   ({x:>2},{y:>2}):Δu = {lap(u, x, y):.1f},Δv = {lap(v, x, y):.1f}")
    print(f"   对照 u=x²+y²(不是调和函数):Δ = {lap(lambda x, y: x * x + y * y, 2, 3):.1f}(应为 4)")
    f = lambda z: z ** 3 + 1j
    print(f"   f(z)=z³+i:f(0) = {c(f(0))};Re f = u?"
          f"{all(abs(f(complex(x, y)).real - u(x, y)) < 1e-9 for x, y in pts)},"
          f"Im f = v+1?{all(abs(f(complex(x, y)).imag - v(x, y) - 1) < 1e-9 for x, y in pts)}")

    # 例2.7
    v7 = lambda x, y: np.exp(x) * (y * np.cos(y) + x * np.sin(y)) + x + y
    f7 = lambda z: z * np.exp(z) + (1 + 1j) * z
    err = max(abs(f7(complex(x, y)).imag - v7(x, y)) for x, y in [(0.3, 0.8), (-1.2, 0.5), (1.5, -0.4)])
    print(f"例2.7 f(z)=z·e^z+(1+i)z:f(0) = {c(f7(0))};Im f 与已知 v 的最大误差 {err:.1e};"
          f"C-R 残差 {max(abs(a) for a in cr_residual(f7, 0.4 + 0.6j)):.1e}")

    # 例2.8
    f8 = lambda z: (1 - 0.5j) * z ** 2 + 0.5j
    err = max(abs(f8(complex(x, y)).real - (x * x - y * y + x * y)) for x, y in [(0.3, 0.8), (-1.2, 0.5), (1.5, -0.4)])
    print(f"例2.8 f(z)=(1-i/2)z²+i/2:f(i) = {c(f8(1j))}(应为 -1+i);Re f 与 x²-y²+xy 最大误差 {err:.1e}")

    # 习题 2.5:Δ|f|² = 4|f'|²
    h = 1e-4
    fz = lambda z: z ** 3 + 2 * z
    sq = lambda x, y: abs(fz(complex(x, y))) ** 2
    x0, y0 = 0.6, -0.9
    lapv = (sq(x0 + h, y0) + sq(x0 - h, y0) + sq(x0, y0 + h) + sq(x0, y0 - h) - 4 * sq(x0, y0)) / h ** 2
    dz = 3 * complex(x0, y0) ** 2 + 2
    print(f"习题2.5 f=z³+2z 在 (0.6,-0.9):Δ|f|² = {lapv:.4f},4|f'|² = {4 * abs(dz) ** 2:.4f}")

    # 习题 2.7
    u7 = lambda z: (z.real ** 2 - z.imag ** 2) + 0j
    v7b = lambda z: z.imag / (z.real ** 2 + z.imag ** 2) + 0j
    print(f"习题2.7 u=x²-y²,v=y/(x²+y²):Δu = {lap(lambda x, y: x * x - y * y, 2, 3):.1f},"
          f"Δv(h=0.01) = {(lap(lambda x, y: y / (x * x + y * y), 2.0, 3.0, 0.01)) / 1e-4:.2e}(≈0:调和);")
    fbad = lambda z: u7(z).real + 1j * v7b(z).real
    print(f"   但 u+iv 的 C-R 残差 = ({cr_residual(fbad, 1 + 1j)[0]:.3f}, {cr_residual(fbad, 1 + 1j)[1]:.3f})(≠0,不解析)")

    # 习题 2.9
    print("习题2.9:")
    f2 = lambda z: z ** 2 + 3j * z
    print(f"   (2) v=2xy+3x → f = z²+3iz+C:Im f(0.4+0.6i) = {f2(0.4 + 0.6j).imag:.4f},"
          f"2xy+3x = {2 * 0.4 * 0.6 + 3 * 0.4:.4f}")
    f3 = lambda z: -1j * (z - 1) ** 2
    zz = 0.4 + 0.6j
    print(f"   (3) u=2(x-1)y,f(0)=-i → f = -i(z-1)²:f(0) = {c(f3(0))},Re f(0.4+0.6i) = {f3(zz).real:.4f},"
          f"2(x-1)y = {2 * (0.4 - 1) * 0.6:.4f}")
    f4 = lambda z: z * np.exp(z)
    print(f"   (4) u=e^x(x cos y - y sin y),f(0)=0 → f = z·e^z:f(0) = {c(f4(0))};"
          f"Re f(0.5+0.7i) = {f4(0.5 + 0.7j).real:.4f},u = {np.exp(0.5) * (0.5 * np.cos(0.7) - 0.7 * np.sin(0.7)):.4f}")


# ---------------------------------------------------------------- 4 指数
def step4_exp() -> None:
    head("4 指数函数")
    z = 0.8 - 1.3j
    print(f"e^(z+2πi) = {c(np.exp(z + 2j * PI))} = e^z = {c(np.exp(z))};|e^z| = {abs(np.exp(z)):.4f} = e^x = {np.exp(0.8):.4f};"
          f"arg e^z = {np.angle(np.exp(z)):.4f} = y = -1.3")
    print(f"e^(z1)·e^(z2) = e^(z1+z2):{abs(np.exp(0.3 + 1j) * np.exp(-1 + 2j) - np.exp(-0.7 + 3j)):.1e}")
    print(f"沿实轴 z→+∞:e^10 = {np.exp(10):.1f};z→-∞:e^-10 = {np.exp(-10):.2e}(所以 e^z 在 ∞ 处没有极限)")
    z = -3 + 1j * PI / 4
    print(f"例2.9 e^(-3+πi/4) = {c(np.exp(z), 6)};书上的形式 (√2/2)e^-3(1+i) = "
          f"{c(np.sqrt(2) / 2 * np.exp(-3) * (1 + 1j), 6)}")
    w = ((-2 + 1j) / (1 + 2j)) ** (1 / 3)
    print(f"例2.10 (-2+i)/(1+2i) = {c((-2 + 1j) / (1 + 2j))};它的 3 个立方根:")
    for k in range(3):
        r = np.exp(1j * (PI / 2 + 2 * PI * k) / 3)
        print(f"   k={k}: {c(r)}  (e^(i·{(PI / 2 + 2 * PI * k) / 3 / PI:.4f}π))")
    del w


# ---------------------------------------------------------------- 5 对数
def step5_log() -> None:
    head("5 对数函数")
    print("例2.11 Ln(-1) = (2k+1)πi:", [c((2 * k + 1) * PI * 1j, 4) for k in (-1, 0, 1)])
    z = 2 - 3j
    print(f"例2.12 Ln(2-3i) = ½ln13 - i(arctan(3/2)+2kπ):½ln13 = {0.5 * np.log(13):.4f},"
          f"arctan(3/2) = {np.arctan(1.5):.4f};主值 np.log = {c(np.log(z))}")
    print(f"例2.13 ln i = {c(np.log(1j))}(πi/2);ln(-2+3i) = {c(np.log(-2 + 3j))} "
          f"= ½ln13 + i(π - arctan(3/2)) = {0.5 * np.log(13):.4f} + {PI - np.arctan(1.5):.4f}i")
    z1, z2 = -1 + 1j, -1 + 2j
    lhs = np.log(z1 * z2)
    rhs = np.log(z1) + np.log(z2)
    print(f"Ln(z1 z2) = Ln z1 + Ln z2:z1=-1+i,z2=-1+2i:主值 ln(z1 z2) = {c(lhs)},ln z1 + ln z2 = {c(rhs)},"
          f"差 = {c(rhs - lhs)}(= 2πi·整数 = {(rhs - lhs).imag / (2 * PI):.1f}·2πi)")
    z = -1 + 1j
    print(f"Ln z² ≠ 2Ln z:z=-1+i:ln z² = {c(np.log(z ** 2))},2 ln z = {c(2 * np.log(z))}"
          f"(差 {c(2 * np.log(z) - np.log(z ** 2))} = 2πi)")
    print(f"习题2.18(2) Ln1 = Ln(z/z) = Ln z - Ln z 的两边:Ln 1 = 2kπi(k 任意整数),"
          f"Ln z - Ln z 取同一分支时才是 0:{[c(2j * PI * k, 2) for k in (-1, 0, 1)]}")
    z0 = 1 + 1j
    h = 1e-6
    print(f"d(ln z)/dz = 1/z:z0=1+i 数值导数 {c((np.log(z0 + h) - np.log(z0 - h)) / (2 * h), 5)},1/z0 = {c(1 / z0, 5)}")
    print(f"ln z 在负实轴上跳变:ln(-1+0.001i) = {c(np.log(-1 + 0.001j), 4)},ln(-1-0.001i) = {c(np.log(-1 - 0.001j), 4)}")


# ---------------------------------------------------------------- 6 幂
def step6_power() -> None:
    head("6 幂函数")
    print("i^i = e^(-(π/2+2kπ)):", [f"k={k}: {np.exp(-(PI / 2 + 2 * PI * k)):.6g}" for k in (-1, 0, 1)])
    print(f"   主值 np.power(i,i) = {c(np.power(1j, 1j), 6)}")
    print("2^(1+i) = 2e^(-2kπ)(cos ln2 + i sin ln2):")
    for k in (-1, 0, 1):
        val = 2 * np.exp(-2 * k * PI) * (np.cos(np.log(2)) + 1j * np.sin(np.log(2)))
        print(f"   k={k}: {c(val)}")
    print(f"   ln2 = {np.log(2):.4f};2^(1+i) 主值 np.power = {c(np.power(2, 1 + 1j))}")
    print("z^(2/3) 有 3 个值(z=8):", [c(8 ** (2 / 3) * np.exp(2j * PI * 2 * k / 3), 4) for k in range(3)])
    print("z^(1/2) 有 2 个值(z=-4):", [c(2 * np.exp(1j * (PI + 2 * PI * k) / 2), 4) for k in range(2)])


# ---------------------------------------------------------------- 7 三角
def step7_trig() -> None:
    head("7 三角函数与双曲函数")
    z = 0.7 - 1.1j
    cz = (np.exp(1j * z) + np.exp(-1j * z)) / 2
    sz = (np.exp(1j * z) - np.exp(-1j * z)) / (2j)
    print(f"cos z = (e^iz+e^-iz)/2 = {c(cz)}(np.cos {c(np.cos(z))});sin z = {c(sz)}(np.sin {c(np.sin(z))})")
    print(f"sin²z + cos²z = {c(sz ** 2 + cz ** 2)};sin(z+2π) - sin z = {c(np.sin(z + 2 * PI) - np.sin(z))}")
    print(f"cos(iy) = cosh y:y=3:cos(3i) = {c(np.cos(3j))},cosh 3 = {np.cosh(3):.4f}"
          f"(>1:cos 在复数里无界);y=10:{abs(np.cos(10j)):.1f}")
    print(f"sin²(-3i) = {c(np.sin(-3j) ** 2)} = -(e³-e^-3)²/4 = {-(np.exp(3) - np.exp(-3)) ** 2 / 4:.4f}(是负数)")
    print(f"cos²(1-i) = {c(np.cos(1 - 1j) ** 2)}(书上说它是一个复数)")
    print(f"习题2.15(5) |sin z|² = sin²x + sinh²y:{abs(sz) ** 2:.6f} vs {np.sin(0.7) ** 2 + np.sinh(-1.1) ** 2:.6f}")
    print(f"习题2.15(1) sin z = sin x cosh y + i cos x sinh y:{c(np.sin(0.7) * np.cosh(-1.1) + 1j * np.cos(0.7) * np.sinh(-1.1))}")
    print(f"习题2.15(6) sin(π/2-z) = cos z:{c(np.sin(PI / 2 - z))} vs {c(cz)}")
    print(f"双曲:sinh z = -i sin(iz):{c(np.sinh(z))} vs {c(-1j * np.sin(1j * z))};"
          f"cosh z = cos(iz):{c(np.cosh(z))} vs {c(np.cos(1j * z))}")
    print(f"习题2.16(1) cosh²z - sinh²z = {c(np.cosh(z) ** 2 - np.sinh(z) ** 2)}")
    print(f"(sin z)' = cos z:数值导数 {c((np.sin(z + 1e-6) - np.sin(z - 1e-6)) / 2e-6, 5)} vs {c(cz, 5)}")


# ---------------------------------------------------------------- 8 习题
def step8_exercises() -> None:
    head("8 习题二的计算题")
    z0 = 0.5 - 0.4j
    print(f"2.1(1) f=1/z:f'(z) = -1/z²:z0=0.5-0.4i:{c(-1 / z0 ** 2)};数值 {c((1 / (z0 + 1e-7) - 1 / z0) / 1e-7, 4)}")
    print("2.1(2) f=z·Re z:在 z0≠0 处不可导,在 z=0 可导,导数 0:")
    g = lambda z: z * z.real
    for z0, name in ((0j, "z=0"), (1 + 1j, "z=1+i")):
        qs = [((g(z0 + 1e-7 * np.exp(1j * th)) - g(z0)) / (1e-7 * np.exp(1j * th))) for th in (0, PI / 2)]
        print(f"   {name}:沿实轴/虚轴差商 {c(qs[0], 3)}、{c(qs[1], 3)}")
    print("2.2 何处可导、何处解析:")
    for name, f, zs in (("(2) x²+iy²", lambda z: z.real ** 2 + 1j * z.imag ** 2, [0j, 1 + 1j, 1 + 0j, 0.5 + 0.5j]),
                        ("(3) x³-3xy²+i(3x²y-y³)", lambda z: z ** 3, [1 + 2j]),
                        ("(4) sin x cosh y + i cos x sinh y", lambda z: np.sin(z), [0.5 + 0.8j])):
        res = [max(abs(a) for a in cr_residual(f, z)) for z in zs]
        print(f"   {name}:C-R 残差 " + ",".join(f"{r:.1e}" for r in res) + f"(点 {[c(z, 1) for z in zs]})")
    print("   (2) x²+iy²:C-R 即 2x = 2y,所以只在直线 y=x 上可导,处处不解析")
    print(f"   2.3(1) 1/(z²-1):奇点 ±1,f' = -2z/(z²-1)²:z0=0.3+0.2i:{c(-2 * (0.3 + 0.2j) / ((0.3 + 0.2j) ** 2 - 1) ** 2, 5)};"
          f"数值 {c((1 / ((0.3 + 0.2j + 1e-7) ** 2 - 1) - 1 / ((0.3 + 0.2j) ** 2 - 1)) / 1e-7, 4)}")
    a, b, cc, d = 2 + 1j, 1 - 1j, 1 + 0j, 3 + 1j
    zq = 0.4 + 0.3j
    f = lambda z: (a * z + b) / (cc * z + d)
    print(f"   2.3(2) (az+b)/(cz+d):f' = (ad-bc)/(cz+d)²:{c((a * d - b * cc) / (cc * zq + d) ** 2, 5)};"
          f"数值 {c((f(zq + 1e-7) - f(zq)) / 1e-7, 4)}")

    print("2.13 解方程:")
    k = np.arange(-1, 2)
    print(f"   (1) e^z = 1+√3i:z = ln2 + i(π/3+2kπ):{[c(np.log(2) + 1j * (PI / 3 + 2 * PI * kk), 4) for kk in k]}")
    print(f"       验算 e^z = {c(np.exp(np.log(2) + 1j * PI / 3), 4)}(应为 1+1.7321i)")
    print(f"   (2) ln z = πi/2:z = e^(πi/2) = {c(np.exp(1j * PI / 2), 4)}")
    z3 = [1j + 2 * PI * kk for kk in k] + [PI - 1j + 2 * PI * kk for kk in k]
    print(f"   (3) sin z = i sinh 1 = {c(1j * np.sinh(1))}:z = i+2kπ 或 π-i+2kπ:"
          f"sin(i) = {c(np.sin(1j))},sin(π-i) = {c(np.sin(PI - 1j))}")
    print(f"   (4) sin z + cos z = 0 ⇔ tan z = -1:z = -π/4 + kπ:sin+cos 在 -π/4 = {c(np.sin(-PI / 4) + np.cos(-PI / 4), 4)},"
          f"在 3π/4 = {c(np.sin(3 * PI / 4) + np.cos(3 * PI / 4), 4)}")

    print("2.14 求值:")
    print(f"   (1) cos i = (e+e^-1)/2 = cosh1 = {c(np.cos(1j))}")
    print(f"   (2) Ln(-3+4i) = ln5 + i(π - arctan(4/3) + 2kπ):ln5 = {np.log(5):.4f},π-arctan(4/3) = {PI - np.arctan(4 / 3):.4f};"
          f"主值 {c(np.log(-3 + 4j))}")
    lg = np.log(1 - 1j)
    by_formula = np.sqrt(2) * np.exp(PI / 4) * (np.cos(0.5 * np.log(2) - PI / 4) + 1j * np.sin(0.5 * np.log(2) - PI / 4))
    print(f"   (3) (1-i)^(1+i) = √2·e^(π/4-2kπ)·[cos(½ln2-π/4) + i sin(½ln2-π/4)]:k=0 → {c(by_formula)};"
          f"np.power 主值 {c(np.exp((1 + 1j) * lg))}(ln(1-i) = {c(lg)})")
    print(f"       k=1 → 模乘 e^(-2π) = {np.exp(-2 * PI):.6f}:{c(by_formula * np.exp(-2 * PI))}")
    print(f"   (4) 3^(3-i):主值 = {c(np.exp((3 - 1j) * np.log(3)))};= 27·e^(-i ln3) = "
          f"{c(27 * (np.cos(np.log(3)) - 1j * np.sin(np.log(3))))}")

    print("2.18(1) Ln z² = 2Ln z 的错:Ln z² = 2 ln z + 2kπi(k 任意整数),而 2Ln z = 2 ln z + 4kπi(只有偶数倍)")
    print(f"       Ln z² 的值集合比 2Ln z 多出 2πi 的奇数倍:z=-1+i:ln z² - 2 ln z = {c(np.log((-1 + 1j) ** 2) - 2 * np.log(-1 + 1j))}")


# ---------------------------------------------------------------- 图
def save_figure() -> None:
    head("图:同一张方格网,送进解析函数与不解析函数")
    f_an = lambda z: z ** 2                          # 解析
    f_na = lambda z: 2 * z.real + 1j * z.imag        # 不解析:w=2x+iy = (3z + z̄)/2
    z0 = 1 + 0.5j

    # 局部线性化的奇异值:解析 → 两个奇异值相等(= |f'|),不解析 → 不等
    def sv(f):
        ux, uy, vx, vy = partials(f, z0)
        s = np.linalg.svd(np.array([[ux, uy], [vx, vy]]), compute_uv=False)
        return s
    s_an, s_na = sv(f_an), sv(f_na)
    print(f"z0=1+0.5i:z² 的雅可比奇异值 {s_an[0]:.4f}、{s_an[1]:.4f}(= |2z0| = {abs(2 * z0):.4f}),最大/最小 = {s_an[0] / s_an[1]:.4f}")
    print(f"        2x+iy 的雅可比奇异值 {s_na[0]:.4f}、{s_na[1]:.4f},最大/最小 = {s_na[0] / s_na[1]:.4f}")
    print(f"        z² 的 C-R 残差 {max(abs(a) for a in cr_residual(f_an, z0)):.1e};2x+iy 的 C-R 残差 "
          f"{cr_residual(f_na, z0)[0]:.1f}、{cr_residual(f_na, z0)[1]:.1f}")
    print(f"        arg f'(z0) = arg(2z0) = {np.degrees(np.angle(2 * z0)):.2f}°(小方格被转过的角度)")

    xs = np.linspace(0.0, 2.0, 9)
    ys = np.linspace(-0.5, 1.5, 9)
    fine = np.linspace(0, 1, 120)
    th = np.linspace(0, 2 * PI, 200)
    r = 0.25
    circle = z0 + r * np.exp(1j * th)
    sq = z0 + r * np.array([-1 - 1j, 1 - 1j, 1 + 1j, -1 + 1j, -1 - 1j])

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 7.4))
    blue, red, green, gray = "#2c6fbb", "#c4442a", "#2a8f4a", "#666"

    def draw(ax, f, title, lim_x, lim_y, note):
        for x in xs:
            w = f(x + 1j * (ys[0] + (ys[-1] - ys[0]) * fine))
            ax.plot(w.real, w.imag, color="#bbb", lw=0.8)
        for y in ys:
            w = f(xs[0] + (xs[-1] - xs[0]) * fine + 1j * y)
            ax.plot(w.real, w.imag, color="#bbb", lw=0.8)
        cw, sw = f(circle), f(sq)
        ax.plot(cw.real, cw.imag, color=red, lw=2)
        ax.plot(sw.real, sw.imag, color=blue, lw=2)
        ax.plot([f(z0).real], [f(z0).imag], "o", color="black", ms=4)
        ax.set_xlim(*lim_x)
        ax.set_ylim(*lim_y)
        ax.set_aspect("equal", adjustable="datalim")     # 保持 1:1,三个框一样大
        ax.set_box_aspect(1)
        ax.axhline(0, color="#999", lw=0.7)
        ax.axvline(0, color="#999", lw=0.7)
        ax.set_title(title, fontsize=11.5, loc="left")
        ax.tick_params(labelsize=8)
        ax.set_xlabel("实轴\n" + note, fontsize=9, color=gray, linespacing=1.5)

    ident = lambda z: z
    draw(axes[0], ident, "① z 平面:方格网、小圆、小方块", (-0.2, 2.2), (-0.7, 1.7),
         "黑点 z0=1+0.5i;红圆半径 0.25,蓝方块边长 0.5")
    axes[0].set_ylabel("虚轴", fontsize=9)
    draw(axes[1], f_an, "② w=z²(解析)", (-3.0, 4.6), (-3.2, 6.0),
         f"f'(z0)=2z0=2+i,|f'|={abs(2 * z0):.3f},辐角 {np.degrees(np.angle(2 * z0)):.1f}°\n"
         f"圆还是圆,方块转了 {np.degrees(np.angle(2 * z0)):.1f}°、放大 {abs(2 * z0):.3f} 倍;最大/最小拉伸 {s_an[0] / s_an[1]:.2f}")
    draw(axes[2], f_na, "③ w=2x+iy(不解析)", (-0.4, 4.4), (-1.6, 3.2),
         f"横向拉伸 {s_na[0]:.1f} 倍、纵向 {s_na[1]:.1f} 倍\n"
         f"圆变椭圆,最大/最小拉伸 {s_na[0] / s_na[1]:.2f};C-R 残差 {cr_residual(f_na, z0)[0]:.0f}(应为 0)")

    four_questions(
        fig,
        did="把同一张方格网、同一个小圆\n和小方块,分别送进解析的 z²\n和不解析的 2x+iy,看变成什么",
        gained="解析时局部只做「旋转+放缩」\n(乘 f'(z0)):小圆仍是圆,\n最大/最小拉伸 = 1.00;\n不解析时 = 2.00,C-R 不成立",
        lost="这只是「无穷小」的性质:\n小圆画大了,② 里的圆也会\n被 z² 弯成蛋形,\n不再是严格的圆",
        limit="f'(z)=0 的点(z² 在原点)\n方格会被压成一点,\n局部保形这条性质失效",
        better="想系统用它做映射,\n看第 6 章共形映射",
        y=0.17, bottom=0.27)
    out = Path(__file__).resolve().parents[2] / "Documents" / "数学基础" / "复变函数" / "images"
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "complex-ch2-conformal.png", dpi=130, bbox_inches="tight", facecolor="white")
    print("  → Documents/数学基础/复变函数/images/complex-ch2-conformal.png")
    plt.close(fig)


def main() -> None:
    step1_derivative()
    step2_cauchy_riemann()
    step3_harmonic()
    step4_exp()
    step5_log()
    step6_power()
    step7_trig()
    step8_exercises()
    save_figure()


if __name__ == "__main__":
    main()
