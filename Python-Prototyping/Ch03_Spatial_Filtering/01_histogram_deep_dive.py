"""直方图的六个深入验证 —— 配合 Documents/histogram-transform.md「深入部分」。

每一节对应文档的一节,打印的数字就是文档里引用的数字:

  1. CDF 变换为什么能摊平任意分布(概率积分变换)
  2. 直方图丢掉了空间信息 —— 三张完全不同的图,同一个直方图
  3. 直方图在哪个域:线性光 vs sRGB 编码,形状完全不同
  4. CLAHE 的 clip 到底怎么削顶重分配
  5. 直方图规定化手算
  6. 彩色图分通道均衡 vs 只均衡亮度 —— 色相偏移实测

用法:
    .venv/bin/python Ch03_Spatial_Filtering/01_histogram_deep_dive.py [--save]
    --save 会把配图写到 Documents/histogram-images/
"""

import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "Assets" / "test-images" / "astronaut.png"
OUT = REPO / "Documents" / "histogram-images"
SAVE = "--save" in sys.argv


def hr(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- 1
def demo_cdf_flattens() -> None:
    hr("1. CDF 变换把任意分布摊成均匀分布(概率积分变换)")
    rng = np.random.default_rng(0)
    n = 1_000_000
    x = np.clip(
        np.concatenate([rng.normal(60, 15, n // 2), rng.normal(180, 25, n // 2)]),
        0, 255,
    )
    hist, _ = np.histogram(x, bins=256, range=(0, 256))
    cdf = np.cumsum(hist) / n
    y = cdf[np.clip(x.astype(int), 0, 255)]  # y = F(x)

    before = np.histogram(x, bins=20, range=(0, 256))[0] / n * 100
    after = np.histogram(y, bins=20, range=(0, 1))[0] / n * 100
    print(f"原分布(双峰)20 桶占比%: {np.round(before, 1)}")
    print(f"F(x) 变换后 20 桶占比% : {np.round(after, 1)}")
    print(f"变换后标准差 = {after.std():.4f} 个百分点(理想均匀 = 5.00%)")


# ---------------------------------------------------------------- 2
def demo_histogram_loses_space() -> None:
    hr("2. 三张完全不同的图,同一个直方图")
    g = cv2.imread(str(SRC), cv2.IMREAD_GRAYSCALE)
    rng = np.random.default_rng(1)
    flat = g.ravel().copy()
    rng.shuffle(flat)
    shuffled = flat.reshape(g.shape)
    sorted_img = np.sort(g.ravel()).reshape(g.shape)

    h = lambda a: np.bincount(a.ravel(), minlength=256)
    print(f"原图 vs 随机打乱,直方图相同: {np.array_equal(h(g), h(shuffled))}")
    print(f"原图 vs 排序后  ,直方图相同: {np.array_equal(h(g), h(sorted_img))}")
    print(f"原图 vs 随机打乱 的 PSNR   : {cv2.PSNR(g, shuffled):.2f} dB")

    if SAVE:
        gap = np.full((g.shape[0], 8), 255, np.uint8)
        panel = np.hstack([g, gap, shuffled, gap, sorted_img])
        cv2.imwrite(str(OUT / "demo-same-histogram.png"), panel)
        print(f"已保存 {OUT.name}/demo-same-histogram.png")


# ---------------------------------------------------------------- 3
def demo_which_domain() -> None:
    hr("3. 同一批像素,线性光域 vs sRGB 编码域")
    rng = np.random.default_rng(2)
    lin = rng.beta(0.6, 6.0, 500_000)  # 线性反射率,自然场景常态:大量暗像素
    srgb = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * lin ** (1 / 2.4) - 0.055)

    for name, v in (("线性光域  ", lin), ("sRGB 编码域", srgb)):
        hist = np.histogram(v, bins=16, range=(0, 1))[0] / len(v) * 100
        print(f"{name} 中位数={np.median(v):.3f}  16 桶占比%: {np.round(hist, 1)}")
    print(f"\n最暗 1/16 区间的像素占比:线性 {np.mean(lin < 1/16)*100:.1f}%"
          f" → sRGB {np.mean(srgb < 1/16)*100:.1f}%")


# ---------------------------------------------------------------- 4
def demo_clahe_clip() -> None:
    hr("4. CLAHE 的 clip 削顶重分配")
    counts = np.array([2, 1, 40, 15, 3, 2, 1, 0])  # 一个 8×8 小块,8 个灰度级
    L, N = 8, counts.sum()
    clip = int(2.0 * N / L)  # clipLimit = 2.0 倍平均高度
    print(f"块内 {N} 像素 / {L} 级,平均每级 {N/L:.1f},clipLimit=2.0 → 上限 {clip}")
    print(f"原始    : {counts.tolist()}")

    excess = int(np.maximum(counts - clip, 0).sum())
    clipped = np.minimum(counts, clip)
    print(f"削顶后  : {clipped.tolist()}  (削下 {excess} 个)")
    clipped = clipped + excess // L
    print(f"均分回填: {clipped.tolist()}  (每级 +{excess // L})")

    eq = lambda h: np.round(np.cumsum(h) / h.sum() * (L - 1)).astype(int)
    print(f"\n不限幅的映射表: {eq(counts).tolist()}")
    print(f"限幅后的映射表: {eq(clipped).tolist()}")


# ---------------------------------------------------------------- 5
def demo_specification() -> None:
    hr("5. 直方图规定化(匹配)手算")
    L = 8
    src = np.array([0, 0, 5, 30, 40, 20, 5, 0])
    ref = np.array([10, 15, 15, 10, 10, 15, 15, 10])
    fs, fr = np.cumsum(src) / src.sum(), np.cumsum(ref) / ref.sum()

    mapping = [int(np.argmin(np.abs(fr - fs[r]))) for r in range(L)]
    for r in range(L):
        print(f"  r={r}  源CDF={fs[r]:.3f} → z={mapping[r]} (目标CDF={fr[mapping[r]]:.3f})")

    out = np.zeros(L, int)
    for r in range(L):
        out[mapping[r]] += src[r]
    pct = lambda a: (a / a.sum() * 100).round(0).astype(int).tolist()
    print(f"\n映射表        : {mapping}")
    print(f"目标形状(占比): {pct(ref)}")
    print(f"实际结果(占比): {pct(out)}   ← 离散下只能逼近,不能吻合")


# ---------------------------------------------------------------- 6
def demo_color_equalization() -> None:
    hr("6. 彩色图:分通道均衡 vs 只均衡亮度")
    bgr = cv2.imread(str(SRC))
    per_channel = np.stack([cv2.equalizeHist(bgr[:, :, c]) for c in range(3)], axis=2)
    ycc = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    ycc[:, :, 0] = cv2.equalizeHist(ycc[:, :, 0])
    luma_only = cv2.cvtColor(ycc, cv2.COLOR_YCrCb2BGR)

    def hue_shift(out):
        hs = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[:, :, 0].astype(int)
        ho = cv2.cvtColor(out, cv2.COLOR_BGR2HSV)[:, :, 0].astype(int)
        d = np.abs(ho - hs)
        return np.minimum(d, 180 - d) * 2  # OpenCV 的 H 是 0~179,×2 还原成度

    for name, out in (("分通道各自均衡", per_channel), ("只均衡 Y 通道", luma_only)):
        d = hue_shift(out)
        print(f"{name}: 色相平均偏移 {d.mean():6.2f}°  "
              f"中位数 {np.median(d):5.2f}°  偏移>10° 的像素 {np.mean(d > 10)*100:5.2f}%")

    if SAVE:
        gap = np.full((bgr.shape[0], 8, 3), 255, np.uint8)
        cv2.imwrite(str(OUT / "demo-color-equalization.png"),
                    np.hstack([bgr, gap, per_channel, gap, luma_only]))
        print(f"已保存 {OUT.name}/demo-color-equalization.png")


if __name__ == "__main__":
    for fn in (demo_cdf_flattens, demo_histogram_loses_space, demo_which_domain,
               demo_clahe_clip, demo_specification, demo_color_equalization):
        fn()
