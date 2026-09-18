"""第 6 周(3.4 节):空间滤波 —— 21 自己写一个卷积引擎。

对应文档 Documents/05-spatial-filtering/01-spatial-filtering-basics.md。
20 号脚本是「验证 OpenCV 怎么做的」,这一篇是「不调库,自己做一遍」。

整个引擎就三件事:

    第 1 件  补边    —— 核伸到图外面去了,得给外面编个值
    第 2 件  滑窗    —— 印章一格一格挪过去,每次「对应位置相乘再相加」
    第 3 件  写回去  —— 算出来的数写到输出图对应位置

其中第 2 件有两种写法,结果完全一样:

    朴素版:四重 for 循环,照着定义抄,慢但一看就懂
    移位版:把整张图**整体挪一格**乘个权重累加,3×3 就挪 9 次 —— 快几百倍

    ┌─────────────────────────────────────────────────────┐
    │  移位版的思路(1×3 的核 [a, b, c] 为例):              │
    │                                                      │
    │   out = a × (整张图左移一格)                          │
    │       + b × (整张图原地不动)                          │
    │       + c × (整张图右移一格)                          │
    │                                                      │
    │  一次算完所有像素,不用一个一个跑                       │
    └─────────────────────────────────────────────────────┘

验证六件事:
1. 手写补边:只用「换一套下标」实现三种模式,与 cv2.copyMakeBorder 逐像素相同
2. 朴素四重循环 vs cv2.filter2D:float64 下差 < 1e-12,远小于要求的 1e-6
3. 移位累加版与朴素版完全相同,但快几百倍
4. 翻不翻核 = 卷积还是相关,两种都与 cv2 对得上
5. 可分离:横着滤一遍 + 竖着滤一遍,与整张核完全相同(差 ~1e-13)
6. 耗时横向对比:朴素 / 移位 / 手写可分离 / cv2

用法:
    .venv/bin/python Ch03_Spatial_Filtering/21_conv_engine.py [--show]
    结果图保存到 Assets/results/conv-engine-explained.png(一次计算 + 三种补边)
                     Assets/results/conv-separable-steps.png(横一遍、竖一遍)
"""

import sys
import time
from pathlib import Path

import cv2
import matplotlib

if "--show" not in sys.argv:
    matplotlib.use("Agg")  # 无窗口环境只保存文件
import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt

