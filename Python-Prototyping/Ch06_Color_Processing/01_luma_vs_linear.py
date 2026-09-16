"""亮度的三种含义、Luma 的近似误差、以及为什么不直接存线性光。

配合 Documents/02-intensity/luma-and-linear-light.md,文档里的每个数字都由这里算出。

  1. Luma Y′ 与真实 Luminance 差多少 —— 高饱和色差 70+,灰和肤色几乎为 0
  2. 同样 8 bit,线性存储与 sRGB 存储的台阶大小(按同一光强水平比)
  3. 256 个码值分别花在了哪段光强上
  4. 线性要多少 bit 才能追平 sRGB 8bit
  5. 各标准的亮度权重差异

用法:
    .venv/bin/python Ch06_Color_Processing/01_luma_vs_linear.py
"""

import numpy as np

# Rec.709 权重(sRGB 用的就是这套原色)
W709 = (0.2126, 0.7152, 0.0722)
W601 = (0.299, 0.587, 0.114)
W2020 = (0.2627, 0.6780, 0.0593)


def to_linear(c):
    """sRGB 编码值(0~1)→ 线性光(0~1)。

    暗部那段 c/12.92 是直线而不是幂函数:纯幂函数在 0 附近斜率无穷大,
    会让最暗的几个码值挤在一起,也不好做定点运算。
    """
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(v):
    """线性光(0~1)→ sRGB 编码值(0~1)。"""
    v = np.clip(np.asarray(v, dtype=np.float64), 0, 1)
    return np.where(v <= 0.0031308, v * 12.92, 1.055 * v ** (1 / 2.4) - 0.055)


def hr(title):
    print(f"\n{'=' * 62}\n{title}\n{'=' * 62}")


# ------------------------------------------------------------------ 1
def demo_luma_error():
    hr("1. Luma 与真实亮度差多少")
    print("Luma      = 直接对 gamma 编码值加权(视频/OpenCV 的做法)")
    print("真实亮度  = 先还原成光强、加权、再编码回来\n")
    print(f"{'颜色':<8}{'R,G,B':>16}{'Luma':>9}{'真实亮度':>10}{'差':>8}")
    print("-" * 52)
    for name, rgb in [
        ("纯红", (255, 0, 0)), ("纯绿", (0, 255, 0)), ("纯蓝", (0, 0, 255)),
        ("纯黄", (255, 255, 0)), ("品红", (255, 0, 255)), ("青", (0, 255, 255)),
        ("中灰", (128, 128, 128)), ("肤色", (222, 184, 155)), ("暗绿", (34, 80, 40)),
    ]:
        luma = sum(w * c for w, c in zip(W709, rgb))
        lin = to_linear(np.array(rgb) / 255.0)
        true_gray = to_srgb(sum(w * c for w, c in zip(W709, lin))) * 255
        print(f"{name:<8}{str(rgb):>16}{luma:>9.1f}{true_gray:>10.1f}{true_gray - luma:>+8.1f}")
    print("\n→ 高饱和色差到 70 以上;灰、肤色、暗绿这些自然色几乎为 0。")
    print("  正是后者占了真实照片的绝大多数,这个近似才能用了 70 年。")


# ------------------------------------------------------------------ 2
def demo_step_size():
    hr("2. 同一光强水平上,8bit 的一档是多大的亮度跳变")
    print("按光强比而不是按码值比 —— 同一个码值在两种编码下对应的光强不同,")
    print("按码值比是不公平的。人眼大约 1% 就能看出台阶。\n")
    print(f"{'光强':>10}{'线性 8bit':>13}{'sRGB 8bit':>15}")
    print("-" * 40)
    for L in (0.001, 0.005, 0.01, 0.05, 0.1, 0.216, 0.5, 1.0):
        step_lin = (1 / 255) / L * 100          # 线性:一档恒为 1/255 的光强
        code = np.floor(to_srgb(L) * 255)
        l0, l1 = to_linear(code / 255), to_linear(min(code + 1, 255) / 255)
        step_srgb = (l1 / l0 - 1) * 100 if l0 > 0 else np.inf
        m1 = "  ←看得出" if step_lin > 1 else ""
        m2 = "  ←看得出" if step_srgb > 1 else ""
        print(f"{L * 100:>9.1f}%{step_lin:>12.1f}%{m1:<9}{step_srgb:>9.1f}%{m2}")
    print("\n→ 暗部线性惨败(0.1% 光强处一档跳 392%),亮部反而是线性更细。")
    print("  但人眼对暗部敏感、对亮部迟钝 —— 线性把精度全花在了没人看的地方。")


