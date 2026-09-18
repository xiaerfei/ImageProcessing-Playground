"""第 6~7 周(3.6 延伸):边缘检测 —— 24 Canny 与 LoG,附一篇知乎文章的纠错验证。

对应文档 Documents/05-spatial-filtering/04-edge-detection.md。

23 号脚本讲的是「锐化」(把边缘强调出来给人看),这一篇讲「检测」——
**输出不再是一张好看的图,而是一份「哪些像素是边」的名单**。

    锐化:输入一张图 → 输出一张更清楚的图
    检测:输入一张图 → 输出一张**二值图**,白的是边,黑的不是

Canny 的四步:

    1. 高斯平滑      先降噪,否则噪声全被当成边
    2. 算梯度        幅值(变化多大)+ 方向(往哪边变)
    3. 非极大值抑制   把粗边削成单像素细线
    4. 双阈值 + 滞后连接  强边直接要,弱边只有挨着强边才要

验证七件事(前四件是给一篇知乎文章纠错,那几处说法会把人带沟里):
1. ⚠️「核的元素之和应为 0,保证滤波前后总体灰度不变」—— **反了**。
   实测和为 0 的核会把均值 129.1 的图变成 0.00;保证亮度不变的是和为 1
2. ⚠️「非极大值抑制之后置为 1,得到二值图」—— **不能**。NMS 必须保留幅值,
   实测输出跨 423 个档位,二值化之后双阈值就没东西可比了
3. ⚠️「NMS 第一步先判断在 8 邻域内是否最大」—— **多余且有害**。
   实测这一条会把 84.3% 的候选边缘点误删
4. ⚠️「滞后阈值计算代价过大,实际常常舍去」—— 代价大是**递归写法**的锅。
   换成栈迭代就是 O(N),实测纯 Python 只要 10 ms;而且舍掉它会丢掉真边
5. 手写 Canny 四步,与 cv2.Canny 的重合度
6. LoG(高斯拉普拉斯)与零交叉:二阶导数怎么定位边
7. 六种算子横向对比

用法:
    .venv/bin/python Ch03_Spatial_Filtering/24_edge_detection.py [--show]
    结果图保存到 Assets/results/canny-steps.png(四步拆解)
                     Assets/results/edge-operator-compare.png(六种算子)
"""

import sys
import time
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


