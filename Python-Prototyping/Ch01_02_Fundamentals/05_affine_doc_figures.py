"""给 04-geometry/01-图像仿射变换原理解析.md 补配图 —— 990 行,原先一张图都没有。

为什么要补:
    这一篇全是矩阵推导和 Objective-C 代码。「绕左上角转会飞出画布」「正向映射
    会留空洞」「最近邻和双线性差在哪」这几件事,画出来一眼就懂,读公式则要反复回看。

    每张图按仓库约定成套回答四问(见 Documents/README.md「写作约定」):
    做了什么 / 得到什么 / 失去什么 / 局限在哪 —— 尤其是后两问,
    只看效果好的那一面最容易在工程里踩坑。

生成 8 张(全部写到 Assets/results/):
    affine-why-homogeneous.png   2×2 装不下平移,升到 3×3 之后平移变成乘法
    affine-order-matters.png     T·R·S ≠ S·R·T;以及哪一组确实可以交换
    affine-sandwich.png          三明治夹层:搬到原点 → 变换 → 搬回去
    affine-center-half-pixel.png (w-1)/2 vs w/2:转一圈回来差了多少
    affine-forward-vs-backward.png  正向映射的空洞 vs 反向映射填满
    affine-interpolation.png     最近邻 vs 双线性:锯齿换模糊
    affine-determinant.png       det 是面积比;det=0 塌成一条线,不可逆
    affine-canvas-fit.png        KeepSize 裁角 vs Fit 扩画布与 offset

本脚本里的 warp 是**从零手写**的(反向映射 + 两种插值),不是调 cv2.warpAffine ——
图要展示的就是机制本身,用黑盒画出来没有说服力。正确性由 check_against_opencv() 验证。

用法:
    .venv/bin/python Ch01_02_Fundamentals/05_affine_doc_figures.py [--show]
"""

import sys
from pathlib import Path

import cv2
import matplotlib

if "--show" not in sys.argv:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "Assets" / "results"
IMAGES = REPO / "Assets" / "test-images"
matplotlib.rcParams["font.family"] = ["Heiti TC", "Arial Unicode MS", "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False


# ═══════════════════════════════════════════════════ 矩阵与 warp ═════════
# 和文档第 3 章的五个构造器一一对应,全部是「以原点 (0,0) 为基准」。


def T(tx: float, ty: float) -> np.ndarray:
    return np.array([[1, 0, tx], [0, 1, ty], [0, 0, 1]], float)


def S(sx: float, sy: float) -> np.ndarray:
    return np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1]], float)


def R(deg: float) -> np.ndarray:
    t = np.deg2rad(deg)
    return np.array([[np.cos(t), -np.sin(t), 0], [np.sin(t), np.cos(t), 0], [0, 0, 1]], float)


def sandwich(core: np.ndarray, w: int, h: int) -> np.ndarray:
    """三明治夹层:搬到原点 → core → 搬回去。中心用 (n-1)/2,见文档 4.3。"""
    cx, cy = (w - 1) / 2, (h - 1) / 2
    return T(cx, cy) @ core @ T(-cx, -cy)


def warp_backward(img, M, out_hw=None, offset=(0.0, 0.0), interp="bilinear", fill=0):
    """反向映射:遍历目标每个像素,用 M⁻¹ 反推它该去源图哪儿取色。

    这是文档 5.1 的那条公式 P_source = M⁻¹ · P_target。
    画布必然被填满 —— 每个目标像素都有唯一答案,不存在「没人写」的格子。
    """
    h, w = img.shape[:2]
    oh, ow = out_hw or (h, w)
    Minv = np.linalg.inv(M)
    yd, xd = np.mgrid[0:oh, 0:ow].astype(float)
    xs = Minv[0, 0] * (xd + offset[0]) + Minv[0, 1] * (yd + offset[1]) + Minv[0, 2]
    ys = Minv[1, 0] * (xd + offset[0]) + Minv[1, 1] * (yd + offset[1]) + Minv[1, 2]

    if interp == "nearest":
        sx, sy = np.rint(xs).astype(int), np.rint(ys).astype(int)
        ok = (sx >= 0) & (sx < w) & (sy >= 0) & (sy < h)
        out = np.full((oh, ow), float(fill))
        out[ok] = img[sy[ok], sx[ok]]
        return out, ok

    # 双线性:粗筛用 w-0.5(像素中心在整数点,见文档 5.5(c) 坑点 9)
    ok = (xs >= -0.5) & (xs <= w - 0.5) & (ys >= -0.5) & (ys <= h - 0.5)
    x0, y0 = np.floor(xs).astype(int), np.floor(ys).astype(int)
    dx, dy = xs - x0, ys - y0
    x1, y1 = x0 + 1, y0 + 1
    # 边缘 clamp:越界邻居被拉回边界,与内侧点重合,末行末列因此不会被裁掉
    x0c, x1c = np.clip(x0, 0, w - 1), np.clip(x1, 0, w - 1)
    y0c, y1c = np.clip(y0, 0, h - 1), np.clip(y1, 0, h - 1)
    v = (img[y0c, x0c] * (1 - dx) * (1 - dy) + img[y0c, x1c] * dx * (1 - dy)
         + img[y1c, x0c] * (1 - dx) * dy + img[y1c, x1c] * dx * dy)
    out = np.where(ok, v, float(fill))
    return out, ok