# ------------------------------------------------------------------ 3
def demo_code_budget():
    hr("3. 256 个码值花在了哪段光强上")
    lin = np.arange(256) / 255.0                  # 线性存储:码值即光强
    srgb = to_linear(np.arange(256) / 255.0)      # sRGB 存储:码值经解码后的光强
    print(f"{'光强区间':>22}{'线性给':>9}{'sRGB 给':>10}")
    print("-" * 42)
    for lo, hi, nm in ((0.0, 0.01, "最暗的 1%"), (0.0, 0.05, "最暗的 5%"),
                       (0.0, 0.216, "暗部到中灰(21.6%)"), (0.5, 1.0, "最亮的一半")):
        n_lin = int(((lin >= lo) & (lin <= hi)).sum())
        n_srgb = int(((srgb >= lo) & (srgb <= hi)).sum())
        print(f"{nm:>22}{n_lin:>8d} 档{n_srgb:>8d} 档")
    print("\n→ 线性把一半码值(128 档)扔给了最亮的一半光强,那里人眼最不敏感;")
    print("  最暗的 1% 只剩 3 档,于是暗部渐变必然出现色带。")


# ------------------------------------------------------------------ 4
def demo_bit_depth():
    hr("4. 线性要多少 bit 才能追平")
    print("要求:全范围内相邻码值的亮度差都不超过 1%\n")
    for nm, floor in (("1/100 最大亮度", 1e-2), ("1/1000(普通暗部)", 1e-3),
                      ("1/10000(HDR 暗部)", 1e-4)):
        need = 1.0 / (floor * 0.01)
        print(f"  黑位定在 {nm:22s} → {need:>9,.0f} 档 = {np.log2(need):4.1f} bit")
    print("\n  sRGB 8bit(256 档)就覆盖了同样的范围")
    print("\n→ 所以结论不是'线性不好',而是'8 bit 装不下线性'。")
    print("  位深一够(RAW 12~14bit、渲染引擎 float32),大家立刻就用线性。")


# ------------------------------------------------------------------ 5
def demo_weights():
    hr("5. 三套亮度权重的差异")
    print(f"{'标准':<12}{'R':>8}{'G':>8}{'B':>8}   用在")
    print("-" * 56)
    for nm, w, use in (("Rec.601", W601, "SDTV、JPEG、OpenCV 默认"),
                       ("Rec.709", W709, "HDTV、sRGB"),
                       ("Rec.2020", W2020, "UHD、HDR")):
        print(f"{nm:<12}{w[0]:>8.4f}{w[1]:>8.4f}{w[2]:>8.4f}   {use}")

    def compare(px, label):
        px = px.astype(np.float64)
        y601 = sum(w * px[:, :, i] for i, w in enumerate(W601))
        y709 = sum(w * px[:, :, i] for i, w in enumerate(W709))
        avg = px.mean(axis=2)
        print(f"\n{label}:")
        print(f"  601 vs 709      最大 {np.abs(y601-y709).max():5.1f}  平均 {np.abs(y601-y709).mean():5.2f}")
        print(f"  601 vs 简单平均  最大 {np.abs(y601-avg).max():5.1f}  平均 {np.abs(y601-avg).mean():5.2f}")

    # 随机像素代表最坏情况:什么颜色都有,包括自然界罕见的高饱和色
    rng = np.random.default_rng(0)
    compare(rng.integers(0, 256, size=(200, 200, 3)), "随机彩色像素(最坏情况)")

    # 真实照片代表实际情况:低饱和色占绝大多数,差距明显小一截
    import cv2
    from pathlib import Path
    img = cv2.imread(str(Path(__file__).resolve().parents[2] /
                         "Assets" / "test-images" / "coffee.png"))
    if img is not None:
        compare(img[:, :, ::-1], "真实照片 coffee.png")

    print("\n→ 全程用同一套就行,混用才是灾难。简单平均是明确的错误。")


if __name__ == "__main__":
    demo_luma_error()
    demo_step_size()
    demo_code_budget()
    demo_bit_depth()
    demo_weights()
    print()
