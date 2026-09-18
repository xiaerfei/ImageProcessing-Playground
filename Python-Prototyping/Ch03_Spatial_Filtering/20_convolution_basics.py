"""第 6 周(3.4 节):空间滤波基础 —— 20 卷积与相关、边界、可分离。

对应文档 Documents/05-spatial-filtering/spatial-filtering-basics.md,
这一篇把里面每个数字都跑出来。

3.4 是整个第 3 章的分水岭:3.2 和 3.3 的所有方法都能塌缩成一张 256 项的表,
从这里开始不行了 —— 输出要看邻居,同一个灰度值在不同位置结果不同。

验证七件事:
1. 它塌缩不成 LUT:5×5 高斯模糊后,原本同为 100 的像素变成了 67 种不同的值
2. ⚠️ cv2.filter2D 做的是**相关**不是卷积:用单位冲激一试就知道 ——
   卷积的冲激响应是核本身,相关的是核翻转 180°,实测是后者
3. 对称核翻不翻都一样(最大差 0.0),方向性核一翻就变号(Sobel 上差 1720)
4. 只有卷积有交换律 —— 这就是教材非要区分两者的理由
5. 五种补边的实测值,以及为什么 OpenCV 默认 REFLECT_101
6. 可分离:秩 = 1 就能拆成两个一维核。15×15 上实测快 25 倍;
   ⚠️ 但 filter2D 在 k≥9 时改用 DFT,耗时曲线根本不是 k²
7. ddepth 的坑:Sobel 用 uint8 输出,45.3% 的像素(负数)被截成 0

用法:
    .venv/bin/python Ch03_Spatial_Filtering/20_convolution_basics.py
"""

import time
from pathlib import Path

import cv2
import numpy as np
import numpy.typing as npt

REPO = Path(__file__).resolve().parents[2]


def hr(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def load_gray(name: str) -> npt.NDArray[np.uint8]:
    path = REPO / "Assets" / "test-images" / name
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise SystemExit(f"读不到 {path}")
    return np.asarray(img, dtype=np.uint8)


def bench(fn, repeat: int = 10) -> float:
    """毫秒/次,先热身一轮。"""
    fn()
    t0 = time.perf_counter()
    for _ in range(repeat):
        fn()
    return (time.perf_counter() - t0) / repeat * 1000


# ---------------------------------------------------------------- 1
def demo_not_a_lut() -> None:
    hr("1. 它是第一个塌缩不成 LUT 的操作")
    img = load_gray("astronaut.png")
    blur = cv2.GaussianBlur(img, (5, 5), 1.0)
    same = img == 100
    print(f"  原图里值为 100 的像素有 {int(same.sum())} 个")
    print(f"  5×5 高斯模糊后,它们变成了 {len(np.unique(blur[same]))} 种不同的值")
    print("\n  同一个输入对应多个输出 —— 一张 256 项的表表达不了,")
    print("  因为输出还取决于这个像素周围长什么样。")
    print("  判据见 Documents/01-fundamentals/lut.md:输出是否只取决于该像素自己的值。")


# ---------------------------------------------------------------- 2
def demo_correlation_not_convolution() -> None:
    hr("2. ⚠️ cv2.filter2D 做的是相关,不是卷积")
    impulse = np.zeros((5, 5), np.float32)
    impulse[2, 2] = 1.0                      # 单位冲激:只有中心一个 1
    k = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], np.float32)

    resp = cv2.filter2D(impulse, -1, k)[1:4, 1:4]
    print(f"  核 k =\n{k.astype(int)}")
    print(f"\n  filter2D(冲激) 的中心 3×3 =\n{resp.astype(int)}")
    print(f"\n  核翻转 180° =\n{k[::-1, ::-1].astype(int)}")
    print(f"\n  两者相同?{np.array_equal(resp, k[::-1, ::-1])}")
    print("\n  怎么读这个结果:")
    print("    卷积的冲激响应 = 核本身(冲激是卷积的单位元,f * δ = f)")
    print("    相关的冲激响应 = 核翻转 180°")
    print("  实测拿到的是后者 → filter2D 做的是相关。名字里有 filter,数学上是 correlation。")
    print("\n  想要真卷积,自己先把核翻过来:cv2.filter2D(img, d, cv2.flip(k, -1))")