def warp_forward(img, M, out_hw=None, offset=(0.0, 0.0), fill=0):
    """正向映射(splatting):遍历源图每个像素,把它投到目标画布上。

    放大时必然留洞 —— 1 个源像素只能占住目标上 1 个点,它理论该覆盖的其余格子
    没有任何人去写。返回 (图, 被写过的掩码),掩码就是「哪些格子有人管」。
    """
    h, w = img.shape[:2]
    oh, ow = out_hw or (h, w)
    ys, xs = np.mgrid[0:h, 0:w].astype(float)
    xd = M[0, 0] * xs + M[0, 1] * ys + M[0, 2] - offset[0]
    yd = M[1, 0] * xs + M[1, 1] * ys + M[1, 2] - offset[1]
    xi, yi = np.rint(xd).astype(int), np.rint(yd).astype(int)
    ok = (xi >= 0) & (xi < ow) & (yi >= 0) & (yi < oh)
    out = np.full((oh, ow), float(fill))
    hit = np.zeros((oh, ow), bool)
    out[yi[ok], xi[ok]] = img[ys[ok].astype(int), xs[ok].astype(int)]
    hit[yi[ok], xi[ok]] = True
    return out, hit


def fit_canvas(M, w, h):
    """把 4 个角点推过去取包围盒 —— 文档 6.1。仿射保平行,矩形的像仍是矩形。"""
    corners = np.array([[0, w - 1, 0, w - 1], [0, 0, h - 1, h - 1], [1, 1, 1, 1]], float)
    p = M @ corners
    minx, maxx = p[0].min(), p[0].max()
    miny, maxy = p[1].min(), p[1].max()
    dw = int(np.ceil(maxx - minx)) + 1
    dh = int(np.ceil(maxy - miny)) + 1
    return (dh, dw), (minx, miny), p


def check_against_opencv() -> None:
    """自检:图里每条结论都建立在这个 warp 正确的前提上,先验一遍再画。

    不拿 cv2.warpAffine 当逐像素基准 —— 它把源坐标**量化到 1/32 像素**
    (INTER_BITS = 5),在非 1/32 整数倍的位移上会比 float64 差出两三个灰阶。
    所以这里用三个有解析答案的情形作硬判据,再用 1/32 整数倍的位移和 OpenCV 对齐。
    """
    img = cv2.imread(str(IMAGES / "camera.png"), cv2.IMREAD_GRAYSCALE).astype(float)
    h, w = img.shape

    # ① 整数平移:双线性的权重此时是 (1,0,0,0),必须逐像素精确
    out, _ = warp_backward(img, T(7, 5), interp="bilinear")
    ref = np.zeros_like(img)
    ref[5:, 7:] = img[:h - 5, :w - 7]
    assert np.abs(out - ref).max() == 0, "整数平移都不精确,别往下画了"

    # ② 旋转 90°:纯置换,同样必须精确
    out, _ = warp_backward(img, sandwich(R(90), w, h), interp="bilinear")
    assert np.abs(out - np.rot90(img, -1)).max() < 1e-9

    # ③ 半像素平移:解析答案就是相邻两列的平均
    out, _ = warp_backward(img, T(0.5, 0), interp="bilinear")
    ref = np.zeros_like(img)
    ref[:, 1:] = (img[:, :-1] + img[:, 1:]) / 2
    assert np.abs(out - ref)[:, 2:-2].max() == 0

    # ④ 位移取 1/32 的整数倍时,和 OpenCV 应当**逐像素完全相同**
    for frac in (0.5, 0.25, 1 / 32):
        M = T(frac, 0)
        mine, _ = warp_backward(img, M, interp="bilinear")
        ref = cv2.warpAffine(img, M[:2], (w, h), flags=cv2.INTER_LINEAR)
        d = np.abs(mine - ref)[2:-2, 2:-2].max()
        assert d == 0, f"位移 {frac} 处与 OpenCV 差 {d}"

    # 对照:不是 1/32 整数倍时的差,正是 OpenCV 的定点量化造成的
    M = T(0.3, 0)
    mine, _ = warp_backward(img, M, interp="bilinear")
    ref = cv2.warpAffine(img, M[:2], (w, h), flags=cv2.INTER_LINEAR)
    d = np.abs(mine - ref)[2:-2, 2:-2]
    print("  自检通过:整数平移 / 旋转 90° / 半像素平移 三个解析情形逐像素精确;")
    print(f"           位移取 1/32 整数倍时与 cv2.warpAffine 差 0;取 0.3 时差 "
          f"最大 {d.max():.3f} 平均 {d.mean():.5f} —— 那是 OpenCV 的 1/32 定点量化,不是本实现的误差。")


