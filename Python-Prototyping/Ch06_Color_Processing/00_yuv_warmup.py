"""第 1 周热身:手写 I420(YUV420P)→ RGB,与 OpenCV 对照。

三步:
1. 侦探实验:用纯色块探测 cv2 的 I420 转换用的是什么亮度系数(601/709)
   和什么 range(video 16~235 / full 0~255)
2. 手写通用 YUV→RGB(Kr/Kb 参数化,四种组合),找出与 cv2 吻合的那组
3. 可视化 601 vs 709 解码差异 —— 推流开发中经典的"矩阵用错"偏色

I420 内存布局:H×W 的 Y 平面,后跟 (H/2)×(W/2) 的 U 平面、V 平面。
转换公式的完整推导见本目录 README「转换原理详解」一节。

用法:
    .venv/bin/python Ch06_Color_Processing/00_yuv_warmup.py [--show]
"""

import sys
from pathlib import Path

import cv2
import matplotlib
import numpy as np

if "--show" not in sys.argv:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[2]
matplotlib.rcParams["font.family"] = ["Heiti TC", "Arial Unicode MS", "sans-serif"]

# 亮度系数:Kr + Kg + Kb = 1
COEFFS = {"bt601": (0.299, 0.114), "bt709": (0.2126, 0.0722)}


def split_i420(yuv: np.ndarray, h: int, w: int):
    """把 cv2 输出的 (H*3/2, W) I420 缓冲拆成 Y/U/V 三个平面。"""
    y = yuv[:h]
    u = yuv[h : h + h // 4].reshape(h // 2, w // 2)
    v = yuv[h + h // 4 :].reshape(h // 2, w // 2)
    return y, u, v


def i420_to_rgb(y, u, v, matrix="bt601", video_range=True):
    """手写 I420 → RGB。matrix: bt601/bt709;video_range: Y 16~235。"""
    kr, kb = COEFFS[matrix]
    kg = 1.0 - kr - kb

    # 色度最近邻上采样回全分辨率(4:2:0 → 4:4:4)
    u = np.repeat(np.repeat(u, 2, axis=0), 2, axis=1).astype(np.float64)
    v = np.repeat(np.repeat(v, 2, axis=0), 2, axis=1).astype(np.float64)
    y = y.astype(np.float64)

    if video_range:  # Y: 16~235 → 0~1;C: 16~240 → -0.5~0.5
        yn = (y - 16.0) / 219.0
        cb = (u - 128.0) / 224.0
        cr = (v - 128.0) / 224.0
    else:  # full range
        yn = y / 255.0
        cb = (u - 128.0) / 255.0
        cr = (v - 128.0) / 255.0

    r = yn + 2.0 * (1.0 - kr) * cr
    b = yn + 2.0 * (1.0 - kb) * cb
    g = (yn - kr * r - kb * b) / kg
    rgb = np.stack([r, g, b], axis=-1)
    return np.clip(rgb * 255.0, 0, 255).astype(np.uint8)


def probe_opencv() -> None:
    """第 1 步:用纯色块反推 cv2.COLOR_RGB2YUV_I420 的系数与 range。"""
    print("=== 侦探实验:cv2 的 I420 编码是什么标准? ===")
    patches = {"白": (255, 255, 255), "黑": (0, 0, 0), "灰": (128, 128, 128),
               "红": (255, 0, 0), "绿": (0, 255, 0), "蓝": (0, 0, 255)}
    for name, rgb_val in patches.items():
        block = np.full((16, 16, 3), rgb_val, dtype=np.uint8)
        yuv = cv2.cvtColor(block, cv2.COLOR_RGB2YUV_I420)
        y, u, v = split_i420(yuv, 16, 16)
        print(f"  {name} {rgb_val}: Y={y[8, 8]:3d}  U={u[4, 4]:3d}  V={v[4, 4]:3d}")

    print("  对照:纯白 Y=235 → video range;Y=255 → full range")
    print("  对照:纯红 Y≈82 → BT.601 video;≈76 → BT.601 full;≈63 → BT.709 video")


def main() -> None:
    probe_opencv()

    # --- 第 2 步:真实图像上验证手写解码 ---
    rgb_src = cv2.cvtColor(
        cv2.imread(str(REPO / "Assets" / "test-images" / "astronaut.png")),
        cv2.COLOR_BGR2RGB,
    )
    h, w = rgb_src.shape[:2]
    yuv = cv2.cvtColor(rgb_src, cv2.COLOR_RGB2YUV_I420)
    y, u, v = split_i420(yuv, h, w)

    reference = cv2.cvtColor(yuv, cv2.COLOR_YUV2RGB_I420)  # cv2 自己解回来作基准

    print("\n=== 手写解码 vs cv2 基准(平均/最大绝对误差) ===")
    results, best = {}, None
    for matrix in ("bt601", "bt709"):
        for vr in (True, False):
            name = f"{matrix}-{'video' if vr else 'full'}"
            decoded = i420_to_rgb(y, u, v, matrix=matrix, video_range=vr)
            diff = np.abs(decoded.astype(int) - reference.astype(int))
            results[name] = decoded
            print(f"  {name:12s} mean={diff.mean():6.2f}  max={diff.max():3d}")
            if best is None or diff.mean() < best[1]:
                best = (name, diff.mean())

    print(f"\n结论:cv2 的 I420 转换 ≈ {best[0]}(平均误差 {best[1]:.2f})")
    status = "PASS ✅" if best[1] < 1.5 else "FAIL ❌(检查实现)"
    print(f"验收(平均误差 < 1.5):{status}")
    print("注:残余误差来自浮点取整;max=1 说明 cv2 的色度上采样同为最近邻。")

    # --- 第 3 步:601 vs 709 的偏色可视化 ---
    match_dec = results[best[0]]
    wrong_name = ("bt709" if best[0].startswith("bt601") else "bt601") + "-" + best[0].split("-")[1]
    wrong_dec = results[wrong_name]
    amp_diff = np.clip(
        np.abs(wrong_dec.astype(int) - match_dec.astype(int)) * 5, 0, 255
    ).astype(np.uint8)

    fig, axes = plt.subplots(2, 2, figsize=(10, 10))
    panels = [
        (rgb_src, "原图 (RGB)"),
        (match_dec, f"手写解码,矩阵正确 ({best[0]})"),
        (wrong_dec, f"矩阵用错 ({wrong_name}) —— 注意肤色"),
        (amp_diff, "两者差异 ×5 放大"),
    ]
    for ax, (img, title) in zip(axes.flat, panels):
        ax.imshow(img)
        ax.set_title(title, fontsize=11)
        ax.axis("off")
    fig.tight_layout()

    out = REPO / "Assets" / "results" / "week01_yuv_warmup.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=110)
    print(f"\n结果已保存: {out.relative_to(REPO)}")
    if "--show" in sys.argv:
        plt.show()


if __name__ == "__main__":
    main()
