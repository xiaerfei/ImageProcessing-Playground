"""第 4 周(3.2 节):灰度变换 —— 06 比特平面分层:把 8 个二进制位拆开。

对应文档 Documents/02-intensity/gray-transform-tutorial.md 第四节 4.3。

一个 8 位像素比如 200,二进制是 11001000。把这 8 位一位一位拆开,
每一位单独拿出来就是一张黑白图,一共 8 张:

    planes[i] = (img >> i) & 1        i = 0(最低位)~ 7(最高位)

⚠️ 它和 01~05 篇不是一回事:前面都是「按值查表」的点运算(s = T(r)),
这里是**按二进制位拆解**,不是映射。之所以还挂在分段线性那一节下面,
是因为教材把它们并在一处讲,不是因为原理相同。

验证五件事:
1. 拆开再拼回去 = 原图:Σ planes[i]·2^i 与原图逐像素相同(无损分解)
2. 量化「高位是轮廓、低位是噪声」:用「与左邻居同值的比例」当指标,
   纯随机平面该是 0.500 —— 实测 bit-7 是 0.968,bit-0 正好 0.500
3. 位深削减:只保留高 N 位,数据量与 PSNR 的换算表(有损压缩的朴素版);
   这也是「8 位降到 4 位会发生什么」那个验收问题的答案 —— 伪轮廓
4. LSB 水印:把一张二值图塞进最低位,最大差 1、PSNR 51 dB,肉眼看不出来
5. ⚠️ 但 LSB 水印极脆:存成 JPEG 再读回,还原率掉到 0.5(= 瞎猜),
   PNG 无损才能保住 —— 只要重编码一次,藏在噪声层里的东西就没了

用法:
    .venv/bin/python Ch03_Spatial_Filtering/06_bit_planes.py [--show]
    结果图保存到 Assets/results/bit-planes-demo.png(8 个平面)
                     Assets/results/bit-plane-uses-demo.png(位深削减与 LSB 水印)
"""

import sys
import tempfile
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


def bit_plane(img: npt.NDArray[np.uint8], i: int) -> npt.NDArray[np.uint8]:
    """取第 i 位(0 = 最低位),返回 0/1 的数组。

    右移再与 1,比「除以 2^i 再取模」直观,也不会引入浮点。
    要显示的话再乘 255 —— 0/1 直接 imshow 会被当成两个挨着的暗值,几乎全黑。
    """
    return ((img >> i) & 1).astype(np.uint8)


def neighbor_agreement(plane: npt.NDArray[np.uint8]) -> float:
    """相邻像素同值的比例 —— 用来量化「这一层是结构还是噪声」。

    图像的相邻像素本来就高度相关,所以承载轮廓的高位平面这个值会接近 1;
    而纯随机的 0/1 就是抛硬币,期望正好 0.5。
    比「看图说话」硬,也比熵直观:熵只看 0/1 各占多少,分不出
    「棋盘格」和「一半黑一半白」,这个指标能。
    """
    return float(np.mean(plane[:, :-1] == plane[:, 1:]))


def psnr(a: npt.NDArray[np.uint8], b: npt.NDArray[np.uint8]) -> float:
    """峰值信噪比,dB。两图完全相同时返回 inf。"""
    mse = float(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2))
    return float("inf") if mse == 0 else 10 * np.log10(255.0 ** 2 / mse)


def keep_high_bits(img: npt.NDArray[np.uint8], n: int) -> npt.NDArray[np.uint8]:
    """只保留高 n 位,低位清零 —— 等价于把位深降到 n 位。"""
    mask = np.uint8((0xFF << (8 - n)) & 0xFF)
    return np.asarray(img & mask, dtype=np.uint8)