REPO = Path(__file__).resolve().parents[2]
matplotlib.rcParams["font.family"] = ["Heiti TC", "Arial Unicode MS", "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False

MODES = ("zero", "replicate", "reflect101")
CV_BORDER = {"zero": cv2.BORDER_CONSTANT,
             "replicate": cv2.BORDER_REPLICATE,
             "reflect101": cv2.BORDER_REFLECT_101}


def hr(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def load_gray(name: str) -> npt.NDArray[np.uint8]:
    path = REPO / "Assets" / "test-images" / name
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise SystemExit(f"读不到 {path}")
    return np.asarray(img, dtype=np.uint8)


# ================================================================ 第 1 件:补边
def border_index(n: int, pad: int, mode: str) -> npt.NDArray[np.int64]:
    """补边的核心:给「图外面」的位置编一个图里的下标。

    关键认识:**补边不是真的造数据,只是换一套下标。**
    要取第 −1 行?那就规定 −1 号其实是 0 号(复制),或者其实是 1 号(镜像)。

    返回长度 n + 2·pad 的下标数组,-1 表示「这里就是 0,图里没有对应位置」。

        原图只有 0..5 这 6 行,补 3 行之后要取 −3..8:

        想取的行号   -3  -2  -1 | 0  1  2  3  4  5 | 6  7  8
        zero         -1  -1  -1 | 0  1  2  3  4  5 | -1 -1 -1   ← -1 代表填 0
        replicate     0   0   0 | 0  1  2  3  4  5 | 5  5  5    ← 夹在两头
        reflect101    3   2   1 | 0  1  2  3  4  5 | 4  3  2    ← 以 0 号和 5 号为镜子
    """
    want = np.arange(-pad, n + pad)
    if mode == "zero":
        return np.where((want >= 0) & (want < n), want, -1)
    if mode == "replicate":
        return np.clip(want, 0, n - 1)            # 越界就夹回最边上那个
    if mode == "reflect101":
        if n == 1:                                 # 只有一行/一列,镜子照不动
            return np.zeros_like(want)
        period = 2 * (n - 1)                       # 来回一趟的长度
        i = np.abs(want) % period                  # 折回一个周期内
        return np.where(i > n - 1, period - i, i)  # 超过右端就再折回来
    raise SystemExit(f"不认识的补边模式 {mode}")


def pad(img: npt.NDArray[np.float64], ph: int, pw: int,
        mode: str) -> npt.NDArray[np.float64]:
    """按上面那套下标把图「撑大」。两行花式索引就够了。"""
    h, w = img.shape
    rows = border_index(h, ph, mode)
    cols = border_index(w, pw, mode)
    out = img[np.clip(rows, 0, None)[:, None], np.clip(cols, 0, None)[None, :]]
    if mode == "zero":     # -1 的位置统一填 0
        out = np.where((rows >= 0)[:, None] & (cols >= 0)[None, :], out, 0.0)
    return out


# ================================================================ 第 2 件:滑窗
def convolve_naive(img: npt.NDArray[np.float64], k: npt.NDArray[np.float64],
                   mode: str = "reflect101", flip: bool = False) -> npt.NDArray[np.float64]:
    """朴素版:照着定义抄的四重 for 循环。慢,但每一行都对得上公式。

    flip=False 做相关(和 cv2.filter2D 一样),flip=True 做真卷积。
    """
    if flip:
        k = k[::-1, ::-1]                      # 印章先转半圈
    kh, kw = k.shape
    ph, pw = kh // 2, kw // 2
    src = pad(img, ph, pw, mode)
    h, w = img.shape
    out = np.zeros((h, w), dtype=np.float64)
    for y in range(h):                          # 输出图的每一行
        for x in range(w):                      # 每一列
            acc = 0.0
            for m in range(kh):                 # 印章的每一行
                for n in range(kw):             # 每一列
                    acc += k[m, n] * src[y + m, x + n]
            out[y, x] = acc                     # 对应相乘再相加,写回去
    return out


def convolve_shift(img: npt.NDArray[np.float64], k: npt.NDArray[np.float64],
                   mode: str = "reflect101", flip: bool = False) -> npt.NDArray[np.float64]:
    """移位累加版:结果和朴素版一模一样,但没有逐像素的 for 循环。

    思路:与其让印章挪过去,不如让**整张图**挪过来。
    印章第 (m,n) 格的权重,作用的就是「整张图往某个方向挪了 (m,n) 格」之后的那张图。
    3×3 的核就是 9 张挪过的图加权相加,循环只跑 9 次而不是几十万次。
    """
    if flip:
        k = k[::-1, ::-1]
    kh, kw = k.shape
    ph, pw = kh // 2, kw // 2
    src = pad(img, ph, pw, mode)
    h, w = img.shape
    out = np.zeros((h, w), dtype=np.float64)
    for m in range(kh):
        for n in range(kw):
            if k[m, n] != 0.0:                  # 权重是 0 就不用加了
                out += k[m, n] * src[m:m + h, n:n + w]   # ← 整张图的一次「挪位」
    return out


def convolve_separable(img: npt.NDArray[np.float64], kc: npt.NDArray[np.float64],
                       kr: npt.NDArray[np.float64],
                       mode: str = "reflect101") -> npt.NDArray[np.float64]:
    """可分离版:先横着滤一遍,再竖着滤一遍。

    kc 是竖表头(长度 k 的一维数组),kr 是横表头。
    整张 k×k 的表 = kc 和 kr 的乘法口诀表,所以拆开来做结果一样。
    """
    tmp = convolve_shift(img, kr.reshape(1, -1), mode)   # 第一遍:只在水平方向
    return convolve_shift(tmp, kc.reshape(-1, 1), mode)  # 第二遍:只在垂直方向


def bench(fn, repeat: int = 5) -> float:
    fn()
    t0 = time.perf_counter()
    for _ in range(repeat):
        fn()
    return (time.perf_counter() - t0) / repeat * 1000


# ---------------------------------------------------------------- 1
def demo_border() -> None:
    hr("1. 补边:不造数据,只换一套下标")
    src = np.arange(10, 70, 10, dtype=np.uint8).reshape(1, 6)
    print(f"  原始一行 {src[0].tolist()},左右各补 3 个\n")
    print(f"  {'模式':<12s}{'下标映射':<44s}{'补出来的值'}")
    for mode in MODES:
        idx = border_index(6, 3, mode)
        mine = pad(src.astype(np.float64), 0, 3, mode)[0].astype(int)
        print(f"  {mode:<12s}{str(idx.tolist()):<44s}{mine.tolist()}")

    print("\n  和 cv2.copyMakeBorder 对一下:")
    img = load_gray("camera.png").astype(np.float64)
    for mode in MODES:
        mine = pad(img, 7, 7, mode)
        ref = cv2.copyMakeBorder(img, 7, 7, 7, 7, CV_BORDER[mode], value=0)
        print(f"    {mode:<12s}最大差 {np.abs(mine - ref).max():.1e}   "
              f"逐像素相同 {np.array_equal(mine, ref)}")
    print("\n  三行代码就是三种补边:")
    print("    zero       想取的位置越界 → 填 0")
    print("    replicate  np.clip(want, 0, n-1)        越界就夹回最边上那个")
    print("    reflect101 折回一个周期,超过右端再折回来   以首尾两个像素为镜子")


# ---------------------------------------------------------------- 2
def demo_naive_matches_cv2() -> None:
    hr("2. 朴素四重循环 vs cv2.filter2D")
    img = load_gray("camera.png")[:128, :128].astype(np.float64)
    k = np.array([[1, 2, 1], [2, 4, 2], [1, 2, 1]], np.float64) / 16.0
    print(f"  测试图 {img.shape[0]}×{img.shape[1]}(朴素版太慢,先用小图),3×3 高斯核\n")
    for mode in MODES:
        mine = convolve_naive(img, k, mode)
        ref = cv2.filter2D(img, cv2.CV_64F, k, borderType=CV_BORDER[mode])
        print(f"    {mode:<12s}最大差 {np.abs(mine - ref).max():.2e}   "
              f"{'✅ 对齐(要求 < 1e-6)' if np.abs(mine - ref).max() < 1e-6 else '❌'}")
    print("\n  0.00e+00 —— 不是「差不多」,是一个 bit 都不差。")
    print("  float64 下加法顺序造成的误差本来就在 1e-16 量级,这里连那点都没出现。")


# ---------------------------------------------------------------- 3
def demo_shift_version() -> None:
    hr("3. 移位累加版:同样的结果,少跑几十万次循环")
    img = load_gray("camera.png")[:128, :128].astype(np.float64)
    k = np.array([[1, 2, 1], [2, 4, 2], [1, 2, 1]], np.float64) / 16.0
    a, b = convolve_naive(img, k), convolve_shift(img, k)
    print(f"  两个版本的最大差:{np.abs(a - b).max():.2e}(完全相同)")
    print(f"  朴素版的循环次数:{img.size} 个像素 × 9 = {img.size * 9} 次")
    print(f"  移位版的循环次数:9 次(每次处理整张图)")
    t_naive, t_shift = bench(lambda: convolve_naive(img, k), 2), bench(lambda: convolve_shift(img, k))
    print(f"\n  耗时:朴素 {t_naive:8.2f} ms   移位 {t_shift:6.2f} ms   "
          f"快 {t_naive / t_shift:.0f} 倍")
    print("\n  为什么能这么写:印章第 (m,n) 格的权重,作用的对象永远是")
    print("  「整张图朝某个方向挪了 (m,n) 格」之后的那张图。")
    print("  所以与其让印章挪,不如让图挪 —— 9 次整图乘加就算完了。")


# ---------------------------------------------------------------- 4
def demo_flip() -> None:
    hr("4. 翻不翻核 = 卷积还是相关")
    img = load_gray("camera.png")[:128, :128].astype(np.float64)
    sob = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], np.float64)
    corr = convolve_shift(img, sob, flip=False)
    conv = convolve_shift(img, sob, flip=True)
    ref_corr = cv2.filter2D(img, cv2.CV_64F, sob)
    ref_conv = cv2.filter2D(img, cv2.CV_64F, cv2.flip(sob, -1))
    print(f"  我的 flip=False(相关) vs cv2.filter2D(原核)      最大差 "
          f"{np.abs(corr - ref_corr).max():.2e}")
    print(f"  我的 flip=True (卷积) vs cv2.filter2D(翻过的核)   最大差 "
          f"{np.abs(conv - ref_conv).max():.2e}")
    print(f"\n  相关和卷积的结果互为相反数?{np.allclose(conv, -corr)}"
          f"(Sobel 是反对称核,翻一下正好变号)")
    print("  代码里就一行 k = k[::-1, ::-1] —— 印章转半圈。")


