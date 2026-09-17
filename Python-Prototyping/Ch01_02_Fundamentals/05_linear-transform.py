"""第 4 周(3.2 节):灰度变换 —— 03 线性变换 s = a·r + b。

对应文档 Documents/02-intensity/intensity-and-grayscale.md 第一节。

    s = a·r + b        a 是斜率(对比度旋钮),b 是截距(亮度旋钮)

这是所有灰度变换里最基础的一条,前面学的**反转就是它的特例**(a = -1,b = 255)。
它也还是点运算,所以照旧「先建 256 项 LUT,再让全图查表」。

两个旋钮干的事完全不同,这是最容易含糊的地方:
    b —— 每个像素一律加 b,整条直线上下平移。这才是真正的「整体提亮」。
    a —— 每个像素乘 a,整条直线绕原点转动。纯黑一动不动,越亮涨得越多。

验证六件事:
1. 两个旋钮各管各的:+b 只挪均值不动标准差;×a 把均值和标准差同时放大 a 倍
2. a 不是整体提亮:r=0 加 0、r=50 加 50、r=200 直接爆表(a=2 时)
3. 反转确实是特例:a=-1、b=255 的 LUT 与 03 篇的 255-r 逐像素相同
4. ⚠️ 截断不可逆:a=2 提上去再 a=0.5 压回来,回不到原图 —— 冲出 255 的那部分被永久拍平
5. ⚠️ cv2.convertScaleAbs 不能拿来当线性变换:它对负数取绝对值,
   减暗时暗部会"反弹"变亮(0-80 应该饱和到 0,它给你 80)
6. 直线的根本局限:扫描 a 看截断比例怎么涨 —— 想让暗部更陡,亮部就必然被拍平。
   这正是下一篇对数/伽马存在的理由
7. 梳齿:a>1 拉伸后直方图变成一排梳子齿。点运算只能把已有的灰阶搬家,
   不能凭空造出新的,拉开之后中间必然空出一格格

用法:
    .venv/bin/python Ch01_02_Fundamentals/05_linear-transform.py [--show]
    结果图保存到 Assets/results/linear-transform-demo.png
    (Assets/results/linear-transform.png 是文档里那张示意图,另一回事,不要混)
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


def linear_lut(a: float, b: float) -> npt.NDArray[np.uint8]:
    """s = a·r + b 的 256 项查找表。

    clip 不是可有可无的收尾,它就是这个变换的一部分:a > 1 时高灰阶会算出
    255 以上,a < 0 或 b < 0 时低灰阶会算出负数,不夹住的话 astype(np.uint8)
    会按 256 取模回绕 —— 提亮后的高光不是变白而是变黑斑。
    取整规矩见 Documents/01-fundamentals/rounding-and-float.md。
    """
    r = np.arange(256, dtype=np.float64)
    s = a * r + b
    return np.clip(np.rint(s), 0, 255).astype(np.uint8)


def apply_linear(img: cv2.typing.MatLike, a: float, b: float) -> npt.NDArray[np.uint8]:
    """按 LUT 做线性变换。灰度图和彩色图都能直接喂进来。"""
    return np.asarray(cv2.LUT(img, linear_lut(a, b)), dtype=np.uint8)


def histogram(y: npt.NDArray[np.uint8]) -> npt.NDArray[np.int64]:
    """0~255 每个灰阶的像素个数,长度恒为 256。

    用 bincount 而不是 np.histogram:后者要分 bin,256 个 bin 铺在 [0,255] 上
    每个宽 255/256,边界会和整数灰阶错位,两端柱子会莫名其妙偏矮。
    """
    return np.bincount(y.ravel(), minlength=256)


def clipped_ratio(lut: npt.NDArray[np.uint8], hist: npt.NDArray[np.int64]) -> float:
    """这张 LUT 会把百分之多少的像素拍到 0 或 255 上(即丢掉细节的比例)。

    只数被**变换拍平**的,不数原图本来就是 0/255 的:后者不是这次操作造成的损失。
    """
    newly_clipped = ((lut == 0) | (lut == 255)) & ~((np.arange(256) == 0)
                                                   | (np.arange(256) == 255))
    return float(hist[newly_clipped].sum() / hist.sum())


def main() -> None:
    path = REPO / "Assets" / "test-images" / "lenna_s.jpg"
    bgr = cv2.imread(str(path))
    # 用 raise 不用 assert:assert 在 python -O 下会被剥掉,
    # 读图失败就会带着 None 一路跑到 cvtColor 里炸出看不懂的报错。
    if bgr is None:
        raise SystemExit(f"读图失败: {path}")

    gray = np.asarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), dtype=np.uint8)
    hist = histogram(gray)
    print(f"原图 {path.name}  灰度 shape={gray.shape}  "
          f"均值 {gray.mean():.2f}  标准差 {gray.std():.2f}")

    # --- ① 两个旋钮各管各的 ---
    B_SHIFT, A_GAIN = 60.0, 1.8
    only_b = apply_linear(gray, 1.0, B_SHIFT)
    only_a = apply_linear(gray, A_GAIN, 0.0)
    print("\n--- ① 两个旋钮分别在动什么 ---")
    print(f"  {'':16s}{'均值':>8s}{'标准差':>9s}")
    print(f"  原图            {gray.mean():8.2f}{gray.std():9.2f}")
    print(f"  只加 b=+{B_SHIFT:<5.0f}    {only_b.mean():8.2f}{only_b.std():9.2f}"
          f"   ← 均值 +{B_SHIFT:.0f},标准差几乎不动:亮度变了,对比度没变")
    print(f"  只乘 a={A_GAIN:<6.1f}   {only_a.mean():8.2f}{only_a.std():9.2f}"
          f"   ← 均值和标准差一起 ×{A_GAIN}:对比度真的被拉开了")
    print("  (两者都略低于理论值,因为超出 255 的部分被截断拍平了)")

    # --- ② a 不是「整体提亮」 ---
    lut_a2 = linear_lut(2.0, 0.0)
    print("\n--- ② a=2 时各灰阶实际涨了多少 ---")
    for r in (0, 5, 50, 128, 200):
        print(f"  r={r:<4d} → s={int(lut_a2[r]):<4d} 增量 {int(lut_a2[r]) - r:+4d}"
              + ("   ← 纯黑一动不动" if r == 0 else "")
              + ("   ← 早就爆了,被拍在 255" if lut_a2[r] == 255 else ""))
    print("  越亮涨得越多、纯黑不动 —— 这就是 a 和 b 的本质区别")

    # --- ③ 反转是它的特例 ---
    inv_linear = linear_lut(-1.0, 255.0)
    inv_direct = np.clip(255 - np.arange(256), 0, 255).astype(np.uint8)
    print("\n--- ③ 反转 = a·r+b 的特例 ---")
    print(f"  a=-1, b=255 的 LUT 与 255-r 是否逐项相同: "
          f"{np.array_equal(inv_linear, inv_direct)}")

    # --- ④ 截断不可逆 ---
    up = apply_linear(gray, 2.0, 0.0)
    back = apply_linear(up, 0.5, 0.0)
    diff = np.abs(back.astype(np.int16) - gray.astype(np.int16))
    n_saturated = int((gray.astype(np.float64) * 2.0 > 255).sum())
    print("\n--- ④ 截断不可逆:a=2 提上去,再 a=0.5 压回来 ---")
    print(f"  提亮时被拍到 255 的像素:{n_saturated} 个 "
          f"({100 * n_saturated / gray.size:.1f}%)")
    print(f"  压回来后与原图:最大差 {int(diff.max())},不一致 {int(np.count_nonzero(diff))} 个像素 "
          f"({100 * np.count_nonzero(diff) / gray.size:.1f}%)")
    print("  乘法本身可逆,截断不可逆 —— 拍平的层次永远回不来")

    # --- ⑤ cv2.convertScaleAbs 的坑 ---
    probe = np.array([[0, 50, 100, 200, 255]], np.uint8)
    print("\n--- ⑤ 为什么不用 cv2.convertScaleAbs 做线性变换 ---")
    print(f"  输入                       {probe.ravel().tolist()}")
    print(f"  convertScaleAbs(a=1,b=-80) "
          f"{cv2.convertScaleAbs(probe, alpha=1, beta=-80).ravel().tolist()}")
    print(f"  LUT 正确结果(饱和到 0)     "
          f"{apply_linear(probe, 1.0, -80.0).ravel().tolist()}")
    print("  名字里的 Abs 是字面意思:算出负数它取绝对值,不是夹到 0。")
    print("  减暗时暗部会「反弹」成亮点(0-80 应该是 0,它给 80)。a>0 且 b≥0 时才凑合能用")

    # --- ⑥ 直线的根本局限 ---
    gains = np.arange(1.0, 3.01, 0.25)
    ratios = [clipped_ratio(linear_lut(g, 0.0), hist) for g in gains]
    print("\n--- ⑥ 想让暗部更陡,亮部就得挨刀 ---")
    print("  " + "  ".join(f"a={g:.2f}" for g in gains))
    print("  " + "  ".join(f"{100 * x:5.1f}%" for x in ratios))
    print("  斜率是全局统一的:暗部拉开多少,亮部就被拍平多少。")
    print("  要「暗部陡、亮部平」,直线做不到 —— 这正是对数和伽马存在的理由")

    # --- ⑦ 拉伸留下的梳齿 ---
    hist_a = histogram(only_a)
    empty_before = int(np.count_nonzero(hist[1:255] == 0))
    empty_after = int(np.count_nonzero(hist_a[1:255] == 0))
    pile = int(hist_a[255])
    print("\n--- ⑦ 拉伸之后直方图为什么变成一排梳子齿 ---")
    print(f"  1~254 里空着的灰阶:原图 {empty_before} 个 → a={A_GAIN} 后 {empty_after} 个")
    print(f"  灰阶 255 上堆了 {pile} 个像素({100 * pile / only_a.size:.1f}%),"
          f"是原图峰值的 {pile / hist.max():.1f} 倍")
    print("  点运算只能把已有的灰阶搬家,不能凭空造新的:256 个值摊到更宽的范围,")
    print("  中间就必然空出一格格。这不是画图的毛刺,是信息量本来就没增加")

    # --- 出图板 ---
    fig, axes = plt.subplots(2, 3, figsize=(15.5, 9.5))
    levels = np.arange(256)

    panels = [
        (gray, f"原图 Y′   均值 {gray.mean():.0f}  标准差 {gray.std():.0f}"),
        (only_b, f"只加 b=+{B_SHIFT:.0f}:整体提亮,层次原封不动\n"
                 f"均值 {only_b.mean():.0f}  标准差 {only_b.std():.0f}"),
        (only_a, f"只乘 a={A_GAIN}:对比度拉开,高光被拍平\n"
                 f"均值 {only_a.mean():.0f}  标准差 {only_a.std():.0f}"),
    ]
    for ax, (img, title) in zip(axes.flat[:3], panels):
        ax.imshow(img, cmap="gray", vmin=0, vmax=255)   # 灰度图必须给死 vmin/vmax
        ax.set_title(title, fontsize=10)
        ax.axis("off")

    # 映射曲线族:一眼看出 b 是平移、a 是转动
    ax = axes.flat[3]
    ax.plot([0, 255], [0, 255], color="0.78", lw=3.0, label="原样 a=1, b=0")
    ax.plot(levels, linear_lut(1.0, B_SHIFT), color="tab:green", lw=1.6,
            label=f"b=+{B_SHIFT:.0f}(平移)")
    ax.plot(levels, linear_lut(A_GAIN, 0.0), color="tab:blue", lw=1.6,
            label=f"a={A_GAIN}(转动)")
    ax.plot(levels, linear_lut(-1.0, 255.0), color="tab:orange", lw=1.4, ls="--",
            label="a=-1, b=255(就是反转)")
    ax.axhline(255, color="tab:red", lw=0.8, ls=":")
    ax.set_xlim(0, 255)
    ax.set_ylim(0, 255)
    ax.set_aspect("equal")   # 正方形,斜率才不会被拉变形
    ax.set_title("映射曲线:b 上下平移,a 绕原点转动", fontsize=11)
    ax.set_xlabel("输入灰阶 r")
    ax.set_ylabel("输出灰阶 s")
    ax.legend(fontsize=8, loc="lower right")

    # 直方图:平移 vs 拉伸,以及 255 处堆起来的那根柱子
    ax = axes.flat[4]
    ax.fill_between(levels, hist, color="0.72", label="原图", zorder=2)
    ax.plot(levels, histogram(only_b), color="tab:green", lw=1.3,
            label=f"b=+{B_SHIFT:.0f}:整条右移", zorder=3)
    ax.plot(levels, histogram(only_a), color="tab:blue", lw=1.3,
            label=f"a={A_GAIN}:横向拉伸 + 末端堆积", zorder=4)
    ax.set_xlim(0, 255)
    ax.set_ylim(0, float(hist.max()) * 1.12)
    # 255 上那根柱子有几万个像素,画出来会把纵轴压扁,所以截断纵轴改用文字标注
    ax.annotate(f"灰阶 255 堆了 {pile} 个\n(超出纵轴 {pile / (hist.max() * 1.12):.0f} 倍)",
                xy=(255, float(hist.max()) * 1.08), xytext=(168, float(hist.max()) * 0.66),
                fontsize=8, color="tab:red", ha="center",
                arrowprops={"arrowstyle": "->", "color": "tab:red", "lw": 1.0})
    ax.set_title(f"直方图:加法搬家,乘法抻开(中间空出 {empty_after} 个灰阶)", fontsize=11)
    ax.set_xlabel("灰阶")
    ax.set_ylabel("像素个数")
    ax.legend(fontsize=8, loc="upper right")

    # 截断比例随 a 的变化:直线方案的代价曲线
    ax = axes.flat[5]
    ax.plot(gains, [100 * x for x in ratios], "o-", color="tab:red", lw=1.6, ms=4)
    ax.fill_between(gains, [100 * x for x in ratios], color="tab:red", alpha=0.12)
    ax.set_xlabel("对比度旋钮 a")
    ax.set_ylabel("被拍平的像素占比 %")
    ax.set_title("代价曲线:a 拧得越大,丢掉的高光越多", fontsize=11)
    ax.grid(alpha=0.3)

    fig.tight_layout()
    out = REPO / "Assets" / "results" / "linear-transform-demo.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=110)
    print(f"\n结果已保存: {out.relative_to(REPO)}")

    if "--show" in sys.argv:
        plt.show()


if __name__ == "__main__":
    main()
