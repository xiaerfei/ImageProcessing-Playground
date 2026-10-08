"""第 11 周前置:31 信号与系统学习路线的「过关题」标准答案 ——
配合 Documents/数学基础/信号与系统学习路线.md。

那篇文档给每一步配了几道**能手算**的过关题。题目只有手算得出来才有意义,
所以答案不能凭感觉写:本脚本把每一道题都用 numpy 重新算一遍,文档里出现的数字全部从这里来。

按文档的步骤顺序,验证九块:
 0. 数学热身:复数乘法、积化和差、等比求和、内积换基、三角函数正交
 1. 离散信号:冲激/阶跃、任何信号 = 一串平移冲激的和、周期与非周期、频率差 2π 等价
 2. 系统:四个系统判线性/时不变;黑盒系统只喂一个冲激,就能预测任意输入的输出
 3. 卷积:手算两题;卷积 = 多项式乘法;交换/结合律;[1,2,1]/4 抹平阶跃
 4. DFT:4 点五个手算结果;DFT 矩阵的正交性;帕塞瓦尔(Parseval);k 对应的频率
 5. DFT 性质:平移只转相位、循环卷积 vs 线性卷积、补零、频谱泄漏与加窗
 6. 频率响应:H(ω)=Σh[n]e^{-iωn} 的三个例子,判低通/高通,零点
 7. 采样与混叠:5 kHz 在 8 kHz 采样下变成 3 kHz;折叠公式;图像隔点抽样
 8. 二维:4×4 条纹只有两个亮点;fft2 = 先行后列;DC 的位置和大小
 9. Z 变换只当多项式看:[1,2,1] = (1+z⁻¹)²,单位圆上就是频率响应

⚠️ 仓库路线图(ROADMAP.md 第 11 周)要你自己写的 `01_dft_1d.py` 不在这里 ——
本脚本只用来核对答案,不是替你做那道作业。

用法:
    .venv/bin/python Ch04_Frequency_Domain/31_signals_roadmap.py
"""

from __future__ import annotations

import numpy as np

I = 1j
np.set_printoptions(precision=4, suppress=True, linewidth=120)
RNG = np.random.default_rng(0)


def head(title: str) -> None:
    print(f"\n{'=' * 8} {title} {'=' * 8}")


def cstr(z: complex, nd: int = 4) -> str:
    z = complex(z)
    if abs(z.imag) < 10 ** (-nd - 1):
        return f"{z.real:.{nd}f}"
    return f"{z.real:.{nd}f}{z.imag:+.{nd}f}i"


def row(a) -> str:
    """向量写成 [10, -2+2i, -2, -2-2i] 的样子;整数值去掉小数点,-0 当 0。"""
    out = []
    for v in np.asarray(a):
        v = complex(round(v.real, 9) + 0.0, round(v.imag, 9) + 0.0)
        if abs(v.imag) < 1e-9:
            out.append(f"{v.real:.4f}".rstrip("0").rstrip("."))
        else:
            out.append(f"{v.real:.0f}{v.imag:+.0f}i" if v.real == int(v.real) and v.imag == int(v.imag) else cstr(v, 3))
    return "[" + ", ".join(out) + "]"


def dft_matrix(n: int) -> np.ndarray:
    k = np.arange(n)
    return np.exp(-2j * np.pi * np.outer(k, k) / n)


