"""LUT(查找表)的五个验证 —— 配合 Documents/01-fundamentals/lut.md。

LUT 就是一张「输入 → 输出」的对照表:8 位图只有 256 种可能的像素值,
所以一张 256 项的表就能穷举所有答案,之后全图只查表、不算数。

验证五件事:
1. 建表 + 查表:和逐像素算公式逐像素相同,但快 88 倍(1080p 实测)
2. 判据「输出只取决于该像素自己的值」:能塌缩的都塌缩成表,并逐像素验证 ——
   包括比特平面(常被当成另一类,其实单层照样是 lut[v] = (v >> i) & 1)
3. 表的构成:直方图均衡化的表是从图统计出来的,但算完之后仍是普通的 256 项表
4. 彩色图:cv2.LUT 三个通道查同一张表;要各通道不同得传 (1,256,3)
5. 天花板:cv2.LUT 只吃 8 位,16 位输入直接抛异常;浮点根本没有「档」

用法:
    .venv/bin/python Ch01_02_Fundamentals/03_lut_basics.py
"""

import time
from pathlib import Path

import cv2
import numpy as np
import numpy.typing as npt

REPO = Path(__file__).resolve().parents[2]


def hr(title: str) -> None:
    print(f"\n{'=' * 66}\n{title}\n{'=' * 66}")


def load_gray(name: str) -> npt.NDArray[np.uint8]:
    path = REPO / "Assets" / "test-images" / name
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise SystemExit(f"读不到 {path}")
    return np.asarray(img, dtype=np.uint8)


def bench(fn, repeat: int = 20) -> float:
    """毫秒/次。先跑一次热身,避免把首次分配算进去。"""
    fn()
    t0 = time.perf_counter()
    for _ in range(repeat):
        fn()
    return (time.perf_counter() - t0) / repeat * 1000


# ---------------------------------------------------------------- 1
def demo_build_and_apply() -> None:
    hr("1. 建表 + 查表:结果一样,但快得多")
    img = cv2.resize(load_gray("astronaut.png"), (1920, 1080),
                     interpolation=cv2.INTER_NEAREST)
    print(f"  测试图 {img.shape[1]}×{img.shape[0]} = {img.size} 个像素,"
          f"但可能的取值只有 256 种")
    print("  做伽马校正 s = 255·(r/255)^(1/2.2)\n")

    def build() -> npt.NDArray[np.uint8]:
        r = np.arange(256)
        s = 255.0 * (r / 255.0) ** (1 / 2.2)
        return np.clip(np.rint(s), 0, 255).astype(np.uint8)

    lut = build()
    print(f"  表长这样:lut[0]={lut[0]}  lut[1]={lut[1]}  lut[128]={lut[128]}  "
          f"lut[255]={lut[255]}")

    def direct() -> npt.NDArray[np.uint8]:
        return np.clip(np.rint(255.0 * (img / 255.0) ** (1 / 2.2)), 0, 255).astype(np.uint8)

    ref = direct()
    for name, out in (("cv2.LUT", np.asarray(cv2.LUT(img, lut), dtype=np.uint8)),
                      ("lut[img]", lut[img])):
        d = int(np.abs(out.astype(np.int64) - ref.astype(np.int64)).max())
        print(f"  {name:<10s} 与逐像素算的最大差 {d}")

    t_direct = bench(direct)
    t_cv = bench(lambda: cv2.LUT(img, lut))
    t_np = bench(lambda: lut[img])
    t_build = bench(build, 200)
    print(f"\n  {'逐像素算 pow(numpy 向量化)':<28s}{t_direct:8.2f} ms")
    print(f"  {'lut[img](numpy 花式索引)':<28s}{t_np:8.2f} ms   快 {t_direct / t_np:.0f} 倍")
    print(f"  {'cv2.LUT':<28s}{t_cv:8.2f} ms   快 {t_direct / t_cv:.0f} 倍")
    print(f"  {'建表本身(256 次 pow)':<28s}{t_build:8.4f} ms   "
          f"只占查表耗时的 {t_build / t_cv * 100:.0f}%,而且是一次性的")
    print("\n  省下的是「207 万次计算里,真正不同的输入只有 256 个」那部分重复劳动。")


