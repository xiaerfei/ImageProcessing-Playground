"""重新生成 intensity-and-grayscale.md 里那 2 张「从彩色取亮度」的配图。

为什么单独有这么个脚本:
    这两张图原先画完就扔进 Assets/results/ 了,仓库里没有代码能重新生成。
    配图和数字一样属于结论,结论就该有出处 —— 换机器、换版本、想改参数时
    不至于只能从头重画。

生成 2 张(全部写到 Assets/results/):
    rgb-to-gray-weighting.png   简单平均 vs 人眼加权:六个纯色块 + 一张真实照片
    brightness-definitions.png  同一张图,六种「亮度」定义,结果差多少

顺带在命令行打印那两张图里的所有数字,方便直接对文档。

用法:
    .venv/bin/python Ch06_Color_Processing/02_brightness_doc_figures.py [--show]

注意:本脚本会覆盖上述 2 个文件,文档正文引用的就是它们。
"""

import sys
from pathlib import Path

import cv2
import matplotlib

if "--show" not in sys.argv:
    matplotlib.use("Agg")  # 无窗口环境只保存文件
import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "Assets" / "results"
matplotlib.rcParams["font.family"] = ["Heiti TC", "Arial Unicode MS", "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False

# 六个纯色块,按 (名字, R, G, B) 给。选纯色是因为加权与平均的差别在这里最极端:
# 纯绿和纯蓝的简单平均都是 85,加权后一个 150 一个 29,差出 121 个灰阶。
SWATCHES = [
    ("红", 255, 0, 0), ("绿", 0, 255, 0), ("蓝", 0, 0, 255),
    ("黄", 255, 255, 0), ("青", 0, 255, 255), ("品红", 255, 0, 255),
]


def rgb_block(r: int, g: int, b: int, size: int = 160) -> npt.NDArray[np.uint8]:
    return np.full((size, size, 3), (r, g, b), dtype=np.uint8)


def mean_gray(rgb: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
    """简单平均 (R+G+B)/3 —— 直觉上合理,但不符合人眼。"""
    return np.clip(np.rint(rgb.astype(np.float64).mean(axis=2)), 0, 255).astype(np.uint8)


def luma_601(rgb: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
    """Rec.601 luma:0.299R + 0.587G + 0.114B。绿的权重是蓝的 5 倍多。"""
    f = rgb.astype(np.float64)
    y = 0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]
    return np.clip(np.rint(y), 0, 255).astype(np.uint8)


def luma_709(rgb: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
    """Rec.709 luma:高清/sRGB 用的那套系数,绿更重、红更轻。"""
    f = rgb.astype(np.float64)
    y = 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]
    return np.clip(np.rint(y), 0, 255).astype(np.uint8)


def load_rgb(name: str) -> npt.NDArray[np.uint8]:
    bgr = cv2.imread(str(REPO / "Assets" / "test-images" / name))
    if bgr is None:
        raise SystemExit(f"读图失败: {name}")
    return np.asarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), dtype=np.uint8)


def fig_weighting() -> None:
    """图一:同样是「转灰度」,简单平均和人眼加权能差出 121 个灰阶。"""
    photo = load_rgb("astronaut.png")
    cols = len(SWATCHES) + 1
    fig, axes = plt.subplots(3, cols, figsize=(17.5, 7.6))

    rows = [
        ("原始 RGB", lambda x: x, None),
        ("简单平均 (R+G+B)/3", mean_gray, "gray"),
        ("加权 0.299R+0.587G+0.114B", luma_601, "gray"),
    ]
    print("六个纯色块的灰度值:")
    print(f"  {'颜色':<6s}{'简单平均':>10s}{'Rec.601 加权':>14s}{'差':>7s}")
    for col, (name, r, g, b) in enumerate([*SWATCHES, ("真实照片", -1, -1, -1)]):
        src = photo if r < 0 else rgb_block(r, g, b)
        for row, (label, fn, cmap) in enumerate(rows):
            ax = axes[row, col]
            out = fn(src)
            ax.imshow(out, cmap=cmap, vmin=0 if cmap else None, vmax=255 if cmap else None)
            ax.set_xticks([]); ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
            if col == 0:
                ax.set_ylabel(label, fontsize=9)
            if row == 0:
                ax.set_title(name if r < 0 else f"{name}\n({r},{g},{b})", fontsize=9)
            elif r >= 0:
                # 纯色块的灰度是一个数,直接标在图下面,省得去猜
                ax.set_xlabel(str(int(out[0, 0])), fontsize=9)
        if r >= 0:
            m, y = int(mean_gray(src)[0, 0]), int(luma_601(src)[0, 0])
            print(f"  {name:<6s}{m:>10d}{y:>14d}{y - m:>+7d}")

    fig.suptitle("RGB → 灰度:简单平均 vs 按人眼感知加权", fontsize=13)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))
    fig.savefig(OUT / "rgb-to-gray-weighting.png", dpi=110)


