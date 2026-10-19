"""第 11 周前置:36《信号与系统快速路线》里新增数字的复核 ——
配合 Documents/数学基础/信号与系统快速路线.md。

快速路线以一份外部对话给的 4 阶段方案为底,补上它没覆盖、或说得不准的地方。
文档里凡是 31_signals_roadmap.py 没有算过的数字,都在这里:

 1. 频谱的「中心」:np.fft.fft2 直流在 [0,0](角落),fftshift 之后才到正中;中心一小块占多少能量
 2. 「线性」与「LTI」:Sobel 的 Gx 是线性时不变的,但梯度幅值 sqrt(Gx²+Gy²) 不是线性的;
    3×3 高斯核在 (0,0) 增益 1、在 (π,π) 增益 0
 3. 卷积定理的二维版:补零后频域相乘 = 线性卷积;不补零 = 循环卷积,只在边缘一圈出错
 4. 位置信息在相位里:平移只改相位、幅度不变;拿 A 的幅度配 B 的相位,长得像 B
 5. 缩小前先低通:0.45 周期/像素的细条纹隔点抽样,先过 [1,2,1]/4 再抽,假纹幅度只剩多少

⚠️ 这里的图像用仓库 Assets/test-images 里的 camera.png 和 coins.png;
换一张图,第 1、4 块里的百分比和相关系数会变,结论(谁在中心、像谁)不变。

用法:
    .venv/bin/python Ch04_Frequency_Domain/36_fast_route_checks.py
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

np.set_printoptions(precision=4, suppress=True, linewidth=120)
RNG = np.random.default_rng(0)
REPO = Path(__file__).resolve().parents[2]


def head(title: str) -> None:
    print(f"\n{'=' * 8} {title} {'=' * 8}")


def load(name: str, size: int = 256) -> np.ndarray:
    img = cv2.imread(str(REPO / "Assets" / "test-images" / name), cv2.IMREAD_GRAYSCALE)
    assert img is not None, name
    return cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA).astype(float)


def conv2_full(a: np.ndarray, k: np.ndarray) -> np.ndarray:
    """直接按定义的二维线性卷积,输出 (H+h-1, W+w-1)。小图用,不求快。"""
    H, W = a.shape
    h, w = k.shape
    out = np.zeros((H + h - 1, W + w - 1))
    for i in range(h):
        for j in range(w):
            out[i:i + H, j:j + W] += k[i, j] * a
    return out


def conv2_same(a: np.ndarray, k: np.ndarray) -> np.ndarray:
    """full 卷积取中间与输入同大小的一块(核为奇数边长)。"""
    full = conv2_full(a, k)
    h, w = k.shape
    return full[h // 2:h // 2 + a.shape[0], w // 2:w // 2 + a.shape[1]]


# ---------------------------------------------------------------- 1
def block1() -> None:
    head("1. 频谱的「中心」:fft2 的直流在角落,fftshift 才把它搬到中间")
    cam = load("camera.png")
    F = np.fft.fft2(cam)
    mag = np.abs(F)
    raw = tuple(int(i) for i in np.unravel_index(mag.argmax(), mag.shape))
    sh = np.fft.fftshift(F)
    shifted = tuple(int(i) for i in np.unravel_index(np.abs(sh).argmax(), sh.shape))
    print(f"camera.png 缩到 256×256;|F| 最大点:fft2 之后在 {raw},fftshift 之后在 {shifted}(正中是 (128, 128))")
    print(f"F[0,0] = 全部像素之和:{F[0, 0].real:.1f} vs 像素和 {cam.sum():.1f}")
    e = np.abs(sh) ** 2
    c = 128
    for r in (2, 8, 16):
        blk = e[c - r:c + r + 1, c - r:c + r + 1].sum() / e.sum()
        area = (2 * r + 1) ** 2 / 256 ** 2
        print(f"  中心 {2 * r + 1}×{2 * r + 1}({area * 100:.2f}% 的面积)占能量 {blk * 100:.2f}%")
    e0 = e.copy()
    e0[c, c] = 0
    blk0 = e0[c - 8:c + 9, c - 8:c + 9].sum() / e0.sum()
    print(f"  去掉直流一点后,中心 17×17 仍占 {blk0 * 100:.2f}%")


# ---------------------------------------------------------------- 2
def block2() -> None:
    head("2. Sobel 的 Gx 是 LTI,梯度幅值不是线性;高斯核的 H(0,0)=1、H(π,π)=0")
    gx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], float)
    gy = gx.T
    a = RNG.standard_normal((12, 12))
    b = RNG.standard_normal((12, 12))

    def fx(x):
        return conv2_same(x, gx)

    def mag(x):
        return np.sqrt(conv2_same(x, gx) ** 2 + conv2_same(x, gy) ** 2)

    lin = np.abs(fx(2 * a + 3 * b) - 2 * fx(a) - 3 * fx(b)).max()
    shift_a = np.roll(a, (2, 3), axis=(0, 1))
    inner = (slice(4, 10), slice(5, 11))  # 避开边界与 roll 的卷绕
    shift_err = np.abs(fx(shift_a)[inner] - np.roll(fx(a), (2, 3), axis=(0, 1))[inner]).max()
    print(f"Gx:线性残差 {lin:.1e};平移不变残差(内部){shift_err:.1e}  → 线性时不变")
    add_err = np.abs(mag(a + b) - mag(a) - mag(b)).max()
    neg_err = np.abs(mag(-a) + mag(a)).max()
    print(f"梯度幅值:|M(a+b) − M(a) − M(b)| 最大 {add_err:.4f};|M(−a) + M(a)| 最大 {neg_err:.4f}(线性要求后者为 0)  → 不是线性")
    # 高斯 3×3 = [1,2,1]/4 的外积
    g1 = np.array([1, 2, 1]) / 4
    g = np.outer(g1, g1)
    w = np.arange(3) - 1
    sign_pi = (-1.0) ** w
    H00 = g.sum()
    Hpp = (g * np.outer(sign_pi, sign_pi)).sum()
    Hp0 = (g * sign_pi[:, None]).sum()
    print(f"3×3 高斯核:H(0,0) = 核之和 = {H00:.4f};H(π,π) = 交错和 = {Hpp:.4f};H(π,0) = {Hp0:.4f}")


# ---------------------------------------------------------------- 3
def block3() -> None:
    head("3. 卷积定理的二维版:补零才等于线性卷积,不补零只在边缘一圈出错")
    img = load("camera.png", 64)[:16, :16]
    k = np.ones((3, 3)) / 9
    lin_same = conv2_same(img, k)
    full = conv2_full(img, k)  # 18×18
    P = img.shape[0] + k.shape[0] - 1
    pad = np.fft.ifft2(np.fft.fft2(img, s=(P, P)) * np.fft.fft2(k, s=(P, P))).real
    print(f"补零到 {P}×{P} 再相乘,与 full 线性卷积最大差 {np.abs(pad - full).max():.1e}")
    nopad = np.fft.ifft2(np.fft.fft2(img) * np.fft.fft2(k, s=img.shape)).real
    # 无补零的循环卷积相当于把核中心放在 (0,0) 之后的结果,需要把核搬到中心才能与 same 对齐
    kc = np.zeros(img.shape)
    kc[:3, :3] = k
    kc = np.roll(kc, (-1, -1), axis=(0, 1))
    circ = np.fft.ifft2(np.fft.fft2(img) * np.fft.fft2(kc)).real
    d = np.abs(circ - lin_same)
    inner = d[1:-1, 1:-1].max()
    border = np.concatenate([d[0], d[-1], d[:, 0], d[:, -1]]).max()
    print(f"不补零(循环卷积)与 same 线性卷积:内部最大差 {inner:.1e};最外一圈最大差 {border:.2f}(灰度 0~255)")
    print(f"  16×16 里被污染的只有最外一圈:{(16 * 16 - 14 * 14)} 个像素,占 {(16 * 16 - 14 * 14) / 256 * 100:.1f}%")
    del nopad


# ---------------------------------------------------------------- 4
def block4() -> None:
    head("4. 位置信息在相位里:平移只改相位;A 的幅度 + B 的相位,长得像 B")
    cam = load("camera.png")
    coin = load("coins.png")
    shift = np.roll(cam, (20, 35), axis=(0, 1))
    Fa, Fs = np.fft.fft2(cam), np.fft.fft2(shift)
    print(f"camera 平移 (20,35) 后:|F| 最大差 {np.abs(np.abs(Fa) - np.abs(Fs)).max():.1e}(相对最大幅度 {np.abs(Fa).max():.2e})")
    dphi = np.angle(Fs / np.where(np.abs(Fa) > 1e-9, Fa, 1))
    expect = np.angle(np.exp(-2j * np.pi * (20 * np.fft.fftfreq(256)[:, None] + 35 * np.fft.fftfreq(256)[None, :])))
    mask = np.abs(Fa) > 1e3
    print(f"  相位变化 = −2π(20·u + 35·v):在幅度较大的点上最大偏差 {np.abs(np.angle(np.exp(1j * (dphi - expect))))[mask].max():.1e} 弧度")
    Fb = np.fft.fft2(coin)
    mix1 = np.fft.ifft2(np.abs(Fa) * np.exp(1j * np.angle(Fb))).real  # A 幅度 + B 相位
    mix2 = np.fft.ifft2(np.abs(Fb) * np.exp(1j * np.angle(Fa))).real  # B 幅度 + A 相位

    def corr(x, y):
        return float(np.corrcoef(x.ravel(), y.ravel())[0, 1])

    print(f"camera 幅度 + coins 相位:与 coins 相关 {corr(mix1, coin):.3f},与 camera 相关 {corr(mix1, cam):.3f}")
    print(f"coins 幅度 + camera 相位:与 camera 相关 {corr(mix2, cam):.3f},与 coins 相关 {corr(mix2, coin):.3f}")


# ---------------------------------------------------------------- 5
def block5() -> None:
    head("5. 缩小前先低通:0.45 周期/像素的条纹隔点抽样")
    N = 400
    n = np.arange(N)
    x = np.cos(2 * np.pi * 0.45 * n)
    g = np.array([1, 2, 1]) / 4
    xb = np.real(np.fft.ifft(np.fft.fft(x) * np.fft.fft(g, N)))  # 循环卷积,长度不变
    gain = (1 + np.cos(2 * np.pi * 0.45)) / 2
    raw = x[::2]
    blur = xb[::2]

    def amp(s):
        X = np.fft.fft(s)
        k = int(np.argmax(np.abs(X[:len(s) // 2])))
        return k, 2 * np.abs(X[k]) / len(s)

    k0, a0 = amp(raw)
    k1, a1 = amp(blur)
    print(f"不先模糊,隔点抽样:峰在 k={k0}({k0 / len(raw):.2f} 周期/像素),假纹幅度 {a0:.4f}")
    print(f"先过 [1,2,1]/4 再抽样:峰仍在 k={k1},幅度 {a1:.4f}(理论 (1+cos2π·0.45)/2 = {gain:.4f})")
    print(f"  假纹幅度缩小为原来的 1/{a0 / a1:.1f}")


if __name__ == "__main__":
    block1()
    block2()
    block3()
    block4()
    block5()