# ---------------------------------------------------------------- 2
def demo_what_can_collapse(img: npt.NDArray[np.uint8]) -> None:
    hr("2. 判据:输出只取决于该像素自己的值 → 能塌缩成表")
    cases = (
        ("线性 s=1.5r−40", lambda g: np.clip(np.rint(1.5 * g.astype(np.float64) - 40), 0, 255),
         np.clip(np.rint(1.5 * np.arange(256) - 40), 0, 255)),
        ("反转 s=255−r", lambda g: 255 - g.astype(np.int64), 255 - np.arange(256)),
        ("阈值化 T=128", lambda g: np.where(g > 128, 255, 0), np.where(np.arange(256) > 128, 255, 0)),
        ("比特平面 bit-3", lambda g: (g.astype(np.int64) >> 3) & 1, (np.arange(256) >> 3) & 1),
    )
    for name, direct, table in cases:
        lut = np.asarray(table, dtype=np.uint8)
        d = int(np.abs(np.asarray(direct(img), dtype=np.int64)
                       - lut[img].astype(np.int64)).max())
        print(f"  {name:<18s} 塌缩成 LUT 后与直接算的最大差:{d}")

    print("\n  ⚠️ 比特平面值得单独说一句:它常被当成「另一类操作」,")
    print("     但单独看一层,lut[v] = (v >> i) & 1 照样只看自己的值,是标准的点运算。")
    print("     它特别的地方是「一进八出」—— 把一张图拆成 8 张,而不是一进一出的 s = T(r)。")

    print("\n  塌缩不了的:")
    blur = cv2.GaussianBlur(img, (5, 5), 1.0)
    same = [int(v) for v in np.unique(blur[img == 100])[:6]]
    print(f"    高斯模糊 —— 原图里所有值为 100 的像素,模糊后变成了 "
          f"{len(np.unique(blur[img == 100]))} 种不同的值(前几个:{same})")
    print("    同一个输入对应多个输出,一张表根本表达不了 —— 因为它要看邻居。")
    clahe = np.asarray(cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(img),
                       dtype=np.uint8)
    print(f"    CLAHE —— 值为 100 的像素输出了 {len(np.unique(clahe[img == 100]))} 种不同的值,"
          f"因为还取决于它在哪儿")


# ---------------------------------------------------------------- 3
def demo_equalize_is_still_a_table(img: npt.NDArray[np.uint8]) -> None:
    hr("3. 直方图均衡化的表是「算出来的」,但仍然只是一张表")
    hist = np.bincount(img.ravel(), minlength=256).astype(np.float64)
    first = int(np.nonzero(hist)[0][0])
    cdf = np.cumsum(hist)
    lut = np.clip(np.rint((cdf - hist[first]) * (255.0 / (img.size - hist[first]))),
                  0, 255).astype(np.uint8)
    ref = np.asarray(cv2.equalizeHist(img), dtype=np.uint8)
    d = int(np.abs(lut[img].astype(np.int64) - ref.astype(np.int64)).max())
    print(f"  统计 → 算 CDF → 得到 256 项的表,查表结果与 cv2.equalizeHist 最大差 {d}")
    print(f"  表的前 8 项:{lut[:8].tolist()}   后 8 项:{lut[-8:].tolist()}")
    print("\n  和伽马那张表的唯一区别:伽马的表来自公式,这张表来自这幅图的统计。")
    print("  一旦算完,两者在使用上没有任何差别 —— 都是 256 项、都是一次数组访问。")
    print("  所以均衡化是「两遍扫描的点运算」:第一遍统计,第二遍查表。")