def load_gray(name: str) -> npt.NDArray[np.uint8]:
    img = cv2.imread(str(REPO / "Assets" / "test-images" / name), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise SystemExit(f"读图失败: {name}")
    return np.asarray(img, dtype=np.uint8)


def make_watermark(shape: tuple[int, int]) -> npt.NDArray[np.uint8]:
    """造一张二值水印(文字块),0/1 数组。"""
    h, w = shape
    canvas = np.zeros((h, w), np.uint8)
    cv2.putText(canvas, "TVU", (w // 8, h // 2), cv2.FONT_HERSHEY_SIMPLEX,
                4.0, 255, 18)
    return (canvas > 0).astype(np.uint8)


def save_planes_figure(out_path: Path, img: npt.NDArray[np.uint8]) -> None:
    """图板一:8 个比特平面并排,标题带权重和「与邻居同值」比例。"""
    fig, axes = plt.subplots(2, 4, figsize=(16, 8.4))
    for ax, i in zip(axes.flat, range(7, -1, -1)):
        plane = bit_plane(img, i)
        ax.imshow(plane * 255, cmap="gray", vmin=0, vmax=255)
        ax.set_title(f"bit-{i}(权重 {1 << i})\n与邻居同值 {neighbor_agreement(plane):.3f}",
                     fontsize=10)
        ax.axis("off")
    fig.suptitle("8 个比特平面:高位扛轮廓,低位是噪声"
                 "(纯随机该是 0.500)", fontsize=13)
    # 每格标题两行,不留行距会压住上一行的图
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.93), h_pad=3.0)
    fig.savefig(out_path, dpi=110)


def save_uses_figure(out_path: Path, img: npt.NDArray[np.uint8],
                     wm: npt.NDArray[np.uint8], stego: npt.NDArray[np.uint8],
                     jpeg_back: npt.NDArray[np.uint8]) -> None:
    """图板二:比特平面的两个实际用途 —— 位深削减与 LSB 水印。"""
    fig, axes = plt.subplots(2, 4, figsize=(16.5, 8.8))

    # 上排:位深削减。渐变图最能暴露伪轮廓 —— 平滑过渡被切成一条条台阶
    grad = load_gray("gradient.png")
    for ax, n in zip(axes[0, :3], (8, 4, 2)):
        ax.imshow(keep_high_bits(grad, n), cmap="gray", vmin=0, vmax=255)
        ax.set_title(f"渐变图保留高 {n} 位"
                     + ("(原图)" if n == 8 else f"\nPSNR {psnr(keep_high_bits(grad, n), grad):.1f} dB"),
                     fontsize=10)
        ax.axis("off")

    ax = axes[0, 3]
    ns = list(range(1, 9))
    ax.plot(ns, [psnr(keep_high_bits(img, n), img) if n < 8 else 60 for n in ns],
            "o-", color="tab:blue", lw=1.8, ms=4)
    ax.set_xlabel("保留的位数 n"); ax.set_ylabel("PSNR (dB)")
    ax.set_title("位深削减:每砍一位,PSNR 掉约 6 dB\n(n=8 无失真,图上按 60 画)",
                 fontsize=10)
    ax.grid(alpha=0.3)

    # 下排:LSB 水印
    for ax, (pic, title) in zip(axes[1], (
            (wm * 255, "要藏的水印(二值)"),
            (stego, f"塞进最低位后\n最大差 1,PSNR {psnr(stego, img):.1f} dB"),
            (bit_plane(stego, 0) * 255, "直接取 LSB → 完整还原"),
            (bit_plane(jpeg_back, 0) * 255,
             "存成 JPEG 再取 LSB → 全是雪花\n重编码一次就没了"))):
        ax.imshow(pic, cmap="gray", vmin=0, vmax=255)
        ax.set_title(title, fontsize=10)
        ax.axis("off")

    fig.suptitle("比特平面的两个用途:位深削减(朴素有损压缩)与 LSB 水印", fontsize=13)
    # 上排右下角有 x 轴标签,下排标题又是两行,不留行距会叠在一起
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.93), h_pad=3.0)
    fig.savefig(out_path, dpi=110)