def hr(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def load_gray(name: str) -> npt.NDArray[np.uint8]:
    path = REPO / "Assets" / "test-images" / name
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise SystemExit(f"读不到 {path}")
    return np.asarray(img, dtype=np.uint8)


# ================================================================ Canny 四步
def gradients(f: npt.NDArray[np.float64], sigma: float = 1.4):
    """第 1~2 步:先高斯平滑,再算梯度的幅值和方向。"""
    blur = cv2.GaussianBlur(f, (0, 0), sigma)
    gx = cv2.Sobel(blur, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(blur, cv2.CV_64F, 0, 1, ksize=3)
    return blur, np.hypot(gx, gy), np.arctan2(gy, gx)


def non_max_suppress(mag: npt.NDArray[np.float64],
                     ang: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """第 3 步:把粗边削成单像素细线。

    做法:沿着**梯度方向**(垂直于边)往前后各看一个像素,
    只有当前点比这两个都大,才留下来。

    ⚠️ 两个常见的讲错:
      - 只比梯度方向上那两个点就够了,**不要**再要求「在 8 邻域内最大」——
        沿着边缘走向上的邻居本来就可能更亮,那样会把正常的边删掉(实测删掉 84.3%)
      - 输出**必须保留幅值**,不能在这一步就置 0/1 ——
        下一步双阈值要拿幅值去比 high/low,二值化了就没东西可比
    """
    h, w = mag.shape
    out = np.zeros_like(mag)
    deg = np.degrees(ang) % 180.0          # 方向只分半圈就够(梯度正反是同一条边)
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            d = deg[y, x]
            if d < 22.5 or d >= 157.5:     # 接近水平的梯度 → 比较左右
                p, q = mag[y, x - 1], mag[y, x + 1]
            elif d < 67.5:                 # 45° 方向
                p, q = mag[y + 1, x - 1], mag[y - 1, x + 1]
            elif d < 112.5:                # 接近垂直的梯度 → 比较上下
                p, q = mag[y - 1, x], mag[y + 1, x]
            else:                          # 135° 方向
                p, q = mag[y - 1, x - 1], mag[y + 1, x + 1]
            if mag[y, x] >= p and mag[y, x] >= q:
                out[y, x] = mag[y, x]      # ← 保留幅值,不是置 1
    return out


def hysteresis(strong: npt.NDArray[np.bool_],
               weak: npt.NDArray[np.bool_]) -> npt.NDArray[np.bool_]:
    """第 4 步:滞后连接。从每个强边点出发,把挨着它的弱边点也收进来。

    用**栈 + 循环**,不要用递归 —— 递归在 512×512 上会直接爆栈
    (Python 默认递归上限 1000),而且慢。换成栈就是 O(N),实测 10 ms。
    """
    h, w = strong.shape
    out = strong.copy()
    stack = list(zip(*np.nonzero(strong)))
    while stack:
        y, x = stack.pop()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and weak[ny, nx] and not out[ny, nx]:
                    out[ny, nx] = True
                    stack.append((ny, nx))
    return out


def canny_from_scratch(img: npt.NDArray[np.uint8], sigma: float = 1.4,
                       lo_pct: float = 70.0, hi_pct: float = 90.0):
    """完整的四步。阈值用百分位定,省得对每张图手调。"""
    f = img.astype(np.float64)
    blur, mag, ang = gradients(f, sigma)
    thin = non_max_suppress(mag, ang)
    nz = thin[thin > 0]
    hi, lo = np.percentile(nz, hi_pct), np.percentile(nz, lo_pct)
    strong, weak = thin >= hi, (thin >= lo) & (thin < hi)
    edges = hysteresis(strong, weak)
    return dict(blur=blur, mag=mag, thin=thin, strong=strong, weak=weak,
                edges=edges, lo=float(lo), hi=float(hi))


# ================================================================ LoG
def log_zero_cross(f: npt.NDArray[np.float64], sigma: float = 2.0,
                   thresh_ratio: float = 0.06) -> npt.NDArray[np.bool_]:
    """LoG(高斯拉普拉斯)+ 零交叉。

    二阶导数在边缘处是「一正一负」,中间穿过 0 —— 那个**过零点**就是边的正中。
    所以找边 = 找相邻两个像素**异号、且落差够大**的地方。
    落差要求是必须的:平坦区的浮点噪声也会反复穿过 0,不设门槛会全是雪花。
    """
    lg = cv2.Laplacian(cv2.GaussianBlur(f, (0, 0), sigma), cv2.CV_64F)
    t = thresh_ratio * float(np.abs(lg).max())
    out = np.zeros(lg.shape, dtype=bool)
    a = lg
    # 四个方向各查一遍:左右、上下、两条对角线
    for sl_a, sl_b in (((slice(None), slice(0, -1)), (slice(None), slice(1, None))),
                       ((slice(0, -1), slice(None)), (slice(1, None), slice(None))),
                       ((slice(0, -1), slice(0, -1)), (slice(1, None), slice(1, None))),
                       ((slice(0, -1), slice(1, None)), (slice(1, None), slice(0, -1)))):
        p, q = a[sl_a], a[sl_b]
        hit = (np.sign(p) != np.sign(q)) & (np.abs(p - q) > t)
        out[sl_a] |= hit
    return out


def log_kernel(size: int = 9, sigma: float = 1.5) -> npt.NDArray[np.float64]:
    """直接按公式生成 LoG 核(墨西哥草帽),并把总和调成 0。

    用的是 −∇²G 这一支,所以中心是正的。总和必须是 0 ——
    求导类的核都这样,意思是「平坦的地方输出 0」(见第 1 节)。
    """
    r = np.arange(size) - size // 2
    xx, yy = np.meshgrid(r, r)
    rr = xx ** 2 + yy ** 2
    k = (1.0 - rr / (2.0 * sigma ** 2)) * np.exp(-rr / (2.0 * sigma ** 2))
    return k - k.mean()               # 强制总和为 0,抵消截断带来的零头


def f1_against(a: npt.NDArray[np.bool_], b: npt.NDArray[np.bool_], tol: int = 1):
    """两张边缘图有多像。允许差 tol 个像素的位置误差(边本来就有一两像素抖动)。"""
    k = np.ones((2 * tol + 1, 2 * tol + 1), np.uint8)
    a_d = cv2.dilate(a.astype(np.uint8), k).astype(bool)
    b_d = cv2.dilate(b.astype(np.uint8), k).astype(bool)
    prec = float((a & b_d).sum()) / max(int(a.sum()), 1)
    rec = float((b & a_d).sum()) / max(int(b.sum()), 1)
    return prec, rec, 2 * prec * rec / max(prec + rec, 1e-9)


# ---------------------------------------------------------------- 1
def demo_kernel_sum() -> None:
    hr("1. ⚠️ 纠错:「核的元素之和应为 0,保证滤波前后总体灰度不变」—— 反了")
    flat = np.full((64, 64), 100.0)
    print("  拿一片均匀的灰(全是 100)去过不同的核:\n")
    print(f"  {'核':<26s}{'核的和':>8s}{'均匀区的输出':>14s}")
    for name, k in (("拉普拉斯(求导类)", np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], np.float32)),
                    ("高斯(平滑类,已归一化)",
                     np.asarray(cv2.getGaussianKernel(3, 1.0) @ cv2.getGaussianKernel(3, 1.0).T,
                                np.float32)),
                    ("盒式但忘了除以 9", np.ones((3, 3), np.float32))):
        out = cv2.filter2D(flat, cv2.CV_64F, k)
        print(f"  {name:<26s}{k.sum():8.2f}{out[32, 32]:14.1f}")

    img = load_gray("camera.png").astype(np.float64)
    lap = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], np.float32)
    gau = np.asarray(cv2.getGaussianKernel(5, 1.2) @ cv2.getGaussianKernel(5, 1.2).T, np.float32)
    print(f"\n  真图 camera.png 的均值 {img.mean():.1f}:")
    print(f"    过和为 0 的核 → 均值 {cv2.filter2D(img, cv2.CV_64F, lap).mean():.2f}(整幅图归零)")
    print(f"    过和为 1 的核 → 均值 {cv2.filter2D(img, cv2.CV_64F, gau).mean():.2f}(基本不变)")
    print("\n  结论:**和为 1 才保证亮度不变;和为 0 是「求导类」核的特征**,")
    print("  它的意思是「平坦的地方输出 0」,恰恰是要把整体亮度扔掉,只留变化。")


