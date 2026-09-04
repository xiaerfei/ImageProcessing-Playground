"""CLAHE 分步拆解 —— 配合 Documents/histogram-transform.md 的 CLAHE 一节。

  1. 全局均衡化为什么搞不定光照不均
  2. AHE(只分块、不限幅)为什么会把噪声放大
  3. clipLimit 削顶重分配的每一步数字
  4. 两个参数的极端值分别退化成什么

用法:
    .venv/bin/python Ch03_Spatial_Filtering/04_clahe_walkthrough.py [--save]
    --save 会把四联对比图写到 Documents/histogram-images/
"""

import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]
PAGE = REPO / "Assets" / "test-images" / "page.png"
OUT = REPO / "Documents" / "histogram-images"
SAVE = "--save" in sys.argv


def hr(title: str) -> None:
    print(f"\n{'=' * 64}\n{title}\n{'=' * 64}")


def halves(g: np.ndarray) -> tuple[float, float]:
    """左半边和右半边的平均亮度 —— 用来衡量光照是否均匀。"""
    w = g.shape[1] // 2
    return float(g[:, :w].mean()), float(g[:, w:].mean())


# ---------------------------------------------------------------- 1
def demo_global_fails() -> None:
    hr("1. 全局均衡化搞不定光照不均")
    g = cv2.imread(str(PAGE), cv2.IMREAD_GRAYSCALE)
    glob = cv2.equalizeHist(g)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(g)

    print("  这张扫描页左边亮、右边暗(光照不均):\n")
    print(f"  {'':14s}{'左半均值':>10s}{'右半均值':>10s}{'左右差':>9s}{'全图标准差':>12s}")
    for name, v in (("原图", g), ("全局均衡化", glob), ("CLAHE", clahe)):
        l, r = halves(v)
        print(f"  {name:14s}{l:10.1f}{r:10.1f}{abs(l - r):9.1f}{v.std():12.1f}")

    lo, hi = halves(g)
    lo2, hi2 = halves(glob)
    lo3, hi3 = halves(clahe)
    print(f"\n  原图左右差 {abs(lo-hi):.1f}")
    print(f"  全局均衡化后 {abs(lo2-hi2):.1f} —— 一张表全图共用,不均匀原样保留")
    print(f"  CLAHE 后     {abs(lo3-hi3):.1f} —— 每块按自己的情况调,差距被拉平")


# ---------------------------------------------------------------- 2
def demo_ahe_amplifies_noise() -> None:
    hr("2. AHE(不限幅)会把平坦区域的噪声放大多少")
    rng = np.random.default_rng(0)
    # 一块平坦的暗部:亮度都在 60 附近,只有 ±2 的传感器噪声
    flat = np.clip(rng.normal(60, 2, (256, 256)), 0, 255).astype(np.uint8)

    ahe = cv2.createCLAHE(clipLimit=40.0, tileGridSize=(8, 8)).apply(flat)  # 几乎不限幅
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(flat)

    print("  输入:一整块平坦暗部(均值 60,噪声标准差仅 2),本该保持平坦\n")
    for name, v in (("原图", flat), ("AHE  clipLimit=40", ahe), ("CLAHE clipLimit=2", clahe)):
        print(f"  {name:20s} 标准差={v.std():6.2f}   放大 {v.std() / flat.std():5.2f} 倍")
    print("\n  → 不限幅时,均衡化把纯噪声当成'需要极力增强的细节'")


# ---------------------------------------------------------------- 3
def demo_clip_steps() -> None:
    hr("3. clipLimit 削顶重分配,一步一步看")
    counts = np.array([2, 1, 40, 15, 3, 2, 1, 0])  # 一个 8x8 小块,8 个灰度级
    L, N = 8, int(counts.sum())
    clip = int(2.0 * N / L)

    print(f"  小块共 {N} 像素 / {L} 个灰度级,平均每级 {N/L:.1f} 个")
    print(f"  clipLimit=2.0 → 上限 = 平均高度 x 2 = {clip}\n")
    print(f"  第1步 原始直方图 : {counts.tolist()}")

    excess = int(np.maximum(counts - clip, 0).sum())
    clipped = np.minimum(counts, clip)
    print(f"  第2步 削顶       : {clipped.tolist()}   削下 {excess} 个")

    clipped = clipped + excess // L
    print(f"  第3步 均分回填   : {clipped.tolist()}   每级 +{excess // L}"
          f"(总数守恒,否则 CDF 末端不是 1)")

    eq = lambda h: np.round(np.cumsum(h) / h.sum() * (L - 1)).astype(int)
    a, b = eq(counts), eq(clipped)
    print(f"\n  第4步 算映射表")
    print(f"        原灰度      : {list(range(L))}")
    print(f"        不限幅 ->   : {a.tolist()}")
    print(f"        限幅后 ->   : {b.tolist()}")
    print(f"\n  看灰度 1→2 这一步:")
    print(f"    不限幅 {a[1]} → {a[2]},跨 {a[2]-a[1]} 级(噪声放大 {a[2]-a[1]} 倍)")
    print(f"    限幅后 {b[1]} → {b[2]},跨 {b[2]-b[1]} 级(温和)")
    print(f"\n  本质:映射表的斜率 = 对比度增益。削高柱子 = 给增益设天花板。")


# ---------------------------------------------------------------- 4
def demo_parameter_extremes() -> None:
    hr("4. 两个参数推到极端会退化成什么")
    g = cv2.imread(str(PAGE), cv2.IMREAD_GRAYSCALE)
    glob = cv2.equalizeHist(g)

    tile1 = cv2.createCLAHE(clipLimit=40.0, tileGridSize=(1, 1)).apply(g)
    diff = int(np.abs(tile1.astype(int) - glob.astype(int)).max())
    print(f"  tileGridSize=(1,1) + clipLimit 极大  vs  全局均衡化")
    print(f"    最大逐像素差 = {diff}  → 完全退化成全局均衡化\n")

    print(f"  clipLimit 从小到大(tileGridSize 固定 8x8):")
    for c in (1.0, 2.0, 5.0, 10.0, 40.0):
        v = cv2.createCLAHE(clipLimit=c, tileGridSize=(8, 8)).apply(g)
        print(f"    clipLimit={c:5.1f}  输出标准差={v.std():6.2f}")
    print("  → clipLimit 越大对比度越强,同时噪声越明显。默认 2.0 是个稳妥起点。")


def save_panel() -> None:
    g = cv2.imread(str(PAGE), cv2.IMREAD_GRAYSCALE)
    panels = [
        ("original", g),
        ("global-equalize", cv2.equalizeHist(g)),
        ("AHE-clip40", cv2.createCLAHE(clipLimit=40.0, tileGridSize=(8, 8)).apply(g)),
        ("CLAHE-clip2", cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(g)),
    ]
    gap = np.full((g.shape[0], 6), 255, np.uint8)
    row = []
    for i, (_, v) in enumerate(panels):
        if i:
            row.append(gap)
        row.append(v)
    cv2.imwrite(str(OUT / "demo-clahe-compare.png"), np.hstack(row))
    print(f"\n已保存 {OUT.name}/demo-clahe-compare.png"
          f"(依次:原图 / 全局均衡 / AHE不限幅 / CLAHE)")


if __name__ == "__main__":
    for fn in (demo_global_fails, demo_ahe_amplifies_noise,
               demo_clip_steps, demo_parameter_extremes):
        fn()
    if SAVE:
        save_panel()
