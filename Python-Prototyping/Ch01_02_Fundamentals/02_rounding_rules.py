"""取整与浮点:小数落回 uint8 的三条规矩,逐条实测。

Documents/01-fundamentals/02-rounding-and-float.md 里的每个数字都由这里算出。

四个实验:
1. 截断 vs 四舍五入 —— 偏差是单向的还是零均值的
2. 反复落回 uint8 vs 全程 float —— 误差怎么累积
3. astype(np.uint8) 的回绕 vs clip 后的饱和
4. cv2.BGR2GRAY 内部的整数定点写法,以及它和浮点实现差多少

用法:
    .venv/bin/python Ch01_02_Fundamentals/02_rounding_rules.py
"""

from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]


def exp1_bias() -> None:
    """截断的误差是单向的(永远少),四舍五入的误差正负抵消。"""
    print("=" * 62)
    print("实验 1:截断 vs 四舍五入 —— 误差的「方向」")
    print("=" * 62)

    rng = np.random.default_rng(0)
    x = rng.uniform(0, 255, 1_000_000)

    trunc = x.astype(np.uint8).astype(np.float64)     # 向下取整
    rint = np.rint(x)                                  # 四舍五入

    print(f"  截断    平均误差 {(trunc - x).mean():+.4f}   (永远 ≤ 0,单向偏置)")
    print(f"  四舍五入 平均误差 {(rint - x).mean():+.4f}   (正负抵消,零均值)")
    print("  → 截断每次平均少 0.5,做 N 次就少 N×0.5;四舍五入不累积\n")


def exp2_accumulate() -> None:
    """中间结果反复落回 uint8,误差会累积;全程 float 只落一次则不会。"""
    print("=" * 62)
    print("实验 2:20 轮「×1.1 再 ÷1.1」,理论上应原样返回")
    print("=" * 62)

    x0 = np.arange(256, dtype=np.uint8)

    def run(mode: str) -> np.ndarray:
        x = x0.astype(np.float64)
        for _ in range(20):
            if mode == "截断":
                x = np.clip(x * 1.1, 0, 255).astype(np.uint8).astype(np.float64)
                x = np.clip(x / 1.1, 0, 255).astype(np.uint8).astype(np.float64)
            elif mode == "四舍五入":
                x = np.clip(np.rint(x * 1.1), 0, 255).astype(np.uint8).astype(np.float64)
                x = np.clip(np.rint(x / 1.1), 0, 255).astype(np.uint8).astype(np.float64)
            else:  # 全程 float,最后才落回
                x = x * 1.1
                x = x / 1.1
        return np.clip(np.rint(x), 0, 255).astype(np.uint8)

    for mode in ("截断", "四舍五入", "全程 float"):
        d = run(mode).astype(np.int32) - x0.astype(np.int32)
        print(f"  {mode:10s} 平均偏移 {d.mean():+6.2f}   最大偏移 {np.abs(d).max():3d}"
              f"   变了 {np.count_nonzero(d)}/256 个灰阶")
    print("  → 取整做得再好也扛不住做 20 次;根本解法是只落一次地\n")


def exp3_wraparound() -> None:
    """numpy 的 astype 对越界值是取模回绕,不是饱和 —— 过曝会变黑斑。"""
    print("=" * 62)
    print("实验 3:越界值 —— 回绕 vs 饱和")
    print("=" * 62)

    raw = np.array([-1, 0, 255, 256, 300], np.int16)
    print(f"  原值                          {raw.tolist()}")
    print(f"  astype(np.uint8)   (回绕)     {raw.astype(np.uint8).tolist()}")
    print(f"  clip 后 astype     (饱和)     "
          f"{np.clip(raw, 0, 255).astype(np.uint8).tolist()}")
    print("  → 300 回绕成 44:提亮后过曝区不是变白,是变黑斑。clip 必须在 astype 之前\n")


def exp4_fixed_point() -> None:
    """cv2 内部是整数定点;各种合理取整之间只差 ±1,但不保证逐像素相同。"""
    print("=" * 62)
    print("实验 4:cv2.BGR2GRAY 的整数定点,以及它和浮点实现差多少")
    print("=" * 62)

    rng = np.random.default_rng(0)
    bgr = rng.integers(0, 256, (400, 400, 3), dtype=np.uint8)
    b, g, r = (bgr[:, :, i].astype(np.int32) for i in range(3))
    cv_y = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.int32)

    # +32768 = 加半个单位再右移,等价于四舍五入;19595 = 0.299 × 65536
    fixed = (r * 19595 + g * 38470 + b * 7471 + (1 << 15)) >> 16
    flt = np.clip(np.rint(0.299 * r + 0.587 * g + 0.114 * b), 0, 255).astype(np.int32)

    for name, y in (("整数定点 shift16", fixed), ("浮点 + rint", flt)):
        d = np.abs(y - cv_y)
        pct = 100 * np.count_nonzero(d) / d.size
        print(f"  {name:16s} vs cv2:最大差 {d.max()}  "
              f"不一致 {np.count_nonzero(d)}/{d.size} ({pct:.2f}%)")

    lenna = cv2.imread(str(REPO / "Assets" / "test-images" / "lenna_s.jpg"))
    if lenna is not None:
        lb, lg, lr = (lenna[:, :, i].astype(np.int32) for i in range(3))
        ly = np.clip(np.rint(0.299 * lr + 0.587 * lg + 0.114 * lb), 0, 255).astype(np.int32)
        d = np.abs(ly - cv2.cvtColor(lenna, cv2.COLOR_BGR2GRAY).astype(np.int32))
        print(f"  同样的浮点实现,换成 lenna 这张真实照片:最大差 {d.max()}  "
              f"不一致 {np.count_nonzero(d)}")
    print("  → 自然照片上常常一个不差,随机噪声上有千分之一二差 1。"
          "结论按「±1 以内」说,别说「完全相同」\n")


def exp5_banker() -> None:
    """numpy 的 rint 是银行家舍入,.5 向偶数靠,不是一律进位。"""
    print("=" * 62)
    print("实验 5:恰好落在 .5 的值往哪边走")
    print("=" * 62)
    vals = [0.5, 1.5, 2.5, 3.5, -0.5, -1.5]
    print(f"  np.rint({vals}) = {[float(np.rint(v)) for v in vals]}")
    print("  → 银行家舍入(round-half-to-even):.5 向偶数靠,让这部分误差也正负抵消")

    # 实践上这个选择几乎不影响结果:恰好落在 .5 的像素极少
    rng = np.random.default_rng(0)
    bgr = rng.integers(0, 256, (400, 400, 3), dtype=np.uint8)
    b, g, r = (bgr[:, :, i].astype(np.int32) for i in range(3))
    cv_y = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.int32)
    raw = 0.299 * r + 0.587 * g + 0.114 * b
    banker = np.clip(np.rint(raw), 0, 255).astype(np.int32)
    half_up = np.clip(np.floor(raw + 0.5), 0, 255).astype(np.int32)
    print(f"  同一张随机图,两种舍入各自与 cv2 的不一致像素数:"
          f"银行家 {np.count_nonzero(banker - cv_y)},"
          f"半数进位 {np.count_nonzero(half_up - cv_y)}")
    print("  → 差别在千分之一以内,图像处理里不用纠结;"
          "但别在单元测试里写死 round(0.5) == 1\n")


if __name__ == "__main__":
    exp1_bias()
    exp2_accumulate()
    exp3_wraparound()
    exp4_fixed_point()
    exp5_banker()
