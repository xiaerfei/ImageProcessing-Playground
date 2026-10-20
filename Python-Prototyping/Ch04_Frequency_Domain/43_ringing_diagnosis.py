"""43《从症状找原因》振铃案例的复现与开关实验 ——
配合 Documents/数学基础/快速路线/5.从症状找原因.md 第三节。

振铃:锐利边缘旁边出现一圈圈和边缘平行的明暗波纹。本脚本:
 1. 复现:白方块做频域理想低通(一刀切)→ 边缘外一圈圈波纹;换成高斯低通 → 没有
 2. 开关实验 A:改截止频率 —— 一刀切的「冲过头」始终约 9%,只是波纹间距跟着变
 3. 开关实验 B:数波纹几圈,区分四种来源:
      一刀切低通(多圈、等间距)/ 锐化过度(一亮一暗一对)/
      lanczos 放大(1~2 圈、很小)/ JPEG 压缩(杂乱,只在含边缘的 8×8 块里)
 4. 开关实验 C:JPEG 的误差集中在含边缘的 8×8 块里

两张图:ringing-cause.png、ringing-sources.png

用法:
    .venv/bin/python Ch04_Frequency_Domain/43_ringing_diagnosis.py
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
BLUE, ORA, GREEN, RED, PURPLE, GRAY = "#2c6fbb", "#d98a14", "#2a8f4a", "#c4442a", "#6b4fa8", "#666"
N = 256
LO, HI = 40.0, 200.0  # 方块外 / 方块内的灰度


def head(title: str) -> None:
    print(f"\n{'=' * 8} {title} {'=' * 8}")


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=130, bbox_inches="tight", facecolor="white")
    print(f"  → Documents/数学基础/快速路线/images/{name}")
    plt.close(fig)


def square() -> np.ndarray:
    a = np.full((N, N), LO)
    # 边缘放在 8×8 块的中间(84 = 10×8 + 4),否则 JPEG 的块边界正好对齐边缘,看不出压缩振铃
    a[84:180, 84:180] = HI
    return a


def edge_at(row: np.ndarray) -> int:
    """左边缘位置:第一次越过台阶中点的地方。"""
    return int(np.argmax(row > (LO + HI) / 2))


def freq_lp(img: np.ndarray, r: float, gauss: bool) -> np.ndarray:
    F = np.fft.fftshift(np.fft.fft2(img))
    yy, xx = np.mgrid[:N, :N]
    d2 = (yy - N // 2) ** 2 + (xx - N // 2) ** 2
    m = np.exp(-d2 / (2 * r * r)) if gauss else (d2 <= r * r).astype(float)
    return np.fft.ifft2(np.fft.ifftshift(F * m)).real


def overshoot(row: np.ndarray, lo: float = LO, hi: float = HI) -> float:
    """冲过头多少:超过亮侧或低于暗侧的最大量,占台阶高度的百分比。"""
    return float(max(row.max() - hi, lo - row.min()) / (hi - lo) * 100)


def lobes(side: np.ndarray, level: float, height: float, thr: float = 0.01) -> int:
    """在边缘外侧的平坦区里,数偏离 level 超过台阶高度 thr 的「鼓包」个数(正负交替算不同的包)。"""
    dev = side - level
    big = np.abs(dev) > thr * height
    count, prev = 0, 0
    for d, b in zip(dev, big):
        s = (1 if d > 0 else -1) if b else 0
        if s != 0 and s != prev:
            count += 1
        if s != 0:
            prev = s
    return count


def reach(side: np.ndarray, level: float, height: float, thr: float = 0.01) -> int:
    """波纹延伸多远:离边缘最远的、偏离超过台阶高度 thr 的像素,距边缘几个像素(side 从边缘往外排)。"""
    idx = np.nonzero(np.abs(side - level) > thr * height)[0]
    return int(idx.max()) + 3 if idx.size else 0


def gibbs_1d() -> list:
    head("2. 改截止频率:冲过头始终约 9%,波纹间距跟着变")
    L = 2048
    x = np.zeros(L)
    x[L // 4:3 * L // 4] = 1.0
    X = np.fft.fft(x)
    k = np.fft.fftfreq(L) * L
    rows = []
    for kc in (16, 32, 64, 128):
        y = np.fft.ifft(X * (np.abs(k) <= kc)).real
        ov = (y.max() - 1) * 100
        seg = y[L // 4 - 10:L // 4 + 6 * L // kc]  # 边缘里侧前几个周期(往外多取 10 点,免得漏掉第一个峰)
        peaks = [i for i in range(1, seg.size - 1) if seg[i] > seg[i - 1] and seg[i] >= seg[i + 1]]
        spacing = peaks[1] - peaks[0] if len(peaks) > 1 else float("nan")
        print(f"  只留最低 {kc:3d} 个频率(截止 {kc / L:.4f} 周期/像素):冲过头 {ov:.2f}%,"
              f"波纹间距 {spacing} 像素(1/截止 = {L / kc:.0f})")
        rows.append((kc, ov, spacing, y))
    return rows


def main() -> None:
    sq = square()
    head("1. 白方块:一刀切 vs 高斯")
    ideal = freq_lp(sq, 15, gauss=False)
    gau = freq_lp(sq, 15, gauss=True)
    rI, rG = ideal[N // 2], gau[N // 2]
    print(f"  一刀切(半径 15):冲过头 {overshoot(rI):.1f}%;高斯(σ=15):冲过头 {overshoot(rG):.2f}%")
    e = edge_at(sq[N // 2])
    print(f"  左边缘外侧 40 像素里的波纹个数:一刀切 {lobes(rI[e - 40:e - 3][::-1], LO, HI - LO)},"
          f"高斯 {lobes(rG[e - 40:e - 3][::-1], LO, HI - LO)}")
    rows = gibbs_1d()

    head("3. 四种来源,数波纹")
    # 锐化过度:USM,amount 1.5,σ 2
    blur = cv2.GaussianBlur(sq, (0, 0), 2.0)
    usm = sq + 1.5 * (sq - blur)
    # lanczos 放大:32×32 的方块图放大 8 倍
    small = np.full((32, 32), LO)
    small[10:22, 10:22] = HI
    lan = cv2.resize(small, (N, N), interpolation=cv2.INTER_LANCZOS4)
    lin = cv2.resize(small, (N, N), interpolation=cv2.INTER_LINEAR)
    # JPEG 质量 20
    ok, buf = cv2.imencode(".jpg", sq.astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 20])
    jpg = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE).astype(float)
    srcs = {"一刀切低通": (ideal, sq), "锐化过度(USM)": (usm, sq), "lanczos 放大": (lan, None), "JPEG 质量 20": (jpg, sq)}
    stats = {}
    for name, (img, _) in srcs.items():
        row = img[N // 2]
        edge = edge_at(row)
        side = row[edge - 60:edge - 3][::-1]  # 边缘外侧(暗区)60 像素,离边缘 3 像素以内是过渡带,不算
        level = float(np.median(row[edge - 70:edge - 50]))  # 暗区自己的平均灰度(JPEG 会让整块整体偏一点)
        n_l = lobes(side, level, HI - LO)
        ov = overshoot(row)
        far = reach(side, level, HI - LO)
        stats[name] = (ov, n_l, far)
        print(f"  {name:14s}:冲过头 {ov:5.1f}%,边缘外侧波纹 {n_l} 个,延伸到离边缘 {far} 像素")
    print(f"  对照:双线性放大冲过头 {overshoot(lin[N // 2]):.2f}%(不振铃)")

    head("4. JPEG:误差集中在含边缘的 8×8 块")
    err = np.abs(jpg - sq)
    gy, gx = np.gradient(sq)
    edge_px = (np.abs(gx) + np.abs(gy)) > 0
    blk_edge = edge_px.reshape(N // 8, 8, N // 8, 8).any(axis=(1, 3))
    blk_err = (err ** 2).reshape(N // 8, 8, N // 8, 8).sum(axis=(1, 3))
    frac_blocks = blk_edge.mean()
    frac_err = blk_err[blk_edge].sum() / blk_err.sum()
    print(f"  含边缘的块占 {frac_blocks * 100:.1f}%,却装了 {frac_err * 100:.1f}% 的误差能量")
    stats["jpeg_frac"] = (frac_blocks, frac_err)

    # ---------------- 图 1
    fig = plt.figure(figsize=(15.5, 4.3))
    gs = fig.add_gridspec(1, 4, width_ratios=[1, 1, 1.5, 1.3])
    for i, (img, t) in enumerate([(ideal, f"① 一刀切低通(半径 15)\n方块外一圈圈波纹"), (gau, "② 高斯低通(σ=15)\n只是变糊,没有波纹")]):
        ax = fig.add_subplot(gs[i])
        ax.imshow(img, cmap="gray", vmin=0, vmax=255)
        ax.axhline(N // 2, color=ORA, lw=0.8, ls="--")
        ax.set_title(t, fontsize=10)
        ax.axis("off")
    ax = fig.add_subplot(gs[2])
    xs = np.arange(N)
    ax.plot(xs, sq[N // 2], color="#bbb", lw=2, label="原图(台阶)")
    ax.plot(xs, rI, color=RED, lw=1.4, label=f"一刀切:冲过头 {overshoot(rI):.1f}%")
    ax.plot(xs, rG, color=GREEN, lw=1.4, label=f"高斯:冲过头 {overshoot(rG):.1f}%")
    ax.set_xlim(30, 140)
    ax.set_ylim(0, 245)
    ax.set_xlabel("像素位置(橙色虚线那一行)", fontsize=9)
    ax.set_title("③ 剖面:一刀切在边缘两侧冲过头、来回摆", fontsize=10, loc="left")
    ax.legend(fontsize=8.5, loc="upper left")
    ax = fig.add_subplot(gs[3])
    for (kc, ov, sp, y), col in zip(rows, [BLUE, ORA, GREEN, PURPLE]):
        L = y.size
        ax.plot(np.arange(L // 4 - 60, L // 4 + 120) - L // 4, y[L // 4 - 60:L // 4 + 120], color=col, lw=1.2,
                label=f"截止 {kc}:冲过头 {ov:.1f}%,间距 {sp}")
    ax.axhline(1, color="#999", lw=0.8)
    ax.set_xlabel("离边缘的距离(像素)", fontsize=9)
    ax.set_ylim(-0.15, 1.25)
    ax.set_title("④ 开关实验 A:改截止频率\n冲过头不变,只是波纹间距变", fontsize=10, loc="left")
    ax.legend(fontsize=7.8, loc="lower right")
    four_questions(
        fig,
        did="白方块做频域低通:一刀切\n和高斯渐变各一次;再把\n截止频率换四档",
        gained=f"一刀切冲过头 {overshoot(rI):.1f}%、来回摆;\n高斯 0;截止变,冲过头仍约\n9%,只有间距跟着变",
        lost="高斯低通更糊一点:同样\n的半径下,它把边缘附近的\n频率也压低了",
        limit="冲过头约 9% 是一刀切本身\n的性质(吉布斯现象),\n截止调多高都去不掉",
        better="频域滤波用高斯或巴特沃斯,\n不用理想(一刀切)",
        y=0.08, bottom=0.30)
    save(fig, "ringing-cause.png")

    # ---------------- 图 2
    fig, axes = plt.subplots(1, 5, figsize=(17, 4.2), gridspec_kw=dict(width_ratios=[1, 1, 1, 1, 1]))
    cols = [RED, ORA, BLUE, PURPLE]
    for ax, ((name, (img, _)), col) in zip(axes[:4], zip(srcs.items(), cols)):
        row = img[N // 2]
        ref = lin[N // 2] if name.startswith("lanczos") else sq[N // 2]
        ax.plot(xs, ref, color="#bbb", lw=2)
        ax.plot(xs, row, color=col, lw=1.3)
        ov, n_l, far = stats[name]
        ax.set_title(f"{name}\n冲过头 {ov:.1f}%,{n_l} 个波纹,延伸 {far} 像素", fontsize=10, loc="left")
        ax.set_xlim(20, 140)
        ax.set_ylim(-20, 310)
        ax.set_xlabel("像素位置", fontsize=9)
    ax = axes[4]
    show = np.sqrt(err)
    ax.imshow(show, cmap="magma")
    for k in range(0, N + 1, 8):
        ax.axhline(k - 0.5, color="#444", lw=0.2)
        ax.axvline(k - 0.5, color="#444", lw=0.2)
    ax.set_xlim(60, 140)
    ax.set_ylim(140, 60)
    fb, fe = stats["jpeg_frac"]
    ax.set_title(f"⑤ JPEG 误差(放大看,网格是 8×8 块)\n含边缘的块占 {fb * 100:.0f}%,装了 {fe * 100:.0f}% 误差", fontsize=10, loc="left")
    ax.axis("off")
    four_questions(
        fig,
        did="同一条边,分别经过一刀切\n低通、锐化、lanczos 放大、\nJPEG 压缩,数外侧的波纹",
        gained="波纹的「长相」能分来源:\n多圈且传得远 / 只有一对 /\n几圈但很快消失 / 困在 8×8 块",
        lost="数波纹要先找一条干净的\n直边;纹理复杂的地方\n分不清",
        limit="真实图像常几种叠加:\n先锐化再压缩,两种波纹\n会混在一起",
        better="逐个关掉处理链里的步骤,\n看哪一步让波纹消失",
        y=0.08, bottom=0.30)
    save(fig, "ringing-sources.png")


if __name__ == "__main__":
    main()
