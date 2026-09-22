"""高斯核里那几个数是从哪儿来的 —— 配合 02-smoothing.md 第二节。

为什么单独做一份:
    文档里高斯是「直接甩公式」出场的 —— 写下 e^(-x²/2σ²),然后说核长这样。
    跳步跳得厉害:为什么偏偏是钟形?为什么 3×3 里填 1/2/1 而不是别的?
    这几个问题不解决,后面「核边长取 6σ+1」这类经验规则就只能死记。

    本脚本把那条推导画出来,一句公式都不用:
    「跟邻居平均一下」做两遍 → 数一数每个原始格子被用到几次 → 就是 1、2、1。

生成 1 张(写到 Assets/results/):
    gaussian-kernel-origin.png

用法:
    .venv/bin/python Ch03_Spatial_Filtering/26_gaussian_kernel_origin.py [--show]
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import IMAGES, four_questions, save, use_cjk_font  # noqa: E402

use_cjk_font()
import matplotlib.pyplot as plt  # noqa: E402

BLUE, ORANGE, GREEN, RED, GREY = "#2c6fbb", "#d95f02", "#2a8f4a", "#c4442a", "#888888"


def binomial(n):
    """做 n 遍「跟左邻平均」,合成的核。n=2 就是 [1,2,1]/4。"""
    k = np.array([1.0])
    for _ in range(n):
        k = np.convolve(k, [0.5, 0.5])
    return k


def dice(n):
    """n 颗骰子点数和的概率分布。用的是和上面同一个卷积 —— 这正是重点。"""
    p = np.array([1.0])
    for _ in range(n):
        p = np.convolve(p, np.ones(6) / 6)
    return p


def truncation(sigma, ksize):
    """核只有 ksize 格时,高斯曲线被剪掉了多少。"""
    x = np.arange(-200, 201)
    g = np.exp(-x ** 2 / (2 * sigma ** 2))
    g /= g.sum()
    return 1 - g[np.abs(x) <= ksize // 2].sum()


def panel_paths(ax):
    """(a) 数路的条数 —— 中间那格为什么是 2。"""
    ax.set_xlim(-0.6, 2.6)
    ax.set_ylim(-0.5, 2.7)
    ax.axis("off")

    top = {0: "②", 1: "③", 2: "④"}
    for x, lab in top.items():
        ax.add_patch(plt.Rectangle((x - 0.22, 2.0), 0.44, 0.34,
                                   fc="#eef3f8", ec=BLUE, lw=1.4))
        ax.text(x, 2.17, lab, ha="center", va="center", fontsize=11, color=BLUE)
    for x in (0.5, 1.5):
        ax.add_patch(plt.Rectangle((x - 0.22, 1.05), 0.44, 0.34,
                                   fc="#fff6e5", ec=ORANGE, lw=1.4))
    ax.add_patch(plt.Rectangle((0.78, 0.1), 0.44, 0.34,
                               fc="#eaf5ec", ec=GREEN, lw=1.8))

    # ③ 的两条路画粗、画橙:它同时喂给了「一遍后」的左右两格,所以被数了两次
    for a, b, hot in ((0, 0.5, False), (1, 0.5, True),
                      (1, 1.5, True), (2, 1.5, False)):
        ax.annotate("", xy=(b, 1.42), xytext=(a, 1.98),
                    arrowprops=dict(arrowstyle="->", lw=2.2 if hot else 1.1,
                                    color=ORANGE if hot else GREY))
    for a in (0.5, 1.5):
        ax.annotate("", xy=(1.0, 0.47), xytext=(a, 1.02),
                    arrowprops=dict(arrowstyle="->", lw=1.6, color=GREEN))

    ax.text(-0.52, 2.17, "原始", fontsize=9, color=BLUE, ha="right", va="center")
    ax.text(-0.52, 1.22, "平均\n1 遍", fontsize=9, color=ORANGE, ha="right", va="center")
    ax.text(-0.52, 0.27, "平均\n2 遍", fontsize=9, color=GREEN, ha="right", va="center")
    for x, n in ((0, 1), (1, 2), (2, 1)):
        ax.text(x, 2.52, f"{n} 条路", ha="center", fontsize=10,
                color=ORANGE if n == 2 else GREY,
                fontweight="bold" if n == 2 else "normal")
    ax.set_title("③ 走了两条路到终点,②④ 各一条\n数路的条数 → [1, 2, 1]", fontsize=10.5)


def panel_converge(ax):
    """(b) 做的遍数越多,形状越靠近钟形。"""
    for n, alpha in ((2, 0.35), (4, 0.5), (8, 0.7), (32, 1.0)):
        k = binomial(n)
        x = (np.arange(len(k)) - (len(k) - 1) / 2) / np.sqrt(n / 4)   # 按宽度对齐
        ax.plot(x, k / k.max(), "-o" if n <= 4 else "-", color=BLUE, alpha=alpha,
                ms=4, lw=1.6, label=f"做 {n} 遍")
    t = np.linspace(-4, 4, 400)
    ax.plot(t, np.exp(-t ** 2 / 2), "--", color=RED, lw=2, label="真高斯")
    ax.set_xlim(-4, 4)
    ax.set_xlabel("离中心多远(已按宽度对齐)")
    ax.set_ylabel("权重(峰值归一)")
    ax.legend(fontsize=8, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    errs = []
    for n in (2, 4, 8, 32):
        k = binomial(n)
        x = np.arange(len(k)) - (len(k) - 1) / 2
        s = np.sqrt((x ** 2 * k).sum())
        g = np.exp(-x ** 2 / (2 * s ** 2))
        g /= g.sum()
        errs.append(np.abs(k - g).max() / k.max() * 100)
    ax.set_title(f"「收敛」= 形状定型,不是越做越平\n偏差 {errs[0]:.0f}% → "
                 f"{errs[1]:.0f}% → {errs[2]:.0f}% → {errs[3]:.1f}%", fontsize=10.5)


def panel_dice(ax):
    """(c) 同一个运算换身衣服:掷骰子。"""
    for n, color in ((1, GREY), (2, ORANGE), (3, BLUE)):
        p = dice(n)
        ax.plot(np.arange(n, n * 6 + 1), p / p.max(), "-o", color=color,
                ms=4, lw=1.6, label=f"{n} 颗骰子")
    ax.set_xlabel("点数和")
    ax.set_ylabel("概率(峰值归一)")
    ax.legend(fontsize=8, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("骰子本身是平的,加起来却成了钟形\n中心极限定理 —— 和左边是同一个运算",
                 fontsize=10.5)


def panel_truncate(ax):
    """(d) 代价:无限长的曲线必须剪断。"""
    sigma = 3.0
    sizes = [7, 13, 19, 25]
    lost = [truncation(sigma, k) * 100 for k in sizes]
    ax.bar([str(k) for k in sizes], lost, 0.55, color=RED)
    for i, v in enumerate(lost):
        ax.text(i, v + 0.9, f"{v:.2f}%", ha="center", fontsize=9, color=RED)
    ax.axvline(1.62, color=GREEN, ls="--", lw=1.4)
    ax.text(1.72, 18, f"经验规则 6σ+1 = {int(6 * sigma + 1)}", fontsize=9, color=GREEN)
    ax.set_ylim(0, 29)
    ax.set_xlabel(f"核边长(σ={sigma:.0f})")
    ax.set_ylabel("高斯曲线被剪掉的比例")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("剪多少都行,就是剪不干净\n「6σ+1」买的就是这个误差", fontsize=10.5)


def main() -> None:
    fig, axes = plt.subplots(1, 4, figsize=(15.2, 5.2))
    fig.subplots_adjust(wspace=0.34)
    panel_paths(axes[0])
    panel_converge(axes[1])
    panel_dice(axes[2])
    panel_truncate(axes[3])

    fig.suptitle("高斯核里那几个数是怎么来的 —— 没有人挑过它们,是数出来的",
                 fontsize=13, y=1.02)
    four_questions(fig,
        "把「跟邻居平均一下」\n重复 N 遍,再数每个\n原始格子被用到几次。\n"
        "数出来就是杨辉三角:\n[1,1] → [1,2,1] →\n[1,3,3,1] → …",
        "核里的数有了出处,\n不用死记。N 越大越靠近\n钟形(32 遍时偏差 0.8%),\n"
        "于是可以反过来\n直接写高斯公式,\n省掉那 N 遍。",
        "精确性。曲线无限长,\n核必须剪断 —— σ=3 配\n7×7 会剪掉 24%。\n"
        "另外像素是一小块面积,\n取中心点值而非积分,\n又差 1.8%。",
        "离散世界里没有真高斯。\n采样高斯、杨辉三角、\n离散高斯核三者互不相同,\n"
        "都只是那条连续曲线\n在格子世界里的影子。",
        "要严格满足离散扩散方程,\n查离散高斯核\n(discrete Gaussian, 贝塞尔函数);\n"
        "要又快又够用,\n盒式滤波连做三次\n(积分图, O(1)/像素)。",
        y=0.02, bottom=0.235)
    save(fig, "gaussian-kernel-origin.png")

    verify()


def verify() -> None:
    """把文档第二、五节引用的每个数字都算一遍。改文档前先跑这个对答案。"""
    import cv2

    print("\n── 做 N 遍合成的核 = 杨辉三角")
    for n in (1, 2, 3, 4):
        print(f"     {n} 遍 → {np.round(binomial(n) * 2 ** n).astype(int)} / {2 ** n}")

    print("\n── [1,2,1]/4 和 [0.25,0.5,0.25] 是不是同一个东西")
    img = cv2.imread(str(IMAGES / "camera.png"), cv2.IMREAD_GRAYSCALE).astype(np.float64)
    a = cv2.filter2D(img, cv2.CV_64F, np.outer([.25, .5, .25], [.25, .5, .25]))
    b = cv2.filter2D(img, cv2.CV_64F, np.outer([1., 2, 1], [1., 2, 1]) / 16)
    print(f"     最大差异 {np.abs(a - b).max():.1e}")

    print("\n── 核的和 ≠ 1 会怎样(一片纯灰 v=100)")
    flat = np.full((64, 64), 100.0)
    for row in ([.25, .5, .25], [.5, 1, .5], [1., 2, 1]):
        out = cv2.filter2D(flat, cv2.CV_64F, np.array(row).reshape(1, 3))
        print(f"     {str(row):22} 和={sum(row):.0f}  输出={out[32, 32]:.0f}")

    print("\n── 换别的数字:去噪与变糊的取舍(camera.png + σ=15 噪声)")
    rng = np.random.default_rng(0)                 # 固定种子,文档里的数字才对得上
    noisy = np.clip(img + rng.normal(0, 15, img.shape), 0, 255)
    print(f"     {'(不处理)':24} 剩余噪声 {np.sqrt(((noisy - img) ** 2).mean()):6.2f}"
          f"   改动量 {0.0:6.2f}")
    for name, row in (("[0,1,0]  什么都不做", [0, 1, 0]), ("[1,1,1]  盒式", [1, 1, 1]),
                      ("[1,2,1]  高斯", [1, 2, 1]), ("[1,4,1]", [1, 4, 1]),
                      ("[1,10,1] 中间重太多", [1, 10, 1])):
        k = np.array(row, float)
        k2 = np.outer(k, k) / k.sum() ** 2
        out, ref = (cv2.filter2D(x, cv2.CV_64F, k2) for x in (noisy, img))
        print(f"     {name:24} 剩余噪声 {np.sqrt(((out - ref) ** 2).mean()):6.2f}"
              f"   改动量 {np.sqrt(((out - noisy) ** 2).mean()):6.2f}")

    print("\n── 做 N 遍与真高斯的偏差(「收敛」是形状定型)")
    for n in (2, 4, 8, 16, 32):
        k = binomial(n)
        x = np.arange(len(k)) - (len(k) - 1) / 2
        s = np.sqrt((x ** 2 * k).sum())
        g = np.exp(-x ** 2 / (2 * s ** 2)); g /= g.sum()
        print(f"     做 {n:>2} 遍(核长 {len(k):>2})  偏差 {np.abs(k - g).max() / k.max() * 100:5.2f}%")

    print("\n── 两个宽度:支撑集线性长,σ 只按 √N 长")
    print(f"     {'N':>5} {'支撑集':>7} {'σ':>7} {'√N/2':>7} {'8 位下还看得见':>14}")
    for n in (8, 32, 128, 512):
        k = binomial(n)
        x = np.arange(len(k)) - (len(k) - 1) / 2
        sg = np.sqrt((x ** 2 * k).sum())
        print(f"     {n:>5} {len(k):>7} {sg:>7.2f} {np.sqrt(n) / 2:>7.2f}"
              f" {int((k > k.max() / 255).sum()):>14}")

    print("\n── 为什么是 √N:每遍加的是方差(0.25),而方差才可加")
    for n in (1, 4, 64):
        k = binomial(n)
        x = np.arange(len(k)) - (len(k) - 1) / 2
        print(f"     {n:>2} 遍累计方差 = {(x ** 2 * k).sum():>8.4f}   = {n} × 0.25")
    print("     反过来 N = (2σ)²:σ 翻一倍,遍数翻四倍")
    for t in (5, 11, 20):
        print(f"       想到 σ={t:>2} 格,要做 {int((2 * t) ** 2):>4} 遍")

    print("\n── 假之一:曲线无限长,必须剪断(σ=3)")
    for ks in (3, 7, 13, 19, 25):
        print(f"     核边长 {ks:>2}  剪掉 {truncation(3, ks) * 100:6.2f}%")

    print("\n── 假之二:像素是一小块面积,取点值 ≠ 求积分(σ=1.5)")
    from math import erf, sqrt
    sg, xs = 1.5, np.arange(-9, 10)
    samp = np.exp(-xs ** 2 / (2 * sg ** 2)); samp /= samp.sum()
    integ = np.array([.5 * (erf((i + .5) / (sg * sqrt(2))) - erf((i - .5) / (sg * sqrt(2))))
                      for i in xs]); integ /= integ.sum()
    print(f"     中心那格:取点值 {samp[9]:.6f}   求积分 {integ[9]:.6f}"
          f"   最大差 {np.abs(samp - integ).max() / samp.max() * 100:.2f}% 峰值")

    print("\n── 假之三:结果要塞回 8 位整数(σ=2)")
    u8 = cv2.imread(str(IMAGES / "camera.png"), cv2.IMREAD_GRAYSCALE)
    f64 = cv2.GaussianBlur(u8.astype(np.float64), (0, 0), 2.0)
    q = cv2.GaussianBlur(u8, (0, 0), 2.0).astype(np.float64)
    print(f"     float64 vs uint8:最大差 {np.abs(f64 - q).max():.3f} 灰阶"
          f"   均方根 {np.sqrt(((f64 - q) ** 2).mean()):.4f}")

    print("\n── OpenCV 的小核压根没算高斯公式")
    for ks in (3, 5, 7, 9):
        ocv = cv2.getGaussianKernel(ks, -1).ravel()
        print(f"     ksize={ks}  与杨辉三角/2^n 的差 {np.abs(ocv - binomial(ks - 1)).max():.2e}")

    print("\n── 试金石:只有真高斯才有的勾股性质,近似版还成立吗")
    ab = cv2.GaussianBlur(cv2.GaussianBlur(img, (0, 0), 3.0), (0, 0), 4.0)
    c = cv2.GaussianBlur(img, (0, 0), 5.0)
    print(f"     σ=3 接 σ=4  vs  直接 σ=5:均方根差 {np.sqrt(((ab - c) ** 2).mean()):.4f} 灰阶")


if __name__ == "__main__":
    main()
    if "--show" in sys.argv:
        plt.show()