def main() -> None:
    img = load_gray("lenna_s.jpg")
    print(f"原图 lenna_s.jpg  shape={img.shape}  dtype={img.dtype}")
    sample = int(img[0, 0])
    print(f"  举个例子:左上角像素 = {sample},二进制 {sample:08b}")

    # --- ① 拆开再拼回去 = 原图 ---
    planes = [bit_plane(img, i) for i in range(8)]
    rebuilt = np.zeros_like(img, dtype=np.uint16)
    for i, p in enumerate(planes):
        rebuilt += p.astype(np.uint16) << i
    print("\n--- ① 分解是无损的 ---")
    print(f"  Σ planes[i]·2^i 与原图逐像素相同: "
          f"{np.array_equal(rebuilt.astype(np.uint8), img)}")
    print("  8 张二值图 = 原图的全部信息,一位不多一位不少")

    # --- ② 量化「高位是轮廓,低位是噪声」 ---
    print("\n--- ② 每一层到底是结构还是噪声 ---")
    print(f"  {'位':>4s}{'权重':>7s}{'置 1 比例':>11s}{'与邻居同值':>12s}")
    for i in range(7, -1, -1):
        print(f"  {i:>4d}{1 << i:>7d}{planes[i].mean():>11.3f}"
              f"{neighbor_agreement(planes[i]):>12.3f}")
    print("  纯随机的 0/1 就是抛硬币,『与邻居同值』期望正好 0.500。")
    print(f"  bit-7 是 {neighbor_agreement(planes[7]):.3f}(高度结构化),"
          f"bit-0 是 {neighbor_agreement(planes[0]):.3f}(和噪声没区别)")
    print("  所以「高位扛轮廓、低位是噪声」不是看图说话,是能量出来的")

    # --- ③ 位深削减 ---
    print("\n--- ③ 只保留高 N 位:有损压缩的朴素版 ---")
    print(f"  {'保留位数':>9s}{'数据量':>9s}{'PSNR':>10s}{'最大差':>8s}")
    for n in range(8, 0, -1):
        q = keep_high_bits(img, n)
        p = psnr(q, img)
        p_txt = "无失真" if np.isinf(p) else f"{p:.1f} dB"
        print(f"  {n:>9d}{n / 8 * 100:>8.1f}%{p_txt:>10s}"
              f"{int(np.abs(q.astype(np.int16) - img.astype(np.int16)).max()):>8d}")
    print("  每砍一位,PSNR 掉约 6 dB(少一位 = 量化步长翻倍)。")
    print("  高 4 位就是「8 位降到 4 位」:数据量减半,PSNR 还有 29.5 dB,")
    print("  但平滑渐变处会出现**伪轮廓** —— 连续的过渡被切成一条条台阶(见图板)")

    # --- ④ LSB 水印 ---
    wm = make_watermark(img.shape)
    stego = np.asarray((img & 0xFE) | wm, dtype=np.uint8)
    print("\n--- ④ 把水印塞进最低位 ---")
    print(f"  水印占 {100 * wm.mean():.1f}% 的像素")
    print(f"  嵌入后与原图:最大差 "
          f"{int(np.abs(stego.astype(np.int16) - img.astype(np.int16)).max())},"
          f"PSNR {psnr(stego, img):.1f} dB —— 肉眼看不出来")
    print(f"  直接取 LSB 的还原率: {np.mean((stego & 1) == wm):.4f}")
    print("  能这么干,正是因为最低位本来就是噪声(见 ②),改了也不影响观感")

    # --- ⑤ 但它极脆 ---
    print("\n--- ⑤ ⚠️ 重编码一次,水印就没了 ---")
    jpeg_back = stego
    with tempfile.TemporaryDirectory() as tmp:
        for ext, params, label in (
                (".png", [], "PNG(无损)"),
                (".jpg", [cv2.IMWRITE_JPEG_QUALITY, 95], "JPEG q=95"),
                (".jpg", [cv2.IMWRITE_JPEG_QUALITY, 75], "JPEG q=75")):
            f = str(Path(tmp) / f"stego{label[:4]}{ext}")
            cv2.imwrite(f, stego, params)
            back = np.asarray(cv2.imread(f, cv2.IMREAD_GRAYSCALE), dtype=np.uint8)
            rate = float(np.mean((back & 1) == wm))
            print(f"  存成 {label:<11s} 再读回:还原率 {rate:.4f}"
                  + ("   ← 完整保住" if rate > 0.99 else "   ← 0.5 就是瞎猜,等于没了"))
            if ext == ".jpg" and params[1] == 95:
                jpeg_back = back
    print("  JPEG 是有损的,它按视觉重要性丢信息 —— 而最低位恰恰是它眼里最没用的部分。")
    print("  藏在噪声层里的东西,只要重编码一次就一起被丢掉了。")
    print("  真正抗攻击的水印要往变换域(DCT/DWT 系数)里塞,那是第 12~14 周的内容")

    # --- 出图板 ---
    out = REPO / "Assets" / "results" / "bit-planes-demo.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    save_planes_figure(out, img)
    print(f"\n结果已保存: {out.relative_to(REPO)}")

    uses = out.with_name("bit-plane-uses-demo.png")
    save_uses_figure(uses, img, wm, stego, jpeg_back)
    print(f"结果已保存: {uses.relative_to(REPO)}")

    if "--show" in sys.argv:
        plt.show()


if __name__ == "__main__":
    main()