# ═══════════════════════════════════════════════════ 四问横幅 ═══════════


def four_questions(fig, did: str, gained: str, lost: str, limit: str,
                   y: float = 0.0, bottom: float = 0.03) -> None:
    """在图底部统一贴一条「做了什么 / 得到 / 失去 / 局限」的横幅。

    这是仓库约定:只看效果好的那一面最容易踩坑,代价和边界必须和收益同框。
    """
    cells = [("做了什么", did, "#eef3f8", "#2c6fbb"),
             ("得到什么", gained, "#eaf5ec", "#2a8f4a"),
             ("失去什么", lost, "#fdeeea", "#c4442a"),
             ("局限在哪", limit, "#fff6e5", "#a8700a")]
    fig.subplots_adjust(bottom=bottom)    # 把横幅收近一点,别和图隔着一大片白
                                          # (带折线图的那几张要留出 x 轴标签的位置)
    for i, (head, body, bg, fg) in enumerate(cells):
        # matplotlib 不认 Markdown,** 会被原样印出来,这里统一剥掉
        body = body.replace("**", "")
        fig.text(0.02 + i * 0.245, y, f"{head}\n{body}", fontsize=8.6, va="top", ha="left",
                 color="#222", linespacing=1.55,
                 bbox=dict(boxstyle="round,pad=0.45", fc=bg, ec=fg, lw=1.0))


def save(fig, name: str) -> None:
    fig.savefig(OUT / name, dpi=130, bbox_inches="tight", facecolor="white")
    print(f"  → Assets/results/{name}")
    if "--show" not in sys.argv:
        plt.close(fig)


def show_gray(ax, data, title, mask=None):
    ax.imshow(data, cmap="gray", vmin=0, vmax=255, interpolation="nearest")
    ax.set_title(title, fontsize=10.5)
    ax.axis("off")


# ═══════════════════════════════════════ 图 1:为什么要升到 3×3 ══════════


def fig_homogeneous() -> None:
    """2×2 能转能缩,就是装不下平移 —— 因为平移是加法,线性变换里没有常数项的位置。"""
    fig = plt.figure(figsize=(12.6, 4.3))
    gs = fig.add_gridspec(1, 3, wspace=0.28)
    sq = np.array([[0, 1, 1, 0, 0], [0, 0, 1, 1, 0]], float)

    ax = fig.add_subplot(gs[0])
    ax.plot(*sq, lw=2, color="#999", label="原始")
    ax.plot(*(np.array([[np.cos(.6), -np.sin(.6)], [np.sin(.6), np.cos(.6)]]) @ sq),
            lw=2, color="#2c6fbb", label="2×2 能做:旋转")
    ax.plot(*(np.array([[1.6, 0], [0, 0.7]]) @ sq), lw=2, color="#2a8f4a",
            label="2×2 能做:缩放")
    ax.plot(sq[0] + 1.8, sq[1] + 0.9, lw=2, ls="--", color="#c4442a",
            label="2×2 做不到:平移")
    ax.axhline(0, color="#ccc", lw=0.8); ax.axvline(0, color="#ccc", lw=0.8)
    ax.set_aspect("equal"); ax.legend(fontsize=8.5, loc="upper left")
    ax.set_xlim(-1.2, 3.2); ax.set_ylim(-1.2, 2.3)
    ax.set_title("2×2 矩阵的能力边界\n旋转缩放都行,唯独平移没处放", fontsize=10.5)

    ax = fig.add_subplot(gs[1]); ax.axis("off")
    ax.set_title("为什么放不下", fontsize=10.5)
    ax.text(0.5, 0.60,
            "线性变换只能写成\n"
            "  x' = a·x + b·y\n"
            "  y' = c·x + d·y\n\n"
            "平移要的是\n"
            "  x' = x + t\n\n"
            "那个常数 t,\n公式里根本没有它的位置。",
            ha="center", va="center", fontsize=11, linespacing=1.8)

    ax = fig.add_subplot(gs[2]); ax.axis("off")
    ax.set_title("升一维之后", fontsize=10.5)
    ax.text(0.5, 0.62,
            "给每个点补一个恒为 1 的分量:\n\n"
            "  [x, y]  →  [x, y, 1]\n\n"
            "那个 1 乘上矩阵第三列,\n"
            "就把常数项「搬」进了乘法里:\n\n"
            "  x' = 1·x + 0·y + t·1\n"
            "                     ↑\n"
            "               平移住在这儿",
            ha="center", va="center", fontsize=10.5, linespacing=1.75,
            bbox=dict(boxstyle="round,pad=0.6", fc="#eef3f8", ec="#2c6fbb"))

    fig.suptitle("为什么非要升到 3×3 齐次矩阵", fontsize=13, y=1.03)
    four_questions(fig,
        "给每个点补第三个\n恒为 1 的分量。",
        "平移从加法变成乘法。\n多步变换能预先连乘\n成一个矩阵;求逆也\n只需求一次。",
        "每点多存一个数,\n每次变换多 3 次乘加。\n(仿射下 z 恒为 1,\n那次除法是空操作)",
        "第三行必须是 [0,0,1]\n才是仿射。改成 [p,q,1]\n就成了透视 —— 那时\n直线还是直线,但\n平行线不再平行。")
    save(fig, "affine-why-homogeneous.png")