def fig_definitions() -> None:
    """图二:同一张图,六种「亮度」定义 —— 名字都叫亮度,数值差别不小。"""
    rgb = load_rgb("astronaut.png")
    f = rgb.astype(np.float64)
    y601 = luma_601(rgb)

    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    # HLS 的 L 直接按定义算 (max+min)/2,不走 cv2.cvtColor:
    # cv2 内部有自己的取整路径,结果会差 0.06 个灰阶,和标题上写的公式对不上。
    hls_l = np.clip(np.rint((f.max(axis=2) + f.min(axis=2)) / 2), 0, 255).astype(np.uint8)
    cases = [
        ("Y (BT.601 luma)\n0.299R+0.587G+0.114B", y601),
        ("Y (BT.709 luma)\n0.2126R+0.7152G+0.0722B", luma_709(rgb)),
        ("V (HSV)\nmax(R,G,B)", np.asarray(hsv[:, :, 2], dtype=np.uint8)),
        ("L (HLS)\n(max+min)/2", hls_l),
        ("L* (Lab)\n感知均匀,OpenCV 已归一到 0~255",
         np.asarray(lab[:, :, 0], dtype=np.uint8)),
        ("平均 (R+G+B)/3\n⚠️ 不要用",
         np.clip(np.rint(f.mean(axis=2)), 0, 255).astype(np.uint8)),
    ]

    # 4 列 × 2 行:第一格放原图,剩下 6 格放六种定义,最后一格空着
    fig, axes = plt.subplots(2, 4, figsize=(15.5, 8.6))
    axes.flat[0].imshow(rgb)
    axes.flat[0].set_title("原图 RGB", fontsize=10)
    axes.flat[0].axis("off")

    print("\n六种「亮度」定义与 Y601 的平均差:")
    ref = y601.astype(np.float64)
    for i, (title, img) in enumerate(cases, start=1):
        d = float(np.abs(img.astype(np.float64) - ref).mean())
        ax = axes.flat[i]
        ax.imshow(img, cmap="gray", vmin=0, vmax=255)
        ax.set_title(f"{title}\n与 Y601 平均差 {d:.1f}", fontsize=9)
        ax.axis("off")
        print(f"  {title.splitlines()[0]:<24s}{d:>6.1f}")
    axes.flat[7].axis("off")   # 第 8 格没内容,关掉免得留个空坐标框

    fig.suptitle("同一张图,六种「亮度」定义 —— 结果差别不小", fontsize=13)
    # 两行标题都是 3 行文字,留足行间距,否则第二行标题会压住第一行的图
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.93), h_pad=3.2)
    fig.savefig(OUT / "brightness-definitions.png", dpi=110)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig_weighting()
    fig_definitions()
    print("\n已重新生成 2 张配图:")
    for name in ("rgb-to-gray-weighting.png", "brightness-definitions.png"):
        print(f"  {(OUT / name).relative_to(REPO)}")
    if "--show" in sys.argv:
        plt.show()


if __name__ == "__main__":
    main()