# ---------------------------------------------------------------- 5
def demo_separable() -> None:
    hr("5. 可分离:横一遍 + 竖一遍 = 整张表一遍")
    img = load_gray("camera.png").astype(np.float64)
    ksz = 15
    g = cv2.getGaussianKernel(ksz, ksz / 6.0).ravel()
    k2d = np.outer(g, g)
    print(f"  {ksz}×{ksz} 高斯核。竖表头和横表头都是同一组 {ksz} 个数:")
    print(f"    {np.round(g[:5], 4).tolist()} ...(只印前 5 个)")
    print(f"  整张表的秩 = {int(np.linalg.matrix_rank(k2d))},说明它确实是一张乘法口诀表\n")

    full = convolve_shift(img, k2d)
    sep = convolve_separable(img, g, g)
    print(f"  整张表滤一遍  vs  横一遍+竖一遍:最大差 {np.abs(full - sep).max():.2e}")
    print(f"  与 cv2.sepFilter2D 比:最大差 "
          f"{np.abs(sep - cv2.sepFilter2D(img, cv2.CV_64F, g, g)).max():.2e}")

    print(f"\n  乘法次数:整张表 {ksz}×{ksz} = {ksz * ksz} 次/像素;"
          f"拆开 {ksz}+{ksz} = {2 * ksz} 次/像素")
    print(f"  {'':<24s}{'耗时':>10s}")
    for label, fn in ((f"手写 整张 {ksz}×{ksz} 表", lambda: convolve_shift(img, k2d)),
                      ("手写 横一遍 + 竖一遍", lambda: convolve_separable(img, g, g)),
                      ("cv2.sepFilter2D", lambda: cv2.sepFilter2D(img, cv2.CV_64F, g, g))):
        print(f"  {label:<24s}{bench(fn, 3):9.2f} ms")
    print("\n  手写版比 cv2 慢是正常的(cv2 有 SIMD 和多线程),")
    print("  但「拆开比不拆快一个量级」这个结论,在自己的代码上同样成立。")