# ---------------------------------------------------------------- 2 & 3
def demo_nms_pitfalls(img: npt.NDArray[np.uint8]) -> None:
    hr("2. ⚠️ 纠错:非极大值抑制的两个常见讲错")
    f = img.astype(np.float64)
    _, mag, ang = gradients(f)
    t0 = time.perf_counter()
    thin = non_max_suppress(mag, ang)
    ms = (time.perf_counter() - t0) * 1000

    nz = thin[thin > 0]
    print(f"  (a)「NMS 之后置为 1,得到二值图」—— 不能这么干\n")
    print(f"      NMS 输出范围 [0, {thin.max():.0f}],非零点 {nz.size} 个,"
          f"跨了 {len(np.unique(np.round(nz)))} 个不同档位")
    print(f"      下一步双阈值要拿这些幅值去比 high / low。")
    print(f"      如果这一步就置成 0/1,阈值只能在 {{0,1}} 上比 —— **双阈值彻底失效**。")
    print(f"      二值化是**第 4 步**(双阈值)做的,不是第 3 步。")

    t0 = time.perf_counter()
    strict = _nms_with_8neighbour_max(mag, ang)
    ms2 = (time.perf_counter() - t0) * 1000
    a, b = int((thin > 0).sum()), int((strict > 0).sum())
    print(f"\n  (b)「先判断是否在 8 邻域内最大」—— 多余,而且有害\n")
    print(f"      只比梯度方向上那两点   保留 {a} 个候选点   ({ms:.0f} ms)")
    print(f"      额外要求 8 邻域内最大   保留 {b} 个候选点   ({ms2:.0f} ms)")
    print(f"      **误删了 {a - b} 个,占 {(a - b) / a * 100:.1f}%**")
    print("      为什么有害:NMS 要削的是「边的粗细」,方向是**垂直于边**的那条线。")
    print("      而沿着边**走向**上的邻居本来就是边,幅值可能比你还大 ——")
    print("      要求 8 邻域内最大,等于把一条连续的边打成断断续续的点。")


