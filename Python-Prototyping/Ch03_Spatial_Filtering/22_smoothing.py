"""第 6 周(3.5 节):空间滤波 —— 22 平滑(模糊)四件套。

对应文档 Documents/05-spatial-filtering/02-smoothing.md。

模糊说白了就是「让每个像素跟邻居商量,取个折中」。
四种做法的区别,只在于**怎么商量**:

    盒式(均值)   一视同仁,不管远近每个邻居都一样听
    高斯         按远近给分,越远越不听
    中值         不算平均,排个队取中间那个 —— 极端值直接出局
    双边         只听「跟我像」的邻居 —— 跨过边的那些不听

验证六件事:
1. 盒式和高斯对「一个孤零零的亮点」的反应:一个是方块,一个是圆
2. ⚠️ 模糊不能直接相加,要按**勾股定理**加:先 σ=3 再 σ=4,等于一次 σ=5
   (实测差 0.006;当成 3+4=7 来算,差 37.1)
3. 盒式连做几次会自己变成高斯(中心极限定理),实测第 2 次就很像了
4. 核太小会把高斯「截断」:σ=3 配 3×3 的核,理想高斯有 61.5% 被切掉了
5. 对症下药:椒盐噪声上中值完胜(29.5 vs 23.2 dB),
   高斯噪声上反过来(28.0 vs 26.9 dB),双边最好(28.9 dB)
6. 耗时:盒式最快,高斯差不多,中值贵 2 倍,双边贵 20 倍以上

用法:
    .venv/bin/python Ch03_Spatial_Filtering/22_smoothing.py [--show]
    结果图保存到 Assets/results/smoothing-kernels.png(核长什么样、效果对比)
                     Assets/results/denoise-compare.png(对症下药 + 边缘剖面)
"""

import sys
import time
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


def hr(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def load_gray(name: str) -> npt.NDArray[np.uint8]:
    path = REPO / "Assets" / "test-images" / name
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise SystemExit(f"读不到 {path}")
    return np.asarray(img, dtype=np.uint8)


def psnr(a: npt.NDArray, b: npt.NDArray) -> float:
    """峰值信噪比,dB。越高越接近原图。"""
    mse = float(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2))
    return float("inf") if mse == 0 else 10.0 * np.log10(255.0 * 255.0 / mse)


def salt_pepper(img: npt.NDArray[np.uint8], ratio: float = 0.10,
                seed: int = 0) -> npt.NDArray[np.uint8]:
    """椒盐噪声:随机把一部分像素打成纯黑(椒)或纯白(盐)。

    这种噪声的特点是**极端**——不是「有点偏」,是直接跳到 0 或 255。
    传感器坏点、传输误码都长这样。
    """
    rng = np.random.default_rng(seed)
    out = img.copy()
    m = rng.random(img.shape)
    out[m < ratio / 2] = 0
    out[m > 1 - ratio / 2] = 255
    return out


def gaussian_noise(img: npt.NDArray[np.uint8], sigma: float = 20.0,
                   seed: int = 1) -> npt.NDArray[np.uint8]:
    """高斯噪声:每个像素都被轻轻推一下,推多少服从正态分布。

    这是「正常」的传感器噪声:大部分偏一点点,偶尔偏多一点,没有极端值。
    """
    rng = np.random.default_rng(seed)
    return np.clip(np.rint(img.astype(np.float64) + rng.normal(0, sigma, img.shape)),
                   0, 255).astype(np.uint8)


def bench(fn, repeat: int = 20) -> float:
    fn()
    t0 = time.perf_counter()
    for _ in range(repeat):
        fn()
    return (time.perf_counter() - t0) / repeat * 1000


