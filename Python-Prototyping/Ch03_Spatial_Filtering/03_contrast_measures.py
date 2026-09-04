"""对比度的三种度量方式对照 —— 配合 Documents/contrast.md。

  1. 亮度和对比度是两件独立的事:加法改亮度,乘法改对比度
  2. max-min 的致命弱点:两个极端像素就能骗过它
  3. 三种度量在真实照片上的表现

用法:
    .venv/bin/python Ch03_Spatial_Filtering/03_contrast_measures.py
"""

from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "Assets" / "test-images" / "astronaut.png"


def hr(title: str) -> None:
    print(f"\n{'=' * 64}\n{title}\n{'=' * 64}")


def span(v: np.ndarray) -> float:
    """跨度:最亮减最暗。最直觉,但一个坏点就毁掉它。"""
    return float(v.max() - v.min())


def rms_contrast(v: np.ndarray) -> float:
    """RMS 对比度:亮度的标准差。每个像素都参与,极端值被稀释。"""
    return float(v.std())


def percentile_span(v: np.ndarray, lo: float = 1.0, hi: float = 99.0) -> float:
    """百分位跨度:扔掉最极端的那一小撮再算。工程上最实用。"""
    a, b = np.percentile(v, [lo, hi])
    return float(b - a)


def report(name: str, v: np.ndarray) -> None:
    print(f"  {name:22s} 跨度={span(v):6.1f}   标准差={rms_contrast(v):6.2f}   "
          f"1~99%跨度={percentile_span(v):6.1f}")


# ---------------------------------------------------------------- 1
def demo_brightness_vs_contrast() -> None:
    hr("1. 亮度和对比度是两件独立的事")
    a = np.array([100.0, 110, 120, 130, 140])  # 挤在中间
    b = np.array([20.0, 70, 120, 170, 220])    # 铺得开

    for name, v in (("A 低对比度", a), ("B 高对比度", b)):
        vals = str(v.astype(int).tolist())
        print(f"  {name}: {vals:26s}  平均={v.mean():.0f}  "
              f"跨度={span(v):.0f}  标准差={v.std():.1f}")

    print("\n  → 平均值都是 120(一样亮),但 B 的差距是 A 的 5 倍\n")

    plus = a + 100                      # 加法
    times = (a - 120) * 5 + 120         # 乘法(以 120 为中心)
    print(f"  A 整体 +100      : {plus.astype(int).tolist()}"
          f"  平均={plus.mean():.0f}  跨度={span(plus):.0f}  标准差={plus.std():.1f}")
    print(f"  A 以120为中心 ×5 : {times.astype(int).tolist()}"
          f"  平均={times.mean():.0f}  跨度={span(times):.0f}  标准差={times.std():.1f}")
    print("\n  → 加法只动平均值(亮度),乘法只动跨度(对比度)。互不干扰。")


# ---------------------------------------------------------------- 2
def demo_outlier_breaks_span() -> None:
    hr("2. max-min 的致命弱点:两个像素就能骗过它")
    n = 10000
    fake = np.full(n, 120.0)     # 一整块均匀的灰板
    fake[0], fake[1] = 0, 255    # 只掺 2 个极端像素(占 0.02%)
    real = np.linspace(0, 255, n)

    report("纯灰 + 2个极端点", fake)
    report("真·高对比度渐变", real)
    report("纯灰(无极端点)", np.full(n, 120.0))

    print("\n  → 跨度对前两者都报 255,完全分不出来")
    print("  → 标准差 1.81 vs 73.62,差 40 倍;1~99% 跨度 0.0 vs 249.9,判断正确")


# ---------------------------------------------------------------- 3
def demo_real_photo() -> None:
    hr("3. 真实照片:原图 / 压低对比度 / 拉高对比度")
    g = cv2.imread(str(SRC), cv2.IMREAD_GRAYSCALE).astype(float)
    mean = g.mean()
    for name, a in (("原图 (a=1.0)", 1.0), ("压低 (a=0.4)", 0.4), ("拉高 (a=2.0)", 2.0)):
        v = np.clip((g - mean) * a + mean, 0, 255)
        report(name, v)
    print("\n  注意 a=2.0 那行:跨度还是 255(本来就顶满),")
    print("  但标准差明显变大 —— 只有标准差反映出了真实变化。")


# ---------------------------------------------------------------- 4
def demo_autolevels() -> None:
    hr("4. 自动色阶为什么要故意扔掉 1%")
    # 造一张真实场景:隔着雾/玻璃拍的低对比度照片,再掺一个镜面反光坏点
    g = cv2.imread(str(SRC), cv2.IMREAD_GRAYSCALE).astype(float)
    hazy = g * 0.3 + 90          # 压成 90~166 的窄区间,灰蒙蒙
    hazy[0, 0] = 255             # 一个反光高光
    hazy[0, 1] = 0               # 一个暗坏点

    naive = (hazy - hazy.min()) / (hazy.max() - hazy.min()) * 255
    lo, hi = np.percentile(hazy, [0.5, 99.5])
    smart = np.clip((hazy - lo) / (hi - lo) * 255, 0, 255)

    report("原图(灰蒙蒙+坏点)", hazy)
    report("按 min/max 拉伸", naive)
    report("按 0.5~99.5% 拉伸", smart)
    print(f"\n  min/max 方案:坏点已经占住 0 和 255,算法以为'已经铺满了',白做一场")
    print(f"    标准差 {hazy.std():.2f} → {naive.std():.2f}(几乎没变)")
    print(f"  百分位方案:坏点被当成那 1% 扔掉,真正把有效区间铺开")
    print(f"    标准差 {hazy.std():.2f} → {smart.std():.2f}(涨了 {smart.std()/hazy.std():.1f} 倍)")


if __name__ == "__main__":
    for fn in (demo_brightness_vs_contrast, demo_outlier_breaks_span,
               demo_real_photo, demo_autolevels):
        fn()