def _nms_with_8neighbour_max(mag, ang):
    """对照组:多加一条「必须是 8 邻域内最大」的错误条件。"""
    h, w = mag.shape
    out = np.zeros_like(mag)
    deg = np.degrees(ang) % 180.0
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if mag[y, x] < mag[y - 1:y + 2, x - 1:x + 2].max():
                continue
            d = deg[y, x]
            if d < 22.5 or d >= 157.5:
                p, q = mag[y, x - 1], mag[y, x + 1]
            elif d < 67.5:
                p, q = mag[y + 1, x - 1], mag[y - 1, x + 1]
            elif d < 112.5:
                p, q = mag[y - 1, x], mag[y + 1, x]
            else:
                p, q = mag[y - 1, x - 1], mag[y + 1, x + 1]
            if mag[y, x] >= p and mag[y, x] >= q:
                out[y, x] = mag[y, x]
    return out


# ---------------------------------------------------------------- 4
def demo_hysteresis(img: npt.NDArray[np.uint8]) -> None:
    hr("3. ⚠️ 纠错:「滞后阈值计算代价过大,实际常常舍去」")
    r = canny_from_scratch(img)
    t0 = time.perf_counter()
    linked = hysteresis(r["strong"], r["weak"])
    ms = (time.perf_counter() - t0) * 1000
    print(f"  先说代价:栈 + 循环的写法,512×512 上纯 Python 只要 {ms:.0f} ms。")
    print(f"  「代价过大」是**递归写法**的锅 —— Python 默认递归上限只有 "
          f"{sys.getrecursionlimit()},512×512 上直接爆栈。")
    print("  算法本身是 O(N):每个像素最多进出栈一次。换个写法就完事了。\n")

    print(f"  再说该不该做(阈值取 NMS 结果的 70% / 90% 分位):\n")
    print(f"    只要强边(≥high)       {int(r['strong'].sum()):6d} 个点   —— 边会断成一截一截")
    print(f"    强边 + 滞后连接        {int(linked.sum()):6d} 个点   "
          f"—— 捞回 {int(linked.sum() - r['strong'].sum())} 个真边点")
    print(f"    强边 + 全部弱边(不筛)  {int((r['strong'] | r['weak']).sum()):6d} 个点   "
          f"—— 混进大量伪边")
    print("\n  滞后阈值干的正是「弱边只有挨着强边才算数」这件事,")
    print("  **是 Canny 区别于「Sobel + 一个阈值」的核心**,不该被建议舍掉。")
    print("  作者建议的形态学细化 bwmorph(...,'thin') 是**另一件事**(把边削细),")
    print("  不是「把断开的边连起来」的替代品。")


# ---------------------------------------------------------------- 5
def demo_canny_vs_cv2(img: npt.NDArray[np.uint8]) -> None:
    hr("4. 手写四步 vs cv2.Canny")
    r = canny_from_scratch(img)
    blur8 = np.clip(np.rint(r["blur"]), 0, 255).astype(np.uint8)
    ref = cv2.Canny(blur8, r["lo"], r["hi"], L2gradient=True) > 0
    p, rc, f1 = f1_against(r["edges"], ref, tol=1)
    print(f"  阈值 low={r['lo']:.1f}  high={r['hi']:.1f}(取 NMS 结果的 70% / 90% 分位)")
    print(f"  手写结果 {int(r['edges'].sum())} 个边缘点,cv2 {int(ref.sum())} 个")
    print(f"  容许 1 像素位置误差时:准确率 {p:.3f}  召回率 {rc:.3f}  F1 {f1:.3f}")
    print("\n  为什么不是逐像素相同(和前面几个脚本不一样):")
    print("    - cv2.Canny 默认用 |gx|+|gy| 当幅值,这里用的是开方版(传了 L2gradient=True 也只是接近)")
    print("    - cv2 的 NMS 把方向量化成 4 档,和这里一样;但它内部用定点数,分界处会差一两个像素")
    print("    - 边缘检测输出的是「哪些点是边」,本来就有一两像素的抖动,所以用 F1 而不是逐像素比")