# ---------------------------------------------------------------- 0 数学热身
def step0_math_warmup() -> None:
    head("0 数学热身")
    z = (2 + I) * (1 - 3 * I)
    print(f"(2+i)(1-3i) = {cstr(z, 1)},模 {abs(z):.4f} = √5·√10 = {np.sqrt(5) * np.sqrt(10):.4f}")
    e = np.exp(I * np.pi / 3)
    print(f"e^(iπ/3) = {cstr(e)};(e^(iπ/3)+e^(-iπ/3))/2 = {((e + np.conj(e)) / 2).real:.4f} = cos(π/3)")

    a, b = RNG.uniform(0, 6, 2)
    lhs = np.cos(a) * np.cos(b)
    rhs = 0.5 * (np.cos(a - b) + np.cos(a + b))
    print(f"积化和差 cosA·cosB = ½[cos(A-B)+cos(A+B)]:随机角两边差 {abs(lhs - rhs):.1e}")

    r, n = 0.5, 10
    s = sum(r ** k for k in range(n))
    print(f"等比求和 r=0.5, N=10:Σ = {s:.9f} = (1-r^N)/(1-r) = {(1 - r ** n) / (1 - r):.9f};"
          f"N→∞ 时 1/(1-r) = {1 / (1 - r):.1f}")
    N = 8
    sums = [sum(np.exp(2j * np.pi * k * m / N) for m in range(N)) for k in range(N)]
    print(f"Σ_m e^(i2πkm/8):k=0 → {abs(sums[0]):.1f};k=1..7 最大模 {max(abs(v) for v in sums[1:]):.1e}"
          "(转满整圈,抵消成 0)")

    x = np.array([3.0, 1.0])
    e1, e2 = np.array([1, 1]) / np.sqrt(2), np.array([1, -1]) / np.sqrt(2)
    c1, c2 = x @ e1, x @ e2
    print(f"换基:x=[3,1],基 [1,1]/√2 与 [1,-1]/√2 → 系数 {c1:.4f}(=2√2)、{c2:.4f}(=√2);"
          f"还原 {c1 * e1 + c2 * e2};能量 {x @ x:.0f} = {c1 ** 2:.0f}+{c2 ** 2:.0f}")

    xs = np.linspace(0, 2 * np.pi, 20000, endpoint=False)
    dx = xs[1] - xs[0]
    for k, l in [(3, 3), (3, 5)]:
        v = np.sum(np.cos(k * xs) * np.cos(l * xs)) * dx
        print(f"∫₀^2π cos({k}x)cos({l}x)dx = {v:.4f}" + ("(= π)" if k == l else "(正交)"))


# ---------------------------------------------------------------- 1 离散信号
def smallest_period(x_func, limit: int = 5000, tol: float = 1e-9) -> int | None:
    n = np.arange(200)
    base = x_func(n)
    for p in range(1, limit):
        if np.max(np.abs(x_func(n + p) - base)) < tol:
            return p
    return None


def step1_signals() -> None:
    head("1 离散信号")
    n = np.arange(-3, 6)
    delta = (n == 0).astype(int)
    u = (n >= 0).astype(int)
    u_shift = (n >= 1).astype(int)
    print(f"δ[n] = u[n] - u[n-1]:{np.array_equal(delta, u - u_shift)}")
    x = np.array([3, 1, 2])
    rebuilt = sum(x[k] * (np.arange(3) == k) for k in range(3))
    print(f"x=[3,1,2] = 3·δ[n] + 1·δ[n-1] + 2·δ[n-2]:{np.array_equal(rebuilt, x)}")
    print(f"cos(2π·3n/8) 的最小周期 = {smallest_period(lambda m: np.cos(2 * np.pi * 3 * m / 8))}")
    print(f"cos(0.9n) 的最小周期 = {smallest_period(lambda m: np.cos(0.9 * m))}(None = 5000 内找不到)")
    print(f"cos(n)    的最小周期 = {smallest_period(lambda m: np.cos(1.0 * m))}(None = 5000 内找不到)")
    m = np.arange(50)
    print(f"cos(0.3n) 与 cos((0.3+2π)n) 最大差 {np.max(np.abs(np.cos(0.3 * m) - np.cos((0.3 + 2 * np.pi) * m))):.1e}")


# ---------------------------------------------------------------- 2 系统
def conv_full(x, h):
    return np.convolve(x, h)


def delay(x, d):
    return np.concatenate([np.zeros(d), x])