# ═══════════════════════════════════════ 图 2:顺序敏感 ══════════════════


def fig_order() -> None:
    """同样三个变换,换个顺序就是另一张图 —— 而且有一组换了也没事。"""
    img = cv2.imread(str(IMAGES / "camera.png"), cv2.IMREAD_GRAYSCALE).astype(float)
    h, w = img.shape
    t, r, s = T(60, 0), R(25), S(1.0, 0.55)

    a, _ = warp_backward(img, sandwich(t @ r @ s, w, h))
    b, _ = warp_backward(img, sandwich(s @ r @ t, w, h))
    diff = np.abs(a - b)

    # 可交换的那一组:旋转 与 均匀缩放
    c1, _ = warp_backward(img, sandwich(R(25) @ S(0.7, 0.7), w, h))
    c2, _ = warp_backward(img, sandwich(S(0.7, 0.7) @ R(25), w, h))
    same = np.abs(c1 - c2).max()

    fig, axes = plt.subplots(1, 4, figsize=(13.2, 3.9))
    show_gray(axes[0], a, "T · R · S\n(先压扁,再转,最后平移)")
    show_gray(axes[1], b, "S · R · T\n(先平移,再转,最后压扁)")
    axes[2].imshow(diff, cmap="inferno")
    axes[2].set_title(f"两者的差\n平均差 {diff.mean():.1f} 灰阶,最大 {diff.max():.0f}", fontsize=10.5)
    axes[2].axis("off")
    show_gray(axes[3], c1, f"R · S(0.7,0.7) 与 S · R\n这一组交换了也一样,最大差 {same:.0f}")
    fig.suptitle("矩阵乘法不满足交换律 —— 顺序是语义的一部分", fontsize=13, y=1.04)
    four_questions(fig,
        "同样的平移、旋转、\n非均匀缩放,只换\n相乘的先后。",
        "看清了「顺序」不是\n写法问题:R 会把平移\n方向一起转走,S 会把\n平移量一起缩放。",
        f"换错顺序 = 换了个功能。\n这里平均差 {diff.mean():.1f} 灰阶,\n而且两张图都「看着\n挺正常」,不会报错。",
        "不是两两都敏感:旋转\n与**均匀**缩放可交换\n(最右,差 0)。只要\n沾上平移或非均匀缩放,\n顺序就必须钉死。")
    save(fig, "affine-order-matters.png")
    print(f"     T·R·S vs S·R·T 平均差 {diff.mean():.1f};R 与均匀 S 交换后最大差 {same:.0f}")


# ═══════════════════════════════════════ 图 3:三明治夹层 ════════════════


