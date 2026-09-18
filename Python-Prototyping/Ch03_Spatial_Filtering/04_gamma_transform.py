"""第 4 周(3.2 节):灰度变换 —— 04 幂律变换(伽马):装了旋钮的对数。

对应文档 Documents/02-intensity/02-gray-transform-tutorial.md 第三节、
        Documents/02-intensity/01-intensity-and-grayscale.md 第三节。

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
8. γ>1 的正经身份是**解码**,不是「调暗」效果:对已经 gamma 编码的图做 γ=2.2,
   等于把它解回线性光;屏幕拿到后还会再解码一次,所以看着「黑了两遍」
9. 域搞错的代价:黑白条纹缩小,编码域算出 128,线性域算出 188,差 60 个灰阶

用法:
    .venv/bin/python Ch03_Spatial_Filtering/04_gamma_transform.py [--show]
    结果图保存到 Assets/results/gamma-transform-demo.png(主图板)
                     Assets/results/gamma-domain-demo.png(编码域 vs 线性域)
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
    取整规矩见 Documents/01-fundamentals/02-rounding-and-float.md。
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


def srgb_encode(lin: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """sRGB 的标准编码曲线(线性光进,0~1 编码值出)。srgb_decode 的逆。

    线性光算完必须走这一步再送显示,否则屏幕会把它当编码值再解码一次,
    画面明显偏暗。参见 Documents/02-intensity/03-luma-and-linear-light.md 第六节。
    """
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)


def histogram(y: npt.NDArray[np.uint8]) -> npt.NDArray[np.int64]:
    """0~255 每个灰阶的像素个数。用 bincount 避免分 bin 时的边界错位。"""
    return np.bincount(y.ravel(), minlength=256)


def save_domain_demo(out_path: Path, gray: npt.NDArray[np.uint8]) -> None:
    """第二张图板:γ>1 是解码,以及「在哪个域做运算」的实际代价。

    左半边回答「为什么 γ=2.2 那张图黑得没法看」;
    右半边用黑白条纹缩小这个最经典的例子,说明域搞错会差多少。
    """
    fig, axes = plt.subplots(2, 3, figsize=(15.5, 8.6))

    # 上排:同一张图的三种身份
    dark = cv2.LUT(gray, gamma_lut(2.2))
    reencoded = np.clip(np.rint(srgb_encode(srgb_decode(gray / 255.0)) * 255), 0, 255
                        ).astype(np.uint8)
    for ax, (img, title) in zip(axes[0], (
            (gray, "原图(sRGB 编码值)\n屏幕会解码一次 → 正常"),
            (dark, "做了 γ=2.2 = 解码成线性光\n屏幕再解一次 → 黑了两遍"),
            (reencoded, "解码后重新编码送显示\n与原图逐像素相同"))):
        ax.imshow(img, cmap="gray", vmin=0, vmax=255)
        ax.set_title(title, fontsize=10)
        ax.axis("off")

    # 左下:编码值 ↔ 线性光的对照曲线
    ax = axes[1, 0]
    c = LEVELS / 255.0
    ax.plot(LEVELS, srgb_decode(c) * 255, color="tab:blue", lw=1.8, label="解码:编码值 → 线性光")
    ax.plot([0, 255], [0, 255], color="0.7", lw=1.0, ls="--", label="如果两者相等")
    ax.plot(128, srgb_decode(np.array(128 / 255.0)) * 255, "o", color="tab:red", ms=6)
    ax.annotate("中灰 128 的线性光只有 55\n(满格的 21.6%)", xy=(128, 55),
                xytext=(150, 175), fontsize=9, color="tab:red",
                arrowprops={"arrowstyle": "->", "color": "tab:red", "lw": 1.0})
    ax.set_xlim(0, 255); ax.set_ylim(0, 255); ax.set_aspect("equal")
    ax.set_title("编码值不是光量:中间的 128 只有两成光", fontsize=10)
    ax.set_xlabel("sRGB 编码值"); ax.set_ylabel("线性光 ×255")
    ax.legend(fontsize=8, loc="upper left")

    # 中下:黑白条纹
    stripes = np.zeros((120, 120), dtype=np.uint8)
    stripes[:, ::2] = 255            # 一列黑一列白,黑白各占一半
    axes[1, 1].imshow(stripes, cmap="gray", vmin=0, vmax=255, interpolation="nearest")
    axes[1, 1].set_title("黑白各半的细条纹\n把它缩成一个像素,该是多亮?", fontsize=10)
    axes[1, 1].axis("off")

    # 右下:两种做法的结果并排
    ax = axes[1, 2]
    naive = 128
    correct = int(round(float(srgb_encode(
        (srgb_decode(np.array(0.0)) + srgb_decode(np.array(1.0))) / 2)) * 255))
    ax.imshow(np.block([[np.full((120, 120), naive, np.uint8),
                         np.full((120, 120), correct, np.uint8)]]),
              cmap="gray", vmin=0, vmax=255)
    ax.set_title(f"编码域平均 = {naive}     线性域平均 = {correct}\n"
                 f"差 {correct - naive} 个灰阶,右边才是物理正确的", fontsize=10)
    ax.axis("off")

    fig.suptitle("γ>1 的正经身份是解码 —— 以及「在哪个域做运算」的代价", fontsize=13)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))
    fig.savefig(out_path, dpi=110)


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

    # --- ⑧ γ>1 的正经身份:解码,不是「调暗」效果 ---
    print("\n--- ⑧ 对已编码的图做 γ>1,做的其实是「解码」 ---")
    probe = np.array([10, 30, 60, 128, 200, 255], dtype=np.float64)
    lin = srgb_decode(probe / 255.0)
    print(f"  输入(sRGB 编码值)     {probe.astype(int).tolist()}")
    print(f"  解码后的线性光 ×255    {np.rint(lin * 255).astype(int).tolist()}")
    print(f"  再编码回去(往返)      "
          f"{np.rint(srgb_encode(lin) * 255).astype(int).tolist()}   ← 回到原值")
    print(f"  中灰 128 的线性光只有 {lin[3] * 100:.1f}% —— 看着在黑白正中间,"
          f"物理上只有五分之一的光")
    print("  所以脚本里 γ=2.2 那张图黑得没法看,不是变换有问题:")
    print("  lenna 是 JPEG,本来就是编码值;你解了一次,屏幕还会再解一次 = 黑了两遍。")
    print("  γ>1 当效果用时档位在 1.1~1.5(去雾感、压背景);2.2 是色彩管理的档位")

    # --- ⑨ 域搞错的代价:黑白条纹缩小 ---
    print("\n--- ⑨ 同一次缩小,在哪个域做差 60 个灰阶 ---")
    naive = (0 + 255) / 2
    correct = srgb_encode((srgb_decode(np.array(0.0)) + srgb_decode(np.array(1.0))) / 2)
    print(f"  黑白各半的细条纹,缩到一个像素:")
    print(f"    编码域直接平均            {naive:.0f}")
    print(f"    解码→平均→再编码(正确)  {float(correct) * 255:.0f}")
    print("  一半时间全亮、一半时间全黑,眼睛收到的光就是满格的一半 ——")
    print("  物理正确答案是 188,编码域算出的 128 偏暗了 60 个灰阶。")
    print("  缩放、模糊、多帧平均、Alpha 混合,严格说都该在线性域做")

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

    save_domain_demo(out.with_name("gamma-domain-demo.png"), gray)
    print(f"结果已保存: {out.with_name('gamma-domain-demo.png').relative_to(REPO)}")

    if "--show" in sys.argv:
        plt.show()


if __name__ == "__main__":
    main()
