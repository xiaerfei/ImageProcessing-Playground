"""重新生成 intensity-and-grayscale.md 里那 4 张灰度变换配图。

为什么单独有这么个脚本:
    这 4 张图原先是「画完扔进 Assets/results/ 就没了」,仓库里没有任何代码能
    重新生成它们。换台机器、换个 matplotlib 版本、想改个参数或修个排版,
    都只能从头重画。配图和数字一样属于结论,结论就该有出处。

生成 4 张(全部写到 Assets/results/):
    intensity-transform-curves.png  六种变换的映射曲线 + 效果并排(moon)
    linear-transform.png            s = a·r + b 的五组 (a,b):曲线/效果/直方图
    log-transform.png               对数曲线的读法 + 它在傅里叶频谱上的杀手级用途
    linear-vs-log.png               同样想看清暗部:线性靠推出画面,对数靠挤扁亮部

用法:
    .venv/bin/python Ch03_Spatial_Filtering/00_intensity_doc_figures.py [--show]

注意:本脚本会覆盖上述 4 个文件。文档正文引用的就是它们,改参数前先想清楚。
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

LEVELS = np.arange(256)
C_LOG = 255.0 / np.log(256.0)   # ≈ 45.99,把 log(1+r) 的 0~5.55 撑满 0~255


def to_lut(s: npt.NDArray[np.float64]) -> npt.NDArray[np.uint8]:
    """浮点曲线 → 256 项 uint8 查找表。

    clip 不是收尾而是变换的一部分:越界不夹住的话 astype 会按 256 取模回绕,
    高光变黑斑。见 Documents/01-fundamentals/rounding-and-float.md。
    """
    return np.clip(np.rint(s), 0, 255).astype(np.uint8)


def lut_linear(a: float, b: float) -> npt.NDArray[np.uint8]:
    return to_lut(a * LEVELS + b)


def lut_log() -> npt.NDArray[np.uint8]:
    return to_lut(C_LOG * np.log(1.0 + LEVELS))


def lut_gamma(gamma: float) -> npt.NDArray[np.uint8]:
    return to_lut(255.0 * (LEVELS / 255.0) ** gamma)


def lut_window(lo: int, hi: int) -> npt.NDArray[np.uint8]:
    """分段拉伸:把 [lo, hi] 撑满 0~255,区间外直接截断。也就是 a=255/(hi-lo)。"""
    return to_lut((LEVELS - lo) * (255.0 / (hi - lo)))


def load(name: str) -> npt.NDArray[np.uint8]:
    img = cv2.imread(str(REPO / "Assets" / "test-images" / name), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise SystemExit(f"读图失败: {name}")
    return np.asarray(img, dtype=np.uint8)


def clipped_pct(lut: npt.NDArray[np.uint8], img: npt.NDArray[np.uint8]) -> float:
    """这条曲线把百分之多少的像素拍到了 0 / 255(不含原本就是 0 / 255 的)。"""
    hist = np.bincount(img.ravel(), minlength=256)
    dead = ((lut == 0) | (lut == 255)) & (LEVELS != 0) & (LEVELS != 255)
    return float(100.0 * hist[dead].sum() / img.size)


def draw_curve(ax: plt.Axes, lut: npt.NDArray[np.uint8], *, shade: bool = False) -> None:
    """画一条映射曲线,虚线是「什么都不做」的对角线。

    shade=True 时把 0 / 255 以外的区域涂红:曲线一旦贴上红区边界就是在丢信息,
    这比只看曲线形状直观得多。
    """
    if shade:
        ax.axhspan(255, 300, color="tab:red", alpha=0.08)
        ax.axhspan(-45, 0, color="tab:red", alpha=0.08)
        ax.set_ylim(-45, 300)
    else:
        ax.set_ylim(0, 255)
    ax.plot([0, 255], [0, 255], color="0.6", lw=0.9, ls="--")
    ax.plot(LEVELS, lut, color="tab:red", lw=2.0)
    ax.set_xlim(0, 255)
    ax.set_xticks([0, 128, 255])


def fig_curves() -> None:
    """图一:六种变换的映射曲线 + 效果并排 —— 「一张兑换表决定每个亮度换成什么」。"""
    img = load("moon.png")
    cases = [
        ("原图(不变)\ns = r", lut_linear(1.0, 0.0)),
        ("反色\ns = 255 - r", lut_linear(-1.0, 255.0)),
        ("对数\ns = c·log(1+r)", lut_log()),
        ("幂律 γ=0.4\ns = 255·(r/255)^γ", lut_gamma(0.4)),
        ("幂律 γ=2.2\n(压暗)", lut_gamma(2.2)),
        ("分段拉伸 [30,120]\n区间外截断", lut_window(30, 120)),
    ]
    fig, axes = plt.subplots(2, len(cases), figsize=(19, 6.6),
                             gridspec_kw={"height_ratios": [1, 1.25]})
    for col, (title, lut) in enumerate(cases):
        ax = axes[0, col]
        draw_curve(ax, lut)
        ax.set_yticks([0, 128, 255])
        ax.set_title(title, fontsize=10)
        if col == 0:
            ax.set_ylabel("输出 s")
        axes[1, col].imshow(cv2.LUT(img, lut), cmap="gray", vmin=0, vmax=255)
        axes[1, col].axis("off")
    fig.suptitle("灰度变换:一张「兑换表」决定每个亮度值换成什么(虚线 = 不做任何改变)",
                 fontsize=13)
    # suptitle 不进 tight_layout 的布局,rect 给它留位,否则会压住第一行标题
    fig.tight_layout(rect=(0.01, 0.0, 1.0, 0.93))
    fig.savefig(OUT / "intensity-transform-curves.png", dpi=110)


def fig_linear() -> None:
    """图二:s = a·r + b 的五组参数 —— 曲线 / 效果 / 直方图三行对照。"""
    img = load("camera.png")
    cases = [
        ("原样", 1.0, 0.0), ("提亮", 1.0, 60.0), ("增对比", 1.8, -100.0),
        ("降对比", 0.5, 64.0), ("反色", -1.0, 255.0),
    ]
    fig, axes = plt.subplots(3, len(cases), figsize=(17, 10.5),
                             gridspec_kw={"height_ratios": [1, 1.2, 0.85]})
    for col, (name, a, b) in enumerate(cases):
        lut = lut_linear(a, b)
        ax = axes[0, col]
        draw_curve(ax, lut, shade=True)
        # 未截断的理想直线画成点线,和被拍平的实际曲线一对比就知道削掉了多少
        ax.plot(LEVELS, a * LEVELS + b, color="0.35", lw=0.8, ls=":")
        ax.set_yticks([0, 128, 255])
        ax.set_title(f"{name}\na={a:g}, b={b:+g}", fontsize=10)
        if col == 0:
            ax.set_ylabel("输出 s")
            ax.text(8, 272, "红区 = 被截断", color="tab:red", fontsize=8)

        out = cv2.LUT(img, lut)
        axes[1, col].imshow(out, cmap="gray", vmin=0, vmax=255)
        axes[1, col].axis("off")

        ax = axes[2, col]
        ax.bar(LEVELS, np.bincount(out.ravel(), minlength=256), width=1.0,
               color="tab:blue")
        # 纵轴取对数:截断会在 0 或 255 上堆出几万个像素的尖峰,线性纵轴下
        # 其余柱子会被压成贴地的一条,什么都看不出来
        ax.set_yscale("log")
        ax.set_xlim(0, 255)
        ax.set_ylim(bottom=1)
        ax.set_yticks([])
        if col == 0:
            ax.set_xlabel("直方图(对数纵轴)")
    fig.suptitle("线性灰度变换 s = a·r + b   ——   a 管对比度(斜率),b 管亮度(截距)",
                 fontsize=13)
    fig.tight_layout(rect=(0.012, 0.0, 1.0, 0.94))
    fig.savefig(OUT / "linear-transform.png", dpi=110)


def fig_log() -> None:
    """图三:对数曲线怎么读,以及它真正无可替代的用途 —— 看傅里叶频谱。"""
    img = load("camera.png")
    lut = lut_log()

    fig = plt.figure(figsize=(15, 8.5))
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 1.1])

    # 左上:对数 vs 最接近的幂律。两条几乎重合 —— 所以伽马能当"可调的对数"用
    ax = fig.add_subplot(gs[0, 0])
    gamma = 0.21
    ax.plot([0, 255], [0, 255], color="0.6", lw=0.9, ls="--", label="不变")
    ax.plot(LEVELS, lut, color="tab:red", lw=2.0, label="对数")
    ax.plot(LEVELS, lut_gamma(gamma), color="tab:blue", lw=1.6, ls="-.",
            label=f"幂律 γ={gamma}")
    ax.set_xlim(0, 255); ax.set_ylim(0, 255)
    ax.set_xticks([0, 128, 255]); ax.set_yticks([0, 128, 255])
    ax.set_title("对数曲线 vs 最接近的幂律", fontsize=11)
    ax.legend(fontsize=8, loc="lower right")

    # 右上:放大看具体读数 —— 0~10 的输入就占掉了输出的 0~110
    ax = fig.add_subplot(gs[0, 1:])
    ax.plot(LEVELS, lut, color="tab:red", lw=2.0)
    for r in (10, 130, 255):
        s = int(lut[r])
        ax.plot([r, r], [0, s], color="0.5", lw=0.7, ls=":")
        ax.plot([0, r], [s, s], color="0.5", lw=0.7, ls=":")
        ax.annotate(f"r={r} → s={s}", xy=(r, s), xytext=(r - 6, s + 12),
                    fontsize=9, color="tab:red", ha="right")
    ax.set_xlim(0, 255); ax.set_ylim(0, 275)
    ax.set_title("暗部被大幅拉宽,亮部被压缩(0~10 的输入占了输出的 0~110)",
                 fontsize=11)

    # 下排:频谱。幅度差几百万倍,不取 log 屏幕上只剩中心一个白点
    spec = np.abs(np.fft.fftshift(np.fft.fft2(img.astype(np.float64))))
    linear_view = np.clip(np.rint(spec / spec.max() * 255.0), 0, 255).astype(np.uint8)
    log_spec = np.log1p(spec)
    log_view = np.clip(np.rint(log_spec / log_spec.max() * 255.0), 0, 255).astype(np.uint8)
    for col, (pic, title) in enumerate((
            (img, "原图"),
            (linear_view, "频谱:线性显示\n(几乎全黑,只剩中心一点)"),
            (log_view, "频谱:取 log 后\n(结构全部显现)"))):
        ax = fig.add_subplot(gs[1, col])
        ax.imshow(pic, cmap="gray", vmin=0, vmax=255)
        ax.set_title(title, fontsize=10)
        ax.axis("off")

    fig.suptitle("对数变换 s = c·log(1+r), c = 255/log(256) ≈ 46", fontsize=13)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))
    fig.savefig(OUT / "log-transform.png", dpi=110)


def fig_linear_vs_log() -> None:
    """图四:同样想看清暗部,线性和对数付出的代价完全不同。"""
    img = load("camera.png")
    a_gain = 3.0
    cases = [
        ("原图", lut_linear(1.0, 0.0)),
        (f"线性 a={a_gain:g}", lut_linear(a_gain, 0.0)),
        ("对数", lut_log()),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 8.2),
                             gridspec_kw={"height_ratios": [1, 1.25]})
    for col, (name, lut) in enumerate(cases):
        ax = axes[0, col]
        draw_curve(ax, lut, shade=True)
        if col == 1:
            ax.plot(LEVELS, a_gain * LEVELS, color="0.35", lw=0.8, ls=":")
        ax.set_yticks([0, 128, 255])
        title = name if col == 0 else f"{name}\n截断 {clipped_pct(lut, img):.0f}% 像素"
        ax.set_title(title, fontsize=11)
        axes[1, col].imshow(cv2.LUT(img, lut), cmap="gray", vmin=0, vmax=255)
        axes[1, col].axis("off")
    fig.suptitle("同样想看清暗部:线性靠「把亮部推出画面」,对数靠「把亮部挤扁」",
                 fontsize=13)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.93))
    fig.savefig(OUT / "linear-vs-log.png", dpi=110)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for fn in (fig_curves, fig_linear, fig_log, fig_linear_vs_log):
        fn()
    print("已重新生成 intensity-and-grayscale.md 的 4 张配图:")
    for name in ("intensity-transform-curves.png", "linear-transform.png",
                 "log-transform.png", "linear-vs-log.png"):
        print(f"  {(OUT / name).relative_to(REPO)}")

    img = load("camera.png")
    print(f"\n顺带一组实测(camera.png):线性 a=3 截断 "
          f"{clipped_pct(lut_linear(3.0, 0.0), img):.0f}% 的像素,"
          f"对数截断 {clipped_pct(lut_log(), img):.0f}%")

    if "--show" in sys.argv:
        plt.show()


if __name__ == "__main__":
    main()