def fig_sandwich() -> None:
    """不夹层就是绕画布左上角转,大半张图转出去了。"""
    img = cv2.imread(str(IMAGES / "camera.png"), cv2.IMREAD_GRAYSCALE).astype(float)
    h, w = img.shape
    naive, ok_n = warp_backward(img, R(30))                      # 直接用原点基准矩阵
    good, ok_g = warp_backward(img, sandwich(R(30), w, h))
    lost_naive = 1 - ok_n.mean()
    lost_good = 1 - ok_g.mean()

    fig = plt.figure(figsize=(13.2, 4.0))
    gs = fig.add_gridspec(1, 4, wspace=0.12)
    show_gray(fig.add_subplot(gs[0]), img, "原图")
    show_gray(fig.add_subplot(gs[1]), naive,
              f"直接乘 R(30°)\n绕画布左上角转,{lost_naive:.0%} 的画布是空的")
    show_gray(fig.add_subplot(gs[2]), good,
              f"三明治夹层之后\n绕图像中心转,空白降到 {lost_good:.0%}")

    ax = fig.add_subplot(gs[3]); ax.axis("off")
    ax.set_title("夹层做了什么", fontsize=10.5)
    ax.text(0.5, 0.92,
            "M = T(+c) · R · T(−c)\n\n"
            "从右往左读,像素经历:\n\n"
            "① T(−c) 把图像中心搬到原点\n\n"
            "② R 此刻「绕原点转」\n     就等于「绕中心转」\n\n"
            "③ T(+c) 再把中心搬回去\n\n"
            "缩放、镜像同理:所有「原点\n基准」的算子夹进去之后,\n全都变成「原地做」。",
            ha="center", va="top", fontsize=9.4, linespacing=1.6,
            bbox=dict(boxstyle="round,pad=0.5", fc="#eef3f8", ec="#2c6fbb"))

    fig.suptitle("三明治夹层法:把中心搬到原点 → 变换 → 搬回去", fontsize=13, y=1.04)
    four_questions(fig,
        "在核心变换两边各\n夹一次平移。",
        "旋转、缩放、镜像\n全部变成「原地做」,\n符合用户直觉。\n多的只有两次矩阵乘。",
        f"什么都没多失去 ——\n转 30° 本来就会有\n{lost_good:.0%} 的角落空出来,\n那是旋转自带的,\n不是夹层造成的。",
        "夹层只解决「绕哪儿转」。\n转出画布的部分照样被裁,\n要留全得配自适应画布\n(见本篇第 6 章)。")
    save(fig, "affine-sandwich.png")
    print(f"     绕左上角:{lost_naive:.1%} 画布为空;夹层后:{lost_good:.1%}")


# ═══════════════════════════════════════ 图 4:那半个像素 ════════════════


def fig_half_pixel() -> None:
    """中心取 w/2 还是 (w-1)/2 —— 转 90°,拿 np.rot90 当真值,差的就是那半像素。

    为什么用「转一次 90°」而不是「转满一圈」:
        绕**错**的中心转满 360°,净效果仍然是恒等变换 —— 半像素偏移自己抵消掉了,
        量出来两种中心一样好,结论是假的。必须看单次变换的落点。
        理论位移 = 2·|δ|·sin(θ/2),δ=(0.5,0.5)、θ=90° 时正好 1.0 像素。
    """
    img = cv2.imread(str(IMAGES / "camera.png"), cv2.IMREAD_GRAYSCALE).astype(float)
    h, w = img.shape
    truth = np.rot90(img, -1)          # 旋转 90° 是纯置换,真值可以直接写出来

    def spin(cx, cy):
        out, _ = warp_backward(img, T(cx, cy) @ R(90) @ T(-cx, -cy), interp="bilinear")
        d = np.abs(out - truth)[3:-3, 3:-3]
        shift, _ = cv2.phaseCorrelate(np.float64(out), np.float64(truth))
        return out, d.mean(), d.max(), shift

    right, er, mr, sr = spin((w - 1) / 2, (h - 1) / 2)
    wrong, ew, mw, sw = spin(w / 2, h / 2)

    fig, axes = plt.subplots(1, 4, figsize=(13.2, 3.9))
    show_gray(axes[0], truth, "真值:np.rot90\n(旋转 90° 是纯置换,答案唯一)")
    show_gray(axes[1], right,
              f"中心 = (w−1)/2\n与真值平均差 {er:.3f},位移 {abs(sr[0]):.3f} px")
    show_gray(axes[2], wrong,
              f"中心 = w/2\n与真值平均差 {ew:.2f},位移 {abs(sw[0]):.3f} px")
    axes[3].imshow(np.abs(wrong - truth), cmap="inferno")
    axes[3].set_title(f"用 w/2 时与真值的差\n整幅图都在发亮 = 整体挪了一个像素", fontsize=10.5)
    axes[3].axis("off")

    fig.suptitle("中心为什么是 (w−1)/2 而不是 w/2 —— 转 90°,和 np.rot90 对答案", fontsize=13, y=1.04)
    four_questions(fig,
        "把旋转轴心从 w/2\n改成 (w−1)/2,也就是\n往回挪半个像素。",
        f"轴心落在像素网格真正的\n几何中心,结果与真值\n**逐像素相同**\n(平均差 {er:.3f},位移 {abs(sr[0]):.3f})。",
        f"用 w/2 的代价:整幅图\n系统性平移 {abs(sw[0]):.3f} 像素,\n平均差 {ew:.2f} 灰阶。\n不报错,只是「有点飘」。",
        "别用「转满一圈」去测这个 ——\n绕错的中心转满 360°,\n净效果还是恒等变换,\n半像素偏移自己抵消了,\n两种中心会测得一样好。\n单次变换才看得出来。")
    save(fig, "affine-center-half-pixel.png")
    print(f"     转 90°:(w−1)/2 平均差 {er:.3f}/位移 {abs(sr[0]):.3f}px;"
          f"w/2 平均差 {ew:.2f}/位移 {abs(sw[0]):.3f}px")