def step2_systems() -> None:
    head("2 系统:线性与时不变")
    L = 12

    def diff(x):  # y[n] = x[n] - x[n-1]
        return x - np.concatenate([[0], x[:-1]])

    def square(x):
        return x ** 2

    def times_n(x):  # y[n] = n·x[n]
        return np.arange(len(x)) * x

    def plus_one(x):
        return x + 1

    x1, x2 = RNG.normal(size=L), RNG.normal(size=L)
    for name, f in [("y=x[n]-x[n-1]", diff), ("y=x[n]²", square), ("y=n·x[n]", times_n), ("y=x[n]+1", plus_one)]:
        lin_err = np.max(np.abs(f(2 * x1 + 3 * x2) - (2 * f(x1) + 3 * f(x2))))
        d = 3
        xs = delay(x1, d)[:L]
        ts_err = np.max(np.abs(f(xs)[d:] - delay(f(x1), d)[d:L]))
        print(f"  {name:15s} 叠加原理误差 {lin_err:.1e}   平移原理误差 {ts_err:.1e}")
    print(f"  平方系统的反例:f(1+1)={square(np.array([2]))[0]},f(1)+f(1)={2 * square(np.array([1]))[0]}")

    h = np.array([1, -1])
    imp = np.zeros(L)
    imp[0] = 1
    print(f"  差分系统的冲激响应 = {diff(imp)[:4]}")
    shifted = np.zeros(L)
    shifted[1] = 1
    print(f"  n·x[n] 系统:喂 δ[n] 得 {times_n(imp)[:4]},喂 δ[n-1] 得 {times_n(shifted)[:4]}"
          "(后者不是前者右移一格 → 时变)")

    def black_box(x):  # 观察者看不到内部:一个不知道的 LTI 系统
        y = np.zeros(len(x))
        for i in range(len(x)):
            y[i] = 0.5 * x[i] + 0.3 * (x[i - 1] if i >= 1 else 0) - 0.2 * (x[i - 3] if i >= 3 else 0)
        return y

    probe = np.zeros(8)
    probe[0] = 1
    h_est = black_box(probe)[:5]
    x = RNG.normal(size=20)
    pred = conv_full(x, h_est)[:20]
    print(f"  黑盒只喂一个冲激 → h = {h_est};用 x*h 预测随机输入,与真实输出最大差 "
          f"{np.max(np.abs(pred - black_box(x))):.1e}")


# ---------------------------------------------------------------- 3 卷积
def step3_convolution() -> None:
    head("3 卷积")
    x = np.array([1, 2, 3])
    print(f"[1,2,3]*[1,1]    = {np.convolve(x, [1, 1])}(长度 3+2-1 = 4)")
    print(f"[1,2,3]*[1,0,-1] = {np.convolve(x, [1, 0, -1])}(长度 {len(np.convolve(x, [1, 0, -1]))})")
    # 多项式乘法
    p = np.polynomial.polynomial.polymul([1, 2, 3], [1, 1])
    print(f"多项式 (1+2z+3z²)(1+z) 系数 = {p}")
    a, b, c = RNG.normal(size=4), RNG.normal(size=3), RNG.normal(size=5)
    print(f"交换律 {np.max(np.abs(np.convolve(a, b) - np.convolve(b, a))):.1e},"
          f"结合律 {np.max(np.abs(np.convolve(np.convolve(a, b), c) - np.convolve(a, np.convolve(b, c)))):.1e},"
          f"分配律 {np.max(np.abs(np.convolve(a, b + b * 2) - (np.convolve(a, b) + 2 * np.convolve(a, b)))):.1e}")
    print(f"[1,2,3] * δ = {np.convolve(x, [1])};[1,2,3] * δ[n-2] = {np.convolve(x, [0, 0, 1])}(整体右移 2)")
    step = np.array([0, 0, 4, 4, 4])
    print(f"[1,2,1]/4 抹平阶跃 [0,0,4,4,4] → {np.convolve(step, [.25, .5, .25])}(陡坡变成 1,3,4 的斜坡)")
    print(f"[1,1]*[1,1] = {np.convolve([1, 1], [1, 1])}(两个盒子卷一次 = 三角核 [1,2,1])")


