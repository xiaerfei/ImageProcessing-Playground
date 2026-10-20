"""41《从症状找原因》摩尔纹案例的复现与开关实验 ——
配合 Documents/数学基础/快速路线/5.从症状找原因.md。

自己造图,复现摩尔纹,再把文档里的开关实验逐个跑一遍:
 1. 复现:波带片(zone plate,越往外条纹越细)缩小到 1/4,最近邻抽点出现假圆环
 2. 开关实验 A:缩小前先低通(INTER_AREA、先高斯模糊再抽点),与「应有的样子」比误差
 3. 开关实验 B:换缩放比例,假纹粗细乱跳;真实纹理的粗细只会按比例变
 4. 开关实验 C:看频谱,细纹的亮点从边缘「折回」到中心附近
 5. 开关实验 D:只在色度里的细纹,4:2:0 式抽点后,亮度完全不变,色度出现粗彩带

两张图:moire-zoneplate.png、moire-evidence.png

用法:
    .venv/bin/python Ch04_Frequency_Domain/41_moire_diagnosis.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import four_questions, use_cjk_font  # noqa: E402

use_cjk_font()
import matplotlib.pyplot as plt  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "Documents" / "数学基础" / "快速路线" / "images"
BLUE, ORA, GREEN, RED, GRAY = "#2c6fbb", "#d98a14", "#2a8f4a", "#c4442a", "#666"
N, K = 512, 4  # 原图边长、缩小倍数


def head(title: str) -> None:
    print(f"\n{'=' * 8} {title} {'=' * 8}")


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=130, bbox_inches="tight", facecolor="white")
    print(f"  → Documents/数学基础/快速路线/images/{name}")
    plt.close(fig)


# ---------------------------------------------------------------- 波带片
KZ = 0.5 / (N / 2)  # 局部频率 = KZ·r(周期/像素),在边缘中点 r=256 处刚好 0.5


def zone(n: int, step: float, cut: float | None = None) -> np.ndarray:
    """在 n×n 网格上采样波带片,每格对应原图 step 个像素;cut 给出时,局部频率超过 cut 的地方置灰(理想低通)。"""
    c = (np.arange(n) + 0.5) * step - N / 2
    x, y = np.meshgrid(c, c)
    r = np.hypot(x, y)
    img = 0.5 + 0.5 * np.cos(np.pi * KZ * r ** 2)
    if cut is not None:
        img = np.where(KZ * r > cut, 0.5, img)
    return img * 255


def rms(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((a - b) ** 2)))


def exp_zoneplate() -> dict:
    head("1~2. 复现摩尔纹;缩小前先低通")
    src = zone(N, 1.0)
    m = N // K
    ideal = zone(m, K, cut=0.5 / K)  # 应有的样子:新网格放得下的条纹保留,放不下的变灰
    nearest = src[K // 2::K, K // 2::K]
    area = cv2.resize(src, (m, m), interpolation=cv2.INTER_AREA)
    blur = cv2.GaussianBlur(src, (0, 0), sigmaX=K * 0.5)[K // 2::K, K // 2::K]
    res = {"原图": src, "应有": ideal, "最近邻": nearest, "INTER_AREA": area, "先高斯再抽点": blur}
    for name in ("最近邻", "INTER_AREA", "先高斯再抽点"):
        print(f"  缩小 1/{K}({name}):与应有样子的 RMS 误差 {rms(res[name], ideal):.1f}(灰度 0~255)")
    r_alias = 0.5 / K / KZ
    print(f"  缩小后放得下的最细条纹:{0.5 / K:.3f} 周期/原像素;对应半径 {r_alias:.0f} 原像素,超出就会折叠")
    return res


def apparent(f: float, k: int) -> float:
    """原图 f 周期/像素的条纹,每 k 个像素抽一个后,在新图里看到的频率(周期/新像素)。"""
    g = f * k
    return abs(g - round(g))


def exp_ratio_and_spectrum() -> dict:
    head("3. 换缩放比例:假纹粗细乱跳")
    f = 0.45
    L = 1200
    n = np.arange(L)
    row = np.cos(2 * np.pi * f * n)
    out = {}
    fr = 0.43  # 换比例实验用 0.43:0.45 恰好在几个比例下折到同一处,看不出「乱跳」
    row_r = np.cos(2 * np.pi * fr * n)
    for k in (2, 3, 4, 5):
        s = row_r[::k]
        S = np.abs(np.fft.rfft(s))
        kk = int(np.argmax(S[1:]) + 1)
        fa = kk / len(s)
        period_new = 1 / fa
        print(f"  每 {k} 点抽 1:测得 {fa:.3f} 周期/新像素(公式 {apparent(fr, k):.3f}),"
              f"假纹周期 {period_new:.2f} 新像素 = {period_new * k:.2f} 原像素")
        out[k] = period_new * k
    print(f"  真实纹理:周期永远是 {1 / fr:.2f} 原像素")

    head("4. 频谱:亮点从边缘折回中心")
    S0 = np.abs(np.fft.rfft(row))
    s2 = row[::2]
    S2 = np.abs(np.fft.rfft(s2))
    f0 = np.argmax(S0[1:]) / L + 1 / L
    f2 = (np.argmax(S2[1:]) + 1) / len(s2)
    print(f"  原图峰在 {f0:.3f} 周期/像素(上限 0.5,靠边);抽点后峰在 {f2:.3f}(靠中心)")
    return dict(periods=out, S0=S0, S2=S2, row=row, s2=s2)


def ycc2rgb(y, cb, cr):
    r = y + 1.402 * (cr - 128)
    g = y - 0.344136 * (cb - 128) - 0.714136 * (cr - 128)
    b = y + 1.772 * (cb - 128)
    return np.clip(np.dstack([r, g, b]), 0, 255) / 255


def exp_chroma() -> dict:
    head("5. 只在色度里的细纹:4:2:0 式抽点")
    H, W = 48, 400
    x = np.arange(W)
    y = np.full((H, W), 128.0)
    cr_row = 128 + 60 * np.cos(2 * np.pi * 0.45 * x)
    cb_row = 128 - 60 * np.cos(2 * np.pi * 0.45 * x)
    cr = np.tile(cr_row, (H, 1))
    cb = np.tile(cb_row, (H, 1))
    # 色度每 2 个像素只留 1 个(最近邻抽点),再复制回原宽度显示;亮度不动
    cr2 = np.repeat(cr[:, ::2], 2, axis=1)
    cb2 = np.repeat(cb[:, ::2], 2, axis=1)
    y_err = np.abs(y - y).max()
    S = np.abs(np.fft.rfft(cr_row[::2] - 128))
    fa = (np.argmax(S[1:]) + 1) / (W // 2)
    print(f"  亮度 Y 最大变化 {y_err:.0f}(灰度图里什么都看不到);色度抽点后出现 {fa:.2f} 周期/新像素的假纹,"
          f"周期 {1 / fa * 2:.0f} 原像素")
    return dict(before=ycc2rgb(y, cb, cr), after=ycc2rgb(y, cb2, cr2), gray=y)


def fig_zoneplate(res: dict) -> None:
    fig, axes = plt.subplots(1, 5, figsize=(16, 4.0))
    ideal = res["应有"]
    items = [("原图", f"① 原图 {N}×{N}\n越往外条纹越细"),
             ("应有", f"② 缩小 1/{K} 应有的样子\n太细处放不下,变灰"),
             ("最近邻", f"③ 最近邻抽点:外圈冒出假圆环\n误差 {rms(res['最近邻'], ideal):.1f}"),
             ("INTER_AREA", f"④ INTER_AREA(先平均再缩)\n误差 {rms(res['INTER_AREA'], ideal):.1f}"),
             ("先高斯再抽点", f"⑤ 先高斯模糊再抽点\n误差 {rms(res['先高斯再抽点'], ideal):.1f}")]
    for ax, (key, title) in zip(axes, items):
        ax.imshow(res[key], cmap="gray", vmin=0, vmax=255, interpolation="nearest")
        ax.set_title(title, fontsize=10)
        ax.axis("off")
    four_questions(
        fig,
        did="造一张越往外越细的波带片,\n用三种方法缩小到 1/4,\n和「应有的样子」比",
        gained="最近邻在外圈冒出原图没有\n的粗圆环(摩尔纹);先低通\n的两种方法误差小得多",
        lost="先低通会让太细的纹理\n直接变灰:细节没了,\n但不会出假纹",
        limit="误差数字只对这张合成图;\n真实照片里纹理方向、\n粗细混杂,判断要看局部",
        better="缩小用 INTER_AREA 或\nlanczos;拍摄端靠光学\n低通滤镜(OLPF)",
        y=0.06, bottom=0.30)
    save(fig, "moire-zoneplate.png")


def fig_evidence(d: dict, ch: dict) -> None:
    fig = plt.figure(figsize=(16, 7.6))
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 0.8], hspace=0.55)
    # ① 条纹抽点前后
    ax = fig.add_subplot(gs[0, 0])
    n = np.arange(60)
    ax.plot(n, d["row"][:60], color="#bbb", lw=1, label="原图细纹(2.22 像素一个周期)")
    ax.plot(n[::2], d["s2"][:30], "o-", color=RED, ms=3.5, lw=1.4, label="每 2 点抽 1:假粗纹")
    ax.set_title("① 抽点后,细纹变成一道粗得多的假纹", fontsize=10.5, loc="left")
    ax.set_xlabel("原像素位置", fontsize=9)
    ax.set_ylim(-1.3, 1.9)
    ax.legend(fontsize=8.5, loc="upper right")
    # ② 频谱折回
    ax = fig.add_subplot(gs[0, 1])
    L = len(d["row"])
    f0 = np.arange(len(d["S0"])) / L
    f2 = np.arange(len(d["S2"])) / len(d["s2"])
    ax.plot(f0, d["S0"] / d["S0"].max(), color=GRAY, lw=1.5, label="原图:峰在 0.45(靠边)")
    ax.plot(f2, d["S2"] / d["S2"].max(), color=RED, lw=1.5, label="抽点后:峰在 0.10(靠中心)")
    ax.annotate("", (0.10, 1.03), (0.45, 1.03), arrowprops=dict(arrowstyle="->", color=RED, lw=1.5))
    ax.text(0.2, 1.08, "折回", color=RED, fontsize=10)
    ax.set_xlim(0, 0.5)
    ax.set_ylim(0, 1.25)
    ax.set_xlabel("频率(周期/像素,0.5 是能表示的上限)", fontsize=9)
    ax.set_title("② 开关实验 C:看频谱,亮点从边缘折回中心", fontsize=10.5, loc="left")
    ax.legend(fontsize=8.5, loc="center right")
    # ③ 换比例
    ax = fig.add_subplot(gs[0, 2])
    ks = list(d["periods"].keys())
    ps = [d["periods"][k] for k in ks]
    ax.bar([str(k) for k in ks], ps, color=RED, width=0.5, label="假纹周期")
    ax.axhline(1 / 0.43, color=GREEN, ls="--", lw=1.5, label="真实纹理周期 2.33")
    for i, p in enumerate(ps):
        ax.text(i, p + 0.4, f"{p:.2f}", ha="center", fontsize=9.5)
    ax.set_xlabel("每 k 个像素抽 1 个", fontsize=9)
    ax.set_ylabel("纹理周期(原像素)", fontsize=9)
    ax.set_ylim(0, 44)
    ax.set_title("③ 开关实验 B:换比例,假纹粗细乱跳\n(0.43 周期/像素的细纹)", fontsize=10.5, loc="left")
    ax.legend(fontsize=8.5, loc="upper left")
    # ④⑤⑥ 色度(只显示前 80 列:整宽缩进图里,细纹自己就会在屏幕上混叠)
    for col, (img, title) in enumerate([
            (ch["gray"][:, :80], "④ 亮度 Y:完全平的,灰度图里看不到任何纹"),
            (ch["before"][:, :80], "⑤ 色度里有 0.45 周期/像素的细彩纹"),
            (ch["after"][:, :80], "⑥ 开关实验 D:色度隔点抽样后变成粗彩带")]):
        ax = fig.add_subplot(gs[1, col])
        if img.ndim == 2:
            ax.imshow(img, cmap="gray", vmin=0, vmax=255, aspect="auto")
        else:
            ax.imshow(img, aspect="auto", interpolation="nearest")
        ax.set_title(title, fontsize=10.5, loc="left")
        ax.axis("off")
    four_questions(
        fig,
        did="对同一组细纹做三个开关实验:\n看频谱、换缩放比例、\n只抽色度",
        gained="频谱上直接看见「折回」;\n假纹粗细随比例乱跳;\n彩色假纹只在色度里",
        lost="每个实验只回答一个问题,\n要几个一起做才能定位",
        limit="真实图像里几种原因可能\n同时存在,要一处一处关掉\n再看症状剩多少",
        better="把处理链每一步的中间\n结果都存下来,逐步对比",
        y=0.04, bottom=0.17)
    save(fig, "moire-evidence.png")


if __name__ == "__main__":
    res = exp_zoneplate()
    d = exp_ratio_and_spectrum()
    ch = exp_chroma()
    fig_zoneplate(res)
    fig_evidence(d, ch)