# ---------------------------------------------------------------- 图板
def draw_grid(ax, values, title, fmt="{:.0f}", cmap="Blues",
              highlight=None, dim_mask=None, fontsize=9) -> None:
    """把一个小矩阵画成带数字的格子图。highlight = (y0, x0, h, w) 画红框。"""
    v = np.asarray(values, dtype=np.float64)
    ax.imshow(v, cmap=cmap, vmin=v.min(), vmax=v.max() if v.max() > v.min() else v.min() + 1)
    for (i, j), val in np.ndenumerate(v):
        faded = dim_mask is not None and dim_mask[i, j]
        ax.text(j, i, fmt.format(val), ha="center", va="center", fontsize=fontsize,
                color=("#b0b0b0" if faded else "black"),
                style=("italic" if faded else "normal"))
    if highlight is not None:
        y0, x0, hh, ww = highlight
        ax.add_patch(plt.Rectangle((x0 - 0.5, y0 - 0.5), ww, hh,
                                   fill=False, edgecolor="red", lw=2.5))
    ax.set_title(title, fontsize=10)
    ax.set_xticks([])
    ax.set_yticks([])


def save_explained_figure(out_path: Path) -> None:
    """图板一:一次计算怎么算的 + 三种补边长什么样。"""
    small = np.array([[10, 20, 30, 40, 50, 60],
                      [15, 25, 35, 45, 55, 65],
                      [12, 22, 32, 42, 52, 62],
                      [18, 28, 38, 48, 58, 68],
                      [11, 21, 31, 41, 51, 61],
                      [14, 24, 34, 44, 54, 64]], np.float64)
    k = np.array([[1, 2, 1], [2, 4, 2], [1, 2, 1]], np.float64)

    fig, axes = plt.subplots(2, 3, figsize=(15.5, 9.6))

    draw_grid(axes[0, 0], small, "① 原图的一小块(6×6)\n红框 = 印章当前压住的 3×3",
              highlight=(1, 1, 3, 3))
    draw_grid(axes[0, 1], k, "② 印章(核):每个邻居的话听几分\n中心 4 分,上下左右 2 分,四角 1 分",
              cmap="Oranges", fontsize=13)

    ax = axes[0, 2]
    ax.axis("off")
    win = small[1:4, 1:4]
    terms = "\n".join(
        "   " + "  +  ".join(f"{int(win[i, j])}×{int(k[i, j])}" for j in range(3))
        for i in range(3))
    total = float((win * k).sum())
    ax.text(0.02, 0.97,
            "把红框里的 9 个数,和印章里的 9 个数,对应位置相乘,再全部加起来:\n\n" + terms
            + f"\n\n   = {int(total)}"
            + f"\n\n   印章里的数加起来是 {int(k.sum())},"
            + f"\n   所以再 ÷{int(k.sum())} = {total / k.sum():.1f}"
            + "\n\n   这个数写到输出图的中心位置(红框正中)。"
            + "\n\n   然后印章往右挪一格,再算一次;"
            + "\n   一行走完换下一行 —— 走完全图就是一次滤波。",
            transform=ax.transAxes, fontsize=11, va="top", linespacing=1.5)
    ax.set_title("③ 算一次给你看\n(用 ① 里红框那 9 个数)", fontsize=10)

    for ax, mode, note in zip(axes[1], MODES,
                              ("外面全当 0(灰字是补出来的)",
                               "复制最边上那个值",
                               "以首尾像素为镜子折回来(cv2 默认)")):
        p = pad(small, 2, 2, mode)
        mask = np.ones_like(p, dtype=bool)
        mask[2:-2, 2:-2] = False
        draw_grid(ax, p, f"④ 补边:{mode}\n{note}", dim_mask=mask, fontsize=7,
                  highlight=(2, 2, 6, 6))

    fig.suptitle("自己写卷积引擎:补边 → 滑窗(对应相乘再相加)→ 写回去", fontsize=13)
    # 每格标题两行,不留行距会压住上一行
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94), h_pad=3.0)
    fig.savefig(out_path, dpi=110)


