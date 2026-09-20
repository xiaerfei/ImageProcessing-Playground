"""直方图规定化(匹配)—— 配合 Documents/03-histogram/06-histogram-matching.md。

均衡化的目标分布固定是「均匀」;规定化的目标分布**由你给**。
做法就一句:两边各算 CDF,对每个源灰度 r,在目标 CDF 里找累计比例最接近的那个 z。

本脚本回答三个问题,并把它们画成 2 张配图:

  1. 它到底怎么算的 —— 手算那张 8 灰度级小图,看清「查 CDF」这一步
  2. 它**做不到**什么 —— 桶不可拆分,离散图像上只能逼近
  3. 最实在的用途 —— 多机位色调对齐,以及「只匹配亮度」够不够

    histogram-matching-steps.png     两条 CDF 怎么配出一张映射表,以及为什么对不准
    histogram-matching-multicam.png  三路不同曝光/白平衡的画面对齐到基准路

用法:
    .venv/bin/python Ch03_Spatial_Filtering/18_histogram_matching.py [--show]
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import IMAGES, four_questions, save, use_cjk_font  # noqa: E402

use_cjk_font()
import cv2  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402


def cdf_of(hist: np.ndarray) -> np.ndarray:
    """归一化直方图 → CDF。总数为 0 时返回全 0,避免除零。"""
    total = hist.sum()
    return np.cumsum(hist) / total if total else np.zeros_like(hist, float)


def match_lut(src_hist: np.ndarray, ref_hist: np.ndarray) -> np.ndarray:
    """由两个直方图配出映射表 LUT[r] = z。

    规则:对每个源灰度 r,在目标 CDF 里找**累计比例最接近**的 z,并列时取小的那个。

    ⚠️ 这里有个容易踩的分歧。另一种常见写法是
        z = np.searchsorted(ref_cdf, src_cdf)
    它找的是「**第一个不小于**」,不是「最接近」,两者在并列处会给出不同答案。
    文档那张手算表里源灰度 5 就是个例子:源 CDF = 0.95,目标 CDF 里
    0.90 和 1.00 与它距离相等 —— 「最接近」取 z=6,searchsorted 取 z=7。
    两种都有人用,但**必须和你文档/测试里写的规则一致**,否则对不上账。
    """
    s, g = cdf_of(src_hist), cdf_of(ref_hist)
    z = np.abs(s[:, None] - g[None, :]).argmin(axis=1)   # 并列时 argmin 取靠左的
    return z.astype(np.uint8)


def hist_of(img: np.ndarray, levels: int = 256) -> np.ndarray:
    return np.bincount(img.ravel(), minlength=levels).astype(np.int64)


# ═══════════════════════════════════ 图 1:它怎么算,又差在哪 ═════════════


def fig_steps() -> None:
    """用 04-equalization.md 里那张同样的 8 灰度级小图,把三步拆开看。

    重点不是「怎么算」(三行代码而已),是**为什么算完对不准** ——
    源图灰度 4 那 40 个像素是一个不可分割的整体,只能整体搬到某一个 z。
    """
    src = np.array([0, 0, 5, 30, 40, 20, 5, 0], np.int64)        # 挤在中间
    ref = np.array([10, 15, 15, 10, 10, 15, 15, 10], np.int64)   # 想要的形状
    L = len(src)
    s_cdf, r_cdf = cdf_of(src), cdf_of(ref)
    lut = np.abs(s_cdf[:, None] - r_cdf[None, :]).argmin(axis=1)   # 同 match_lut 的规则

    out = np.zeros(L, np.int64)                                   # 套用映射表后的实际分布
    for r, n in enumerate(src):
        out[lut[r]] += n

    fig = plt.figure(figsize=(13.4, 4.3))
    gs = fig.add_gridspec(1, 4, wspace=0.3)

    # ── ① 两个直方图
    ax = fig.add_subplot(gs[0])
    x = np.arange(L)
    ax.bar(x - 0.2, src / src.sum() * 100, 0.4, color="#2c6fbb", label="源图(挤在中间)")
    ax.bar(x + 0.2, ref / ref.sum() * 100, 0.4, color="#2a8f4a", label="想要的形状")
    ax.set_xlabel("灰度"); ax.set_ylabel("占比(%)")
    ax.legend(fontsize=8.4)
    ax.set_title("① 两个直方图\n一个是现状,一个是目标", fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)

    # ── ② 两条 CDF + 怎么查
    ax = fig.add_subplot(gs[1])
    ax.step(x, s_cdf, where="mid", lw=2, color="#2c6fbb", label="源 CDF")
    ax.step(x, r_cdf, where="mid", lw=2, color="#2a8f4a", label="目标 CDF")
    r0 = 4                                            # 拿灰度 4 当例子
    ax.plot([0, r0], [s_cdf[r0]] * 2, ls=":", color="#c4442a", lw=1.4)
    ax.plot([lut[r0]] * 2, [0, s_cdf[r0]], ls=":", color="#c4442a", lw=1.4)
    ax.plot(r0, s_cdf[r0], "o", color="#2c6fbb", ms=7)
    ax.plot(lut[r0], s_cdf[r0], "o", color="#2a8f4a", ms=7)
    ax.annotate(f"源灰度 {r0} 的累计比例 {s_cdf[r0]:.2f}\n"
                f"在目标 CDF 上落到 z={lut[r0]}",
                (lut[r0], s_cdf[r0]), textcoords="offset points", xytext=(-95, -44),
                fontsize=8.4, color="#c4442a",
                arrowprops=dict(arrowstyle="->", color="#c4442a"))
    ax.set_xlabel("灰度"); ax.set_ylabel("累计比例")
    ax.legend(fontsize=8.4, loc="lower right")
    ax.set_title("② 横着查过去\n这就是全部的算法", fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)

    # ── ③ 映射表
    ax = fig.add_subplot(gs[2])
    ax.step(x, lut, where="mid", lw=2, color="#c4442a")
    ax.plot(x, lut, "o", color="#c4442a", ms=5)
    for r in x:
        ax.annotate(str(lut[r]), (r, lut[r]), textcoords="offset points",
                    xytext=(0, 7), ha="center", fontsize=8)
    ax.set_xlabel("原灰度 r"); ax.set_ylabel("新灰度 z")
    ax.set_ylim(-0.6, L)
    ax.set_title(f"③ 映射表\n{lut.tolist()}", fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)

    # ── ④ 结果 vs 目标:差在哪
    ax = fig.add_subplot(gs[3])
    ax.bar(x - 0.2, out / out.sum() * 100, 0.4, color="#c4442a", label="实际结果")
    ax.bar(x + 0.2, ref / ref.sum() * 100, 0.4, color="#2a8f4a", label="想要的形状")
    ax.set_xlabel("灰度"); ax.set_ylabel("占比(%)")
    ax.legend(fontsize=8.4)
    ax.set_title("④ 对不准,而且差得挺远\n不是算错了 —— 桶拆不开", fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)

    fig.suptitle("直方图规定化:两条 CDF 横着一查,就是一张映射表", fontsize=13, y=1.03)
    four_questions(fig,
        "源图和目标各算一条 CDF,\n对每个源灰度 r,\n在目标 CDF 里找累计比例\n最接近的那个 z。",
        "目标分布**由你给**,\n不再固定是「均匀」。\n均衡化只是它的特例 ——\n把目标直方图设成平的。",
        f"精度。源灰度 4 的那 {src[4]} 个像素\n"
        "是一个不可分割的整体,\n只能整体搬到某一个 z。\n"
        "目标想要「15% 在 z=1、\n15% 在 z=2」,源图根本\n没有能拆出 15% 的桶。",
        "桶越少、分布越集中,\n偏差越大 —— 这张 8 级小图\n几乎面目全非。真实照片\n256 级、几百万像素,\n效果好得多,但原理上的\n偏差始终存在。",
        y=-0.03, bottom=0.14)
    save(fig, "histogram-matching-steps.png")
    print("  小图实测:")
    print(f"    源     {(src / src.sum() * 100).round(0).astype(int).tolist()}")
    print(f"    目标   {(ref / ref.sum() * 100).round(0).astype(int).tolist()}")
    print(f"    映射表 {lut.tolist()}")
    print(f"    结果   {(out / out.sum() * 100).round(0).astype(int).tolist()}")


# ═══════════════════════════════════ 图 2:多机位色调对齐 ═══════════════


def fig_multicam() -> None:
    """最实在的用途。顺带回答一个文档里说得太简单的问题:只匹配亮度够不够。

    结论(实测):**看你要修的是什么**。
      · 曝光差异 → 只匹配 Y 就够,而且不会动颜色
      · 白平衡差异 → 只匹配 Y 修不了,必须逐通道匹配
    所以「只动亮度通道」这条规矩对**均衡化**成立(那是单张图自增强),
    对**跨机位对齐**要分情况。
    """
    base = cv2.imread(str(IMAGES / "coffee.png"))
    h, w = base.shape[:2]

    def cam(gain_b, gain_g, gain_r, bias):
        """模拟另一台机器:三通道增益不同(白平衡偏)+ 整体偏移(曝光偏)。"""
        f = base.astype(float) * np.array([gain_b, gain_g, gain_r]) + bias
        return np.clip(f, 0, 255).astype(np.uint8)

    dark = cam(1, 1, 1, -45)
    blue = cam(1.35, 1.0, 0.72, 0)
    # 压暗把一部分暗部直接压到 0,那些信息是**真没了**,匹配也变不回来 —— 见四问
    crushed = ((base.astype(float) - 45) < 0).mean()
    cams = [("基准路", base), ("第 2 路:曝光偏暗", dark), ("第 3 路:白平衡偏蓝", blue)]

    def match_y_only(img, ref):
        """只对亮度通道做匹配,色度原样保留。"""
        a = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
        b = cv2.cvtColor(ref, cv2.COLOR_BGR2YCrCb)
        a[..., 0] = match_lut(hist_of(a[..., 0]), hist_of(b[..., 0]))[a[..., 0]]
        return cv2.cvtColor(a, cv2.COLOR_YCrCb2BGR)

    def match_per_channel(img, ref):
        """三个通道各自匹配。能修白平衡,代价见四问。"""
        out = img.copy()
        for c in range(3):
            out[..., c] = match_lut(hist_of(img[..., c]), hist_of(ref[..., c]))[img[..., c]]
        return out

    def dist(img):
        """和基准路差多少:三通道直方图的总变差距离(%),0 = 逐桶完全相同。"""
        d = 0.0
        for c in range(3):
            d += np.abs(hist_of(img[..., c]) / (h * w) - hist_of(base[..., c]) / (h * w)).sum()
        return d / 3 * 100

    fig = plt.figure(figsize=(13.4, 5.6))
    gs = fig.add_gridspec(2, 4, hspace=0.42, wspace=0.08)
    rows = []
    for i, (name, img) in enumerate(cams[1:]):
        y_only = match_y_only(img, base)
        per_ch = match_per_channel(img, base)
        rows.append((name, dist(img), dist(y_only), dist(per_ch)))
        for j, (d, title) in enumerate([
                (base, "基准路(每行都放一份便于对照)"),
                (img, f"{name}\n与基准差 {dist(img):.1f}"),
                (y_only, f"只匹配亮度 Y\n差 {dist(y_only):.1f}"),
                (per_ch, f"逐通道匹配\n差 {dist(per_ch):.1f}")]):
            ax = fig.add_subplot(gs[i, j])
            ax.imshow(cv2.cvtColor(d, cv2.COLOR_BGR2RGB))
            ax.set_title(title, fontsize=9.6)
            ax.axis("off")

    fig.suptitle("多机位色调对齐 —— 选一路作基准,其余各路对它做直方图匹配",
                 fontsize=13, y=0.97)
    exposure, wb = rows[0], rows[1]
    four_questions(fig,
        "选一路当基准,\n其余各路把自己的直方图\n匹配成基准的样子。",
        f"曝光差异能修:第 2 路与基准的差\n{exposure[1]:.1f} → {exposure[2]:.1f}(只匹配 Y),\n"
        "而且完全没碰色度通道,\n不会引入偏色。",
        f"白平衡差异只匹配 Y 修不了:\n第 3 路 {wb[1]:.1f} → {wb[2]:.1f},\n"
        f"不降反升 —— 偏色在色度通道里,\n动 Y 等于隔靴搔痒。\n"
        f"逐通道能压到 {wb[3]:.1f},代价是\n各自改变三通道的比例关系。",
        f"丢掉的信息变不回来。压暗 45\n把 {crushed:.0%} 的像素压到了 0,\n"
        f"那些层次是真没了,所以第 2 路\n只能降到 {exposure[2]:.1f} 而不是 0。\n"
        "另外逐帧独立做会闪烁\n(和 CLAHE 同一个病),要在\n时间上平滑映射表。",
        y=0.0, bottom=0.06)
    save(fig, "histogram-matching-multicam.png")
    print("  多机位实测(与基准路的直方图差,越小越像):")
    for name, d0, dy, dc in rows:
        print(f"    {name:<16} 原始 {d0:6.1f}  只匹配 Y {dy:6.1f}  逐通道 {dc:6.1f}")


if __name__ == "__main__":
    fig_steps()
    fig_multicam()
    if "--show" in sys.argv:
        plt.show()
