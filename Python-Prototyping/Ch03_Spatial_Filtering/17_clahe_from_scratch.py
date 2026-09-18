"""第 5 周(3.3 节):直方图处理 —— 17 手写 CLAHE,重点是块间双线性插值怎么实现。

对应文档 Documents/03-histogram/histogram-transform.md 第十四节。

13 号脚本拆了 CLAHE 的四个步骤,16 号脚本比了它和全局均衡化的差别,
但「块与块之间用双线性插值平滑接上」这句话一直没落到代码上。这一篇把它写出来。

整个算法只有两个函数:

    tile_luts(img)   ——  切块 → 每块统计直方图 → 削顶 + 回填 → CDF → 8×8 张 LUT
    interpolate(...) ——  每个像素查周围 4 张 LUT,按到块中心的距离双线性加权

⚠️ 关键在于插值的坐标系:**LUT 属于块的中心,不属于块的左上角**。
所以像素 x 落在「哪两张表之间」要用 x/tw − 0.5 算,减的这个 0.5 就是半块。
漏掉它,整张图会朝左上角偏半块,块边界上照样有痕迹。

验证六件事:
1. 手写版与 cv2.createCLAHE 在 512×512 图上**逐像素完全相同**(最大差 0)
2. 挑一个具体像素,把它的 4 个块、4 个权重、4 个 LUT 输出、加权结果全打出来
3. 边界像素:图的最外圈半块没有 4 个邻居,权重怎么退化(clamp),占多大比例
4. 不插值会怎样:最近块版本在块边界上的跳变幅度是插值版的几倍(方格痕迹)
5. 「先插 LUT 再查表」与「先查表再插值」完全等价 —— 两种实现随便选
6. ⚠️ OpenCV 的一个怪癖:尺寸不能整除 tileGridSize 时,**能整除的那一边也会补满一整块**。
   不照着做,page.png 上最大差 27;照着做,最大差 1

用法:
    .venv/bin/python Ch03_Spatial_Filtering/17_clahe_from_scratch.py [--show]
    结果图保存到 Assets/results/clahe-interpolation-demo.png(主图 astronaut.png)
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

TILES = 8
CLIP = 2.0


def hr(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def load_gray(name: str) -> npt.NDArray[np.uint8]:
    path = REPO / "Assets" / "test-images" / name
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise SystemExit(f"读不到 {path}")
    return np.asarray(img, dtype=np.uint8)


# ================================================================ 算法本体
def tile_luts(img: npt.NDArray[np.uint8], clip: float = CLIP,
              tiles: int = TILES) -> npt.NDArray[np.uint8]:
    """第 1~4 步:切块 → 统计 → 削顶回填 → CDF,返回 (tiles, tiles, 256) 的 LUT 数组。

    每一步都照 OpenCV 的算法写,包括那些教材不会提的细节:
    - 上限是 clip × 块面积 / 256,再和 1 取大(否则小块上上限可能算成 0)
    - 削下来的总量先整除 256 均分回填,余数再按固定步长补 1(总数必须守恒)
    - CDF 乘的是 255 / 块面积,不是 255 / 总像素数
    """
    h, w = img.shape
    th, tw = h // tiles, w // tiles
    area = th * tw
    limit = max(int(clip * area / 256), 1)
    luts = np.empty((tiles, tiles, 256), dtype=np.uint8)

    for i in range(tiles):
        for j in range(tiles):
            block = img[i * th:(i + 1) * th, j * tw:(j + 1) * tw]
            hist = np.bincount(block.ravel(), minlength=256).astype(np.int64)

            excess = int(np.maximum(hist - limit, 0).sum())   # 削掉多少
            hist = np.minimum(hist, limit)                    # 削顶
            batch = excess // 256                             # 每个桶均分到的整数份
            hist += batch
            residual = excess - batch * 256                   # 除不尽的零头
            if residual:
                # OpenCV 的做法:按固定步长挑 residual 个桶各 +1,而不是全堆在开头
                step = max(256 // residual, 1)
                hist[np.arange(0, 256, step)[:residual]] += 1

            luts[i, j] = np.clip(np.rint(np.cumsum(hist) * (255.0 / area)), 0, 255)
    return luts


def interpolate(img: npt.NDArray[np.uint8], luts: npt.NDArray[np.uint8],
                tile_h: int, tile_w: int) -> npt.NDArray[np.uint8]:
    """第 5 步:每个像素查周围 4 张 LUT,双线性加权。

    坐标系是这里唯一的难点。第 j 列块的**中心**在 x = (j + 0.5) · tw,
    所以反过来问「像素 x 在第几个块中心的位置上」就是:

        u = x / tw − 0.5        ← 减的这半块就是块中心的偏移

    u 的整数部分 j1 = floor(u) 是左边那张表,j2 = j1 + 1 是右边那张,
    小数部分 xa = u − j1 就是右表的权重。图最外圈半块的 u 会落到
    [−0.5, 0) 或 [tiles−1, tiles−0.5),clamp 到合法范围后两张表变成同一张,
    加权自动退化成「只用这一张」—— 不需要为边界写特例。
    """
    h, w = img.shape
    tiles_y, tiles_x = luts.shape[0], luts.shape[1]

    v = np.arange(h) / tile_h - 0.5
    y1 = np.floor(v).astype(np.int64)
    ya = v - y1                                   # 下面那张表的权重
    y2 = np.clip(y1 + 1, 0, tiles_y - 1)
    y1 = np.clip(y1, 0, tiles_y - 1)

    u = np.arange(w) / tile_w - 0.5
    x1 = np.floor(u).astype(np.int64)
    xa = u - x1                                   # 右边那张表的权重
    x2 = np.clip(x1 + 1, 0, tiles_x - 1)
    x1 = np.clip(x1, 0, tiles_x - 1)

    def lookup(iy: npt.NDArray[np.int64], ix: npt.NDArray[np.int64]) -> npt.NDArray[np.uint8]:
        """用 (行块号, 列块号, 像素值) 三重索引一次性查完整幅图。"""
        return luts[iy[:, None], ix[None, :], img]

    out = (lookup(y1, x1) * ((1 - ya)[:, None] * (1 - xa)[None, :])
           + lookup(y1, x2) * ((1 - ya)[:, None] * xa[None, :])
           + lookup(y2, x1) * (ya[:, None] * (1 - xa)[None, :])
           + lookup(y2, x2) * (ya[:, None] * xa[None, :]))
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def clahe_from_scratch(img: npt.NDArray[np.uint8], clip: float = CLIP,
                       tiles: int = TILES) -> npt.NDArray[np.uint8]:
    """完整的 CLAHE。包含 OpenCV 那个补边怪癖(见第 6 节)。"""
    h, w = img.shape
    if h % tiles == 0 and w % tiles == 0:
        src = img
    else:
        # ⚠️ 只要有一边除不尽,两边都按 tiles − (n % tiles) 补;
        #    能整除的那一边余数是 0,于是补满一整块 8 行/列。这是 OpenCV 的实际行为。
        src = cv2.copyMakeBorder(img, 0, tiles - h % tiles, 0, tiles - w % tiles,
                                 cv2.BORDER_REFLECT_101)
    luts = tile_luts(src, clip, tiles)
    return interpolate(img, luts, src.shape[0] // tiles, src.shape[1] // tiles)


def nearest_tile(img: npt.NDArray[np.uint8], luts: npt.NDArray[np.uint8],
                 tiles: int = TILES) -> npt.NDArray[np.uint8]:
    """对照组:不插值,像素属于哪块就用哪块的表(这就是原始 AHE 的做法)。"""
    h, w = img.shape
    th, tw = h // tiles, w // tiles
    out = np.empty_like(img)
    for i in range(tiles):
        for j in range(tiles):
            blk = img[i * th:(i + 1) * th, j * tw:(j + 1) * tw]
            out[i * th:(i + 1) * th, j * tw:(j + 1) * tw] = luts[i, j][blk]
    return out


def seam_jump(img: npt.NDArray[np.uint8], tiles: int = TILES) -> float:
    """块边界上的平均跳变 ÷ 别处的平均跳变 —— 「方格痕迹」有多明显。

    水平方向相邻两列的差,在块的分界列上取平均,再除以其他列的平均值。
    没有痕迹时这个比值接近 1;有瓷砖感时会明显大于 1。
    """
    tw = img.shape[1] // tiles
    d = np.abs(np.diff(img.astype(np.float64), axis=1))     # 第 k 列 = |x[k+1] − x[k]|
    seam = np.zeros(d.shape[1], dtype=bool)
    seam[[j * tw - 1 for j in range(1, tiles)]] = True       # 分界线落在块的最后一列
    return float(d[:, seam].mean() / d[:, ~seam].mean())


# ---------------------------------------------------------------- 1
def demo_matches_opencv() -> None:
    hr("1. 手写版 vs cv2.createCLAHE")
    for name in ("moon.png", "astronaut.png", "camera.png", "page.png", "coins.png"):
        img = load_gray(name)
        ref = np.asarray(cv2.createCLAHE(clipLimit=CLIP, tileGridSize=(TILES, TILES)).apply(img),
                         dtype=np.uint8)
        mine = clahe_from_scratch(img)
        d = np.abs(mine.astype(np.int64) - ref.astype(np.int64))
        div = "整除" if img.shape[0] % TILES == 0 and img.shape[1] % TILES == 0 else "需补边"
        print(f"  {name:<15s} {str(img.shape):<12s} {div:<7s} "
              f"最大差 {d.max()}  平均差 {d.mean():.4f}  差 ≤1 的像素 {(d <= 1).mean() * 100:.2f}%")
    print("\n  整除的图逐像素相同。需补边的图差 1 —— 剩下的那点是 OpenCV 内部用定点数、")
    print("  这里用 float64 的舍入差,不是算法差(补边规则见第 6 节)。")


# ---------------------------------------------------------------- 2
def demo_one_pixel(img: npt.NDArray[np.uint8]) -> None:
    hr("2. 拆开一个像素:4 个块、4 个权重、4 个查表结果")
    luts = tile_luts(img)
    th, tw = img.shape[0] // TILES, img.shape[1] // TILES
    y, x = 100, 200                      # 随便挑一个不在块中心、也不在边界的像素
    val = int(img[y, x])

    u, v = x / tw - 0.5, y / th - 0.5
    j1, i1 = int(np.floor(u)), int(np.floor(v))
    xa, ya = u - j1, v - i1
    j2, i2 = min(j1 + 1, TILES - 1), min(i1 + 1, TILES - 1)

    print(f"  像素 (y={y}, x={x}),原始灰度 {val};块大小 {th}×{tw}")
    print(f"  u = x/tw − 0.5 = {x}/{tw} − 0.5 = {u:.3f}  →  左表列号 {j1},右表权重 xa = {xa:.3f}")
    print(f"  v = y/th − 0.5 = {y}/{th} − 0.5 = {v:.3f}  →  上表行号 {i1},下表权重 ya = {ya:.3f}\n")

    total = 0.0
    print(f"  {'参与的块':<12s}{'权重':>9s}{'这张表把 ' + str(val) + ' 映射到':>20s}{'贡献':>10s}")
    for (bi, bj, wy, wx, label) in ((i1, j1, 1 - ya, 1 - xa, "左上"),
                                    (i1, j2, 1 - ya, xa, "右上"),
                                    (i2, j1, ya, 1 - xa, "左下"),
                                    (i2, j2, ya, xa, "右下")):
        wgt = wy * wx
        s = int(luts[bi, bj][val])
        total += wgt * s
        print(f"  {label}块 ({bi},{bj}){wgt:9.3f}{s:20d}{wgt * s:10.2f}")
    print(f"  {'':<12s}{'权重和 1.000':>9s}{'':>20s}{total:10.2f}  → 四舍五入 {int(round(total))}")

    mine = interpolate(img, luts, th, tw)
    print(f"\n  整幅图算出来的同一个像素:{int(mine[y, x])}  ✓")
    print(f"  注意四张表把同一个灰度 {val} 分别映射到了 "
          f"{[int(luts[i, j][val]) for i, j in ((i1, j1), (i1, j2), (i2, j1), (i2, j2))]}"
          f" —— 差距就是「自适应」本身。")


# ---------------------------------------------------------------- 3
def demo_border(img: npt.NDArray[np.uint8]) -> None:
    hr("3. 边界像素:没有 4 个邻居怎么办")
    th, tw = img.shape[0] // TILES, img.shape[1] // TILES
    h, w = img.shape
    u = np.arange(w) / tw - 0.5
    v = np.arange(h) / th - 0.5
    inner_x = (u >= 0) & (u <= TILES - 1)
    inner_y = (v >= 0) & (v <= TILES - 1)

    print(f"  图 {h}×{w},块 {th}×{tw},最外圈半块({th // 2} 行 / {tw // 2} 列)没有外侧的邻居")
    print(f"  真正用上 4 张表的像素:{inner_y.sum()} 行 × {inner_x.sum()} 列 = "
          f"{inner_y.sum() * inner_x.sum() / img.size * 100:.1f}% 的画面")
    print(f"  其余 {(1 - inner_y.sum() * inner_x.sum() / img.size) * 100:.1f}% 落在边上或角上:")
    print(f"    边上 —— u 或 v 被 clamp,两张表变成同一张,那个方向的插值自动失效,只剩另一方向")
    print(f"    角上 —— 两个方向都被 clamp,4 张表全是同一张,等于直接用角块的表")
    print("  所以代码里不需要写任何 if:clamp 之后权重照样加起来是 1,退化是自动发生的。")


# ---------------------------------------------------------------- 4
def demo_seams(img: npt.NDArray[np.uint8]) -> None:
    hr("4. 不插值会怎样 —— 方格痕迹的量化")
    th, tw = img.shape[0] // TILES, img.shape[1] // TILES
    print("  指标:「块边界上的平均跳变 ÷ 别处的平均跳变」,越接近原图基线越看不出接缝\n")
    print(f"    原图基线{seam_jump(img):>28.2f}\n")
    print(f"    {'clipLimit':>10s}{'不插值(AHE 的做法)':>22s}{'双线性插值(CLAHE)':>21s}")
    for c in (2.0, 5.0, 40.0):
        luts = tile_luts(img, clip=c)
        print(f"    {c:10.1f}{seam_jump(nearest_tile(img, luts)):22.2f}"
              f"{seam_jump(interpolate(img, luts, th, tw)):21.2f}")

    luts = tile_luts(img)
    near, bili = nearest_tile(img, luts), interpolate(img, luts, th, tw)
    print(f"\n  不插值时接缝处的跳变是别处的两三倍,而且 clipLimit 越大越明显"
          f"(拉得越狠,两张表分歧越大)")
    print(f"  —— 这就是肉眼看到的瓷砖格,也是 AHE 不能直接用的原因。")
    print(f"  插值后三档都回到原图基线,接缝彻底消失。")
    print(f"  clip=2 时两种做法的最大逐像素差:"
          f"{int(np.abs(near.astype(np.int64) - bili.astype(np.int64)).max())}")
    print("\n  ⚠️ 选图有讲究:这个指标要求原图基线接近 1。astronaut.png 是 1.14,干净;")
    print("     moon.png 是 2 倍放大出来的(偶数列的梯度恒为 0),基线就有 1.97,")
    print("     拿它量会把放大的痕迹一起算进去。指标要挑对图用。")


# ---------------------------------------------------------------- 5
def demo_equivalence(img: npt.NDArray[np.uint8]) -> None:
    hr("5. 「先插 LUT 再查表」与「先查表再插值」等价")
    luts = tile_luts(img)
    th, tw = img.shape[0] // TILES, img.shape[1] // TILES
    y, x = 100, 200
    val = int(img[y, x])
    u, v = x / tw - 0.5, y / th - 0.5
    j1, i1 = int(np.floor(u)), int(np.floor(v))
    xa, ya = u - j1, v - i1
    j2, i2 = min(j1 + 1, TILES - 1), min(i1 + 1, TILES - 1)
    wgts = ((i1, j1, (1 - ya) * (1 - xa)), (i1, j2, (1 - ya) * xa),
            (i2, j1, ya * (1 - xa)), (i2, j2, ya * xa))

    a = sum(w * float(luts[bi, bj][val]) for bi, bj, w in wgts)      # 先查表,再加权
    blended = sum(w * luts[bi, bj].astype(np.float64) for bi, bj, w in wgts)
    b = float(blended[val])                                          # 先把 4 张表混成 1 张,再查
    print(f"  先查表再加权:{a:.6f}")
    print(f"  先混表再查表:{b:.6f}")
    print(f"  差 {abs(a - b):.2e}\n")
    print("  原因:加权求和是线性的,而查表只是「取第 val 项」,两者可以交换顺序。")
    print("  实现上一般选前者 —— 混表要对 256 项全算一遍,查表只需要 1 项。")


# ---------------------------------------------------------------- 6
def demo_padding_quirk() -> None:
    hr("6. ⚠️ OpenCV 的补边怪癖")
    img = load_gray("page.png")
    h, w = img.shape
    ref = np.asarray(cv2.createCLAHE(clipLimit=CLIP, tileGridSize=(TILES, TILES)).apply(img),
                     dtype=np.uint8)
    print(f"  page.png 是 {h}×{w}:{h} % {TILES} = {h % TILES},{w} % {TILES} = {w % TILES}"
          f"(高除不尽,宽正好整除)\n")

    def try_pad(pad_h: int, pad_w: int, note: str) -> None:
        src = cv2.copyMakeBorder(img, 0, pad_h, 0, pad_w, cv2.BORDER_REFLECT_101)
        luts = tile_luts(src)
        out = interpolate(img, luts, src.shape[0] // TILES, src.shape[1] // TILES)
        d = np.abs(out.astype(np.int64) - ref.astype(np.int64))
        print(f"  补 {pad_h} 行 {pad_w} 列 → {src.shape}  最大差 {d.max():2d}  "
              f"平均差 {d.mean():.3f}   {note}")

    try_pad(0, 0, "不补边:块大小 23×48,最后 7 行根本没进统计")
    try_pad(TILES - h % TILES, 0, "只补除不尽的那一边 —— 看着合理,但对不上")
    try_pad(TILES - h % TILES, TILES - w % TILES, "← OpenCV 的实际做法")
    print("\n  OpenCV 的判断是「只要有一边除不尽,就两边都补 tiles − (n % tiles)」。")
    print("  宽本来整除,余数 0,于是补了满满一整块 8 列。这不是文档写的,是源码的实际行为。")
    print("  为什么重要:块大小从 48 变成 49,所有块的边界都跟着挪,结果完全不同。")
    print("  自己实现时如果要和 OpenCV 对齐,这一条必须照抄;不对齐的话其实随便补都行。")


# ---------------------------------------------------------------- 图板
def save_figure(out_path: Path, img: npt.NDArray[np.uint8]) -> None:
    th, tw = img.shape[0] // TILES, img.shape[1] // TILES
    # 上排故意用 clipLimit=40(几乎不限幅,也就是 AHE):拉得越狠,相邻两张表分歧越大,
    # 接缝才看得清。插值和限幅是两件独立的事,这样正好把「接缝」单独拎出来看。
    ahe_luts = tile_luts(img, clip=40.0)
    near = nearest_tile(img, ahe_luts)
    bili = interpolate(img, ahe_luts, th, tw)
    luts = tile_luts(img)

    fig, axes = plt.subplots(2, 3, figsize=(16.5, 9.5))

    axes[0, 0].imshow(near, cmap="gray", vmin=0, vmax=255)
    axes[0, 0].set_title(f"AHE 不插值:块内直接查本块的表\n块边界跳变是别处的 {seam_jump(near):.2f} 倍,瓷砖格",
                         fontsize=10)
    axes[0, 1].imshow(bili, cmap="gray", vmin=0, vmax=255)
    axes[0, 1].set_title(f"同样的表,改成查周围 4 张加权\n降到 {seam_jump(bili):.2f} 倍(原图基线 "
                         f"{seam_jump(img):.2f}),接缝消失", fontsize=10)
    for ax in axes[0, :2]:
        ax.axis("off")
        for k in range(1, TILES):     # 把块边界画出来,好对照
            ax.axhline(k * th - 0.5, color="tab:red", lw=0.5, alpha=0.45)
            ax.axvline(k * tw - 0.5, color="tab:red", lw=0.5, alpha=0.45)

    diff = np.abs(near.astype(np.float64) - bili.astype(np.float64))
    im = axes[0, 2].imshow(diff, cmap="magma")
    axes[0, 2].set_title(f"两者之差:最大 {diff.max():.0f} 级\n差得最多的正是块中心之间的过渡带",
                         fontsize=10)
    axes[0, 2].axis("off")
    fig.colorbar(im, ax=axes[0, 2], fraction=0.046)

    # 假想一个灰度恒为 v0 的像素,沿着一行走过去,看它被映射到哪
    # —— 不掺画面内容,插值的形状最干净
    ax = axes[1, 0]
    v0 = 128
    row_tile = 3
    xs = np.arange(img.shape[1])
    u = xs / tw - 0.5
    j1 = np.floor(u).astype(int)
    xa = u - j1
    j2 = np.clip(j1 + 1, 0, TILES - 1)
    j1 = np.clip(j1, 0, TILES - 1)
    step = ahe_luts[row_tile, np.clip(xs // tw, 0, TILES - 1), v0]
    smooth = ahe_luts[row_tile, j1, v0] * (1 - xa) + ahe_luts[row_tile, j2, v0] * xa
    ax.step(xs, step, where="post", color="tab:red", lw=1.4, label="不插值:整块一个值,台阶")
    ax.plot(xs, smooth, color="tab:green", lw=1.8, label="双线性:块中心之间连直线")
    for k in range(TILES):
        ax.axvline(k * tw + tw / 2, color="gray", ls=":", lw=0.8)
    for k in range(1, TILES):
        ax.axvline(k * tw, color="gray", ls="--", lw=0.8)
    ax.set_xlim(0, img.shape[1] - 1)
    ax.set_xlabel(f"列号(虚线 = 块边界,点线 = 块中心);第 {row_tile} 行块")
    ax.set_ylabel(f"灰度 {v0} 被映射到")
    ax.set_title(f"同一个输入灰度 {v0},走过一整行的去向\n台阶在块边界上跳,直线在块中心处转折",
                 fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # 权重场:某一张表在全图上的权重
    ax = axes[1, 1]
    bi, bj = 3, 3
    u = np.arange(img.shape[1]) / tw - 0.5
    v = np.arange(img.shape[0]) / th - 0.5
    wx = np.clip(1 - np.abs(u - bj), 0, 1)
    wy = np.clip(1 - np.abs(v - bi), 0, 1)
    im = ax.imshow(wy[:, None] * wx[None, :], cmap="viridis", vmin=0, vmax=1)
    ax.set_title(f"第 ({bi},{bj}) 块那张表的权重场\n块中心是 1,一个块的距离外降到 0",
                 fontsize=10)
    ax.axis("off")
    fig.colorbar(im, ax=ax, fraction=0.046)

    # 四张相邻表的曲线
    ax = axes[1, 2]
    for (i, j), color in zip(((3, 3), (3, 4), (4, 3), (4, 4)),
                             ("tab:blue", "tab:orange", "tab:green", "tab:red")):
        ax.plot(np.arange(256), luts[i, j], color=color, lw=1.4, label=f"块 ({i},{j})")
    ax.plot(np.arange(256), np.arange(256), "--", color="gray", lw=1.0, label="恒等")
    ax.set_xlim(0, 255)
    ax.set_ylim(0, 255)
    ax.set_aspect("equal")
    ax.set_xlabel("输入 r")
    ax.set_ylabel("输出 s")
    ax.set_title("参与插值的那 4 张表\n同一个输入,四张表给出不同答案", fontsize=10)
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(alpha=0.3)

    fig.suptitle("CLAHE 的块间双线性插值:LUT 属于块中心,像素按到中心的距离加权查 4 张表",
                 fontsize=13)
    # 每格标题两行,不留行距会压住上一行
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94), h_pad=3.0)
    fig.savefig(out_path, dpi=110)


def main() -> None:
    img = load_gray("astronaut.png")
    print(f"主图 astronaut.png  shape={img.shape}  tileGridSize=({TILES},{TILES})  clipLimit={CLIP}")

    demo_matches_opencv()
    demo_one_pixel(img)
    demo_border(img)
    demo_seams(img)
    demo_equivalence(img)
    demo_padding_quirk()

    out = REPO / "Assets" / "results" / "clahe-interpolation-demo.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    save_figure(out, img)
    print(f"\n结果已保存: {out.relative_to(REPO)}")

    if "--show" in sys.argv:
        plt.show()


if __name__ == "__main__":
    main()