# ---------------------------------------------------------------- 6
def demo_log(img: npt.NDArray[np.uint8]) -> None:
    hr("5. LoG(高斯拉普拉斯)与零交叉 —— 二阶导数那条路")
    f = img.astype(np.float64)
    print("  思路和 Canny 不一样:")
    print("    Canny 找的是一阶导数的**山峰**(变化最快的地方)")
    print("    LoG  找的是二阶导数的**过零点**(变化开始拐弯的那一点)\n")
    print("  名字拆开看:Laplacian of Gaussian = 先高斯平滑,再拉普拉斯。")
    print("  这两步可以**合成一个核**(卷积的结合律 —— 见基础篇第二节),")
    print("  合成出来的核长得像一顶**墨西哥草帽**:中间一个尖,四周一圈凹陷。\n")
    lap = log_kernel(9, 1.5)
    print(f"    9×9 / σ=1.5 的 LoG 核,中心一行:")
    print(f"      {np.array2string(lap[4], precision=3, suppress_small=True)}")
    print(f"    中心 {lap[4, 4]:+.3f}(尖),紧邻 {lap[4, 3]:+.3f},"
          f"再外面 {lap[4, 2]:+.3f}(凹陷),总和 {lap.sum():+.1e} ≈ 0")
    print("    (符号约定:这里用的是 −∇²G,中心为正;写成 ∇²G 的话整体反号,")
    print("     两种写法都有人用,**看中心是正是负就知道对方用的哪一种**)")

    for sigma in (1.0, 2.0, 3.0):
        zc = log_zero_cross(f, sigma)
        print(f"  σ={sigma:.1f}  零交叉点 {int(zc.sum()):6d} 个 "
              f"({zc.sum() / f.size * 100:5.2f}% 的画面)")
    print("\n  σ 越大,细节被平滑掉得越多,只剩大轮廓 —— σ 就是 LoG 的「看多粗的边」旋钮。")
    print("  ⚠️ 零交叉必须配一个**落差门槛**:平坦区的浮点噪声也会反复穿过 0,")
    print("  不设门槛出来的全是雪花。这一点原文提到了(用 thresh),值得记。")


