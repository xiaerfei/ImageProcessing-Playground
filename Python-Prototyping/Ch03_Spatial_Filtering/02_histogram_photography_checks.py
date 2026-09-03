"""核对摄影文章里的两个技术说法 —— 配合 Documents/histogram-reading.md。

  1. RGB 叠加直方图 vs 明度直方图,到底差在哪
     (对应文档第二节,以及纠错清单第 1 条:"叠加后除以 3" 这个说法为什么误导)
  2. 线性传感器的档位码值分配,解释向右曝光(ETTR)为何有效
     (对应文档第六节)

用法:
    .venv/bin/python Ch03_Spatial_Filtering/02_histogram_photography_checks.py
"""

from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "Assets" / "test-images" / "astronaut.png"

# Rec.601 luma —— Photoshop"明度"直方图用的就是这一组权重
KR, KG, KB = 0.299, 0.587, 0.114


def hr(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def stacked_hist(rgb: np.ndarray) -> np.ndarray:
    """RGB 直方图:三个通道各自统计后相加,一个像素贡献 3 次。"""
    return sum(np.bincount(rgb[:, :, c].ravel(), minlength=256) for c in range(3)).astype(float)


def luma_hist(rgb: np.ndarray) -> np.ndarray:
    """明度直方图:每个像素先算一个亮度值再统计,一个像素贡献 1 次。"""
    luma = np.round(KR * rgb[:, :, 0] + KG * rgb[:, :, 1] + KB * rgb[:, :, 2]).astype(np.uint8)
    return np.bincount(luma.ravel(), minlength=256).astype(float)


# ---------------------------------------------------------------- 1a
def demo_pure_red() -> None:
    hr("1a. 极端例子:一张全是纯红 (255,0,0) 的图,100 个像素")
    img = np.zeros((10, 10, 3), np.uint8)
    img[:, :, 0] = 255
    a, b = stacked_hist(img), luma_hist(img)
    print(f"  {'':16s}{'亮度 0':>8s}{'亮度 76':>9s}{'亮度 255':>10s}")
    print(f"  {'RGB 叠加直方图':14s}{a[0]:8.0f}{a[76]:9.0f}{a[255]:10.0f}")
    print(f"  {'明度直方图':16s}{b[0]:8.0f}{b[76]:9.0f}{b[255]:10.0f}")
    print("\n  叠加图的结论:既有大量死黑,又有死白")
    print("  明度图的结论:全部是中偏暗的 76,既没有黑也没有白  ← 这才是人眼看到的")


# ---------------------------------------------------------------- 1b
def demo_real_photo() -> None:
    hr("1b. 真实照片上,两者差多少")
    rgb = cv2.cvtColor(cv2.imread(str(SRC)), cv2.COLOR_BGR2RGB)
    n = rgb.shape[0] * rgb.shape[1]
    a, b = stacked_hist(rgb), luma_hist(rgb)

    print(f"  像素总数 N = {n}")
    print(f"  叠加直方图总计数 = {a.sum():.0f} (= 3N),除以 3 后 = {a.sum()/3:.0f}")
    print(f"  明度直方图总计数 = {b.sum():.0f}")
    print(f"\n  两者形状相关系数 = {np.corrcoef(a / 3, b)[0, 1]:.4f}")
    print(f"  归一化后最大差异 = {np.abs(a / 3 / n - b / n).max() * 100:.2f} 个百分点")
    print("  → 整体趋势基本一致,'除以 3' 只是纵向缩放,不改形状")

    any0 = (rgb == 0).any(axis=2).sum()
    all0 = (rgb == 0).all(axis=2).sum()
    any255 = (rgb == 255).any(axis=2).sum()
    all255 = (rgb == 255).all(axis=2).sum()
    print(f"\n  但端点上差别明显 —— 这才是判断死黑死白的地方:")
    print(f"    至少一个通道为 0  : {any0:6d}  ({any0/n*100:5.2f}%)   ← 叠加图最左端反映的")
    print(f"    三个通道全为 0    : {all0:6d}  ({all0/n*100:5.2f}%)   ← 明度图最左端反映的")
    print(f"    至少一个通道为 255: {any255:6d}  ({any255/n*100:5.2f}%)")
    print(f"    三个通道全为 255  : {all255:6d}  ({all255/n*100:5.2f}%)")
    print("\n  检测过曝时的判据选择:")
    print("    max(R,G,B)==255 → 单通道溢出,色彩偏了但亮度信息还在")
    print("    min(R,G,B)==255 → 全通道溢出,真的没救了")


# ---------------------------------------------------------------- 2
def demo_ettr_code_values(bits: int = 12) -> None:
    hr(f"2. {bits} 位线性 RAW 的档位码值分配 —— 向右曝光为何有效")
    total = 2 ** bits
    print(f"  共 {total} 个码值。传感器是线性的:降一档曝光 = 进光量减半 = 码值减半\n")
    print(f"  {'从最亮往下第几档':>16s}{'分到码值':>10s}{'占比':>10s}")
    lo = total
    for i in range(bits):
        hi, lo = lo, lo // 2
        print(f"  {i + 1:>16d}{hi - lo:>10d}{(hi - lo) / total * 100:>9.2f}%")
    print("\n  最亮 1 档独占一半码值,最暗几档只剩个位数。")
    print("  ETTR = 把场景推到码值密集的那几档去记录,后期再压暗。")
    print("  同一个景物:记在第 1 档有 2048 级可用,记在第 8 档只有 16 级。")


if __name__ == "__main__":
    for fn in (demo_pure_red, demo_real_photo, demo_ettr_code_values):
        fn()