# ---------------------------------------------------------------- 1
def demo_point_response() -> None:
    hr("1. 盒式 vs 高斯:对「一个孤零零的亮点」的反应")
    imp = np.zeros((41, 41), np.float64)
    imp[20, 20] = 1.0
    box = cv2.blur(imp, (9, 9))
    gau = cv2.GaussianBlur(imp, (0, 0), 2.0)

    print("  拿一张全黑、正中间一个白点的图去过滤波器,看它被摊成什么形状:\n")
    print(f"  {'':<10s}{'中心值':>10s}{'亮起来的范围':>12s}   形状")
    for name, out in (("盒式 9×9", box), ("高斯 σ=2", gau)):
        on = out > out.max() * 0.01
        ys, xs = np.nonzero(on)
        span = f"{int(ys.max() - ys.min()) + 1}×{int(xs.max() - xs.min()) + 1}"
        shape = "方方正正的一块" if name.startswith("盒") else "中间浓四周淡,是个圆"
        print(f"  {name:<10s}{out.max():10.4f}{span:>12s}   {shape}")
    print("\n  盒式把这个点摊成了一个**方块**:因为它对 81 个邻居一视同仁,")
    print("  在方块边上「有没有被算进去」是突然切换的 —— 这就是方块感和振铃的来源。")
    print("  高斯摊成一个**圆**:越远的邻居权重越小,平滑地降到 0,所以边界不突兀。")
    print("  而且高斯是各个方向一样的(旋转对称),斜着和正着糊的程度相同;盒式做不到。")


# ---------------------------------------------------------------- 2
def demo_sigma_adds_in_quadrature(img: npt.NDArray[np.uint8]) -> None:
    hr("2. ⚠️ 模糊不能直接相加,要按勾股定理加")
    f = img.astype(np.float64)
    s1, s2 = 3.0, 4.0
    twice = cv2.GaussianBlur(cv2.GaussianBlur(f, (0, 0), s1), (0, 0), s2)
    right = cv2.GaussianBlur(f, (0, 0), float(np.hypot(s1, s2)))
    wrong = cv2.GaussianBlur(f, (0, 0), s1 + s2)
    print(f"  先做一次 σ={s1:.0f} 的高斯模糊,再做一次 σ={s2:.0f} 的,等于一次多大的?\n")
    print(f"    答案是 σ = √({s1:.0f}² + {s2:.0f}²) = {np.hypot(s1, s2):.0f}"
          f"   ← 最大差 {np.abs(twice - right).max():.3f}")
    print(f"    如果按 {s1:.0f} + {s2:.0f} = {s1 + s2:.0f} 来算"
          f"          ← 最大差 {np.abs(twice - wrong).max():.1f},差得离谱")
    print("\n  3、4、5 —— 正好是勾股数,拿来记这条规则再方便不过。")
    print("  为什么是平方相加:σ² 是方差,而两次独立的「随机抖动」叠加,方差才是可加的。")
    print("  实用价值:已经模糊过 σ=3 的图,想达到 σ=5 的效果,只需要再来一次 σ=4,不是 σ=2。")


# ---------------------------------------------------------------- 3
def demo_box_becomes_gaussian() -> None:
    hr("3. 盒式连做几次,会自己变成高斯")
    imp = np.zeros((81, 81), np.float64)
    imp[40, 40] = 1.0
    cur = imp.copy()
    print("  对同一张「一个亮点」的图,反复用 9×9 的盒式滤波:\n")
    print(f"  {'做几次':>6s}{'等效 σ':>9s}{'与同 σ 高斯的差(占峰值)':>24s}")
    for n in range(1, 5):
        cur = cv2.blur(cur, (9, 9))
        row = cur[40]
        var = float(((np.arange(81) - 40) ** 2) @ row / row.sum())
        sig = float(np.sqrt(var))
        gau = cv2.GaussianBlur(imp, (0, 0), sig)[40]
        rel = float(np.abs(row - gau).max() / row.max()) * 100
        print(f"  {n:>6d}{sig:9.2f}{rel:22.1f}%")
    print("\n  第 1 次还是个方方正正的东西(差了 93%),从第 2 次起就掉到 10% 上下 ——")
    print("  肉眼已经分不出它和真高斯了(剩下的零头是核被截断带来的抖动,不再变小)。")
    print("  这就是概率论里的**中心极限定理**:一堆各自随便什么形状的东西反复叠加,")
    print("  最后都会趋近正态(高斯)分布。")
    print("  工程上有人利用这一点:盒式滤波可以用积分图做到 O(1)/像素,")
    print("  连做三次得到「近似高斯」,比真高斯还快 —— 大核模糊的常用手法。")