# ---------------------------------------------------------------- 4 DFT
def step4_dft() -> None:
    head("4 DFT 手算")
    for x in ([1, 0, -1, 0], [1, 1, 1, 1], [1, 0, 0, 0], [1, 2, 3, 4], [1, -1, 1, -1]):
        X = dft_matrix(4) @ np.array(x, dtype=float)
        ok = np.max(np.abs(X - np.fft.fft(x)))
        print(f"  DFT{x} = {row(X)}   与 np.fft 最大差 {ok:.0e}")
    F = dft_matrix(4)
    print(f"  4 点 DFT 的 W = e^(-i2π/4) 的幂(W⁰..W³):{row([np.exp(-2j * np.pi * k / 4) for k in range(4)])}")
    for N in (4, 64):
        F = dft_matrix(N)
        print(f"  F·F^H = N·I:N={N} 最大偏差 {np.max(np.abs(F @ F.conj().T - N * np.eye(N))):.1e}")
    x = np.array([1.0, 2, 3, 4])
    X = np.fft.fft(x)
    print(f"  帕塞瓦尔:Σ|x|² = {np.sum(x ** 2):.0f};(1/N)Σ|X|² = {np.sum(abs(X) ** 2) / 4:.0f}")
    print(f"  共轭对称:X[1] = {cstr(X[1], 1)},X[3] = {cstr(X[3], 1)}(互为共轭)")
    fs, N, f = 8000, 64, 1000
    t = np.arange(N) / fs
    mag = abs(np.fft.fft(np.sin(2 * np.pi * f * t)))
    k = int(np.argmax(mag[:N // 2]))
    print(f"  fs=8000 Hz,N=64:谱线间隔 fs/N = {fs / N:.0f} Hz;1000 Hz 的正弦峰在 k={k}"
          f"(k·fs/N = {k * fs / N:.0f} Hz),幅值 {mag[k]:.0f} = N/2·A = {N / 2 * 1:.0f}")


# ---------------------------------------------------------------- 5 DFT 性质
def step5_properties() -> None:
    head("5 DFT 性质")
    x = np.array([1.0, 2, 3, 4])
    xs = np.roll(x, 1)
    X, Xs = np.fft.fft(x), np.fft.fft(xs)
    ph = np.exp(-2j * np.pi * np.arange(4) / 4)
    print(f"  右移 1 格 {xs}:|X| 不变 {row(abs(X))} → {row(abs(Xs))};X'/X 与 e^(-i2πk/4) 最大差 "
          f"{np.max(np.abs(Xs - X * ph)):.1e}")
    h = np.array([1.0, 1, 0, 0])
    circ = np.real(np.fft.ifft(np.fft.fft(x) * np.fft.fft(h)))
    lin = np.convolve(x, [1, 1])
    print(f"  循环卷积 [1,2,3,4]⊛[1,1,0,0] = {circ}(FFT 相乘);线性卷积 = {lin};"
          f"线性的最后一项 {lin[-1]} 绕回去加到了第 0 项:{lin[0]}+{lin[-1]} = {circ[0]:.0f}")
    M = len(x) + 2 - 1
    padded = np.real(np.fft.ifft(np.fft.fft(x, M) * np.fft.fft([1, 1], M)))
    print(f"  补零到 N+M-1 = {M} 再相乘 → {np.round(padded, 6)},与线性卷积最大差 {np.max(np.abs(padded - lin)):.1e}")

    N = 64
    n = np.arange(N)
    for cyc in (8, 8.5):
        s = np.cos(2 * np.pi * cyc * n / N)
        e = abs(np.fft.fft(s)) ** 2
        top4 = np.sort(e)[-4:].sum() / e.sum()
        print(f"  cos({cyc} 圈/64 点):能量最集中的 4 个点占 {100 * top4:.2f}%")
    s = np.cos(2 * np.pi * 8.5 * n / N)
    far = 20
    rect = abs(np.fft.fft(s))
    hann = abs(np.fft.fft(s * np.hanning(N)))
    print(f"  8.5 圈在远处 k={far} 的泄漏:矩形窗 {20 * np.log10(rect[far] / rect.max()):.1f} dB,"
          f"汉宁窗 {20 * np.log10(hann[far] / hann.max()):.1f} dB(相对各自峰值)")


# ---------------------------------------------------------------- 6 频率响应
def H(h, w, start=0):
    n = np.arange(len(h)) + start
    return np.sum(np.asarray(h, dtype=float) * np.exp(-1j * w * n))


def step6_frequency_response() -> None:
    head("6 频率响应")
    tri = np.array([1, 2, 1]) / 4
    for w, name in [(0, "0"), (np.pi / 2, "π/2"), (np.pi, "π")]:
        print(f"  [1,2,1]/4 在 ω={name:3s}:|H| = {abs(H(tri, w)):.4f};(1+cosω)/2 = {(1 + np.cos(w)) / 2:.4f}")
    for w, name in [(0, "0"), (np.pi / 2, "π/2"), (np.pi, "π")]:
        print(f"  [1,-1]  在 ω={name:3s}:|H| = {abs(H([1, -1], w)):.4f};2|sin(ω/2)| = {2 * abs(np.sin(w / 2)):.4f}")
    w0 = 2 * np.pi / 5
    print(f"  5 点盒式 [1,1,1,1,1]/5 在 ω=2π/5:|H| = {abs(H(np.ones(5) / 5, w0)):.1e}(整好被抹掉)")
    print(f"  判低通/高通:H(0)=核之和,H(π)=交错和 —— [1,2,1]/4:{tri.sum():.0f} 和 "
          f"{(tri * np.array([1, -1, 1])).sum():.0f};[1,-1]:{1 - 1} 和 {1 + 1}")
    n = np.arange(400)
    out = np.convolve(np.cos(0.9 * n), tri, mode="same")[5:-5]
    xin = np.cos(0.9 * n)[5:-5]
    gain = np.max(np.abs(out)) / np.max(np.abs(xin))
    print(f"  cos(0.9n) 过 [1,2,1]/4:输出仍是 cos(0.9n),振幅 ×{gain:.4f};(1+cos0.9)/2 = {(1 + np.cos(0.9)) / 2:.4f};"
          f"相关系数 {np.corrcoef(out, xin)[0, 1]:.12f}")


# ---------------------------------------------------------------- 7 采样与混叠
def alias(f: float, fs: float) -> float:
    return abs(f - round(f / fs) * fs)


def step7_sampling() -> None:
    head("7 采样与混叠")
    fs = 8000
    n = np.arange(64)
    a = np.cos(2 * np.pi * 5000 * n / fs)
    b = np.cos(2 * np.pi * 3000 * n / fs)
    print(f"  5 kHz 与 3 kHz 余弦在 fs=8 kHz 下采出来:最大差 {np.max(np.abs(a - b)):.1e}")
    print("  折叠后的表观频率(fs=8000):" + ",".join(f"{f}→{alias(f, fs):.0f}" for f in (1000, 3000, 5000, 7000, 8000, 9000)))
    N = 400
    n = np.arange(N)
    stripe = np.cos(2 * np.pi * 0.45 * n)
    sub = stripe[::2]
    k_full = int(np.argmax(abs(np.fft.fft(stripe))[:N // 2]))
    k_sub = int(np.argmax(abs(np.fft.fft(sub))[:len(sub) // 2]))
    print(f"  条纹 0.45 周期/像素(周期 {1 / 0.45:.2f} 像素):隔点抽样前峰在 k={k_full}(= {k_full / N:.2f} 周期/像素);"
          f"抽样后峰在 k={k_sub}(= {k_sub / len(sub):.2f} 周期/像素,周期 {len(sub) / k_sub:.0f} 个像素)")


# ---------------------------------------------------------------- 8 二维
def step8_2d() -> None:
    head("8 二维")
    img = np.tile(np.array([1.0, 0, -1, 0]), (4, 1))
    F = np.fft.fft2(img)
    nz = [(int(r), int(c), cstr(F[r, c], 0)) for r, c in zip(*np.nonzero(abs(F) > 1e-9))]
    print(f"  4×4 竖条纹(每行 [1,0,-1,0])的 fft2 非零点:{nz};M·N/2 = {4 * 4 // 2}")
    rnd = RNG.normal(size=(5, 6))
    rc = np.fft.fft(np.fft.fft(rnd, axis=1), axis=0)
    print(f"  fft2 = 先对每行再对每列:最大差 {np.max(np.abs(rc - np.fft.fft2(rnd))):.1e}")
    flat = np.full((4, 4), 5.0)
    Ff = np.fft.fft2(flat)
    sh = np.fft.fftshift(Ff)
    print(f"  纯色 4×4(值 5):DC = F[0,0] = {Ff[0, 0].real:.0f} = 像素和;fftshift 后跑到 "
          f"{tuple(int(v) for v in np.argwhere(abs(sh) > 1)[0])}")
    k1 = np.array([1, 2, 1]) / 4
    K = np.outer(k1, k1)
    print(f"  3×3 高斯近似核的秩 = {np.linalg.matrix_rank(K)}(秩 1 → 可拆成横一遍竖一遍)")


# ---------------------------------------------------------------- 9 Z 变换当多项式
def step9_z_as_polynomial() -> None:
    head("9 Z 变换只当多项式")
    c = np.polynomial.polynomial.polymul([1, 1], [1, 1])
    print(f"  (1+z⁻¹)² 的系数 = {c} = [1,1]*[1,1],即 [1,2,1]")
    for w in (0, np.pi / 2, np.pi):
        z = np.exp(1j * w)
        print(f"  ω={w:.4f}:H(z=e^(iω)) = {abs(((1 + 1 / z) ** 2) / 4):.4f} = |H(ω)| = {abs(H([1, 2, 1], w)) / 4:.4f}"
              f";|1+e^(-iω)|²/4 = {abs(1 + np.exp(-1j * w)) ** 2 / 4:.4f}")
    print("  z=-1 是 (1+z⁻¹)² 的双重零点 → ω=π 处被完全抹掉")


def main() -> None:
    step0_math_warmup()
    step1_signals()
    step2_systems()
    step3_convolution()
    step4_dft()
    step5_properties()
    step6_frequency_response()
    step7_sampling()
    step8_2d()
    step9_z_as_polynomial()


if __name__ == "__main__":
    main()