# ---------------------------------------------------------------- 4
def demo_color() -> None:
    hr("4. 彩色图:一张表 vs 三张表")
    path = REPO / "Assets" / "test-images" / "coffee.png"
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise SystemExit(f"读不到 {path}")
    lut = np.clip(np.rint(255.0 * (np.arange(256) / 255.0) ** (1 / 2.2)), 0, 255).astype(np.uint8)
    same = np.asarray(cv2.LUT(bgr, lut), dtype=np.uint8)
    print(f"  cv2.LUT(bgr, 256 项的表):三个通道查同一张表")
    print(f"    原图 BGR 均值 {np.round(bgr.reshape(-1, 3).mean(axis=0), 1)}")
    print(f"    处理后        {np.round(same.reshape(-1, 3).mean(axis=0), 1)}")

    # 各通道不同:表的形状要变成 (1, 256, 3)
    three = np.stack([
        np.clip(np.rint(np.arange(256) * 0.8), 0, 255),           # B 压暗
        np.arange(256),                                            # G 不动
        np.clip(np.rint(np.arange(256) * 1.2), 0, 255),           # R 提亮
    ], axis=-1).astype(np.uint8).reshape(1, 256, 3)
    warm = np.asarray(cv2.LUT(bgr, three), dtype=np.uint8)
    print(f"\n  传 (1,256,3) 的表:三个通道各查各的(这里做了个偏暖的白平衡)")
    print(f"    处理后 BGR 均值 {np.round(warm.reshape(-1, 3).mean(axis=0), 1)} —— B 降 R 升")
    print("\n  但 1D LUT 有个根本限制:输出的 R 只能由输入的 R 决定,跟 G、B 无关。")
    print("  真实的颜色变换(色彩空间转换、调色、LOG 转 Rec.709)三个通道是纠缠的,")
    print("  那就得上 3D LUT:33×33×33 的立方体 + 三线性插值,也就是 .cube 文件。")


# ---------------------------------------------------------------- 5
def demo_bit_depth_ceiling(img: npt.NDArray[np.uint8]) -> None:
    hr("5. 天花板:位深一高,查表这条路就开始别扭")
    lut8 = np.arange(256, dtype=np.uint8)
    img16 = (img.astype(np.uint16) << 2)          # 假装是 10 bit 数据,装在 16 位里

    try:
        cv2.LUT(img16, lut8)
        print("  16 位输入 + 256 项表:居然通过了(意料之外)")
    except cv2.error:
        print("  16 位输入 + 256 项表  → 抛异常。表的长度必须和输入的取值范围对上。")

    lut16 = np.arange(65536, dtype=np.uint16)
    out = np.asarray(cv2.LUT(img16, lut16), dtype=np.uint16)
    print(f"  16 位输入 + 65536 项表 → 通过,最大差 "
          f"{int(np.abs(out.astype(np.int64) - img16.astype(np.int64)).max())}(恒等表)")
    print("\n  ⚠️ 所以 cv2.LUT 不是「只支持 8 位」,它支持 8 位和 16 位 —— 但表的长度写死了:")
    print("     8 位输入要 256 项,16 位输入要 65536 项,中间的挡位没有。")
    print("     10 bit 数据(装在 uint16 里,实际只用 0~1023)想用 cv2.LUT,")
    print("     就得建一张 65536 项的表,浪费 64 倍;更省的做法是 np.take + 1024 项的表:")
    lut10 = np.arange(1024, dtype=np.uint16)
    taken = np.take(lut10, np.clip(img16, 0, 1023))
    print(f"       np.take(lut1024, img10) → shape {taken.shape},"
          f"表只要 {lut10.nbytes} 字节(65536 项要 {lut16.nbytes} 字节)\n")

    print(f"  {'位深':<10s}{'表的项数':>10s}   查表还划算吗")
    for label, n, note in ((" 8 bit", "256", "划算。表 256 字节,全程待在 L1 缓存"),
                           ("10 bit", "1024", "划算。表 2 KB,但 cv2.LUT 要 65536 项,得自己 np.take"),
                           ("12 bit", "4096", "还行,缓存开始不友好"),
                           ("16 bit", "65536", "表 128 KB,超出 L1;常改成粗表 + 插值"),
                           ("  浮点", "—", "不能 —— 没有「档」这个概念,只能直接算")):
        print(f"  {label:<10s}{n:>10s}   {note}")
    print("\n  浮点想查表只能自己定范围和分辨率,再插值 —— 那时候 LUT 就从「精确」变成「近似」了。")
    print("  这也是为什么 3D LUT 必须配插值:33×33×33 的网格根本不可能精确覆盖所有颜色。")


def main() -> None:
    img = load_gray("astronaut.png")
    demo_build_and_apply()
    demo_what_can_collapse(img)
    demo_equalize_is_still_a_table(img)
    demo_color()
    demo_bit_depth_ceiling(img)


if __name__ == "__main__":
    main()