# ═══════════════════════════════════════ 图 5:正向 vs 反向 ══════════════


def fig_forward_backward() -> None:
    """正向映射的空洞:1 个源像素占不住它该覆盖的 4 个目标格子。"""
    src = cv2.imread(str(IMAGES / "camera.png"), cv2.IMREAD_GRAYSCALE)[100:164, 100:164].astype(float)
    h, w = src.shape
    k = 3
    M = S(k, k)
    fwd, hit = warp_forward(src, M, out_hw=(h * k, w * k))
    bwd, _ = warp_backward(src, M, out_hw=(h * k, w * k), interp="bilinear")
    holes = 1 - hit.mean()

    fig, axes = plt.subplots(1, 4, figsize=(13.2, 3.9))
    show_gray(axes[0], src, f"源图 {w}×{h}")
    show_gray(axes[1], fwd, f"正向映射 放大 {k}×\n{holes:.0%} 的格子没人写 → 空洞")
    axes[2].imshow(~hit, cmap="gray_r", interpolation="nearest")
    axes[2].set_title(f"黑 = 没被写到的格子\n理论值 1 − 1/{k}² = {1 - 1 / k**2:.0%}", fontsize=10.5)
    axes[2].axis("off")
    show_gray(axes[3], bwd, "反向映射 + 双线性\n每个目标格子都有唯一答案,零空洞")

    fig.suptitle("为什么必须反过来:遍历目标问「我该去源图哪儿取色」", fontsize=13, y=1.04)
    four_questions(fig,
        "把循环从「遍历源图」\n改成「遍历目标画布」,\n每个目标像素用 M⁻¹\n反推源坐标。",
        "画布必然填满,零空洞。\n缩小时也不用处理\n「多个源像素抢同一格」\n的冲突。",
        "得先求逆 —— 所以\ndet=0 的矩阵直接没法用,\n必须在求逆前拦下来\n(见本篇第 3.6 节)。",
        "**缩小时会欠采样**:\n反向映射每个目标格子\n只采 1 个点,源图上\n其余像素根本没被看过,\n细密纹理会抖动成摩尔纹。\n缩小要先降采样\n(高斯金字塔 / INTER_AREA)。")
    save(fig, "affine-forward-vs-backward.png")
    print(f"     正向映射放大 {k}× 的空洞率 {holes:.1%}(理论 {1 - 1 / k**2:.1%})")


# ═══════════════════════════════════════ 图 6:两种插值 ══════════════════


