"""第 4 周(3.2 节):灰度变换 —— 04 幂律变换(伽马):装了旋钮的对数。

对应文档 Documents/02-intensity/gray-transform-tutorial.md 第三节、
        Documents/02-intensity/intensity-and-grayscale.md 第三节。

    s = 255 · (r / 255)^γ

和对数同一个思路(把暗部掰开),区别是**弯多少由 γ 说了算,而且能反向**:
    γ < 1  往上凸,提亮暗部(和对数同方向,但温和可调)
    γ = 1  直线,什么都不做
    γ > 1  往下凹,压暗

这是三种基本变换里最该记住的一个 —— 你的屏幕、相机、视频编码每一秒都在做它。

验证七件事:
1. γ 是个连续旋钮:0.3 / 0.5 / 1 / 2.2 / 3 五条曲线与效果并排,γ=1 恒等
2. 对数其实就是「固定档位的幂律」:扫描 γ 找出最接近对数的那一个(实测 γ≈0.21)
3. 和线性的根本区别:幂律**两端永远不动**(0→0、255→255),不存在线性那种截断
4. ⚠️ 但不截断 ≠ 不丢信息:γ>1 会把多个暗部灰阶压进同一个值,
   信息照样丢,只是丢法从「拍平在 255」变成「合并成一个值」
5. 必须先归一化再求幂:(r/255)^γ 不是 r^γ —— 漏了除以 255 会得到一片黑
6. 伽马校正是一来一回:存图时 1/2.2、显示时 2.2,串起来等于恒等
7. ⚠️ sRGB 不是纯幂律:最暗处接了一小段直线,与纯 γ=2.2 最大差约 2 个灰阶

用法:
    .venv/bin/python Ch03_Spatial_Filtering/04_gamma_transform.py [--show]
    结果图保存到 Assets/results/gamma-transform-demo.png
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
GAMMAS = (0.3, 0.5, 1.0, 2.2, 3.0)


def gamma_lut(gamma: float) -> npt.NDArray[np.uint8]:
    """s = 255·(r/255)^γ 的 256 项查找表。

    先除以 255 归一化再求幂,最后乘回 255 —— 这一步不能省。
    直接 r^γ 的话,γ<1 时 255^0.5 只有 16(整张图几乎全黑),
    γ>1 时 255^2.2 是 20 万(全部撑爆成白)。归一化保证了两端固定在 0 和 255。
    取整规矩见 Documents/01-fundamentals/rounding-and-float.md。
    """
    s = 255.0 * (LEVELS / 255.0) ** gamma
    return np.clip(np.rint(s), 0, 255).astype(np.uint8)


def log_lut() -> npt.NDArray[np.uint8]:
    """对数变换的 LUT,用来和幂律对照。c = 255/log(256) ≈ 45.99。"""
    s = 255.0 / np.log(256.0) * np.log(1.0 + LEVELS)
    return np.clip(np.rint(s), 0, 255).astype(np.uint8)


def srgb_decode(c: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """sRGB 的标准解码曲线(0~1 进,线性光出)。

    它不是纯幂律:c ≤ 0.04045 那一段是直线 c/12.92,再往上才是 2.4 次幂。
    接直线是为了避开原点附近导数发散(纯幂律在 0 处斜率无穷,对噪声极敏感)。
    """
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def histogram(y: npt.NDArray[np.uint8]) -> npt.NDArray[np.int64]:
    """0~255 每个灰阶的像素个数。用 bincount 避免分 bin 时的边界错位。"""
    return np.bincount(y.ravel(), minlength=256)


def main() -> None:
    path = REPO / "Assets" / "test-images" / "lenna_s.jpg"
    bgr = cv2.imread(str(path))
    # 用 raise 不用 assert:assert 在 python -O 下会被剥掉,
    # 读图失败就会带着 None 一路跑到 cvtColor 里炸出看不懂的报错。
    if bgr is None:
        raise SystemExit(f"读图失败: {path}")
    gray = np.asarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), dtype=np.uint8)
    print(f"原图 {path.name}  灰度 shape={gray.shape}  均值 {gray.mean():.2f}")

    # --- ① γ 是个连续旋钮 ---
    print("\n--- ① 同一张图,五个 γ ---")
    print(f"  {'γ':>5s}{'均值':>9s}{'中位数':>8s}   曲线方向")
    for g in GAMMAS:
        out = cv2.LUT(gray, gamma_lut(g))
        arrow = "恒等" if g == 1.0 else ("上凸,提亮" if g < 1 else "下凹,压暗")
        print(f"  {g:>5.1f}{out.mean():>9.2f}{np.median(out):>8.0f}   {arrow}")
    identical = np.array_equal(cv2.LUT(gray, gamma_lut(1.0)), gray)
    print(f"  γ=1 与原图逐像素相同: {identical}")

    # --- ② 对数 = 固定档位的幂律 ---
    lg = log_lut().astype(np.float64)
    scan = np.arange(0.05, 1.0, 0.01)
    diffs = [np.abs(gamma_lut(g).astype(np.float64) - lg).mean() for g in scan]
    best = int(np.argmin(diffs))
    print("\n--- ② 扫描 γ,找最像对数的那一个 ---")
    print(f"  最接近对数的 γ = {scan[best]:.2f},两条 LUT 平均差 {diffs[best]:.2f} 个灰阶")
    print("  所以:对数 = 固定档位的幂律(≈γ0.2,且只能往提亮方向);幂律 = 可调档位")

    # --- ③ 两端永远不动,不存在线性那种截断 ---
    print("\n--- ③ 和线性的根本区别:幂律不截断 ---")
    for g in GAMMAS:
        lut = gamma_lut(g)
        print(f"  γ={g:<4.1f} lut[0]={int(lut[0]):<4d} lut[255]={int(lut[255]):<4d} "
              f"单调递增={bool(np.all(np.diff(lut.astype(np.int16)) >= 0))}")
    print("  (r/255)^γ 在 0 和 1 处都等于自身,所以黑还是黑、白还是白 ——")
    print("  线性 a=2 会把一半像素拍在 255 上,幂律不会")

    # --- ④ 但不截断 ≠ 不丢信息 ---
    print("\n--- ④ 幂律丢信息的方式:把多个灰阶合并成一个 ---")
    hist = histogram(gray)
    for g in GAMMAS:
        lut = gamma_lut(g)
        merged = 256 - len(np.unique(lut))          # 有多少灰阶被并掉了
        out_levels = len(np.unique(cv2.LUT(gray, lut)))
        print(f"  γ={g:<4.1f} 256 个输入灰阶合并后只剩 {256 - merged:<4d} 个不同输出值"
              f"   这张图实际用到的灰阶 {len(np.unique(gray))} → {out_levels}")
    print("  γ 越远离 1,合并越狠。线性是「拍平在两端」,幂律是「中间挤到一起」,")
    print("  都是不可逆的 —— 点运算只能重排,不能新增灰度级")

    # --- ⑤ 忘了归一化会怎样 ---
    print("\n--- ⑤ 为什么必须先除以 255 ---")
    for g in (0.5, 2.2):
        wrong = np.clip(np.rint(LEVELS.astype(np.float64) ** g), 0, 255).astype(np.uint8)
        # 直接 r^γ 的值域是 [0, 255^γ],和 8 bit 对不上:γ<1 时够不着 255,
        # γ>1 时远远超出。归一化的作用就是把值域锁回 0~255。
        print(f"  γ={g}: 漏了归一化 → 输出范围 [{int(wrong.min())}, {int(wrong.max())}],"
              f"255 个输入里有 {int(np.count_nonzero(wrong == 255))} 个变成纯白、"
              f"{int(np.count_nonzero(wrong == 0))} 个变成纯黑"
              + ("   ← 最亮也才 16,整张图几乎全黑" if g < 1
                 else "   ← r≥13 全部撑爆成白"))

    # --- ⑥ 伽马校正:一来一回 ---
    encode = gamma_lut(1.0 / 2.2)     # 存图时压一次
    decode = gamma_lut(2.2)           # 显示时抬回来
    roundtrip = decode[encode]        # 查两次表
    d = np.abs(roundtrip.astype(np.int16) - LEVELS.astype(np.int16))
    print("\n--- ⑥ 伽马校正是一来一回 ---")
    print(f"  存图 γ=1/2.2 再显示 γ=2.2:与原值最大差 {int(d.max())} 个灰阶,"
          f"平均 {d.mean():.2f}")
    print("  差不为 0 是因为中间落回了一次 uint8(8 bit 只有 256 档,来回各量化一次)")

    # --- ⑦ sRGB 不是纯幂律 ---
    c = LEVELS / 255.0
    diff_srgb = np.abs(srgb_decode(c) - c ** 2.2) * 255.0
    print("\n--- ⑦ sRGB 不是纯粹的 γ=2.2 ---")
    print(f"  与纯幂律的差(折算到 0~255 刻度):最大 {diff_srgb.max():.2f},"
          f"平均 {diff_srgb.mean():.2f} 个灰阶")
    print("  差异集中在最暗处 —— sRGB 在 c ≤ 0.04045 接了一小段直线,")
    print("  避开纯幂律在 0 点斜率无穷、对噪声极敏感的问题。")
    print("  日常用 pow(x, 2.2) 近似够了,精确色彩管理不能这么糊")

    # --- 出图板 ---
    fig, axes = plt.subplots(2, 4, figsize=(17, 9))

    # 曲线族
    ax = axes[0, 0]
    for g in GAMMAS:
        ax.plot(LEVELS, gamma_lut(g), lw=1.8 if g != 1.0 else 2.4,
                color="0.5" if g == 1.0 else None, label=f"γ={g}")
    ax.set_xlim(0, 255); ax.set_ylim(0, 255); ax.set_aspect("equal")
    ax.set_title("曲线族:γ<1 上凸提亮,γ>1 下凹压暗", fontsize=10)
    ax.set_xlabel("输入 r"); ax.set_ylabel("输出 s")
    ax.legend(fontsize=8, loc="lower right")

    # 三张效果图
    for i, g in enumerate((0.3, 1.0, 3.0)):
        ax = axes[0, i + 1]
        ax.imshow(cv2.LUT(gray, gamma_lut(g)), cmap="gray", vmin=0, vmax=255)
        ax.set_title(f"γ={g}" + ("(原图)" if g == 1.0 else ""), fontsize=10)
        ax.axis("off")

    # 幂律 vs 对数
    ax = axes[1, 0]
    ax.plot([0, 255], [0, 255], color="0.7", lw=1.0, ls="--", label="不变")
    ax.plot(LEVELS, log_lut(), color="tab:red", lw=2.4, label="对数")
    ax.plot(LEVELS, gamma_lut(scan[best]), color="tab:blue", lw=1.5, ls="-.",
            label=f"幂律 γ={scan[best]:.2f}")
    ax.set_xlim(0, 255); ax.set_ylim(0, 255); ax.set_aspect("equal")
    ax.set_title(f"对数 ≈ 幂律 γ={scan[best]:.2f}(平均差 {diffs[best]:.1f} 灰阶)",
                 fontsize=10)
    ax.set_xlabel("输入 r"); ax.legend(fontsize=8, loc="lower right")

    # 直方图:γ<1 右移,γ>1 左移
    ax = axes[1, 1]
    h05 = histogram(cv2.LUT(gray, gamma_lut(0.5)))
    h22 = histogram(cv2.LUT(gray, gamma_lut(2.2)))
    ax.fill_between(LEVELS, hist, color="0.72", label="原图", zorder=2)
    ax.plot(LEVELS, h05, color="tab:blue", lw=1.2, label="γ=0.5 整体右移", zorder=3)
    ax.plot(LEVELS, h22, color="tab:orange", lw=1.2, label="γ=2.2 整体左移", zorder=4)
    # 纵轴按三条里最高的那根来,否则 γ=2.2 把灰阶挤到一起后冒出的尖峰会被切掉,
    # 看着像画错了 —— 而那个尖峰恰恰是「合并」这件事最直观的证据
    ax.set_xlim(0, 255)
    ax.set_ylim(0, float(max(hist.max(), h05.max(), h22.max())) * 1.05)
    ax.set_title("直方图:γ<1 往亮端搬,γ>1 往暗端搬", fontsize=10)
    ax.set_xlabel("灰阶"); ax.legend(fontsize=8, loc="upper right")

    # 合并掉的灰阶数:幂律的代价曲线
    ax = axes[1, 2]
    sweep = np.arange(0.2, 4.01, 0.1)
    merged = [256 - len(np.unique(gamma_lut(g))) for g in sweep]
    ax.plot(sweep, merged, color="tab:red", lw=1.8)
    ax.fill_between(sweep, merged, color="tab:red", alpha=0.12)
    ax.axvline(1.0, color="0.6", lw=0.9, ls="--")
    ax.set_xlabel("γ"); ax.set_ylabel("被合并掉的灰阶数")
    ax.set_title("代价曲线:γ 越远离 1,并掉的灰阶越多", fontsize=10)
    ax.grid(alpha=0.3)

    # sRGB vs 纯幂律
    ax = axes[1, 3]
    ax.plot(LEVELS, srgb_decode(c) * 255.0, color="tab:blue", lw=1.8, label="sRGB 标准曲线")
    ax.plot(LEVELS, (c ** 2.2) * 255.0, color="tab:orange", lw=1.4, ls="--",
            label="纯幂律 γ=2.2")
    ax.set_xlim(0, 60)   # 差异全在最暗处,放大这一段才看得见
    ax.set_ylim(0, 8)
    ax.set_title(f"sRGB 的直线段(最大差 {diff_srgb.max():.1f} 灰阶)", fontsize=10)
    ax.set_xlabel("输入 r(只画最暗的 0~60)"); ax.set_ylabel("线性光 ×255")
    ax.legend(fontsize=8, loc="upper left")

    fig.tight_layout()
    out = REPO / "Assets" / "results" / "gamma-transform-demo.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=110)
    print(f"\n结果已保存: {out.relative_to(REPO)}")

    if "--show" in sys.argv:
        plt.show()


if __name__ == "__main__":
    main()