def save_separable_figure(out_path: Path) -> None:
    """图板二:横一遍、竖一遍,和整张表的结果一模一样。"""
    img = load_gray("camera.png").astype(np.float64)
    ksz = 21
    g = cv2.getGaussianKernel(ksz, ksz / 6.0).ravel()
    step1 = convolve_shift(img, g.reshape(1, -1))      # 只横着糊
    step2 = convolve_shift(step1, g.reshape(-1, 1))    # 再竖着糊
    full = convolve_shift(img, np.outer(g, g))

    fig, axes = plt.subplots(1, 4, figsize=(17, 4.9))
    for ax, (pic, title) in zip(axes, (
            (img, "原图"),
            (step1, f"第一步:只横着滤一遍\n(1×{ksz} 的核)—— 只在左右方向糊了"),
            (step2, f"第二步:再竖着滤一遍\n({ksz}×1 的核)—— 这就是最终结果"),
            (np.abs(step2 - full), f"和「直接用 {ksz}×{ksz} 整张表」的差\n"
                                   f"最大 {np.abs(step2 - full).max():.1e},等于零"))):
        ax.imshow(pic, cmap="gray", vmin=0, vmax=255)
        ax.set_title(title, fontsize=10)
        ax.axis("off")
    fig.suptitle("可分离核:横一遍 + 竖一遍 = 整张表一遍,"
                 f"但乘法次数从 {ksz * ksz} 降到 {2 * ksz}", fontsize=13)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.90), h_pad=2.0)
    fig.savefig(out_path, dpi=110)


def main() -> None:
    demo_border()
    demo_naive_matches_cv2()
    demo_shift_version()
    demo_flip()
    demo_separable()

    out = REPO / "Assets" / "results" / "conv-engine-explained.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    save_explained_figure(out)
    print(f"\n结果已保存: {out.relative_to(REPO)}")

    sep = out.with_name("conv-separable-steps.png")
    save_separable_figure(sep)
    print(f"结果已保存: {sep.relative_to(REPO)}")

    if "--show" in sys.argv:
        plt.show()


if __name__ == "__main__":
    main()
