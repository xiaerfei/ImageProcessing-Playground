"""第 4 周(3.2 节):灰度变换 —— 03 对数变换:把暗部掰开。

对应文档 Documents/02-intensity/gray-transform-tutorial.md 第二节。

    s = c · log(1 + r)        c = 255 / log(256) ≈ 45.99

和反转一样,这还是个**点运算**,所以照样是「先建 256 项 LUT,再让全图查表」。
麻烦都在公式里那两个补丁上,它们不是数学原理,只是为了让它能在 8 位图像上跑起来:

    +1  —— 躲开 log(0) = -∞。顺带 log(1) 正好是 0,纯黑变换后还是纯黑。
    ×c  —— 把只有 0~5.55 的结果等比撑满 0~255。不乘的话存进去就是一片黑。

曲线形状:**左边陡、右边平**。陡 = 把挤在暗部的那点细节拉开,平 = 把亮部压扁。
注意它不是一个固定倍数的放大:增益随输入递减(r=10 放大 11 倍,r=200 只放大 1.2 倍),
所以暗部抬得猛、亮部几乎不动 —— 这才是它和"整体乘个系数"的本质区别。

验证六件事:
1. LUT 端点严丝合缝:lut[0] = 0(黑还是黑)、lut[255] = 255(白还是白),且单调递增;
   并且它**不是固定倍数放大** —— r=10 放大 11 倍,r=200 只放大 1.2 倍,增益随输入递减
2. 不加 ×c:裸 log 的值域只有 [0, 5.55],直接当灰度存下去 → 一片黑
3. 坑:既乘 c 又 min-max 归一化,c 会被归一化整个约掉,纯属白乘(实测三个 c 输出逐像素相同)
4. 那固定 c 和交给归一化差在哪:归一化按实际最大最小值反算 c,图里没有纯白时会更亮一截
5. 暗图提亮:挤在 0~51 的像素被摊到 0~181;纯黑像素的个数前后一模一样(log(1) = 0,黑不变灰)
6. 反例:同一个对数用在**正常曝光**的图上,亮部被压成一坨 —— 偏袒暗部是有代价的

> 对数真正无可替代的用途是**看傅里叶频谱**(幅度差几百万倍,不取对数屏幕上只剩中心一个白点)。
> 那属于第 11~14 周的内容,这里只做空域提亮。
> 脚本里只用手写公式 + `cv2.LUT`;`cv2.normalize` 只出现在"坑"的对照里,不用来出结果。

用法:
    .venv/bin/python Ch03_Spatial_Filtering/03_log_transform.py [--show]
    结果图保存到 Assets/results/log-transform-demo.png
    (Assets/results/log-transform.png 是另一张图,属于 intensity-and-grayscale.md,不要混)
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

LOG_C = 255.0 / np.log(256.0)   # ≈ 45.99,把 [0, log(256)] 撑满 [0, 255]
EXPOSURE = 0.2                  # 人为压暗到 20%,模拟低照度(欠曝)的图


def log_lut() -> npt.NDArray[np.uint8]:
    """s = c·log(1+r) 的 256 项查找表。"""
    r = np.arange(256, dtype=np.float64)
    # 用 log1p 而不是 np.log(1 + r):算的是同一个东西,但 r 很小时不丢精度
    # (r = 1e-9 时 1 + r 还是 1.0,log 出来是 0;log1p 能给出正确的小值)。
    s = LOG_C * np.log1p(r)
    return np.clip(s, 0, 255).astype(np.uint8)


def log_transform(img: cv2.typing.MatLike) -> cv2.typing.MatLike:
    """按 LUT 做对数变换。灰度图、彩色图都能直接喂进来(和反转同一个套路)。"""
    return cv2.LUT(img, log_lut())


def underexpose(img: npt.NDArray[np.uint8], factor: float = EXPOSURE) -> npt.NDArray[np.uint8]:
    """模拟欠曝:整体乘一个小于 1 的系数。

    真实拍暗了也是这个结果 —— 大量像素挤在低灰阶,亮部干脆没用到。
    乘的时候先升 float64,免得 uint8 直接乘又踩回绕的坑。
    """
    return np.clip(img.astype(np.float64) * factor, 0, 255).astype(np.uint8)


def histogram(y: cv2.typing.MatLike) -> npt.NDArray[np.int64]:
    """统计 0~255 每个灰阶的像素个数,返回长度恒为 256 的计数数组。"""
    return np.bincount(np.asarray(y, dtype=np.uint8).ravel(), minlength=256)


def minmax_norm(f: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """min-max 归一化:把实际范围撑满 0~255(等价 cv2.normalize(NORM_MINMAX))。

    只用在这个"坑"的对照里,不用它出结果。手写出来是为了让"归一化 = 自适应 c"
    这件事直接写在代码上:下面这行乘的 `255 / (hi - lo)`,就是公式里的 c。
    """
    lo, hi = float(f.min()), float(f.max())
    return np.clip((f - lo) * (255.0 / (hi - lo)), 0, 255)


def max_diff(a: cv2.typing.MatLike, b: cv2.typing.MatLike) -> int:
    """两张图的最大绝对差。相减前升 int16,否则 uint8 相减会回绕成假差值。"""
    return int(np.abs(a.astype(np.int16) - b.astype(np.int16)).max())


def main() -> None:
    path = REPO / "Assets" / "test-images" / "astronaut.png"
    bgr = cv2.imread(str(path))
    if bgr is None:
        raise SystemExit(f"读图失败: {path}")

    gray = np.asarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), dtype=np.uint8)
    dark = underexpose(gray)
    out = np.asarray(log_transform(dark), dtype=np.uint8)
    lut = log_lut()

    # 三条直方图:原图当基准,欠曝是变换前,out 是变换后。
    # 控制台和画图都要用,在这里算一次就够了。
    h_ref = histogram(gray)
    h_dark = histogram(dark)
    h_out = histogram(out)

    print(f"原图 {path.name}  灰度 {gray.shape}  dtype={gray.dtype}")
    print(f"c = 255 / log(256) = {LOG_C:.2f}")

    # --- ① LUT 的端点、单调性、以及"增益随输入递减" ---
    print("\n--- ① LUT:端点 / 单调性 / 增益 ---")
    print(f"  lut[0]   = {lut[0]:3d}   纯黑还是纯黑")
    print(f"  lut[255] = {lut[255]:3d}   纯白还是纯白")
    print(f"  单调递增 = {bool(np.all(np.diff(lut.astype(np.int16)) >= 0))}")
    print("  不是固定倍数放大:越暗放大越多,越亮几乎不动")
    for r in (1, 10, 100, 200, 255):
        s = LOG_C * np.log1p(r)
        print(f"    r={r:3d} → s={s:6.1f}   (LUT 存 {lut[r]:3d})   增益 {s / r:5.1f}×")
    # 亮部被压扁到什么程度:算出来比嘴说可信
    print(f"  亮部代价:r=200~255 这 56 个灰阶,被压进 {lut[200]}~255 的"
          f" {255 - int(lut[200]) + 1} 级里")

    # --- ② 两个补丁分别在防什么 ---
    print("\n--- ② +1 和 ×c 各防什么 ---")
    print("  +1 : log(0) = -inf(程序直接爆)。取 log1p 后 log(1) = 0,纯黑仍是纯黑")
    raw_float = np.log1p(dark.astype(np.float64))
    raw_u8 = raw_float.astype(np.uint8)
    # 这里必须转 int:raw_u8.max() 是 np.uint8,直接 100 * 它会静默回绕(300 → 44),
    # 和 GUIDE 里 uint8 的 200+100 = 44 是同一个坑
    raw_max = int(raw_u8.max())
    print(f"  ×c : 裸 log 的值域 [{raw_float.min():.2f}, {raw_float.max():.2f}],"
          f"直接 astype(uint8) 之后:")
    print(f"       最大灰度只有 {raw_max} / 255 = 全量程的 {100 * raw_max / 255:.1f}%,"
          f"所有像素全挤在 0~{raw_max} 这几级里")
    print("       → 肉眼就是一片黑(8 位存不下小数,那点层次直接被取整抹平)")

    # --- ③ 常见的坑:c 和 normalize 一起用 ---
    print("\n--- ③ 坑:既乘 c 又归一化 ---")
    scaled = []
    for c in (1.0, 2.0, 5.0):
        s = c * np.log1p(dark.astype(np.float64))
        scaled.append(minmax_norm(s).astype(np.uint8))
    print(f"  c=1 / 2 / 5 再 min-max 归一化,两两最大差 "
          f"{max_diff(scaled[0], scaled[1])} / {max_diff(scaled[0], scaled[2])}"
          f" → 三个输出逐像素相同")
    print("  原因:归一化本身就在干「把结果撑满 0~255」这件事,公式里的 c 被重新算了一遍")

    # --- ④ 那固定 c 和交给归一化,差在哪 ---
    print("\n--- ④ 固定 c 还是交给 min-max 归一化 ---")
    norm = minmax_norm(LOG_C * np.log1p(dark.astype(np.float64)))
    diff = np.abs(norm - out.astype(np.float64))
    print(f"  固定 c     :c = {LOG_C:.2f},输出范围 [{out.min()}, {out.max()}]")
    print(f"  归一化     :按实际最大最小值反算 c = {255 / np.log1p(float(dark.max())):.2f}"
          f"(这张图没有纯白,所以反算出来的 c 更大)")
    print(f"  两者差异   :平均 {diff.mean():.2f},最大 {diff.max():.0f} → 归一化会额外更亮一截")

    # --- ⑤ 效果:暗部掰开(含原图基准) ---
    print("\n--- ⑤ 效果:三条分布放一起看 ---")
    print(f"  {'':10s} {'均值':>7s} {'中位数':>7s} {'p99':>7s}   范围")
    for name, img in (("原图(基准)", gray), ("欠曝图", dark), ("对数后", out)):
        print(f"  {name:10s} {img.mean():7.1f} {np.percentile(img, 50):7.1f} "
              f"{np.percentile(img, 99):7.1f}   [{img.min()}, {img.max()}]")
    print(f"  欠曝把分布挤在 0~{int(dark.max())} 这 {int(dark.max()) + 1} 个灰阶里,"
          f"对数把它摊到 0~{int(out.max())}(约 {out.max() / max(int(dark.max()), 1):.1f} 倍宽)")
    # 纯黑那根尖峰:压暗会凭空制造一批"死黑",而它是对数唯一救不回来的部分
    n_black_ref = int(h_ref[0])
    n_black_dark = int(h_dark[0])
    print(f"  纯黑像素(值就是 0):原图 {n_black_ref} 个({100 * n_black_ref / gray.size:.1f}%)"
          f" → 压暗后 {n_black_dark} 个({100 * n_black_dark / dark.size:.1f}%)")
    print(f"    多出来的 {n_black_dark - n_black_ref} 个像素,细节已经死在 0 里;"
          f"对数也救不回来 —— log(1) = 0,0 查表还是 0")
    # 这句是重点:别把"摊开"误读成"还原"。
    # 峰位置只对欠曝/对数后有意义 —— 原图除了纯黑背景那根尖峰,分布本来就又宽又平,
    # 没有明显的主峰(平掉 0 之后最高的一格才 2000 出头)。
    peak_dark = int(h_dark[1:].argmax()) + 1
    peak_out = int(h_out[1:].argmax()) + 1
    span_ref = float(np.percentile(gray, 99) - np.percentile(gray, 1))
    span_out = float(np.percentile(out, 99) - np.percentile(out, 1))
    print(f"  峰的位置:欠曝 {peak_dark} → 对数后 {peak_out}"
          f"(原图没有主峰,分布本来就摊得开)")
    print(f"  但摊开 ≠ 还原:p1~p99 跨度 原图 {span_ref:.0f} 级 → 对数后 {span_out:.0f} 级,")
    print("  亮部被压紧、中位数还偏高 —— 对数只负责让暗部别埋在 0 里,不负责还原原来的层次")

    # --- ⑥ 反例:同一个对数用在正常曝光的图上 ---
    on_normal = np.asarray(log_transform(gray), dtype=np.uint8)
    print("\n--- ⑥ 反例:对数用在正常曝光的图上 ---")
    print(f"  中位数 {np.percentile(gray, 50):.0f} → {np.percentile(on_normal, 50):.0f}"
          f"(整张图被抬到高灰阶);p99 {np.percentile(gray, 99):.0f}"
          f" → {np.percentile(on_normal, 99):.0f}")
    print("  亮部被压成一坨、对比度反而下降 —— 对数偏袒暗部,亮部为主的图别用它")

    # --- 出对比图板 ---
    fig, axes = plt.subplots(2, 3, figsize=(15.5, 9.5))

    panels = [
        (gray, "原图(灰度,正常曝光)"),
        (dark, f"人为压暗到 {EXPOSURE:.0%} —— 模拟低照度"),
        (out, "对数变换后:暗部被掰开"),
    ]
    for ax, (img, title) in zip(axes[0], panels):
        # 灰度图必须给死 vmin/vmax,否则 matplotlib 会按当前图的最小最大值自动拉伸,
        # 一张全黑的图也能被显示出层次,看着像算法生效了其实没有
        ax.imshow(img, cmap="gray", vmin=0, vmax=255)
        ax.set_title(title, fontsize=11)
        ax.axis("off")

    # --- 映射曲线:两条曲线 + 一条对角线 ---
    ax = axes[1, 0]
    levels = np.arange(256)
    ax.plot([0, 255], [0, 255], color="0.78", lw=3.0, label="什么都不做 s = r")
    ax.plot(levels, np.log1p(levels), color="tab:blue", lw=1.2,
            label=f"裸 log(1+r):最高只到 {np.log1p(255):.2f}")
    ax.plot(levels, lut, color="tab:orange", lw=1.6, label=f"×c 之后:c = {LOG_C:.1f}")
    # 裸曲线是贴着横轴的,不标一下容易被当成"没画出来"
    ax.annotate("裸 log 贴在这条线上\n(值域 0~5.55,直接存就是一片黑)",
                xy=(150, float(np.log1p(150))), xytext=(8, 96), fontsize=8, color="tab:blue",
                arrowprops=dict(arrowstyle="->", color="tab:blue", lw=0.8))
    ax.set_xlim(0, 255)
    ax.set_ylim(0, 255)
    ax.set_aspect("equal")   # 正方形,斜率才不会被拉变形
    ax.set_title("映射曲线:左陡右平,×c 就是把裸 log 撑满 0~255", fontsize=11)
    ax.set_xlabel("输入 r")
    ax.set_ylabel("输出 s")
    ax.legend(fontsize=8, loc="lower right")

    # --- 直方图:原图(基准) / 欠曝 / 对数后,三条摆在一起 ---
    ax = axes[1, 1]
    med_ref = float(np.percentile(gray, 50))
    med_dark = float(np.percentile(dark, 50))
    med_out = float(np.percentile(out, 50))

    # 纵轴取对数:灰阶 0 那根尖峰有 3.6 万个纯黑像素,是主体峰值的 4 倍,
    # 线性刻度下其余部分会被压成一条平线,三条曲线的高低关系全看不出来。
    # 计数为 0 的灰阶挖成 nan —— 对数轴上 0 画不出来。
    def visible(h: npt.NDArray[np.int64]) -> npt.NDArray[np.float64]:
        return np.where(h > 0, h, np.nan)

    ax.fill_between(levels, visible(h_ref), color="0.75",
                    label=f"原图(正常曝光,中位数 {med_ref:.0f})")
    ax.plot(levels, visible(h_dark), color="tab:blue", lw=1.2,
            label=f"欠曝 {EXPOSURE:.0%}(中位数 {med_dark:.0f})")
    ax.plot(levels, visible(h_out), color="tab:orange", lw=1.5,
            label=f"对数变换后(中位数 {med_out:.0f})")

    # 三条中位数竖线:不用去目测,"挤到左边"和"摊回来"各差多少一目了然
    for x, color in ((med_ref, "0.5"), (med_dark, "tab:blue"), (med_out, "tab:orange")):
        ax.axvline(x, color=color, ls=":", lw=1.1)

    ax.set_xlim(0, 255)
    ax.set_yscale("log")
    ax.set_ylim(0.8, max(float(h_ref.max()), float(h_dark.max()), float(h_out.max())) * 1.5)
    # 峰值挪到哪去了,是这张图最想说的:39 → 169
    peak_d = int(h_dark[1:].argmax()) + 1
    peak_o = int(h_out[1:].argmax()) + 1
    ax.annotate(f"主体峰值 {peak_d} → {peak_o}",
                xy=(peak_o, float(h_out[peak_o])), xytext=(88, 11000), fontsize=8,
                color="tab:orange",
                arrowprops=dict(arrowstyle="->", color="tab:orange", lw=0.8))
    ax.set_title("直方图(纵轴取对数,虚线 = 各自中位数)\n"
                 "欠曝把分布挤到左边,对数再把它摊开 —— 但形状回不到原图", fontsize=10)
    ax.set_xlabel("灰阶")
    ax.set_ylabel("像素个数")
    ax.legend(fontsize=7, loc="upper right")

    # --- 不加 ×c 长什么样 ---
    ax = axes[1, 2]
    ax.imshow(raw_u8, cmap="gray", vmin=0, vmax=255)
    ax.set_title(f"不加 ×c:直接 log(1+r) 当灰度存\n"
                 f"最大灰度只有 {raw_max} / 255,层次全被抹平",
                 fontsize=11)
    ax.axis("off")

    fig.tight_layout()
    out_path = REPO / "Assets" / "results" / "log-transform-demo.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110)
    print(f"\n结果已保存: {out_path.relative_to(REPO)}")

    if "--show" in sys.argv:
        plt.show()


if __name__ == "__main__":
    main()
