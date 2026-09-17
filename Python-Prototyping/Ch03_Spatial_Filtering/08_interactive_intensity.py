"""可拖滑块的灰度变换实验台 —— 参数一动,图像 / 直方图 / 映射曲线三者同时变。

为什么值得有这么一个东西:
    静态脚本每次改参数都要重跑一遍,看到的是一张张孤立的快照。
    而"γ 从 1.0 慢慢拖到 0.4,暗部怎么一点点浮起来、直方图怎么整体左移、
    映射曲线怎么从直线弯成上凸"—— 这个连续过程才是理解曲线的关键,
    截图是拍不出来的。

三块画面的分工(和 macOS 版 ImageAlgorithm 的直方图面板一致):
    左   变换结果
    右上 直方图 —— 灰色是原图,蓝色是结果
    右下 映射曲线 —— 横轴输入 r,纵轴输出 s,虚线是"什么都不做"的对角线

LUT 的算法和 ImageAlgorithm/Modules/IAIntensityModule.m 是同一套公式,
两边结果应当一致 —— 可以拿这个当那边的对照。

用法:
    .venv/bin/python Ch03_Spatial_Filtering/08_interactive_intensity.py
    .venv/bin/python Ch03_Spatial_Filtering/08_interactive_intensity.py --image ../Assets/test-images/page.png
    .venv/bin/python Ch03_Spatial_Filtering/08_interactive_intensity.py --save   # 只存一张静态图,不开窗口
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]
DEFAULT_IMAGE = REPO / "Assets" / "test-images" / "coffee.png"

MODES = ["线性 s=a·r+b", "幂律 (γ)", "对数", "分段拉伸", "反色"]


# --------------------------------------------------------------- LUT
def build_lut(mode: str, a: float, b: float, gamma: float,
              low: float, high: float) -> np.ndarray:
    """按当前参数生成 256 项查找表。

    点运算的输出只取决于当前像素值,与邻居无关 —— 所以 256 个可能的输入
    各算一次就够了,不必对几十万个像素逐个算。这是所有调色管线的做法。
    """
    r = np.arange(256, dtype=np.float64)

    if mode == MODES[0]:                       # 线性
        s = a * r + b
    elif mode == MODES[1]:                     # 幂律
        s = 255.0 * (r / 255.0) ** gamma
    elif mode == MODES[2]:                     # 对数
        s = (255.0 / np.log(256.0)) * np.log1p(r)
    elif mode == MODES[3]:                     # 分段拉伸
        span = max(high - low, 1.0)            # 防止低高重合时除以 0
        s = (r - low) * 255.0 / span
    else:                                      # 反色
        s = 255.0 - r

    # 超出 0~255 的部分被截断 —— 这一步不可逆,信息就此丢失
    return np.clip(s, 0, 255).astype(np.uint8)


def luma(bgr: np.ndarray) -> np.ndarray:
    """Rec.601 亮度。和 IAHistogram 的 lumaPlaneFrom 用同一套权重。"""
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)


def hist_norm(gray: np.ndarray) -> np.ndarray:
    """归一化直方图(总和为 1),这样不同尺寸的图能直接比形状。"""
    h = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    total = h.sum()
    return h / total if total else h


# --------------------------------------------------------------- 主体
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    ap.add_argument("--save", action="store_true",
                    help="不开窗口,只把初始状态存成一张图(给没有 GUI 的环境用)")
    args = ap.parse_args()

    import matplotlib
    if args.save:
        # Agg 是纯绘图后端,不需要窗口系统 —— 拖滑块自然也就没了
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Button, RadioButtons, Slider

    # 中文标签:macOS 自带这两个字体,缺了就退回英文,不让脚本因为字体挂掉
    matplotlib.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti SC", "sans-serif"]
    matplotlib.rcParams["axes.unicode_minus"] = False

    src = cv2.imread(str(args.image), cv2.IMREAD_COLOR)
    if src is None:
        raise SystemExit(f"读不到图片:{args.image}")
    src_rgb = cv2.cvtColor(src, cv2.COLOR_BGR2RGB)
    src_gray = luma(src)
    src_hist = hist_norm(src_gray)

    fig = plt.figure(figsize=(12, 7))
    fig.canvas.manager.set_window_title("灰度变换实验台")
    # 左半边留给图像,右半边上下分给直方图和映射曲线;
    # 底部 32% 空出来放控件 —— bottom=0.34 就是给它们让位
    gs = fig.add_gridspec(2, 2, left=0.05, right=0.97, top=0.95, bottom=0.34,
                          width_ratios=[1.45, 1], hspace=0.32, wspace=0.18)

    ax_img = fig.add_subplot(gs[:, 0])
    ax_img.set_title("变换结果", fontsize=10)
    ax_img.axis("off")
    im = ax_img.imshow(src_rgb)

    ax_hist = fig.add_subplot(gs[0, 1])
    ax_hist.set_title("直方图   灰=原图  蓝=结果", fontsize=9)
    ax_hist.set_xlim(0, 255)
    ax_hist.set_yticks([])
    ax_hist.fill_between(np.arange(256), src_hist, color="0.6", label="原图")
    (line_hist,) = ax_hist.plot(np.arange(256), src_hist, color="tab:blue", lw=1.2)

    ax_lut = fig.add_subplot(gs[1, 1])
    ax_lut.set_title("映射曲线   横轴 r → 纵轴 s", fontsize=9)
    ax_lut.set_xlim(0, 255)
    ax_lut.set_ylim(0, 255)
    # 对角线画粗、映射线画细:γ=1 之类的恒等情况下两者重合,
    # 粗细一样会看成"只有一条橙线",分不清是重合还是参考线没画出来
    ax_lut.plot([0, 255], [0, 255], "-", color="0.78", lw=3.0,
                label="什么都不做")   # 偏离它多远,就改动了多少
    (line_lut,) = ax_lut.plot(np.arange(256), np.arange(256),
                              color="tab:orange", lw=1.4)
    ax_lut.legend(fontsize=7, loc="upper left")

    # ---- 控件区 ----
    # add_axes 的四个数是 [左, 下, 宽, 高],取值 0~1 是相对整个窗口的比例。
    # 用手摆而不是交给 gridspec:控件高度必须固定,不能随窗口一起被拉伸变形。
    ax_mode = fig.add_axes([0.05, 0.04, 0.14, 0.24])
    ax_mode.set_title("变换方式", fontsize=9)
    radio = RadioButtons(ax_mode, MODES, active=1)
    for label in radio.labels:
        label.set_fontsize(8)

    def srow(y: float, label: str, lo: float, hi: float, init: float):
        ax = fig.add_axes([0.30, y, 0.52, 0.03])
        return Slider(ax, label, lo, hi, valinit=init)

    s_gamma = srow(0.245, "γ", 0.1, 3.0, 1.0)
    s_a     = srow(0.195, "a  斜率", -2.0, 3.0, 1.0)
    s_b     = srow(0.145, "b  截距", -255, 255, 0)
    s_low   = srow(0.095, "拉伸 低", 0, 255, 0)
    s_high  = srow(0.045, "拉伸 高", 0, 255, 255)

    ax_reset = fig.add_axes([0.87, 0.045, 0.10, 0.045])
    btn_reset = Button(ax_reset, "重置")

    status = fig.text(0.30, 0.295, "", fontsize=9, color="0.35")

    # ---- 联动 ----
    def update(_=None) -> None:
        mode = radio.value_selected
        low, high = s_low.val, s_high.val
        if low >= high:
            # 分段拉伸的分母是 high-low,重合就除以 0。
            # 这里只在显示上兜住,不去反写滑块 —— 反写会触发新一轮回调,容易打转
            high = low + 1.0

        lut = build_lut(mode, s_a.val, s_b.val, s_gamma.val, low, high)

        # 对彩色图的三个通道用同一张表 —— 三条曲线一致,所以不会偏色。
        # (分通道各用一张表就会偏色,那是直方图那一章的错误示范)
        out = cv2.LUT(src, lut)
        im.set_data(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))

        out_hist = hist_norm(luma(out))
        line_hist.set_ydata(out_hist)
        ax_hist.set_ylim(0, max(src_hist.max(), out_hist.max()) * 1.08)

        line_lut.set_ydata(lut)

        # 被压到 0 或 255 的输入值有多少 —— 截断意味着这些层次永久合并了
        clipped_lo = int((lut == 0).sum())
        clipped_hi = int((lut == 255).sum())
        g = luma(out)
        status.set_text(
            f"{mode}    均值 {g.mean():5.1f}   σ {g.std():5.1f}    "
            f"映射表两端压平:低 {clipped_lo} 级 / 高 {clipped_hi} 级"
        )
        fig.canvas.draw_idle()

    for s in (s_gamma, s_a, s_b, s_low, s_high):
        s.on_changed(update)
    radio.on_clicked(update)

    def reset(_) -> None:
        for s in (s_gamma, s_a, s_b, s_low, s_high):
            s.reset()
        update()

    btn_reset.on_clicked(reset)
    update()

    if args.save:
        out_path = Path(__file__).with_suffix(".png")
        fig.savefig(out_path, dpi=110)
        print(f"已存静态图:{out_path}")
        print("(Agg 后端没有窗口,滑块拖不动 —— 去掉 --save 才是交互模式)")
    else:
        plt.show()


if __name__ == "__main__":
    main()