# ---------------------------------------------------------------- 3
def demo_when_it_matters(img: npt.NDArray[np.uint8]) -> None:
    hr("3. 什么时候这个区别不重要")
    g1 = cv2.getGaussianKernel(5, 1.0)
    gau = np.asarray(g1 @ g1.T, dtype=np.float32)
    sob = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], np.float32)

    print(f"  {'核':<20s}{'相关 vs 卷积 最大差':>22s}{'卷积 = −相关?':>16s}")
    for name, k in (("5×5 高斯(对称)", gau), ("3×3 Sobel-x(反对称)", sob)):
        a = cv2.filter2D(img, cv2.CV_32F, k)
        b = cv2.filter2D(img, cv2.CV_32F, cv2.flip(k, -1))
        print(f"  {name:<20s}{np.abs(a - b).max():22.1f}{str(bool(np.allclose(b, -a))):>16s}")
    print("\n  平滑类的核(盒式、高斯)全是中心对称的,翻不翻一样 ——")
    print("  这就是为什么很多人写了一辈子 filter2D 都没发现它是相关。")
    print("  但方向性的核(Sobel、Prewitt、各种梯度算子)一翻就变号,梯度方向整个反过来。")


# ---------------------------------------------------------------- 4
def demo_why_convolution() -> None:
    hr("4. 那为什么教材非要区分 —— 只有卷积有交换律")
    a = np.array([1.0, 2.0, 3.0])
    b = np.array([0.0, 0.0, 1.0])
    print(f"  a = {a.tolist()}   b = {b.tolist()}\n")
    print(f"  conv(a,b) = {np.convolve(a, b).tolist()}")
    print(f"  conv(b,a) = {np.convolve(b, a).tolist()}   ← 一样")
    print(f"  corr(a,b) = {np.correlate(a, b, 'full').tolist()}")
    print(f"  corr(b,a) = {np.correlate(b, a, 'full').tolist()}   ← 不一样")
    print("\n  交换律和结合律是整个信号处理的地基:")
    print("    结合律 (f*g)*h = f*(g*h) → 两个滤波器可以先合成一个,省一遍扫描")
    print("    第 4 章「空间卷积 ↔ 频域相乘」的定理,说的也是卷积,不是相关")
    print("  所以:理论上讲卷积,代码里用相关 —— 核对称就不会出事,不对称自己翻一下。")


# ---------------------------------------------------------------- 5
def demo_borders() -> None:
    hr("5. 边界:五种补边的实测值")
    row = np.array([[10, 20, 30, 40, 50]], np.uint8)
    print(f"  原始一行 {row[0].tolist()},左右各补 3 个:\n")
    notes = {
        "BORDER_CONSTANT": "外面全当 0(黑)—— 边框会变暗",
        "BORDER_REPLICATE": "边缘像素复制出去 —— 最安全",
        "BORDER_REFLECT": "以边缘外侧为轴镜像 —— 边缘值出现两次",
        "BORDER_REFLECT_101": "以边缘像素为轴镜像,不重复它 ← OpenCV 默认",
        "BORDER_WRAP": "从另一头绕回来 —— 只对周期性图像正确",
    }
    for name, note in notes.items():
        out = cv2.copyMakeBorder(row, 0, 0, 3, 3, getattr(cv2, name), value=0)
        print(f"  {name:<20s}{str(out[0].tolist()):<40s}{note}")

    print("\n  为什么 REFLECT_101 是默认:它保证边界处的一阶差分连续。")
    print("  REFLECT 把边缘像素写了两遍,等于人为造了一小块「平的地方」,")
    print("  做梯度/锐化时会在四周留下一圈伪响应。")

    print("\n  filter2D 的 borderType 参数,同一个核不同模式下第一个像素的差别:")
    rowf = row.astype(np.float32)
    k = np.array([[1, 0, 0]], np.float32)      # 相关时取左邻居
    for name in ("BORDER_REFLECT_101", "BORDER_REPLICATE", "BORDER_CONSTANT"):
        out = cv2.filter2D(rowf, -1, k, borderType=getattr(cv2, name))
        print(f"    {name:<20s}{[int(v) for v in out[0]]}")
    print("  (核 [1,0,0] 做相关取的是左邻居 —— 相关不翻核,权重在左就取左)")

    print("\n  还有第四条路:根本不补,只算核能完整覆盖的区域,输出小一圈(numpy 的 'valid')。")
    print("  三选一,没有标准答案:编造边界数据 / 让图变小 / 算了但不信边缘。")


