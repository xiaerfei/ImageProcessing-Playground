"""给 02-intensity/03-luma-and-linear-light.md 补配图 —— 446 行,原先一张图都没有。

为什么要补:
    这一篇讲的三件事都是"反直觉但有确切数字"的类型:
    Luma 算错了却用了 70 年、线性光是对的却不能用 8 bit 存、
    视频里的黑不是 0 是 16。光看表格容易"读过就忘",看见色带和直方图的缺口才记得住。

    每张图按仓库约定成套回答四问(见 Documents/README.md「写作约定」)。

生成 4 张(全部写到 Assets/results/):
    luma-vs-luminance-error.png  编码域加权 vs 线性域加权:高饱和差 73,自然色差 0
    linear-8bit-banding.png      线性 8bit 的暗部色带,以及码值都花到哪儿去了
    yuv-limited-range.png        limited range:黑是 16 白是 235,当成 full 用会怎样
    y-to-screen.png              抄三份 = YUV(U=V=128)→RGB;以及 vmin/vmax 不给的坑

本篇第一、二节的配图沿用已有的 rgb-to-gray-weighting.png 与 brightness-definitions.png
(由同目录 02_brightness_doc_figures.py 生成),不重复造。

数字与 01_luma_vs_linear.py 共用同一套传递函数(sRGB 分段)和 Rec.709 权重,
所以图里的值和文档里那张表逐个对得上。

用法:
    .venv/bin/python Ch06_Color_Processing/03_luma_doc_figures.py [--show]
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import IMAGES, four_questions, save, show_gray, use_cjk_font  # noqa: E402

use_cjk_font()
import cv2  # noqa: E402
import matplotlib  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

W709 = (0.2126, 0.7152, 0.0722)


def to_linear(c):
    """sRGB 编码值(0~1)→ 线性光。

    暗部那段 c/12.92 是直线而不是幂函数:纯幂函数在 0 附近斜率无穷大,
    定点实现会炸,所以标准里接了一小段直线。
    """
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(v):
    """线性光 → sRGB 编码值,to_linear 的反函数。"""
    return np.where(v <= 0.0031308, v * 12.92, 1.055 * np.maximum(v, 0) ** (1 / 2.4) - 0.055)


# ═════════════════════════════════════ 图 1:Luma 错多少 ═════════════════


def fig_luma_error() -> None:
    """同一个颜色,两条路径算出来的"亮度"差多少。

    差的根源是顺序:gamma 是条弯曲线,加权平均是直的操作,
    弯的和直的换顺序结果就不一样 —— 和"两个 60 dB 叠加不是 120 dB"是同一回事。
    """
    colors = [("纯红", (255, 0, 0)), ("纯绿", (0, 255, 0)), ("纯蓝", (0, 0, 255)),
              ("纯黄", (255, 255, 0)), ("品红", (255, 0, 255)), ("青", (0, 255, 255)),
              ("中灰", (128, 128, 128)), ("肤色", (222, 184, 155)), ("暗绿", (34, 80, 40))]
    names, lumas, trues = [], [], []
    for name, rgb in colors:
        luma = sum(w * c for w, c in zip(W709, rgb))
        lin = to_linear(np.array(rgb, float) / 255.0)
        true = float(to_srgb(sum(w * c for w, c in zip(W709, lin)))) * 255
        names.append(name); lumas.append(luma); trues.append(true)
    diffs = [t - l for t, l in zip(trues, lumas)]

    fig = plt.figure(figsize=(13.4, 4.6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.35, 1, 1.1], wspace=0.3)

    # ── (a) 九个颜色的两个"亮度"并排
    ax = fig.add_subplot(gs[0])
    x = np.arange(len(names))
    ax.bar(x - 0.2, lumas, 0.4, label="Luma Y′:直接对编码值加权", color="#c4442a")
    ax.bar(x + 0.2, trues, 0.4, label="真实亮度:解码→加权→再编码", color="#2c6fbb")
    for i, d in enumerate(diffs):
        if abs(d) >= 3:
            ax.text(i, max(lumas[i], trues[i]) + 6, f"{d:+.0f}", ha="center",
                    fontsize=8.6, color="#c4442a")
    # 色块贴在横轴下面,一眼看出哪几个是高饱和色
    for i, (_, rgb) in enumerate(colors):
        ax.add_patch(plt.Rectangle((i - 0.35, -26), 0.7, 18, color=np.array(rgb) / 255,
                                   clip_on=False, ec="#bbb", lw=0.5))
    ax.set_xticks(x); ax.set_xticklabels(names, fontsize=9)
    ax.tick_params(axis="x", pad=22)
    ax.set_ylim(0, 310); ax.set_ylabel("亮度(0~255)")
    ax.legend(fontsize=8.6, loc="upper center")
    ax.set_title("同一个颜色,两条路径算出来的亮度\n左边三个高饱和色差到 70 以上", fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)

    # ── (b) 误差随饱和度怎么走 —— 解释"为什么还能用"
    ax = fig.add_subplot(gs[1])
    sats = np.linspace(0, 1, 41)
    for hue, label, color in [(0, "红相", "#c4442a"), (120 / 360, "绿相", "#2a8f4a"),
                              (240 / 360, "蓝相", "#2c6fbb")]:
        errs = []
        for s in sats:
            hsv = np.uint8([[[hue * 179, s * 255, 255]]])
            rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)[0, 0].astype(float)
            luma = sum(w * c for w, c in zip(W709, rgb))
            lin = to_linear(rgb / 255.0)
            true = float(to_srgb(sum(w * c for w, c in zip(W709, lin)))) * 255
            errs.append(true - luma)
        ax.plot(sats * 100, errs, lw=2, color=color, label=label)
    ax.axhline(0, color="#999", lw=0.9)
    ax.set_xlabel("饱和度(%)"); ax.set_ylabel("真实亮度 − Luma(灰阶)")
    ax.legend(fontsize=8.6)
    ax.set_title("饱和度一低,误差就归零\n这就是它能用 70 年的原因", fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)

    # ── (c) 真实照片上的每个像素:饱和度 vs 误差
    #     这一格是用来把 (b) 那条理论曲线落到真实数据上的。
    #     只画一张高饱和的图会以偏概全,所以三张一起画,并在标题里给出各自的平均。
    stats = []
    sat_all, err_all = [], []
    for fname in ("coffee.png", "lenna_s.jpg", "astronaut.png"):
        bgr = cv2.imread(str(IMAGES / fname))
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(float)
        e = to_srgb(to_linear(rgb / 255.0) @ np.array(W709)) * 255 - rgb @ np.array(W709)
        s = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[..., 1].astype(float) / 255 * 100
        stats.append((fname, s.mean(), e.mean(), np.median(e), e.max()))
        sat_all.append(s.ravel()); err_all.append(e.ravel())
    sat_all = np.concatenate(sat_all); err_all = np.concatenate(err_all)

    ax = fig.add_subplot(gs[2])
    ax.hist2d(sat_all, err_all, bins=(70, 70), range=[[0, 100], [-2, 35]],
              cmap="inferno", norm=matplotlib.colors.LogNorm())
    ax.set_xlabel("这个像素的饱和度(%)"); ax.set_ylabel("真实亮度 − Luma(灰阶)")
    ax.set_title("三张真实照片的每一个像素\n理论曲线在真实数据上确实成立", fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)
    note = "\n".join(f"{n:<14} 饱和度 {sm:4.0f}%  平均差 {em:4.2f}"
                      for n, sm, em, _, _ in stats)
    ax.text(0.03, 0.97, note, transform=ax.transAxes, va="top", fontsize=8,
            family="monospace" if False else None, color="#fff",
            bbox=dict(boxstyle="round,pad=0.35", fc="#333", ec="none", alpha=0.75))

    fig.suptitle("Luma 是「把三个分贝值直接加权平均」—— 数学上没道理,工程上用了 70 年",
                 fontsize=13, y=1.04)
    four_questions(fig,
        "跳过解码,直接对\ngamma 编码后的 R′G′B′\n加权求和。",
        "三个乘法一个加法,\n1953 年的电阻网络就能做,\n而且算出的一路信号\n刚好喂给黑白电视机。",
        f"高饱和色彻底失真:\n纯红差 {diffs[0]:+.0f}(Luma 说它\n是 54「很暗」,按真实光强\n该是 127「中灰」)。\n正式名字叫\nconstant luminance failure。",
        f"误差严格跟着饱和度走。\n三张真实照片:饱和度 {stats[0][1]:.0f}% 的\n"
        f"coffee 平均差 {stats[0][2]:.1f} 灰阶,\n"
        f"{stats[2][1]:.0f}% 的 astronaut 中位数只有 {stats[2][3]:.2f}。\n"
        "**不是 0,但远小于纯色的 73**。\n纯色 UI、图表、绿幕、霓虹灯\n这些场合会崩,得转线性。",
        y=-0.04, bottom=0.18)
    save(fig, "luma-vs-luminance-error.png")
    print(f"     纯红 {lumas[0]:.1f} vs {trues[0]:.1f}(差 {diffs[0]:+.1f})")
    for n, sm, em, med, mx in stats:
        print(f"       {n:<16} 饱和度 {sm:5.1f}%  平均 {em:5.2f} 中位 {med:5.2f} 最大 {mx:5.1f}")


# ═════════════════════════════════════ 图 2:8bit 装不下线性 ═════════════


def fig_linear_banding() -> None:
    """同样 256 档,分给光强的方式不同,暗部就是能看和不能看的区别。"""
    h, w = 150, 900
    # 横轴走的是**光强**(0~25%),两种编码各自量化到 8 bit 再解回来对比
    inten = np.linspace(0.0, 0.25, w)[None, :].repeat(h, 0)
    lin_q = np.round(inten * 255) / 255.0                      # 线性 8bit:平均分
    srgb_q = to_linear(np.round(to_srgb(inten) * 255) / 255.0)  # sRGB 8bit:编码后再分
    # 两条都转成 sRGB 显示值,这样屏幕上看到的才是同一个光强
    band_lin = (to_srgb(lin_q) * 255).astype(np.uint8)
    band_srgb = (to_srgb(srgb_q) * 255).astype(np.uint8)
    n_lin = len(np.unique(lin_q))
    n_srgb = len(np.unique(srgb_q))

    fig = plt.figure(figsize=(13.4, 5.4))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.5], width_ratios=[1.3, 1], hspace=0.55,
                          wspace=0.25)

    ax = fig.add_subplot(gs[0, :])
    ax.imshow(np.vstack([band_lin, np.full((14, w), 255, np.uint8), band_srgb]),
              cmap="gray", vmin=0, vmax=255, aspect="auto")
    ax.set_yticks([h / 2, h + 14 + h / 2])
    ax.set_yticklabels([f"线性 8bit\n({n_lin} 档", f"sRGB 8bit\n({n_srgb} 档"], fontsize=9)
    ax.set_yticklabels([f"线性 8bit:{n_lin} 档", f"sRGB 8bit:{n_srgb} 档"], fontsize=9.5)
    ax.set_xticks(np.linspace(0, w - 1, 6))
    ax.set_xticklabels([f"{v:.0%}" for v in np.linspace(0, 0.25, 6)])
    ax.set_xlabel("光强")
    ax.set_title("同一段暗部渐变(光强 0 → 25%),两种编码各用 256 档去装\n"
                 "上面那条的色带是数出来的,不是画出来的", fontsize=11)

    # ── 左下:每一档跳多少
    ax = fig.add_subplot(gs[1, 0])
    lv = np.logspace(-3.3, 0, 300)
    step_lin = (1 / 255) / lv * 100                       # 线性:每档恒为 1/255 的光强
    code = to_srgb(lv)
    step_srgb = (to_linear(np.minimum(code + 1 / 255, 1.0)) - lv) / lv * 100
    ax.loglog(lv * 100, step_lin, lw=2, color="#c4442a", label="线性 8bit")
    ax.loglog(lv * 100, step_srgb, lw=2, color="#2c6fbb", label="sRGB 8bit")
    ax.axhline(1, color="#2a8f4a", ls="--", lw=1.4, label="人眼阈值 ≈1%")
    ax.set_xlabel("光强(%,对数轴)"); ax.set_ylabel("相邻两档差多少(%,对数轴)")
    ax.legend(fontsize=8.6)
    ax.set_title("在 0.1% 光强处,线性的一档跳 392%\n亮度差近 5 倍,中间没有任何过渡", fontsize=10.5)
    ax.grid(alpha=0.25, which="both")

    # ── 右下:码值都花到哪儿去了
    ax = fig.add_subplot(gs[1, 1])
    # 口径和 01_luma_vs_linear.py 的 demo_code_budget() 完全一致:
    # 数「解码后落在这段光强里」的码值有几个
    lin_i = np.arange(256) / 255.0                  # 线性存储:码值即光强
    srgb_i = to_linear(np.arange(256) / 255.0)      # sRGB 存储:码值解码后的光强
    zones = [("最暗的 1%", 0.0, 0.01), ("最暗的 5%", 0.0, 0.05),
             ("暗部到中灰\n(21.6%)", 0.0, 0.216), ("最亮的一半", 0.5, 1.0)]
    lin_codes = [int(((lin_i >= lo) & (lin_i <= hi)).sum()) for _, lo, hi in zones]
    srgb_codes = [int(((srgb_i >= lo) & (srgb_i <= hi)).sum()) for _, lo, hi in zones]
    labels = [z[0] for z in zones]
    y = np.arange(len(labels))
    ax.barh(y - 0.2, lin_codes, 0.4, color="#c4442a", label="线性给")
    ax.barh(y + 0.2, srgb_codes, 0.4, color="#2c6fbb", label="sRGB 给")
    for i, (a, b) in enumerate(zip(lin_codes, srgb_codes)):
        ax.text(a + 3, i - 0.2, f"{a} 档", va="center", fontsize=8.6, color="#c4442a")
        ax.text(b + 3, i + 0.2, f"{b} 档", va="center", fontsize=8.6, color="#2c6fbb")
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlim(0, 175); ax.set_xlabel("分到几个码值(共 256)")
    ax.legend(fontsize=8.6, loc="lower right")
    ax.set_title("线性把一半码值扔给了最亮的一半光强\n而人眼在那儿最不敏感", fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)

    fig.suptitle("结论不是「线性不好」,而是「8 bit 装不下线性」", fontsize=13, y=1.0)
    four_questions(fig,
        "存图前先做 gamma 编码,\n把 256 个码值按人眼\n敏感度重新分配 ——\n暗部多给,亮部少给。",
        "8 bit 就够用了。最暗的 1%\n"
        f"从 {lin_codes[0]} 档变成 {srgb_codes[0]} 档,\n"
        "暗部渐变不再出色带。",
        "码值不再正比于光强。\n于是「加法」和「平均」\n在编码域全是错的 ——\n缩放、模糊、图层混合\n严格说都该先转回线性。",
        "位深一够,大家立刻\n就用线性:相机 RAW 12~14 bit、\n渲染引擎 float32,都是线性。\n要全程 1% 以内的台阶,\n线性得 16.6 bit 才追得平\nsRGB 的 8 bit。",
        y=-0.03, bottom=0.14)
    save(fig, "linear-8bit-banding.png")
    print(f"     线性 8bit 在这段只剩 {n_lin} 档,sRGB 有 {n_srgb} 档;"
          f"最暗 1%:{lin_codes[0]} vs {srgb_codes[0]} 档")


# ═════════════════════════════════════ 图 3:limited range ══════════════


def fig_limited_range() -> None:
    """视频里的黑是 16、白是 235。当成 0~255 用,整张图的账就全错了。"""
    bgr = cv2.imread(str(IMAGES / "coffee.png"))
    y_full = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(float)
    y_lim = y_full * 219 / 255 + 16                      # 打包成 limited range
    wrong = y_lim                                        # 误当 full range 直接用
    right = np.clip((y_lim - 16) * 255 / 219, 0, 255)    # 正确展开

    fig = plt.figure(figsize=(13.4, 4.6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1.35], wspace=0.25)

    show_gray(fig.add_subplot(gs[0]), wrong,
              f"把 limited 当 full 直接用\n对比度被压扁:σ {wrong.std():.1f},"
              f"范围 [{wrong.min():.0f}, {wrong.max():.0f}]")
    show_gray(fig.add_subplot(gs[1]), right,
              f"先展开再用\nσ {right.std():.1f},范围 [{right.min():.0f}, {right.max():.0f}]")

    ax = fig.add_subplot(gs[2])
    ax.hist(wrong.ravel(), bins=256, range=(0, 255), color="#c4442a", alpha=0.65,
            label="limited(直接用)")
    ax.hist(right.ravel(), bins=256, range=(0, 255), color="#2c6fbb", alpha=0.55,
            label="展开之后")
    ax.axvline(16, color="#2a8f4a", ls="--", lw=1.4)
    ax.axvline(235, color="#2a8f4a", ls="--", lw=1.4)
    ax.text(16, ax.get_ylim()[1] * 0.92, " 黑=16", fontsize=9, color="#2a8f4a")
    ax.text(235, ax.get_ylim()[1] * 0.92, "白=235 ", fontsize=9, color="#2a8f4a", ha="right")
    ax.set_xlim(0, 255); ax.set_xlabel("Y 值"); ax.set_ylabel("像素数")
    ax.legend(fontsize=8.8)
    ax.set_title("直方图两端空出来的那一截\n就是 limited range 的余量", fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)

    fig.suptitle("limited range:视频里的黑是 16、白是 235", fontsize=13, y=1.03)
    four_questions(fig,
        "把 0~255 压进 16~235,\n两头留出余量\n(给模拟信号过冲用的\n历史遗留)。",
        "信号超调时不会\n直接削顶,老式设备\n的兼容性。这是\nyuv420p 的默认行为。",
        f"直接当 0~255 用的代价:\n对比度凭空少一截\n(σ {right.std():.1f} → {wrong.std():.1f}),\n"
        "全黑画面读到 16,\n直方图左边空一截,\n算出的对比度偏小。",
        "OpenCV 这边**全是 full range**,\n`cv2.cvtColor(BGR2YUV)` 和\nffmpeg 的 yuv420p 不是一回事。\n"
        "查清楚再用:\n`ffprobe -show_entries`\n`stream=pix_fmt,color_range`\ntv=limited,pc=full。",
        y=-0.03, bottom=0.05)
    save(fig, "yuv-limited-range.png")
    print(f"     误当 full 用:σ {right.std():.1f} → {wrong.std():.1f},"
          f"范围 [{right.min():.0f},{right.max():.0f}] → [{wrong.min():.0f},{wrong.max():.0f}]")


# ═════════════════════════════════════ 图 4:Y 怎么显示回屏幕 ═══════════


def fig_y_to_screen() -> None:
    """屏幕不认识灰度图。抄三份是精确解,不是偷懒 —— 顺带演示 vmin/vmax 的坑。"""
    y = np.array([[0, 64, 128, 200, 255]], np.uint8)
    gray2bgr = cv2.cvtColor(y, cv2.COLOR_GRAY2BGR).reshape(-1, 3)
    yuv = np.dstack([y, np.full_like(y, 128), np.full_like(y, 128)])
    via_yuv = cv2.cvtColor(yuv, cv2.COLOR_YUV2RGB).reshape(-1, 3)
    identical = np.array_equal(gray2bgr, via_yuv)

    # 一张真实范围不是 0~255 的图,用来演示 vmin/vmax 不给会怎样
    # 拿第五节那个 limited range 的 Y 平面来演示 —— 这是最有现实意义的例子:
    # 从视频里抠出的 Y 只占 16~235,不给范围的话 matplotlib 会把它拉满,
    # **正好把 limited range 这个毛病给盖住了**,你永远不会发现。
    full = cv2.imread(str(IMAGES / "lenna_s.jpg"), cv2.IMREAD_GRAYSCALE).astype(float)
    img = np.round(full * 219 / 255 + 16).astype(np.uint8)   # 打包成 limited range
    lo, hi = int(img.min()), int(img.max())
    assert (lo, hi) != (0, 255), "换张范围不满的图,不然这张图演示不出任何东西"

    fig = plt.figure(figsize=(13.4, 4.4))
    gs = fig.add_gridspec(1, 4, width_ratios=[1.25, 1, 1, 1.15], wspace=0.32)

    ax = fig.add_subplot(gs[0]); ax.axis("off")
    ax.set_title("抄三份是精确解,不是近似", fontsize=10.5)
    ax.text(0.5, 0.95,
            "BT.601 全范围的反变换:\n\n"
            "  R = Y + 1.402 (V−128)\n"
            "  G = Y − 0.344 (U−128)\n"
            "           − 0.714 (V−128)\n"
            "  B = Y + 1.772 (U−128)\n\n"
            "灰度 = 没有色度 = U = V = 128\n"
            "(8 bit 下 128 才是「零」)\n\n"
            "括号里全变 0,三条式子\n当场坍缩成 R = G = B = Y。\n\n"
            f"实测逐值相同:{identical}",
            ha="center", va="top", fontsize=9.3, linespacing=1.6,
            bbox=dict(boxstyle="round,pad=0.5", fc="#eef3f8", ec="#2c6fbb"))

    a = fig.add_subplot(gs[1])
    a.imshow(img, cmap="gray", vmin=0, vmax=255)
    a.set_title("给了 vmin=0, vmax=255\n发灰、不够黑 —— 一眼看出是 limited", fontsize=10)
    a.axis("off")

    a = fig.add_subplot(gs[2])
    a.imshow(img, cmap="gray")                     # 故意不给,演示后果
    a.set_title(f"没给 vmin/vmax\n被按 [{lo},{hi}] 拉满,毛病被盖住", fontsize=10)
    a.axis("off")

    ax = fig.add_subplot(gs[3])
    ax.plot([0, 255], [0, 255], lw=2, color="#2c6fbb", label="给了范围:原样映射")
    ax.plot([lo, hi], [0, 255], lw=2, color="#c4442a", label=f"没给:按 [{lo},{hi}] 拉满")
    ax.plot([0, lo], [0, 0], lw=2, color="#c4442a")
    ax.plot([hi, 255], [255, 255], lw=2, color="#c4442a")
    ax.set_xlim(0, 255); ax.set_ylim(-8, 263)
    ax.set_xlabel("图里存的值"); ax.set_ylabel("屏幕上显示成什么")
    ax.legend(fontsize=8.5, loc="lower right")
    ax.set_title("差别在这条线上\n斜率被偷偷改大了", fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)

    fig.suptitle("Y 怎么显示回屏幕:屏幕根本不认识「灰度图」", fontsize=13, y=1.03)
    four_questions(fig,
        "把一个 Y 值抄成\n三份送给红绿蓝三颗灯。\nmatplotlib 里干这事的\n就是 cmap=\"gray\"。",
        "三色等量混合 = 中性灰。\n这不是近似,是色度为中性时\nYUV→RGB 的精确解 ——\n实测逐值相同。",
        f"什么都没失去 ——\n前提是那些 R、G、B\n本来就是 gamma 编码值。\n"
        "若先转了线性光再算亮度,\n就必须重新编码才能送显示,\n漏了会明显偏暗\n(中灰该是 188,送 128 过去)。",
        f"vmin/vmax 必须显式给。\n这里放的是一段 limited range\n"
        f"的 Y(范围 [{lo}, {hi}])。不给范围,\nmatplotlib 就拿它自己的\n"
        "min/max 拉满 —— 看上去很正常,\n**而你永远不会发现\n它其实是 limited range**。",
        y=-0.03, bottom=0.12)
    save(fig, "y-to-screen.png")
    print(f"     GRAY2BGR 与 YUV(U=V=128)→RGB 逐值相同:{identical};"
          f"limited range Y 的范围 [{lo}, {hi}]")


if __name__ == "__main__":
    fig_luma_error()
    fig_linear_banding()
    fig_limited_range()
    fig_y_to_screen()
    if "--show" in sys.argv:
        plt.show()
