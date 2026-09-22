"""卷积能干什么、又干不了什么 —— 配合 01-spatial-filtering-basics.md 第零节。

为什么单独做一份:
    自学时问了一句「相关和卷积的作用是什么,提升暗部?」——
    这是个分类上的误会:卷积是**运算方式**不是**效果**,效果由核决定。
    而「提升暗部」恰好是卷积做不到的事,它需要区别对待亮像素和暗像素,
    卷积的权重却是写死的。这个反例最能把「点运算 vs 空间滤波」那条线立起来。

    文档第零节原本只说了「同一个灰度值在不同位置结果不同」(正面),
    缺一个反面例子。本脚本把两边都量出来。

生成 1 张(写到 Assets/results/):
    what-convolution-can-do.png

用法:
    .venv/bin/python Ch03_Spatial_Filtering/27_what_convolution_can_do.py [--show]
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import IMAGES, four_questions, save, show_gray, use_cjk_font  # noqa: E402

use_cjk_font()
import cv2  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

# 同一个卷积,换核换出完全不同的效果。名字 → (核, 显示时怎么归一)
KERNELS = {
    "原样不动": np.array([[0., 0, 0], [0, 1, 0], [0, 0, 0]]),
    "模糊": np.ones((5, 5)) / 25,
    "锐化": np.array([[0., -1, 0], [-1, 5, -1], [0, -1, 0]]),
    "找竖边": np.array([[-1., 0, 1], [-2, 0, 2], [-1, 0, 1]]),
    "浮雕": np.array([[-2., -1, 0], [-1, 1, 1], [0, 1, 2]]),
}


def load():
    return cv2.imread(str(IMAGES / "camera.png"), cv2.IMREAD_GRAYSCALE).astype(np.float64)


def quarters(img):
    """最暗四分之一 / 最亮四分之一的掩码。按原图分,后面才比得了。"""
    return img < np.percentile(img, 25), img > np.percentile(img, 75)


def main() -> None:
    img = load()
    dark, brit = quarters(img)

    fig = plt.figure(figsize=(15.0, 8.4))
    gs = fig.add_gridspec(2, 5, height_ratios=[1, 1], hspace=0.30, wspace=0.10)

    # ── 上排:同一个卷积,五张核
    for i, (name, k) in enumerate(KERNELS.items()):
        out = cv2.filter2D(img, cv2.CV_64F, k)
        ax = fig.add_subplot(gs[0, i])
        # 找竖边/浮雕的输出有正有负,不加偏移只会看到一片黑
        disp = out + 128 if k.sum() == 0 or name == "浮雕" else out
        show_gray(ax, np.clip(disp, 0, 255),
                  f"{name}\n核的和 = {k.sum():.0f}")

    # ── 下排左三:提升暗部,点运算做得到,卷积做不到
    gamma = 255 * (img / 255) ** 0.5
    louder = cv2.filter2D(img, cv2.CV_64F, np.outer([1., 2, 1], [1., 2, 1]) / 16 * 1.5)
    for i, (name, out) in enumerate((("原图", img),
                                     ("gamma 0.5(点运算)", gamma),
                                     ("核整体 ×1.5(卷积)", louder))):
        ax = fig.add_subplot(gs[1, i])
        blown = (np.clip(out, 0, 255) >= 255).mean() * 100
        show_gray(ax, np.clip(out, 0, 255),
                  f"{name}\n过曝 {blown:.2f}%" if i else f"{name}\n暗部 {img[dark].mean():.1f}"
                  f" / 亮部 {img[brit].mean():.1f}")

    # ── 下排右二:把上面三张的暗部/亮部涨幅摆在一起
    ax = fig.add_subplot(gs[1, 3:])
    names = ["gamma 0.5\n(点运算)", "整体 +40\n(点运算)", "高斯模糊\n(卷积)", "核 ×1.5\n(卷积)"]
    outs = [gamma, img + 40,
            cv2.filter2D(img, cv2.CV_64F, np.outer([1., 2, 1], [1., 2, 1]) / 16), louder]
    d = [np.clip(o, 0, 255)[dark].mean() - img[dark].mean() for o in outs]
    b = [np.clip(o, 0, 255)[brit].mean() - img[brit].mean() for o in outs]
    x = np.arange(len(names))
    ax.bar(x - 0.19, d, 0.36, label="暗部涨幅", color="#2c6fbb")
    ax.bar(x + 0.19, b, 0.36, label="亮部涨幅", color="#d95f02")
    for xi, (dv, bv) in enumerate(zip(d, b)):
        ax.text(xi - 0.19, dv + 1.5, f"{dv:+.0f}", ha="center", fontsize=8.5, color="#2c6fbb")
        ax.text(xi + 0.19, bv + 1.5, f"{bv:+.0f}", ha="center", fontsize=8.5, color="#d95f02")
    ax.axhline(0, color="#555", lw=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=8.6)
    ax.set_ylabel("灰度涨幅")
    ax.set_ylim(-4, 68)                 # 留够顶部空间,否则图例会压住 +46 那根
    ax.legend(fontsize=8.5, frameon=False, loc="upper center", ncol=2)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("「提升暗部」要的是暗部涨得比亮部多\n只有点运算做得到 —— 卷积反过来了",
                 fontsize=10.5)

    fig.suptitle("卷积是「怎么算」,不是「算出什么」 —— 效果全在核里", fontsize=13.5, y=0.955)
    four_questions(fig,
        "对邻居做一次加权和,\n权重由核给定。\n运算本身一个字没改,\n"
        "换核就换效果:\n模糊、锐化、找边、浮雕\n都是同一个卷积。",
        "凡是「必须看邻居」的活\n它都能干 —— 一个像素\n自己说了不算的事:\n"
        "去噪、模糊、锐化、\n找边缘、浮雕、\n模板匹配。",
        "「只看自己」的活它干不了。\n权重是写死的,不看\n当前像素多亮 ——\n"
        "所以提升暗部、拉对比度、\n调色调这些要**区别对待**的,\n卷积做不到。",
        "核一旦固定,\n就无法因地制宜:\n边缘和平坦区一视同仁,\n"
        "模糊必然连边一起糊掉。\n另外算完可能越界,\n要留够位宽再夹回 8 位。",
        "要区别对待亮暗 → 点运算\n(伽马、LUT、直方图);\n要因地制宜 → 非线性滤波\n"
        "(双边、引导、NLM);\n要让机器自己定核 → CNN。",
        y=0.02, bottom=0.215)
    save(fig, "what-convolution-can-do.png")
    verify()


def verify() -> None:
    """文档第零节引用的每个数字。"""
    img = load()
    dark, brit = quarters(img)
    print(f"\n── 原图:暗部均值 {img[dark].mean():.1f}  亮部均值 {img[brit].mean():.1f}")

    def report(name, out):
        out = np.clip(out, 0, 255)
        print(f"     {name:24} 暗部 {out[dark].mean() - img[dark].mean():+6.1f}"
              f"   亮部 {out[brit].mean() - img[brit].mean():+6.1f}"
              f"   过曝 {(out >= 255).mean() * 100:5.2f}%")

    print("\n── 提升暗部:点运算 vs 卷积")
    report("gamma 0.5(点运算)", 255 * (img / 255) ** 0.5)
    report("整体 +40(点运算)", img + 40)
    g = np.outer([1., 2, 1], [1., 2, 1]) / 16
    report("高斯模糊(卷积)", cv2.filter2D(img, cv2.CV_64F, g))
    report("同一个核 ×1.5(卷积)", cv2.filter2D(img, cv2.CV_64F, g * 1.5))

    print("\n── 同一个卷积,换核换效果")
    for name, k in KERNELS.items():
        out = cv2.filter2D(img, cv2.CV_64F, k)
        print(f"     {name:10} 和={k.sum():5.2f}  输出范围 [{out.min():7.1f}, {out.max():6.1f}]"
              f"  与原图均方差 {np.sqrt(((np.clip(out, 0, 255) - img) ** 2).mean()):6.2f}")

    print("\n── 相关和卷积差在哪儿(核转不转 180°)")
    for name, k in (("[1,2,1] 高斯(对称)", g),
                    ("Sobel(左右反号)", KERNELS["找竖边"]),
                    ("浮雕(完全不对称)", KERNELS["浮雕"])):
        corr = cv2.filter2D(img, cv2.CV_64F, k)                # OpenCV 做的是相关
        conv = cv2.filter2D(img, cv2.CV_64F, k[::-1, ::-1])    # 转 180° 才是卷积
        print(f"     {name:22} 两者最大差 {np.abs(corr - conv).max():7.1f}")


if __name__ == "__main__":
    main()
    if "--show" in sys.argv:
        plt.show()