# ---------------------------------------------------------------- 4
def demo_kernel_too_small() -> None:
    hr("4. 核太小,高斯就被「切掉」了")
    print("  高斯这条钟形曲线理论上是无限宽的,但核只有那么大,两边一定要切掉一截。")
    print("  切掉多少,取决于**核的边长是 σ 的几倍**:\n")
    print(f"  {'σ':>4s}{'ksize':>7s}{'k/σ':>7s}{'被切掉的比例':>14s}   够不够")
    sig = 3.0
    wide = np.arange(-90, 91)
    total = float(np.exp(-wide ** 2 / (2 * sig * sig)).sum())
    for k in (3, 5, 7, 9, 13, 19, 25):
        half = np.arange(-(k // 2), k // 2 + 1)
        kept = float(np.exp(-half ** 2 / (2 * sig * sig)).sum())
        cut = (1 - kept / total) * 100
        verdict = "太小,已经不是高斯了" if cut > 10 else ("勉强" if cut > 1 else "够了")
        print(f"  {sig:4.0f}{k:7d}{k / sig:7.1f}{cut:13.2f}%   {verdict}")
    print("\n  经验规则:**核边长取 6σ+1**(左右各留 3σ),切掉的不到 0.3%,肉眼绝对看不出。")
    print("  OpenCV 帮你处理了这件事:")
    print("    cv2.GaussianBlur(img, (0,0), sigma)   ← ksize 给 0,它按 σ 自动算核多大(推荐)")
    print("    cv2.GaussianBlur(img, (k,k), 0)       ← σ 给 0,它按 ksize 反推一个 σ")
    print("  最怕的是两个都自己写死还配不上,比如 σ=3 配 3×3 —— 名义上是高斯,实际不是。")


# ---------------------------------------------------------------- 5
def demo_right_tool(img: npt.NDArray[np.uint8]) -> None:
    hr("5. 对症下药:两种噪声,两种赢家")
    sp = salt_pepper(img, 0.10)
    gn = gaussian_noise(img, 20.0)

    print(f"  【椒盐噪声】10% 的像素被打成纯黑或纯白,PSNR {psnr(sp, img):.2f} dB\n")
    for name, out in (("盒式 5×5", cv2.blur(sp, (5, 5))),
                      ("高斯 5×5", cv2.GaussianBlur(sp, (5, 5), 1.0)),
                      ("中值 3×3", cv2.medianBlur(sp, 3)),
                      ("中值 5×5", cv2.medianBlur(sp, 5))):
        print(f"    {name:<10s}PSNR {psnr(out, img):6.2f} dB")
    print("\n    中值 3×3 比高斯高了 6 个多 dB —— 差距非常大。为什么?")
    print("    一个纯黑点(0)混进 9 个邻居里:")
    print("      **求平均**:它照样有 1/9 的发言权,把结果往下拽 → 黑点变成灰点,糊开了")
    print("      **取中位数**:排好队它站在最边上,中间那个根本不是它 → 直接出局,像没来过")
    print("    这就是「极端值」和「排序」的天生克制关系。")
    print("    注意中值 5×5 反而比 3×3 差(27.64 vs 29.50):噪声早就去干净了,")
    print("    再放大窗口只是在糊掉真正的细节。**窗口不是越大越好。**")

    print(f"\n  【高斯噪声】每个像素轻轻推一下(σ=20),PSNR {psnr(gn, img):.2f} dB\n")
    for name, out in (("高斯 5×5", cv2.GaussianBlur(gn, (5, 5), 1.0)),
                      ("中值 5×5", cv2.medianBlur(gn, 5)),
                      ("双边 d=9", cv2.bilateralFilter(gn, 9, 50, 50))):
        print(f"    {name:<10s}PSNR {psnr(out, img):6.2f} dB")
    pg = psnr(cv2.GaussianBlur(gn, (5, 5), 1.0), img)
    pm = psnr(cv2.medianBlur(gn, 5), img)
    pb = psnr(cv2.bilateralFilter(gn, 9, 50, 50), img)
    print(f"\n    换成高斯噪声,排名就反过来了:高斯滤波 {pg:.2f} > 中值 {pm:.2f}。")
    print("    因为这次没有极端值可踢,噪声是「大家都偏一点」——")
    print("    这种情况求平均最划算(N 个独立的抖动一平均,幅度降到 1/√N)。")
    print(f"    双边最好({pb:.2f}):它一边平均一边躲着边缘走,细节保得更多。")
    print("\n  结论:**没有最好的平滑,只有对不对症。** 先看噪声长什么样,再挑工具。")


# ---------------------------------------------------------------- 6
def demo_cost(img: npt.NDArray[np.uint8]) -> None:
    hr("6. 代价")
    print(f"  512×512 上跑一次(单位 ms):\n")
    rows = (("盒式 cv2.blur 5×5", lambda: cv2.blur(img, (5, 5)), "最快。可以用积分图做到与核大小无关"),
            ("高斯 GaussianBlur 5×5", lambda: cv2.GaussianBlur(img, (5, 5), 1.0), "可分离,横竖各一遍"),
            ("中值 medianBlur 5×5", lambda: cv2.medianBlur(img, 5), "要排序,而且不可分离"),
            ("双边 bilateralFilter d=9", lambda: cv2.bilateralFilter(img, 9, 50, 50), "权重每个像素都要重算"))
    times = []
    for name, fn, note in rows:
        t = bench(fn)
        times.append(t)
        print(f"  {name:<26s}{t:7.3f} ms   {note}")
    print(f"\n  以盒式为 1 倍:高斯 {times[1] / times[0]:.1f} 倍,"
          f"中值 {times[2] / times[0]:.1f} 倍,双边 {times[3] / times[0]:.0f} 倍。")
    print("  实时视频里双边通常用不起,会换成引导滤波(guided filter)这类近似方案。")


# ---------------------------------------------------------------- 图板
def save_kernel_figure(out_path: Path, img: npt.NDArray[np.uint8]) -> None:
    """图板一:两种核对一个亮点的反应,以及实际效果。"""
    imp = np.zeros((41, 41), np.float64)
    imp[20, 20] = 1.0
    box = cv2.blur(imp, (9, 9))
    gau = cv2.GaussianBlur(imp, (0, 0), 2.0)

    fig, axes = plt.subplots(2, 3, figsize=(15.5, 9.4))

    axes[0, 0].imshow(box, cmap="magma")
    axes[0, 0].set_title("盒式 9×9 对一个亮点的反应\n摊成一个「方块」:81 个邻居一视同仁", fontsize=10)
    axes[0, 1].imshow(gau, cmap="magma")
    axes[0, 1].set_title("高斯 σ=2 对同一个亮点的反应\n摊成一个「圆」:越远权重越小", fontsize=10)
    for ax in axes[0, :2]:
        ax.axis("off")

    ax = axes[0, 2]
    ax.plot(np.arange(41) - 20, box[20], "o-", color="tab:blue", ms=3, lw=1.6,
            label="盒式 9×9:平顶,边上一刀切")
    ax.plot(np.arange(41) - 20, gau[20], "o-", color="tab:orange", ms=3, lw=1.6,
            label="高斯 σ=2:钟形,平滑降到 0")
    ax.set_xlim(-15, 15)
    ax.set_xlabel("离中心几个像素")
    ax.set_ylabel("这个邻居的话听几分")
    ax.set_title("横切一刀看权重\n盒式那个「断崖」就是方块感的来源", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    for ax, (pic, title) in zip(axes[1], (
            (img, "原图"),
            (cv2.blur(img, (9, 9)), "盒式 9×9\n糊了,但细看有方块状的痕迹"),
            (cv2.GaussianBlur(img, (0, 0), 2.0), "高斯 σ=2(≈9×9)\n同样糊,过渡更自然"))):
        ax.imshow(pic, cmap="gray", vmin=0, vmax=255)
        ax.set_title(title, fontsize=10)
        ax.axis("off")

    fig.suptitle("盒式 vs 高斯:区别在「怎么给邻居打分」", fontsize=13)
    # 每格标题两行,不留行距会压住上一行
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94), h_pad=3.0)
    fig.savefig(out_path, dpi=110)


def save_denoise_figure(out_path: Path, img: npt.NDArray[np.uint8]) -> None:
    """图板二:两种噪声各自的赢家,外加一条边缘剖面。"""
    sp = salt_pepper(img, 0.10)
    gn = gaussian_noise(img, 20.0)

    fig, axes = plt.subplots(2, 4, figsize=(17.5, 9.6))

    for ax, (pic, title) in zip(axes[0], (
            (sp, f"椒盐噪声 10%\nPSNR {psnr(sp, img):.2f} dB"),
            (cv2.GaussianBlur(sp, (5, 5), 1.0),
             f"高斯 5×5\n{psnr(cv2.GaussianBlur(sp, (5, 5), 1.0), img):.2f} dB —— 黑点被抹匀了"),
            (cv2.medianBlur(sp, 3),
             f"中值 3×3\n{psnr(cv2.medianBlur(sp, 3), img):.2f} dB —— 黑点直接消失"),
            (cv2.medianBlur(sp, 5),
             f"中值 5×5\n{psnr(cv2.medianBlur(sp, 5), img):.2f} dB —— 反而变差,细节被吃了"))):
        ax.imshow(pic, cmap="gray", vmin=0, vmax=255)
        ax.set_title(title, fontsize=9)
        ax.axis("off")

    for ax, (pic, title) in zip(axes[1, :3], (
            (gn, f"高斯噪声 σ=20\nPSNR {psnr(gn, img):.2f} dB"),
            (cv2.GaussianBlur(gn, (5, 5), 1.0),
             f"高斯 5×5\n{psnr(cv2.GaussianBlur(gn, (5, 5), 1.0), img):.2f} dB —— 这次它赢了"),
            (cv2.bilateralFilter(gn, 9, 50, 50),
             f"双边 d=9\n{psnr(cv2.bilateralFilter(gn, 9, 50, 50), img):.2f} dB —— 最好,但贵一个量级"))):
        ax.imshow(pic, cmap="gray", vmin=0, vmax=255)
        ax.set_title(title, fontsize=9)
        ax.axis("off")

    # 一条跨过强边缘的剖面:看谁把边糊了
    ax = axes[1, 3]
    row, lo, hi = 176, 38, 78     # 这一段正好从亮天空(≈250)跨到深色大衣(≈15)
    xs = np.arange(lo, hi)
    ax.plot(xs, img[row, lo:hi], color="black", lw=1.8, label="原图")
    ax.plot(xs, cv2.GaussianBlur(img, (0, 0), 3.0)[row, lo:hi],
            color="tab:blue", lw=1.5, label="高斯 σ=3:边被拉成斜坡")
    ax.plot(xs, cv2.bilateralFilter(img, 15, 80, 80)[row, lo:hi],
            color="tab:red", lw=1.5, label="双边:边还是立着的")
    ax.set_xlabel(f"第 {row} 行的列号")
    ax.set_ylabel("灰度")
    ax.set_title("横切一刀看边缘(天空 → 大衣,落差 240 级)\n"
                 "高斯把这一刀拉成了斜坡,双边基本还是直上直下", fontsize=9)
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)

    fig.suptitle("没有最好的平滑,只有对不对症:上排椒盐(中值赢),下排高斯噪声(高斯/双边赢)",
                 fontsize=13)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94), h_pad=3.0)
    fig.savefig(out_path, dpi=110)


def main() -> None:
    img = load_gray("camera.png")
    print(f"主图 camera.png  shape={img.shape}")

    demo_point_response()
    demo_sigma_adds_in_quadrature(img)
    demo_box_becomes_gaussian()
    demo_kernel_too_small()
    demo_right_tool(img)
    demo_cost(img)

    out = REPO / "Assets" / "results" / "smoothing-kernels.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    save_kernel_figure(out, img)
    print(f"\n结果已保存: {out.relative_to(REPO)}")

    den = out.with_name("denoise-compare.png")
    save_denoise_figure(den, img)
    print(f"结果已保存: {den.relative_to(REPO)}")

    if "--show" in sys.argv:
        plt.show()


if __name__ == "__main__":
    main()