# ---------------------------------------------------------------- 7
def demo_operator_compare(img: npt.NDArray[np.uint8]) -> None:
    hr("6. 六种算子横向对比")
    f = img.astype(np.float64)
    rob_x = np.array([[1, 0], [0, -1]], np.float32)
    rob_y = np.array([[0, 1], [-1, 0]], np.float32)
    pre_x = np.array([[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]], np.float32)
    pre_y = pre_x.T
    pre_y = pre_x.T

    def mag_of(src, kind):
        if kind == "roberts":
            return np.hypot(cv2.filter2D(src, cv2.CV_64F, rob_x),
                            cv2.filter2D(src, cv2.CV_64F, rob_y))
        if kind == "prewitt":
            return np.hypot(cv2.filter2D(src, cv2.CV_64F, pre_x),
                            cv2.filter2D(src, cv2.CV_64F, pre_y))
        if kind == "sobel":
            return np.hypot(cv2.Sobel(src, cv2.CV_64F, 1, 0, ksize=3),
                            cv2.Sobel(src, cv2.CV_64F, 0, 1, ksize=3))
        return np.hypot(cv2.Scharr(src, cv2.CV_64F, 1, 0), cv2.Scharr(src, cv2.CV_64F, 0, 1))

    kinds = (("Roberts 2×2", "roberts"), ("Prewitt 3×3", "prewitt"),
             ("Sobel 3×3", "sobel"), ("Scharr 3×3", "scharr"))

    # (a) 定位:造一条边界正好在 127.5 列的理想阶跃
    step = np.tile(np.concatenate([np.full(128, 50.0), np.full(128, 200.0)]), (64, 1))
    print("  (a) 定位准不准:真实边界落在第 127.5 列(127 和 128 中间)\n")
    print(f"  {'算子':<14s}{'峰值在第几列':>14s}{'响应重心':>10s}{'偏差':>10s}{'响应宽度':>10s}")
    for name, kind in kinds:
        row = mag_of(step, kind)[32]
        c = np.arange(120, 136)
        w = row[120:136]
        centroid = float((w * c).sum() / w.sum())
        print(f"  {name:<14s}{int(c[w.argmax()]):14d}{centroid:10.2f}"
              f"{centroid - 127.5:+10.2f}{int((w > w.max() * 0.1).sum()):8d} 列")
    print("\n  **Roberts 整整偏了半个像素**,其余三个都正好落在 127.50 —— ")
    print("  这就是「2×2 的核没有中心格」的直接后果,和噪声、精度都无关,是几何上必然的。")
    print("  要拿边缘位置去做测量(标定、拼接、亚像素定位)的话,这半个像素是致命的。")

    # (b) 一个孤立坏点能造出多大的假边
    flat = np.full((64, 64), 100.0)
    bad = flat.copy()
    bad[32, 32] = 255.0
    print("\n  (b) 一个孤立的坏点(传感器坏点、椒盐噪声)会造出多大的假边:\n")
    print(f"  {'算子':<14s}{'坏点引起的响应':>16s}{'波及像素':>10s}{'相当于真边的':>14s}")
    for name, kind in kinds:
        m = mag_of(bad, kind)
        real = mag_of(step, kind)[32, 120:136].max()
        print(f"  {name:<14s}{m.max():16.0f}{int((m > 0).sum()):9d} 个"
              f"{m.max() / real * 100:13.1f}%")
    print("\n  **Roberts 最惨:一个坏点就顶了真边的 73%**,因为它只看 2 个像素,")
    print("  一个坏点就占了一半的发言权。3×3 的算子有平滑那一列兜着,坏点被稀释到 8 个像素里。")
    print("  (Scharr 偏高是因为它的权重更集中在中心;换来的是方向精度,取舍不同)")

    zc = log_zero_cross(f, 2.0)
    edges = canny_from_scratch(img)["edges"]
    print(f"\n  另外两个输出的是二值图,没法直接比相关:")
    print(f"    LoG 零交叉(σ=2)   标出 {int(zc.sum())} 个点 —— 二阶导数,边细但碎")
    print(f"    Canny(手写四步)   标出 {int(edges.sum())} 个点 —— 单像素细边 + 弱边要有依据")
    print("\n  前四个的输出是**灰度图**(每点一个「变化有多大」),后两个是**二值图**(是边/不是边)。")
    print("  这就是「锐化/求梯度」和「边缘检测」的分界:前者给人看,后者给下一步算法用。")