def fig_interpolation() -> None:
    """最近邻 vs 双线性。

    关键在于**怎么量**:
        「平均梯度」量不出区别 —— 一个台阶和一段斜坡的总变差本来就相等,
        两种插值都是 0.7。得换成两个指标配着看:
          · 与**高清真值**的 PSNR —— 谁还原得准
          · 内部最陡一级 —— 谁的边缘硬
        这两个指标会打架,而那个矛盾正是这张图最值得看的地方。
    """
    full = cv2.imread(str(IMAGES / "camera.png"), cv2.IMREAD_GRAYSCALE).astype(float)
    k = 8
    hi = full[64:320, 64:320]                                        # 256×256,当真值
    lo = cv2.resize(hi, (256 // k, 256 // k), interpolation=cv2.INTER_AREA)   # 32×32

    def up(mode):
        o, _ = warp_backward(lo, S(k, k), out_hw=(256, 256), interp=mode)
        return o

    near, bili = up("nearest"), up("bilinear")

    def psnr(a):
        return 10 * np.log10(255.0 ** 2 / np.mean((a - hi) ** 2))

    def step(a):                     # 内部最陡的一级,避开与填充色相接的外框
        return np.abs(np.diff(a, axis=1))[8:-8, 8:-8].max()

    row = 128
    fig = plt.figure(figsize=(13.4, 4.2))
    gs = fig.add_gridspec(1, 5, width_ratios=[1, 1, 1, 1, 1.5], wspace=0.22)
    show_gray(fig.add_subplot(gs[0]), lo, f"源图 {lo.shape[1]}×{lo.shape[0]}")
    show_gray(fig.add_subplot(gs[1]), near,
              f"最近邻 放大 {k}×\nPSNR {psnr(near):.2f} dB,最陡一级 {step(near):.0f}")
    show_gray(fig.add_subplot(gs[2]), bili,
              f"双线性 放大 {k}×\nPSNR {psnr(bili):.2f} dB,最陡一级 {step(bili):.0f}")
    show_gray(fig.add_subplot(gs[3]), hi,
              f"高清真值 256×256\n最陡一级 {step(hi):.0f}")

    ax = fig.add_subplot(gs[4])
    ax.plot(hi[row], lw=1.2, color="#999", label="真值")
    ax.plot(near[row], lw=1.5, color="#c4442a", label="最近邻:台阶")
    ax.plot(bili[row], lw=1.5, color="#2c6fbb", label="双线性:斜坡")
    ax.set_xlim(40, 170)
    ax.set_xlabel("沿第 128 行走过去")
    ax.set_ylabel("灰度")
    ax.legend(fontsize=8.5)
    ax.set_title("同一行的剖面\n台阶落在哪儿,全凭运气", fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)

    fig.suptitle("最近邻 vs 双线性 —— 「看着更锐」和「还原得更准」不是一回事", fontsize=13, y=1.04)
    four_questions(fig,
        "非整数坐标上取色:\n最近邻「抄最近那个」,\n双线性「按面积混合\n周围 4 个」。",
        f"双线性还原得更准:\nPSNR {psnr(near):.2f} → {psnr(bili):.2f} dB。\n"
        "台阶被摊成斜坡,\n放大和旋转不再有\n马赛克锯齿。",
        f"锐度:最陡一级从\n{step(near):.0f} 掉到 {step(bili):.0f}。\n"
        "每混合一次糊一点,\n反复变换会越来越糊 ——\n所以多步变换要先把\n矩阵连乘再采样一次。",
        f"最近邻的「锐」是假的:\n它的最陡一级 {step(near):.0f} 很接近\n真值 {step(hi):.0f},可 PSNR 反而低 ——\n"
        "锐边长在了错的位置。\n而且 8× 放大下两者都远不如\n真值,凭空的细节谁也变不出来,\n要更好得上双三次 / Lanczos。",
        y=-0.05, bottom=0.17)
    save(fig, "affine-interpolation.png")
    print(f"     PSNR 最近邻 {psnr(near):.2f} / 双线性 {psnr(bili):.2f} dB;"
          f"最陡一级 {step(near):.0f} / {step(bili):.0f}(真值 {step(hi):.0f})")


# ═══════════════════════════════════════ 图 7:行列式 ════════════════════


def fig_determinant() -> None:
    """det 就是面积比。det=0 意味着面积被压成 0,信息已经没了,逆矩阵无从谈起。"""
    img = cv2.imread(str(IMAGES / "camera.png"), cv2.IMREAD_GRAYSCALE).astype(float)
    h, w = img.shape
    cases = [(S(1, 1), "原图\ndet = 1"),
             (S(1.4, 1.4), "缩放 1.4×\ndet = 1.96(面积变 1.96 倍)"),
             (S(-1, 1), "水平镜像\ndet = −1(负号 = 手性翻转,照样可逆)"),
             (S(1, 0.06), "sy → 0\ndet ≈ 0.06,已经快塌了")]

    fig, axes = plt.subplots(1, 4, figsize=(13.2, 3.9))
    for ax, (core, title) in zip(axes, cases):
        out, _ = warp_backward(img, sandwich(core, w, h), interp="bilinear")
        show_gray(ax, out, title)

    fig.suptitle("行列式是面积比 —— 它等于 0,就等于把图压没了", fontsize=13, y=1.04)
    four_questions(fig,
        "求一次 det,在求逆\n之前把它拦下来:\nif |det| < 1e-12: 拒绝",
        "提前拒绝坏参数。\n顺带读懂 det 的含义:\n绝对值 = 面积缩放倍数,\n负号 = 手性翻转。",
        "多一次行列式计算 ——\n3×3 的 det 只有几次\n乘加,可以忽略。",
        "阈值不能写 == 0。浮点\n连乘后 det 很少精确为 0,\n但 1e-13 这种接近 0 的值\n求逆会产出天文数字坐标,\n采样结果照样是乱码。")
    save(fig, "affine-determinant.png")


# ═══════════════════════════════════════ 图 8:自适应画布 ════════════════


def fig_canvas() -> None:
    """KeepSize 把转出去的切掉;Fit 按四角包围盒把画布撑大。"""
    img = cv2.imread(str(IMAGES / "camera.png"), cv2.IMREAD_GRAYSCALE).astype(float)
    h, w = img.shape
    M = sandwich(R(30), w, h)
    keep, ok_k = warp_backward(img, M, interp="bilinear")
    (dh, dw), off, corners = fit_canvas(M, w, h)
    fit, ok_f = warp_backward(img, M, out_hw=(dh, dw), offset=off, interp="bilinear")

    # 被裁掉了多少:源图有多少像素落在原画布之外
    ys, xs = np.mgrid[0:h, 0:w].astype(float)
    xd = M[0, 0] * xs + M[0, 1] * ys + M[0, 2]
    yd = M[1, 0] * xs + M[1, 1] * ys + M[1, 2]
    cut = ((xd < 0) | (xd > w - 1) | (yd < 0) | (yd > h - 1)).mean()

    fig = plt.figure(figsize=(13.2, 4.3))
    gs = fig.add_gridspec(1, 4, wspace=0.2)
    show_gray(fig.add_subplot(gs[0]), img, f"原图 {w}×{h}")
    show_gray(fig.add_subplot(gs[1]), keep, f"KeepSize {w}×{h}\n四角被切掉,{cut:.1%} 的源像素没了")
    show_gray(fig.add_subplot(gs[2]), fit, f"Fit {dw}×{dh}\n一个像素都不丢")

    ax = fig.add_subplot(gs[3])
    ax.plot(np.append(corners[0][[0, 1, 3, 2]], corners[0][0]),
            np.append(corners[1][[0, 1, 3, 2]], corners[1][0]),
            lw=2, color="#2c6fbb", label="变换后的四角")
    ax.add_patch(plt.Rectangle((off[0], off[1]), dw - 1, dh - 1, fill=False,
                               ec="#c4442a", lw=1.8, ls="--", label="包围盒 = 新画布"))
    ax.add_patch(plt.Rectangle((0, 0), w - 1, h - 1, fill=False, ec="#999", lw=1.4,
                               label="原画布"))
    ax.plot(off[0], off[1], "o", color="#c4442a")
    ax.annotate(f"offset = ({off[0]:.0f}, {off[1]:.0f})\n通常是负的 —— 图转出去了",
                (off[0], off[1]), textcoords="offset points", xytext=(16, -60),
                fontsize=8.8, color="#c4442a",
                arrowprops=dict(arrowstyle="->", color="#c4442a", lw=1))
    ax.invert_yaxis(); ax.set_aspect("equal")
    ax.legend(fontsize=8.0, loc="upper right")
    ax.set_title("怎么算出来的:4 个角点推过去取 min/max", fontsize=10.5)

    fig.suptitle("自适应画布:仿射保平行,所以只要看 4 个角", fontsize=13, y=1.04)
    four_questions(fig,
        "把 4 个角点用正向\n矩阵推过去,取包围盒\n当新画布,左上角\n记为 offset。",
        f"一个像素都不丢\n(KeepSize 会切掉 {cut:.1%})。\n只要 4 次矩阵乘,\n不用对全图做正向投射。",
        "画布变大了 —— 这里\n"
        f"{w}×{h} → {dw}×{dh},\n"
        f"内存涨 {(dw * dh) / (w * h):.2f} 倍,\n"
        "而且多出来的全是空白。",
        "反向映射时必须把\noffset 加回去,漏了就\n整体错位一个包围盒 ——\nKeepSize 下 offset 为 0,\n测不出来,一开 Fit 就炸。\n另外要设尺寸上限:\n缩放 100× 能把内存吃光。")
    save(fig, "affine-canvas-fit.png")
    print(f"     KeepSize 切掉 {cut:.1%};Fit 画布 {w}×{h} → {dw}×{dh},offset=({off[0]:.1f},{off[1]:.1f})")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    check_against_opencv()
    for fn in (fig_homogeneous, fig_order, fig_sandwich, fig_half_pixel,
               fig_forward_backward, fig_interpolation, fig_determinant, fig_canvas):
        fn()
    if "--show" in sys.argv:
        plt.show()
