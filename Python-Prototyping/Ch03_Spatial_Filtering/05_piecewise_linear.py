"""第 4 周(3.2 节):灰度变换 —— 05 分段线性:分区间各管各的。

对应文档 Documents/02-intensity/02-gray-transform-tutorial.md 第四节 4.1 / 4.2。

前面四种都是**一个公式管全图**。分段线性把 0~255 切成几段,每段用不同的
(a, b) —— 所以它不是新公式,只是把 01 篇那条 s = a·r + b 分段用了而已。
灵活的代价是转折点得自己定。

本篇做两件事:
    4.1 对比度拉伸  把感兴趣的那一段拉满 0~255,两头压掉
    4.2 灰度级分层  只把某个亮度区间挑出来(工业检测找缺陷的典型手法)

4.3 比特平面是另一套机制(拆二进制位,不是分段映射),留给 06 篇;
阈值化是本篇的退化情形,留给 07 篇,这里只验证「退化」这件事本身。

验证七件事:
1. 三段折线就是三组 (a, b):打印每段的斜率与截距,转折点处首尾相接不断开
2. 拉伸效果:moon.png 的 1%~99% 只跨 83 个灰阶(灰蒙蒙),拉伸后铺满
3. ⚠️ 代价:中间拉开 = 两头压平,被压平的灰阶数与丢掉的像素占比
4. ⚠️ 梳齿:拉伸只能把已有灰度级摊开,不能凭空造中间级,直方图会出现缝隙
5. 转折点怎么选:手工指定 vs 按百分位自动选(1%/99%,即「自动色阶」的做法)
6. r1 = r2 时中间段变垂直,退化成阈值化 —— 与 cv2.threshold 逐像素比对
7. 灰度级分层两种做法:A 二值突出(背景全丢)、B 保留背景(压成一片中灰)

用法:
    .venv/bin/python Ch03_Spatial_Filtering/05_piecewise_linear.py [--show]
    结果图保存到 Assets/results/piecewise-linear-demo.png(对比度拉伸)
                     Assets/results/gray-slicing-demo.png(灰度级分层)
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
matplotlib.rcParams["font.family"] = ["Heiti TC", "Arial Unicode MS", "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False

LEVELS = np.arange(256)


def stretch_lut(r1: float, s1: float, r2: float, s2: float) -> npt.NDArray[np.uint8]:
    """三段折线:[0,r1] → [0,s1],[r1,r2] → [s1,s2],[r2,255] → [s2,255]。

    用 np.interp 而不是三个 if 分支:转折点处两段共用同一个端点,
    天然首尾相接,不会因为边界写成 < 还是 <= 而差一个灰阶。
    r1 == r2 时 np.interp 在该点直接跳变,正好退化成阈值化,不用特判。
    """
    s = np.interp(LEVELS, [0.0, r1, r2, 255.0], [0.0, s1, s2, 255.0])
    return np.clip(np.rint(s), 0, 255).astype(np.uint8)


def segment_params(r1: float, s1: float, r2: float, s2: float) -> list[tuple]:
    """把三段折线还原成三组 (区间, a, b) —— 证明它就是分段用的 s = a·r + b。"""
    pts = [(0.0, 0.0, r1, s1), (r1, s1, r2, s2), (r2, s2, 255.0, 255.0)]
    out = []
    for x0, y0, x1, y1 in pts:
        a = (y1 - y0) / (x1 - x0) if x1 != x0 else float("inf")
        out.append((f"[{x0:.0f}, {x1:.0f}]", a, y0 - a * x0 if np.isfinite(a) else float("nan")))
    return out


def histogram(y: npt.NDArray[np.uint8]) -> npt.NDArray[np.int64]:
    """0~255 每个灰阶的像素个数。用 bincount 避免分 bin 时的边界错位。"""
    return np.bincount(y.ravel(), minlength=256)


def flattened_ratio(lut: npt.NDArray[np.uint8],
                    hist: npt.NDArray[np.int64]) -> tuple[int, float]:
    """这条 LUT 压平了多少个输入灰阶,以及落在这些灰阶上的像素占比。

    「压平」= 相邻输入映射到同一个输出。这是分段线性真正的代价:
    不像线性那样拍在 0/255 上显眼,它是在两端悄悄把层次抹平。
    """
    flat = np.zeros(256, dtype=bool)
    same = lut[1:] == lut[:-1]
    flat[1:] |= same
    flat[:-1] |= same
    return int(flat.sum()), float(hist[flat].sum() / hist.sum())


def load_gray(name: str) -> npt.NDArray[np.uint8]:
    img = cv2.imread(str(REPO / "Assets" / "test-images" / name), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise SystemExit(f"读图失败: {name}")
    return np.asarray(img, dtype=np.uint8)


def save_slicing_demo(out_path: Path) -> None:
    """4.2 灰度级分层:只把某个亮度区间挑出来,两种做法并排。"""
    img = load_gray("coins.png")
    hist = histogram(img)
    # 硬币比背景亮,取 150 以上这一段。
    # 但这张图打光不均(右上角背景比左下角的硬币还亮),所以必然会误伤 ——
    # 这正是灰度级分层的固有局限:它只看像素值,不看位置。留着不修,见 ⑦ 的输出。
    low, high = 150, 255
    mask = (img >= low) & (img <= high)

    out_a = np.where(mask, 255, 0).astype(np.uint8)          # 二值突出
    out_b = img.copy()
    # 方法 B 的 //3 + 50 没有玄机:把不关心的部分压进 50~135 这个窄范围,
    # 压成一片不刺眼的中灰,目标才显眼,同时还看得见背景在哪。
    out_b[~mask] = out_b[~mask] // 3 + 50

    print("\n--- ⑦ 灰度级分层:只挑 "
          f"[{low}, {high}] 这一段 ---")
    print(f"  命中像素 {int(mask.sum())} 个 = {100 * mask.mean():.1f}%")
    print(f"  方法 A(二值)  输出只剩 {len(np.unique(out_a))} 个值 —— 背景信息全丢")
    print(f"  方法 B(保背景)输出还有 {len(np.unique(out_b))} 个值,"
          f"未命中区被压进 [{int(out_b[~mask].min())}, {int(out_b[~mask].max())}]")
    # 量化「误伤」:右上角那片背景比左下角的硬币还亮,阈值挡不住
    top_right = mask[:mask.shape[0] // 3, -mask.shape[1] // 3:]
    print(f"  ⚠️ 局限:右上角那片纯背景里也有 {100 * top_right.mean():.0f}% 被选中 ——")
    print("     打光不均时,同一个亮度阈值在画面各处的含义不一样。")
    print("     灰度级分层只看像素值、不看位置,这是点运算的天花板;")
    print("     要按局部判断,得上自适应阈值或 CLAHE(见 13_clahe_walkthrough.py)")

    fig, axes = plt.subplots(1, 4, figsize=(17, 4.6))
    for ax, (pic, title) in zip(axes[:3], (
            (img, "原图 coins.png"),
            (out_a, f"方法 A:[{low},{high}] 变白,其余变黑\n干脆,但背景全丢"),
            (out_b, f"方法 B:[{low},{high}] 原样保留,其余压暗压平\n柔和,还看得见背景"))):
        ax.imshow(pic, cmap="gray", vmin=0, vmax=255)
        ax.set_title(title, fontsize=10)
        ax.axis("off")

    ax = axes[3]
    ax.fill_between(LEVELS, hist, color="0.72", zorder=2)
    ax.axvspan(low, high, color="tab:orange", alpha=0.25, zorder=1, label="被挑出的区间")
    ax.set_xlim(0, 255); ax.set_ylim(0, float(hist.max()) * 1.1)
    ax.set_title("选区间就是在直方图上划一刀", fontsize=10)
    ax.set_xlabel("灰阶"); ax.legend(fontsize=8)

    fig.suptitle("灰度级分层:只关心某个亮度区间(工业检测找缺陷的典型手法)", fontsize=12)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.92))
    fig.savefig(out_path, dpi=110)


def main() -> None:
    img = load_gray("moon.png")
    hist = histogram(img)
    p1, p99 = np.percentile(img, [1, 99])
    print(f"原图 moon.png  shape={img.shape}  均值 {img.mean():.1f}  "
          f"标准差 {img.std():.1f}")
    print(f"  1%~99% 只跨 [{p1:.0f}, {p99:.0f}] = {p99 - p1:.0f} 个灰阶 —— 典型的灰蒙蒙")

    R1, S1, R2, S2 = 70.0, 0.0, 145.0, 255.0
    lut = stretch_lut(R1, S1, R2, S2)
    out = np.asarray(cv2.LUT(img, lut), dtype=np.uint8)

    # --- ① 三段折线 = 三组 (a, b) ---
    print(f"\n--- ① 分段线性不是新公式,是分段用 s = a·r + b ---")
    print(f"  转折点 (r1,s1)=({R1:.0f},{S1:.0f})  (r2,s2)=({R2:.0f},{S2:.0f})")
    for rng, a, b in segment_params(R1, S1, R2, S2):
        print(f"  {rng:<12s} a={a:6.2f}  b={b:8.2f}")
    joints_ok = int(lut[int(R1)]) == int(round(S1)) and int(lut[int(R2)]) == int(round(S2))
    print(f"  转折点处首尾相接(不断开): {joints_ok}")
    print(f"  单调递增: {bool(np.all(np.diff(lut.astype(np.int16)) >= 0))}")

    # --- ② 拉伸效果 ---
    q1, q99 = np.percentile(out, [1, 99])
    print("\n--- ② 拉伸效果 ---")
    print(f"  {'':10s}{'标准差':>8s}{'1%~99% 跨度':>14s}{'用到的灰阶数':>14s}")
    print(f"  原图      {img.std():>8.1f}{p99 - p1:>14.0f}{len(np.unique(img)):>14d}")
    print(f"  拉伸后    {out.std():>8.1f}{q99 - q1:>14.0f}{len(np.unique(out)):>14d}")
    print(f"  对比度(标准差)涨到 {out.std() / img.std():.1f} 倍")

    # --- ③ 代价:两头被压平 ---
    n_flat, ratio = flattened_ratio(lut, hist)
    print("\n--- ③ 中间拉开的代价:两头被压平 ---")
    print(f"  256 个输入灰阶里,有 {n_flat} 个被压进了相邻值(层次没了)")
    print(f"  落在这些灰阶上的像素占 {100 * ratio:.1f}%")
    print(f"  纯黑像素 {int(hist[0])} → {int(histogram(out)[0])}   "
          f"纯白像素 {int(hist[255])} → {int(histogram(out)[255])}")
    print("  拉伸不是免费的:r1 以下全压成 0、r2 以上全压成 255,这部分不可逆")

    # --- ④ 梳齿 ---
    ho = histogram(out)
    empty_before = int(np.count_nonzero(hist[1:255] == 0))
    empty_after = int(np.count_nonzero(ho[1:255] == 0))
    print("\n--- ④ 梳齿:拉开之后中间空出一格格 ---")
    print(f"  1~254 里空着的灰阶:原图 {empty_before} 个 → 拉伸后 {empty_after} 个")
    print("  点运算只能把已有灰度级摊开,不能凭空造出中间级 —— 和 01 篇 a>1 时一个道理")

    # --- ⑤ 转折点怎么选 ---
    auto = stretch_lut(float(p1), 0.0, float(p99), 255.0)
    out_auto = np.asarray(cv2.LUT(img, auto), dtype=np.uint8)
    print("\n--- ⑤ 转折点:手工指定 vs 按百分位自动选 ---")
    print(f"  手工 [{R1:.0f}, {R2:.0f}]      标准差 {out.std():.1f}  "
          f"压平灰阶 {flattened_ratio(lut, hist)[0]}")
    print(f"  自动 [{p1:.0f}, {p99:.0f}](1%/99%) 标准差 {out_auto.std():.1f}  "
          f"压平灰阶 {flattened_ratio(auto, hist)[0]}")
    print("  自动色阶就是这么干的:按百分位取转折点,故意扔掉两端各 1% 的极值,")
    print("  免得几个噪点把整个区间撑开(详见 Documents/03-histogram/03-contrast.md)")

    # --- ⑥ r1 = r2 退化成阈值化 ---
    T = 112
    degenerate = stretch_lut(float(T), 0.0, float(T), 255.0)
    mine = np.asarray(cv2.LUT(img, degenerate), dtype=np.uint8)
    _, ref = cv2.threshold(img, T - 1, 255, cv2.THRESH_BINARY)
    print("\n--- ⑥ r1 = r2 时中间段变垂直,退化成阈值化 ---")
    print(f"  取 r1 = r2 = {T}:LUT 里只剩 {len(np.unique(degenerate))} 个不同值 "
          f"{np.unique(degenerate).tolist()}")
    print(f"  与 cv2.threshold(阈值 {T - 1}, BINARY) 逐像素相同: "
          f"{np.array_equal(mine, ref)}")
    print("  所以阈值化不是另一种方法,是分段线性中间段斜率 → ∞ 的极限")

    # --- 图板一:对比度拉伸 ---
    fig, axes = plt.subplots(2, 3, figsize=(15.5, 9))
    for ax, (pic, title) in zip(axes[0], (
            (img, f"原图 moon.png\n标准差 {img.std():.1f},层次全挤在中间"),
            (out, f"拉伸 [{R1:.0f},{R2:.0f}] → [0,255]\n标准差 {out.std():.1f}"),
            (mine, f"r1=r2={T} 的退化情形\n= 阈值化"))):
        ax.imshow(pic, cmap="gray", vmin=0, vmax=255)
        ax.set_title(title, fontsize=10)
        ax.axis("off")

    ax = axes[1, 0]
    ax.plot([0, 255], [0, 255], color="0.75", lw=1.0, ls="--", label="不变")
    ax.plot(LEVELS, lut, color="tab:red", lw=2.0, label=f"手工 [{R1:.0f},{R2:.0f}]")
    ax.plot(LEVELS, auto, color="tab:blue", lw=1.3, ls="-.",
            label=f"自动 [{p1:.0f},{p99:.0f}]")
    ax.plot([R1, R2], [S1, S2], "o", color="tab:red", ms=6)
    ax.set_xlim(0, 255); ax.set_ylim(0, 255); ax.set_aspect("equal")
    ax.set_title("三段折线:中间陡(拉开),两头平(压掉)", fontsize=10)
    ax.set_xlabel("输入 r"); ax.set_ylabel("输出 s")
    ax.legend(fontsize=8, loc="upper left")

    ax = axes[1, 1]
    ax.fill_between(LEVELS, hist, color="0.72", label="原图:挤成一坨", zorder=2)
    ax.plot(LEVELS, ho, color="tab:red", lw=1.1, label="拉伸后:摊开(带梳齿)", zorder=3)
    ax.axvline(R1, color="0.45", lw=0.9, ls=":")
    ax.axvline(R2, color="0.45", lw=0.9, ls=":")
    ax.set_xlim(0, 255)
    ax.set_ylim(0, float(max(hist.max(), ho.max())) * 1.05)
    ax.set_title(f"直方图:原来只占 83 级,拉伸后铺满\n中间空出 {empty_after} 个灰阶",
                 fontsize=10)
    ax.set_xlabel("灰阶"); ax.legend(fontsize=8, loc="upper right")

    # 扫描区间宽度:窄 = 对比度高但压平多,这就是那个取舍
    ax = axes[1, 2]
    centre = (R1 + R2) / 2
    widths = np.arange(20, 231, 10)
    stds, flats = [], []
    for w in widths:
        lo, hi = max(0.0, centre - w / 2), min(255.0, centre + w / 2)
        lu = stretch_lut(lo, 0.0, hi, 255.0)
        stds.append(float(cv2.LUT(img, lu).std()))
        flats.append(100 * flattened_ratio(lu, hist)[1])
    ax.plot(widths, stds, color="tab:blue", lw=1.8, label="对比度(标准差)")
    ax.plot(widths, flats, color="tab:red", lw=1.8, label="被压平的像素 %")
    ax.axvline(R2 - R1, color="0.5", lw=0.9, ls="--")
    ax.set_xlabel("拉伸区间宽度"); ax.set_title("取舍:区间越窄对比越强,压平也越多",
                                                fontsize=10)
    ax.grid(alpha=0.3); ax.legend(fontsize=8)

    fig.tight_layout()
    out_path = REPO / "Assets" / "results" / "piecewise-linear-demo.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110)
    print(f"\n结果已保存: {out_path.relative_to(REPO)}")

    # --- 图板二:灰度级分层 ---
    slicing = out_path.with_name("gray-slicing-demo.png")
    save_slicing_demo(slicing)
    print(f"结果已保存: {slicing.relative_to(REPO)}")

    if "--show" in sys.argv:
        plt.show()


if __name__ == "__main__":
    main()