# ---------------------------------------------------------------- 6
def demo_separable() -> None:
    hr("6. 可分离核:秩 = 1 就能拆成两个一维核")
    g15 = cv2.getGaussianKernel(15, 3.0)
    cases = (
        ("15×15 高斯", np.asarray(g15 @ g15.T, np.float32)),
        ("15×15 盒式", np.ones((15, 15), np.float32) / 225.0),
        ("3×3 Sobel-x", np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], np.float32)),
        ("3×3 拉普拉斯", np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], np.float32)),
    )
    print(f"  {'核':<16s}{'秩':>4s}   能分离吗")
    for name, k in cases:
        r = int(np.linalg.matrix_rank(k))
        print(f"  {name:<16s}{r:>4d}   {'能' if r == 1 else '不能'}")
    sob = cases[2][1]
    outer = np.array([[1.0], [2.0], [1.0]]) @ np.array([[-1.0, 0.0, 1.0]])
    print(f"\n  Sobel-x 正好是 [1,2,1]ᵀ × [−1,0,1] ?{np.allclose(sob, outer)}")
    print("  —— 可分离不是巧合:它天生就是「一个方向差分 × 另一个方向平滑」。")

    big = cv2.resize(load_gray("astronaut.png"), (1920, 1080))
    print(f"\n  在 {big.shape[1]}×{big.shape[0]} 上计时:\n")
    print(f"  {'核':>6s}{'filter2D(2D)':>16s}{'sepFilter2D':>14s}"
          f"{'GaussianBlur':>15s}{'加速':>8s}{'两者最大差':>11s}")
    for ksz in (5, 15, 31):
        g = cv2.getGaussianKernel(ksz, ksz / 6.0)
        k2d = np.asarray(g @ g.T, np.float32)
        t2 = bench(lambda: cv2.filter2D(big, -1, k2d))
        ts = bench(lambda: cv2.sepFilter2D(big, -1, g, g))
        tg = bench(lambda: cv2.GaussianBlur(big, (ksz, ksz), ksz / 6.0))
        d = int(np.abs(cv2.filter2D(big, -1, k2d).astype(np.int64)
                       - cv2.sepFilter2D(big, -1, g, g).astype(np.int64)).max())
        print(f"  {ksz:>4d}²{t2:14.2f} ms{ts:12.2f} ms{tg:13.2f} ms"
              f"{t2 / ts:7.1f}×{d:11d}")

    print("\n  ⚠️ filter2D 的耗时曲线根本不是 k²:")
    line = []
    for ksz in (3, 5, 9, 15, 21, 31, 63):
        g = cv2.getGaussianKernel(ksz, ksz / 6.0)
        k2d = np.asarray(g @ g.T, np.float32)
        line.append((ksz, bench(lambda: cv2.filter2D(big, -1, k2d), 8)))
    print("     k  " + "".join(f"{k:>8d}" for k, _ in line))
    print("    ms  " + "".join(f"{t:>8.2f}" for _, t in line))
    print("  k≥9 之后几乎持平 —— OpenCV 改用了 DFT(频域相乘)。")
    print("  「空间卷积是 O(k²)」这个教科书结论,在真实的库里只在小核上成立。")


# ---------------------------------------------------------------- 7
def demo_ddepth(img: npt.NDArray[np.uint8]) -> None:
    hr("7. ddepth 的坑:uint8 输出会吃掉将近一半的像素")
    sob = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], np.float32)
    f32 = cv2.filter2D(img, cv2.CV_32F, sob)
    u8 = cv2.filter2D(img, -1, sob)
    neg = int((f32 < 0).sum())
    print(f"  3×3 Sobel-x 作用在 camera.png 上:")
    print(f"    ddepth=CV_32F(真实结果):范围 [{f32.min():.0f}, {f32.max():.0f}]")
    print(f"    ddepth=-1  (uint8 输出):范围 [{u8.min()}, {u8.max()}]")
    print(f"    负数像素 {neg} 个,占 {neg / img.size * 100:.1f}% —— 全被截成 0")
    print(f"    超过 255 的 {int((f32 > 255).sum())} 个")

    print("\n  ⚠️ 是饱和(截断)成 0,不是取绝对值。和 convertScaleAbs 不一样:")
    print(f"    filter2D(uint8) 把 −860 变成 0;convertScaleAbs 会把它变成 255。")
    print("    两个都不是真实结果,但错法不同。")

    sharp = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], np.float32)
    s32 = cv2.filter2D(img, cv2.CV_32F, sharp)
    out = int(((s32 < 0) | (s32 > 255)).sum())
    print(f"\n  锐化核同理:真实范围 [{s32.min():.0f}, {s32.max():.0f}],"
          f"越界 {out} 个像素({out / img.size * 100:.1f}%)")

    print("\n  正确做法:中间一律用浮点,要看的时候再映射回来 —— 三种映射含义不同:")
    print("    cv2.convertScaleAbs(grad)          取绝对值,看「变化有多大」")
    print("    np.clip(grad + 128, 0, 255)        0 移到中灰,看「往哪个方向变」")
    print("    cv2.normalize(..., NORM_MINMAX)    拉满整个范围,只为看清")


def main() -> None:
    img = load_gray("camera.png")
    print(f"主图 camera.png  shape={img.shape}")
    demo_not_a_lut()
    demo_correlation_not_convolution()
    demo_when_it_matters(img)
    demo_why_convolution()
    demo_borders()
    demo_separable()
    demo_ddepth(img)


if __name__ == "__main__":
    main()