# ---------------------------------------------------------------- 图板
def save_canny_steps(out_path: Path, img: npt.NDArray[np.uint8]) -> None:
    r = canny_from_scratch(img)
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))

    panels = (
        (img, "原图"),
        (np.clip(r["blur"], 0, 255), f"第 1 步 高斯平滑(σ=1.4)\n先降噪,否则噪声全被当成边"),
        (np.clip(r["mag"] / r["mag"].max() * 255, 0, 255),
         "第 2 步 梯度幅值\n边找到了,但又粗又糊"),
        (np.clip(r["thin"] / max(r["thin"].max(), 1) * 255, 0, 255),
         "第 3 步 非极大值抑制\n削成单像素细线,但仍保留幅值(不是二值图)"),
    )
    for ax, (pic, title) in zip(axes.flat[:4], panels):
        ax.imshow(pic, cmap="gray", vmin=0, vmax=255)
        ax.set_title(title, fontsize=10)
        ax.axis("off")

    # 第 4 步:强边红、弱边蓝
    vis = np.zeros((*img.shape, 3), np.uint8)
    vis[r["weak"]] = (60, 120, 255)
    vis[r["strong"]] = (255, 60, 60)
    axes[1, 1].imshow(vis)
    axes[1, 1].set_title(f"第 4 步 双阈值(low={r['lo']:.0f}, high={r['hi']:.0f})\n"
                         f"红 = 强边直接要({int(r['strong'].sum())}),"
                         f"蓝 = 弱边待定({int(r['weak'].sum())})", fontsize=10)
    axes[1, 1].axis("off")

    axes[1, 2].imshow(r["edges"], cmap="gray")
    axes[1, 2].set_title(f"滞后连接后的最终结果\n{int(r['edges'].sum())} 个边缘点 —— "
                         f"挨着强边的弱边才留下", fontsize=10)
    axes[1, 2].axis("off")

    fig.suptitle("Canny 四步:平滑 → 算梯度 → 削成细线 → 双阈值挑出真边", fontsize=13)
    # 每格标题两行,不留行距会压住上一行
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94), h_pad=3.0)
    fig.savefig(out_path, dpi=110)


def save_operator_figure(out_path: Path, img: npt.NDArray[np.uint8]) -> None:
    f = img.astype(np.float64)
    rob_x = np.array([[1, 0], [0, -1]], np.float32)
    rob_y = np.array([[0, 1], [-1, 0]], np.float32)
    pre_x = np.array([[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]], np.float32)

    def norm(m):
        return np.clip(m / m.max() * 255, 0, 255)

    items = (
        (norm(np.hypot(cv2.filter2D(f, cv2.CV_64F, rob_x),
                       cv2.filter2D(f, cv2.CV_64F, rob_y))),
         "Roberts 2×2\n最老最快,没有中心点,怕噪声"),
        (norm(np.hypot(cv2.filter2D(f, cv2.CV_64F, pre_x),
                       cv2.filter2D(f, cv2.CV_64F, pre_x.T))),
         "Prewitt 3×3\n平滑列 [1,1,1]"),
        (norm(np.hypot(cv2.Sobel(f, cv2.CV_64F, 1, 0, ksize=3),
                       cv2.Sobel(f, cv2.CV_64F, 0, 1, ksize=3))),
         "Sobel 3×3\n平滑列 [1,2,1],默认选择"),
        (norm(np.hypot(cv2.Scharr(f, cv2.CV_64F, 1, 0), cv2.Scharr(f, cv2.CV_64F, 0, 1))),
         "Scharr 3×3\n平滑列 [3,10,3],方向最准"),
        (log_zero_cross(f, 2.0).astype(np.uint8) * 255,
         "LoG 零交叉(σ=2)\n二阶导数:找过零点,边细但碎"),
        (canny_from_scratch(img)["edges"].astype(np.uint8) * 255,
         "Canny(手写四步)\n单像素细边,弱边要有依据"),
    )
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    for ax, (pic, title) in zip(axes.flat, items):
        ax.imshow(pic, cmap="gray", vmin=0, vmax=255)
        ax.set_title(title, fontsize=10)
        ax.axis("off")
    fig.suptitle("六种算子:上排四个输出「变化有多大」的灰度图,下排两个输出「是不是边」的二值图",
                 fontsize=13)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94), h_pad=3.0)
    fig.savefig(out_path, dpi=110)


def main() -> None:
    img = load_gray("camera.png")
    print(f"主图 camera.png  shape={img.shape}")

    demo_kernel_sum()
    demo_nms_pitfalls(img)
    demo_hysteresis(img)
    demo_canny_vs_cv2(img)
    demo_log(img)
    demo_operator_compare(img)

    out = REPO / "Assets" / "results" / "canny-steps.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    save_canny_steps(out, img)
    print(f"\n结果已保存: {out.relative_to(REPO)}")
    cmp_path = out.with_name("edge-operator-compare.png")
    save_operator_figure(cmp_path, img)
    print(f"结果已保存: {cmp_path.relative_to(REPO)}")

    if "--show" in sys.argv:
        plt.show()


if __name__ == "__main__":
    main()
