"""第 6 周(3.6 节):空间滤波 —— 23 锐化:跟邻居对着干。

对应文档 Documents/05-spatial-filtering/03-sharpening.md。

平滑是「跟邻居商量,取个折中」;锐化正好相反 ——

    **我比邻居亮,那就让我更亮;我比邻居暗,就让我更暗。**

怎么知道「我比邻居亮多少」?这就要用到导数(差分):

    一阶导数 = 变化有多快   —— 斜坡上一路都有响应,适合「找边在哪儿」
    二阶导数 = 变化的变化   —— 只在拐弯的地方响应,适合「把边精确定位」

验证七件事:
1. 一维小例子:一个斜坡 + 一个台阶,亲眼看一阶和二阶差分长什么样
2. 拉普拉斯(二阶)的核为什么和为 0,以及锐化核 [[0,-1,0],[-1,5,-1],[0,-1,0]]
   就是「原图 − 拉普拉斯」
3. USM(反锐化掩模)三步:模糊 → 原图减模糊 = 细节 → 把细节加回去
4. ⚠️ USM 半径很小时,它和拉普拉斯锐化几乎是同一件事(相关系数 0.9918)
5. 锐化的代价一:过冲(halo)。原本 [50,200] 的边,拉普拉斯锐化后变成 [−100,350]
6. 锐化的代价二:放大噪声。拉普拉斯放大 5.4 倍,USM(k=1)只有 1.86 倍
   —— 这就是工程上用 USM 不用裸拉普拉斯的原因
7. 一阶导数:Sobel 梯度;|gx|+|gy| 可以替代开方(相关 0.9921,最多高估 41%);
   Prewitt/Sobel/Scharr 的区别只在平滑那一列,方向误差 0.549° / 0.275° / 0.068°

用法:
    .venv/bin/python Ch03_Spatial_Filtering/23_sharpening.py [--show]
    结果图保存到 Assets/results/sharpening-derivatives.png(一阶/二阶 + 过冲)
                     Assets/results/sharpening-compare.png(拉普拉斯 vs USM)
                     Assets/results/gradient-compare.png(Sobel 梯度与 Scharr)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figkit import four_questions  # noqa: E402

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

LAP4 = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], np.float32)       # 只看上下左右
LAP8 = np.array([[1, 1, 1], [1, -8, 1], [1, 1, 1]], np.float32)       # 连四个角也看
SHARP = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], np.float32)   # = 单位核 − LAP4


def hr(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def load_gray(name: str) -> npt.NDArray[np.uint8]:
    path = REPO / "Assets" / "test-images" / name
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise SystemExit(f"读不到 {path}")
    return np.asarray(img, dtype=np.uint8)


def laplacian_sharpen(f: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """原图 − 拉普拉斯。中心为负的拉普拉斯核要用减号,搞反了会更糊。"""
    return f - cv2.filter2D(f, cv2.CV_64F, LAP4)


def unsharp(f: npt.NDArray[np.float64], radius: float = 2.0,
            amount: float = 1.0) -> npt.NDArray[np.float64]:
    """USM(反锐化掩模):模糊 → 原图减模糊 = 细节 → 把细节按 amount 倍加回去。"""
    blur = cv2.GaussianBlur(f, (0, 0), radius)
    detail = f - blur
    return f + amount * detail


def to_u8(f: npt.NDArray[np.float64]) -> npt.NDArray[np.uint8]:
    return np.clip(np.rint(f), 0, 255).astype(np.uint8)


def smooth_disk(n: int = 121, radius: float = 40.0) -> npt.NDArray[np.float64]:
    """一个边缘平滑过渡的圆盘。用它测梯度方向,因为**真值是已知的**:

    圆盘上任何一点,亮度变化最快的方向一定是沿着半径 —— 拿算出来的方向
    和它比,就知道这个算子准不准。用硬边(0/200 一刀切)的圆盘不行:
    那种边本身就有锯齿,量到的是锯齿不是算子。
    """
    yy, xx = np.mgrid[-(n // 2):n // 2 + 1, -(n // 2):n // 2 + 1]
    r = np.hypot(xx, yy)
    return 200.0 / (1.0 + np.exp((r - radius) / 1.2))


def angle_error_deg(disk: npt.NDArray[np.float64], ksize: int) -> npt.NDArray[np.float64]:
    """圆盘边缘一圈上,算出来的梯度方向和真实方向差几度。"""
    n = disk.shape[0]
    yy, xx = np.mgrid[-(n // 2):n // 2 + 1, -(n // 2):n // 2 + 1]
    truth = np.arctan2(-yy, -xx)                       # 梯度指向圆心
    dx = cv2.Sobel(disk, cv2.CV_64F, 1, 0, ksize=ksize)
    dy = cv2.Sobel(disk, cv2.CV_64F, 0, 1, ksize=ksize)
    est = np.arctan2(dy, dx)
    diff = np.angle(np.exp(1j * (est - truth)))        # 绕回 ±180° 之内
    return np.degrees(np.abs(diff))


def step_image() -> npt.NDArray[np.float64]:
    """左半 50、右半 200 的一刀切,用来看过冲。"""
    return np.tile(np.concatenate([np.full(20, 50.0), np.full(20, 200.0)]), (40, 1))


# ---------------------------------------------------------------- 1
def demo_derivatives_1d() -> None:
    hr("1. 一维小例子:一阶和二阶差分长什么样")
    x = np.concatenate([np.full(6, 20.0), np.linspace(20, 200, 8),
                        np.full(6, 200.0), np.full(12, 60.0)])
    d1 = np.gradient(x)
    d2 = np.gradient(d1)
    print("  信号:一段平地 → 一个缓坡爬到 200 → 一段平地 → 一刀切到 60\n")
    print("  原始 ", np.round(x).astype(int).tolist())
    print("  一阶 ", np.round(d1).astype(int).tolist())
    print("  二阶 ", np.round(d2).astype(int).tolist())
    print("\n  怎么读:")
    print("    平地上 —— 一阶和二阶都是 0。**不变的地方,两个导数都没反应**")
    print("    缓坡上 —— 一阶一路都是 26(坡有多陡就是多少);")
    print("               二阶只在坡的**起点和终点**有反应(+13 / −13),坡中间是 0")
    print("    一刀切 —— 一阶是一个大尖峰(−70);")
    print("               二阶是**一正一负紧挨着**(−35, +35),中间穿过 0")
    print("\n  所以两者分工不同:")
    print("    **一阶**回答「这儿变化多快」→ 找边缘、算梯度(Sobel 就是干这个的)")
    print("    **二阶**回答「变化在哪儿拐弯」→ 边缘定位更准(那个过零点就是边的正中),")
    print("             而且对缓坡不敏感 —— 只标出真正的突变,不理会平缓的明暗渐变")


# ---------------------------------------------------------------- 2
def demo_laplacian() -> None:
    hr("2. 拉普拉斯:把二阶导数做成一张核")
    print(f"  四邻域版 LAP4 =\n{LAP4.astype(int)}   和 = {int(LAP4.sum())}")
    print(f"  八邻域版 LAP8 =\n{LAP8.astype(int)}   和 = {int(LAP8.sum())}")
    print("\n  为什么和必须是 0:一片均匀的区域经过核,结果 = 值 × 核的和。")
    print("  和为 0 → 平坦区输出 0,只有变化的地方才有响应。**它检测的就是「不平」**。")

    ident = np.zeros((3, 3), np.float32)
    ident[1, 1] = 1.0
    print(f"\n  锐化核怎么来的:单位核 − 拉普拉斯\n{(ident - LAP4).astype(int)}")
    print(f"  这就是那个经典的 [[0,-1,0],[-1,5,-1],[0,-1,0]],"
          f"和 = {int((ident - LAP4).sum())}(亮度不变)")
    print("\n  ⚠️ 符号是最容易搞错的地方:LAP4 的中心是 **−4**(负的),所以要用**减号**。")
    print("     如果核写成中心为 +4 的版本,那就得用加号。判断方法:")
    print("     最后合成出来的锐化核,中心必须是**正的大数**,周围是负数 —— 反了就是在糊图。")

    g = load_gray("camera.png").astype(np.float64)
    a = laplacian_sharpen(g)
    b = cv2.filter2D(g, cv2.CV_64F, ident - LAP4)
    print(f"\n  「原图 − 拉普拉斯」与「直接用锐化核滤一遍」:最大差 {np.abs(a - b).max():.2e}")
    print("  (两种写法完全等价 —— 卷积是线性的,可以先把两个核合成一个,省一遍扫描)")


# ---------------------------------------------------------------- 3
def demo_usm(g: npt.NDArray[np.float64]) -> None:
    hr("3. USM(反锐化掩模):摄影暗房传下来的三步")
    print("  名字很怪:「反锐化」怎么会用来锐化?因为它靠的是一张**不锐**的图:\n")
    print("    第 1 步  把原图模糊一下           blur = GaussianBlur(f, σ)")
    print("    第 2 步  原图减去模糊的 = 只剩细节  detail = f − blur")
    print("    第 3 步  把细节按倍数加回原图      out = f + k × detail\n")
    print("  第 2 步是关键:模糊图里装的是「大块的明暗」,原图减掉它,")
    print("  剩下的正好是「模糊时被抹掉的那些细节」—— 边缘、纹理、噪点。")
    print("  第 3 步再把这份细节加倍还回去,边缘就被强调了。\n")

    blur = cv2.GaussianBlur(g, (0, 0), 2.0)
    detail = g - blur
    print(f"  实测(camera.png,σ=2):")
    print(f"    原图范围      [{g.min():.0f}, {g.max():.0f}]")
    print(f"    模糊图范围    [{blur.min():.0f}, {blur.max():.0f}]")
    print(f"    细节层范围    [{detail.min():.0f}, {detail.max():.0f}]  "
          f"均值 {detail.mean():.3f} —— 以 0 为中心,正负都有")
    print("    (细节层单独看就是一张灰扑扑的浮雕图:平坦区是 0,边缘处一正一负)")

    print("\n  三个参数,对得上 Photoshop 的 USM 对话框:")
    print("    半径 radius(σ) —— 「多大范围算细节」。小 = 只强调最细的纹理;大 = 连大结构一起抬")
    print("    数量 amount(k) —— 加多少倍。k=1 是标准 USM,k>1 叫 high-boost")
    print("    阈值 threshold —— 细节小于这个值就不加(专门用来避开噪声),OpenCV 没有,要自己写")


# ---------------------------------------------------------------- 4
def demo_usm_equals_laplacian(g: npt.NDArray[np.float64]) -> None:
    hr("4. ⚠️ USM 和拉普拉斯锐化,其实是同一件事")
    lap_added = laplacian_sharpen(g) - g          # 拉普拉斯锐化「加上去的那一份」
    print("  两者都是「原图 + 一份细节」,区别只在那份细节怎么算出来的。")
    print("  把两份细节对比一下:\n")
    print(f"  {'USM 半径':>10s}{'与拉普拉斯那份的相关系数':>26s}{'最佳倍率':>12s}")
    for r in (0.6, 1.0, 2.0, 4.0):
        usm_added = unsharp(g, r, 1.0) - g
        a, b = lap_added.ravel(), usm_added.ravel()
        corr = float(np.corrcoef(a, b)[0, 1])
        scale = float(a @ b / (b @ b))
        print(f"  {r:10.1f}{corr:26.4f}{scale:12.2f}")
    print("\n  半径很小时相关系数 0.99 —— **几乎就是同一个东西**。")
    print("  数学上也能解释:高斯模糊做差(DoG)是拉普拉斯的一个近似,")
    print("  半径越小越接近,半径大了就变成「强调大结构」,和二阶导数不是一回事了。")
    print("\n  实际该用哪个:**USM**。原因看下面两节 —— 它的半径给了你一个旋钮,")
    print("  能在「锐化强度」和「噪声/过冲」之间折中;裸拉普拉斯没有旋钮,一上来就是最猛的。")


# ---------------------------------------------------------------- 5
def demo_overshoot() -> None:
    hr("5. 代价一:过冲(halo)—— 边缘两侧会冒出亮边和暗边")
    step = step_image()
    print("  造一张左半 50、右半 200 的一刀切图,锐化之后看它的范围:\n")
    print(f"  {'做法':<18s}{'锐化后范围':>18s}{'下冲':>8s}{'上冲':>8s}")
    for name, out in (("拉普拉斯锐化", laplacian_sharpen(step)),
                      ("USM k=1 σ=2", unsharp(step, 2.0, 1.0)),
                      ("USM k=2 σ=2", unsharp(step, 2.0, 2.0)),
                      ("USM k=0.5 σ=2", unsharp(step, 2.0, 0.5))):
        row = out[20]
        print(f"  {name:<18s}{f'[{row.min():.0f}, {row.max():.0f}]':>18s}"
              f"{50 - row.min():8.0f}{row.max() - 200:8.0f}")
    print("\n  原图明明只有 50 和 200 两个值,锐化后却冲到了 −100 和 350。")
    print("  为什么:锐化就是「让差别更大」,在边缘两侧它会把暗的一侧压得更暗、")
    print("  亮的一侧提得更亮 —— 于是边的两边各多出一条**暗边和亮边**,这就是光晕(halo)。")
    print("\n  两个后果:")
    print("    1. 存成 8 位时,−100 被截成 0、350 被截成 255 —— **信息真的丢了**,不可逆")
    print("    2. 光晕本身就是「锐化过度」最典型的视觉特征,一眼能认出来的「数码味」")
    print("  k 越小、σ 越小,过冲越轻。这就是 USM 的旋钮价值。")


# ---------------------------------------------------------------- 6
def demo_noise(g: npt.NDArray[np.float64]) -> None:
    hr("6. 代价二:噪声被一起放大")
    rng = np.random.default_rng(0)
    sigma = 3.0
    noisy = g + rng.normal(0, sigma, g.shape)
    print(f"  给图加 σ={sigma:.0f} 的噪声,同一个算法分别作用在干净图和带噪图上,")
    print(f"  两者之差就是「被处理过的噪声」:\n")
    print(f"  {'做法':<18s}{'噪声 σ':>10s}{'放大倍数':>10s}")
    for name, fn in (("拉普拉斯锐化", laplacian_sharpen),
                     ("USM k=1 σ=1", lambda f: unsharp(f, 1.0, 1.0)),
                     ("USM k=1 σ=3", lambda f: unsharp(f, 3.0, 1.0)),
                     ("USM k=0.5 σ=3", lambda f: unsharp(f, 3.0, 0.5))):
        d = fn(noisy) - fn(g)
        print(f"  {name:<18s}{d.std():10.2f}{d.std() / sigma:10.2f}×")
    print("\n  原因很直白:**噪声就是「和邻居不一样」**,而锐化干的正是「把和邻居的差别放大」。")
    print("  它分不出哪一份差别是真细节、哪一份是噪点。")
    print("  裸拉普拉斯放大 5.4 倍,USM(k=1)只有 1.86 倍 —— 差了近 3 倍,")
    print("  这就是工程上一律用 USM、不用裸拉普拉斯的原因。")
    print("\n  实用顺序:**先降噪,再锐化**。反过来做,等于先把噪声放大再想办法擦掉。")


# ---------------------------------------------------------------- 7
def demo_gradient(g: npt.NDArray[np.float64]) -> None:
    hr("7. 一阶导数:Sobel 梯度")
    gx = cv2.Sobel(g, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.hypot(gx, gy)
    l1 = np.abs(gx) + np.abs(gy)
    print("  Sobel 分两次做:一次横着找变化(gx),一次竖着找(gy),再合成幅值。\n")
    print(f"    gx 范围 [{gx.min():.0f}, {gx.max():.0f}]   gy 范围 [{gy.min():.0f}, {gy.max():.0f}]")
    print(f"    幅值 √(gx²+gy²) 范围 [0, {mag.max():.0f}]")

    strong = mag > 20                                   # 只看真有梯度的地方
    ratio = (l1 / mag)[strong]
    print(f"\n  省掉开方,直接用 |gx|+|gy| 行不行?")
    print(f"    相关系数 {np.corrcoef(mag.ravel(), l1.ravel())[0, 1]:.4f},"
          f"比值范围 [{ratio.min():.3f}, {ratio.max():.3f}]")
    print(f"    最多高估 {(ratio.max() - 1) * 100:.0f}%(正好是 √2,发生在 45° 斜边上)。")
    print("    开方在老硬件上很贵,所以定点实现里几乎都用 |gx|+|gy| —— 代价是斜边偏亮一点。")

    print("\n  Sobel 的核为什么是 [1,2,1]ᵀ × [−1,0,1]:")
    print("    [−1,0,1] 是差分(找变化),[1,2,1] 是平滑(压噪声)。")
    print("    **先平滑再求导**,不然噪声会被求导放大得没法看。")
    print("    这也是它天生可分离的原因(见基础篇第六节)。")

    disk = smooth_disk()
    n = disk.shape[0]
    yy, xx = np.mgrid[-(n // 2):n // 2 + 1, -(n // 2):n // 2 + 1]
    r = np.hypot(xx, yy)
    band = (r > 34) & (r < 46)
    print("\n  Prewitt / Sobel / Scharr:差别在「方向准不准」")
    print("  拿一个边缘平滑的圆盘测 —— 圆盘上梯度的真实方向一定是沿半径,真值已知:\n")
    print(f"  {'算子':<10s}{'平滑那一列':>14s}{'平均角度误差':>14s}{'最大角度误差':>14s}")
    for name, ks in (("Prewitt", None), ("Sobel", 3), ("Scharr", cv2.FILTER_SCHARR)):
        if name == "Prewitt":
            dx = cv2.filter2D(disk, cv2.CV_64F,
                              np.array([[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]], np.float32))
            dy = cv2.filter2D(disk, cv2.CV_64F,
                              np.array([[-1, -1, -1], [0, 0, 0], [1, 1, 1]], np.float32))
            est = np.arctan2(dy, dx)
            truth = np.arctan2(-yy, -xx)
            err = np.degrees(np.abs(np.angle(np.exp(1j * (est - truth)))))
            col = "[1, 1, 1]"
        else:
            err = angle_error_deg(disk, ks)
            col = "[1, 2, 1]" if name == "Sobel" else "[3, 10, 3]"
        e = err[band]
        print(f"  {name:<10s}{col:>14s}{e.mean():13.3f}°{e.max():13.3f}°")

    print("\n  三个算子的差分那一列都是 [−1,0,1],完全一样;**区别只在平滑那一列**:")
    print("    Prewitt [1,1,1]    一视同仁 —— 就是盒式那套,误差最大")
    print("    Sobel   [1,2,1]    中间重一点,误差减半")
    print("    Scharr  [3,10,3]   中间重得多,误差又降到 Sobel 的四分之一")
    print("  [3,10,3] 这组数不是拍脑袋来的,是**专门解出来让方向误差最小**的。")
    print("  什么时候在意:要算边缘朝向、做 HOG 特征、拼接对齐时,方向准不准直接影响结果;")
    print("  只是想「看看边在哪儿」的话,Sobel 完全够用。")
    print("  3×3 想要精度就用 Scharr:cv2.Scharr(...) 或 cv2.Sobel(..., ksize=cv2.FILTER_SCHARR)。")


# ---------------------------------------------------------------- 图板
def save_derivative_figure(out_path: Path) -> None:
    """一阶/二阶导数。三行上下叠放,共用 x 轴。

    为什么重画(2026-09-23):上一版把原始信号、一阶、二阶三条线挤在同一根 y 轴上,
    而三者单位根本不同 —— 原始是灰度值,一阶二阶是「变化量」。为了让后两条看得见,
    还把它们 ×3,于是图上一阶显示 78,正文表格里却写 26,读的人对不上号。
    上下叠放、各自一根 y 轴、不做任何缩放,就没有这个问题。
    """
    x = np.concatenate([np.full(6, 20.0), np.linspace(20, 200, 8),
                        np.full(6, 200.0), np.full(12, 60.0)])
    d1 = np.gradient(x)
    d2 = np.gradient(d1)

    # 四个路段:拿「骑车」当尺子 —— 海拔 / 陡不陡 / 陡度在不在变
    bands = [(0, 6, "平地", "#f0f3f6"), (6, 14, "缓坡", "#eaf3ea"),
             (14, 19, "平地", "#f0f3f6"), (19, 21, "一刀切", "#fdeeea"),
             (21, 32, "平地", "#f0f3f6")]

    fig, axes = plt.subplots(3, 1, figsize=(10.2, 9.0), sharex=True,
                             gridspec_kw=dict(hspace=0.16))
    rows = [(x, "black", "原始信号\n(海拔:你在多高)", None),
            (d1, "#2c6fbb", "一阶差分\n(陡不陡)", 0),
            (d2, "#c4442a", "二阶差分\n(陡度在不在变)", 0)]
    for ax, (y, color, label, zero) in zip(axes, rows):
        for a, b, name, bg in bands:
            ax.axvspan(a - 0.5, b - 0.5, color=bg, zorder=0)
        if zero is not None:
            ax.axhline(0, color="#999", lw=0.9)
        ax.plot(y, "o-", color=color, ms=3.4, lw=1.8, zorder=3)
        ax.set_ylabel(label, fontsize=9.5)
        ax.spines[["top", "right"]].set_visible(False)
        ax.margins(y=0.22)

    for a, b, name, _ in bands:                 # 路段名只标一次,写在最上面那行
        axes[0].text((a + b - 1) / 2, 232, name, ha="center", fontsize=9.5, color="#4a5560")
    axes[0].set_ylim(0, 250)

    axes[1].set_yticks([-70, -35, 0, 26])
    axes[1].annotate("整个坡上一路都是 26\n坡多陡就是多少", xy=(10, 26), xytext=(1.2, 44),
                     fontsize=9, color="#2c6fbb",
                     arrowprops=dict(arrowstyle="->", color="#2c6fbb", lw=1.0))
    axes[1].annotate("一刀切:一个大尖峰 −70", xy=(19.5, -70), xytext=(22.5, -52),
                     fontsize=9, color="#2c6fbb",
                     arrowprops=dict(arrowstyle="->", color="#2c6fbb", lw=1.0))
    axes[2].annotate("坡中间是 0 ——\n二阶对缓坡没反应", xy=(10, 0), xytext=(7.4, 22),
                     fontsize=9, color="#c4442a",
                     arrowprops=dict(arrowstyle="->", color="#c4442a", lw=1.0))
    axes[2].annotate("一正一负,中间穿过 0\n那个零点正好是边的正中",
                     xy=(20, 0), xytext=(22.5, 22), fontsize=9, color="#c4442a",
                     arrowprops=dict(arrowstyle="->", color="#c4442a", lw=1.0))
    # 索引 6:原始还是 20(看着是平的),一阶却已经是 13 —— 中心差分要看两边,
    # x[7]=46 已经在坡上了。自学时正是在这一格觉得「两行没对齐」,必须标出来。
    for ax in axes:
        ax.axvline(6, color="#6b4fa8", ls="--", lw=1.3, zorder=2)
    axes[0].annotate("算这一格时不看它自己,\n只看左右两边:20 和 46",
                     xy=(6, 20), xytext=(13.6, 52), fontsize=9, color="#6b4fa8",
                     arrowprops=dict(arrowstyle="->", color="#6b4fa8", lw=1.0))
    axes[1].annotate("于是一阶 = (46−20)/2 = 13\n= 坡度 26 的一半\n(窗口只有一半踩在坡上)",
                     xy=(6, 13), xytext=(0.2, -48), fontsize=9, color="#6b4fa8",
                     arrowprops=dict(arrowstyle="->", color="#6b4fa8", lw=1.0))
    axes[2].set_xlabel("位置")

    fig.suptitle("一阶问「变化多快」,二阶问「变化在哪儿拐弯」", fontsize=13, y=0.955)
    four_questions(fig,
        "对同一段信号做两次减法:\n一阶 = 右邻减左邻,\n二阶 = 对一阶再做一次。\n"
        "三行共用一根 x 轴,\n各自一根 y 轴,不做缩放 ——\n图上的数就是表里的数。",
        "两个分工清楚的探针:\n一阶「整条坡都有反应」,\n适合算梯度、找边在哪;\n"
        "二阶「只在起点和终点响」,\n零点正好落在边的正中,\n定位更准。",
        "二阶对缓坡完全无感\n(坡中间是 0)。天空那种\n平缓渐变它一点不标 ——\n"
        "这既是优点也是代价:\n想增强缓变的层次,\n它帮不上忙。",
        "3 格宽的核会在真边界\n前后各多响一格(紫线处:\n信号还平着,一阶已 13)——\n"
        "**梯度图上的边总是胖的**。\n又都是裸差分没有平滑,\n噪声会被原样放大。",
        "求导前先平滑:一阶用 Sobel,\n二阶用高斯拉普拉斯(LoG);\n"
        "胖边要削回一格宽,\n查非极大值抑制(NMS);\n要既锐化又不放大噪声,\n改用 USM 并调小 k 和 σ。",
        y=0.02, bottom=0.235)
    fig.savefig(out_path, dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def save_overshoot_figure(out_path: Path) -> None:
    """过冲(halo)单独成图 —— 它属于第五节,不该混在第一节那张导数图里。

    上一版把它当作导数图的右半边,于是第一节的读者被迫先看一个
    还没讲到的东西(拉普拉斯锐化、USM 都在后面几节)。
    """
    step = step_image()
    row = 20
    fig, ax = plt.subplots(figsize=(9.6, 4.6))
    ax.axhspan(0, 255, color="#2c6fbb", alpha=0.06, zorder=0)
    ax.plot(step[row], color="black", lw=2.4, label="原图:只有 50 和 200", zorder=3)
    ax.plot(laplacian_sharpen(step)[row], color="#c4442a", lw=1.6,
            label="拉普拉斯锐化:冲到 −100 / 350", zorder=3)
    ax.plot(unsharp(step, 2.0, 1.0)[row], color="#2a8f4a", lw=1.6,
            label="USM k=1 σ=2:冲到 −10 / 260", zorder=3)
    for v in (0, 255):
        ax.axhline(v, color="#2c6fbb", ls="--", lw=1.0)
    ax.text(0.5, 264, "8 位能存的范围 0~255,冲出去的部分会被截掉,不可逆",
            fontsize=9, color="#2c6fbb")
    ax.set_xlabel("列号")
    ax.set_ylabel("灰度")
    ax.legend(fontsize=9, loc="lower right", frameon=False)
    ax.spines[["top", "right"]].set_visible(False)

    fig.suptitle("过冲(halo):锐化必然在边的两侧造出暗边和亮边", fontsize=13, y=0.99)
    four_questions(fig,
        "对一条「左 50 右 200」的\n硬边做锐化,\n把整行的值画出来。",
        "边变陡了 —— 这正是\n锐化想要的效果,\n人眼看上去更「清楚」。",
        "边的两侧各多出一条\n暗边和亮边。拉普拉斯\n冲到 −100 / 350,\n"
        "存成 8 位时被截成 0 / 255,\n**信息真的丢了,不可逆**。",
        "过冲是锐化的固有产物,\n不是参数没调好 ——\n只要让差别变大,\n"
        "边两侧就必然反向偏移。\n它也是「数码味」\n最典型的视觉特征。",
        "用 USM 并调小 k 和 σ\n(k=0.5 时过冲只剩 30);\n"
        "要完全避开光晕,\n改用保边的做法:\n双边滤波、引导滤波,\n或局部对比度增强。",
        y=0.02, bottom=0.30)
    fig.savefig(out_path, dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def save_compare_figure(out_path: Path, g: npt.NDArray[np.float64]) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(15.5, 9.8))

    lap = cv2.filter2D(g, cv2.CV_64F, LAP4)
    detail = g - cv2.GaussianBlur(g, (0, 0), 2.0)

    axes[0, 0].imshow(to_u8(g), cmap="gray", vmin=0, vmax=255)
    axes[0, 0].set_title("原图", fontsize=10)
    axes[0, 1].imshow(np.clip(lap + 128, 0, 255).astype(np.uint8), cmap="gray", vmin=0, vmax=255)
    axes[0, 1].set_title("拉普拉斯的响应(0 移到中灰)\n平坦处是灰的,只有边缘一正一负", fontsize=10)
    axes[0, 2].imshow(np.clip(detail + 128, 0, 255).astype(np.uint8), cmap="gray", vmin=0, vmax=255)
    axes[0, 2].set_title("USM 的「细节层」= 原图 − 模糊\n模糊时被抹掉的东西,都在这儿", fontsize=10)

    axes[1, 0].imshow(to_u8(laplacian_sharpen(g)), cmap="gray", vmin=0, vmax=255)
    axes[1, 0].set_title("拉普拉斯锐化(没有旋钮)\n噪声放大 5.4 倍,过冲最重", fontsize=10)
    axes[1, 1].imshow(to_u8(unsharp(g, 2.0, 1.0)), cmap="gray", vmin=0, vmax=255)
    axes[1, 1].set_title("USM k=1 σ=2(标准)\n噪声只放大 1.9 倍", fontsize=10)
    axes[1, 2].imshow(to_u8(unsharp(g, 2.0, 3.0)), cmap="gray", vmin=0, vmax=255)
    axes[1, 2].set_title("USM k=3 σ=2(过头了)\n边上的白边黑边就是光晕", fontsize=10)
    for ax in axes.flat:
        ax.axis("off")

    fig.suptitle("锐化 = 原图 + 一份「细节」。区别只在那份细节怎么算、加多少", fontsize=13)
    # 每格标题两行,不留行距会压住上一行
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94), h_pad=3.0)
    fig.savefig(out_path, dpi=110)


def save_gradient_figure(out_path: Path, g: npt.NDArray[np.float64]) -> None:
    gx = cv2.Sobel(g, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.hypot(gx, gy)

    fig, axes = plt.subplots(1, 4, figsize=(17.5, 5.0))
    for ax, (pic, title) in zip(axes[:3], (
            (np.clip(gx + 128, 0, 255), "gx:横着找变化\n竖直的边最亮(左右两侧一黑一白)"),
            (np.clip(gy + 128, 0, 255), "gy:竖着找变化\n水平的边最亮"),
            (np.clip(mag, 0, 255), "幅值 √(gx²+gy²)\n不分方向,只说「这儿变化有多大」"))):
        ax.imshow(pic.astype(np.uint8), cmap="gray", vmin=0, vmax=255)
        ax.set_title(title, fontsize=9)
        ax.axis("off")

    disk = smooth_disk()
    n = disk.shape[0]
    ax = axes[3]
    ang = np.linspace(0, 90, 181)
    for name, ks, color in (("Sobel  [1,2,1]", 3, "tab:blue"),
                            ("Scharr [3,10,3]", cv2.FILTER_SCHARR, "tab:orange")):
        err = angle_error_deg(disk, ks)
        vals = [err[int(round(n // 2 - 40 * np.sin(np.radians(a)))),
                    int(round(n // 2 + 40 * np.cos(np.radians(a))))] for a in ang]
        ax.plot(ang, vals, color=color, lw=1.6, label=name)
    ax.set_xlabel("边缘的朝向(度)")
    ax.set_ylabel("算出来的方向差几度")
    ax.set_title("方向准不准:拿平滑圆盘测(真值沿半径)\n"
                 "0°/45°/90° 处最准,中间最差;Scharr 全程更低", fontsize=9)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    fig.suptitle("一阶导数:Sobel 分横竖两次求导,再合成幅值", fontsize=13)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.90), h_pad=2.0)
    fig.savefig(out_path, dpi=110)


def demo_center_weight_zero() -> None:
    """求导核中间那格为什么是 0 —— 不是谁定的,是被两条要求逼出来的。

    自学时问到这儿:「为什么和 6 自己的位置无关」。答案是坡度本来就是
    两点之间的事,一个点没有坡度;而下面两条要求一联立,中间那格只能是 0。
    """
    x = np.concatenate([np.full(6, 20.0), np.linspace(20, 200, 8), np.full(6, 200.0)])

    def apply(k, sig):
        a, c, b = k
        return np.array([a * sig[i-1] + c * sig[i] + b * sig[i+1]
                         for i in range(1, len(sig) - 1)])

    print("\n【核中间为什么是 0】设核 = [a, c, b],c 是「自己那一格」的权重")
    print("  要求① 整条路抬高 100,坡度不能变 —— 淘汰「和不为 0」的核")
    for name, k in (("[-1, 0, 1]/2", (-0.5, 0, 0.5)), ("[-1, 0.5, 1]", (-1, 0.5, 1)),
                    ("[-1, 1, 1]", (-1, 1, 1))):
        d = np.abs(apply(k, x) - apply(k, x + 100)).max()
        print(f"     {name:14} 和={sum(k):>4.1f}   抬高前后最大差 {d:>6.1f}"
              + ("   不变" if d < 1e-9 else "   变了 ✗"))

    print("  要求② 左右翻转,坡度应原样翻转再变号 —— 淘汰「和为 0 但不对称」的核")
    for name, k in (("[-1, 0, 1]/2", (-0.5, 0, 0.5)), ("[-1, 1, 0]", (-1, 1, 0)),
                    ("[-1.5, 1, 0.5]", (-1.5, 1, 0.5))):
        f = apply(k, x)
        r = apply(k, x[::-1])[::-1]
        d = np.abs(f + r).max()
        print(f"     {name:14} 和={sum(k):>4.1f}   与 −(翻转版) 最大差 {d:>6.1f}"
              + ("   不偏" if d < 1e-9 else "   偏了 ✗"))

    print("  两条联立: ① a+c+b=0  ② a=−b  →  c = −(a+b) = −(−b+b) = 0")
    print("  只剩 0 这一个选择:给正数则平地也有输出,保持和为 0 但左右不等则位置偏半格。")


def demo_half_pixel_shift() -> None:
    """为什么求导核是 [-1,0,1] 而不是照抄定义的 [-1,1]。

    照抄导数定义会得到「右邻减自己」,但它估计的是 x+0.5 处的导数,
    不是 x 处的 —— 核里没有中心格,结果就没处落脚。
    拿 f(x)=x²(真导数 2x,已知)一量就露馅。
    """
    print("\n【中心差分】为什么是「右减左」而不是「右减自己」")
    x = np.arange(0, 12, dtype=float)
    f = x ** 2
    fwd = f[1:] - f[:-1]                  # [-1, 1]      右邻减自己
    ctr = (f[2:] - f[:-2]) / 2            # [-1, 0, 1]/2 右邻减左邻
    print("    x              :", x[1:6])
    print("    真导数 2x      :", (2 * x)[1:6])
    print("    [-1,1]  右减自己:", fwd[1:6], " ← 偏了半格")
    print("    2(x+0.5) 验证   :", (2 * (x + 0.5))[1:6], " ← 和上一行一模一样")
    print("    [-1,0,1] 右减左 :", ctr[0:5], " ← 与真导数分毫不差")
    print("  半格偏移在找边缘时不致命(边还在,只是整体挪半格),")
    print("  但做图像配准、光流、亚像素定位时会变成系统误差。")


def main() -> None:
    g = load_gray("camera.png").astype(np.float64)
    print(f"主图 camera.png  shape={g.shape}")

    demo_derivatives_1d()
    demo_center_weight_zero()
    demo_half_pixel_shift()
    demo_laplacian()
    demo_usm(g)
    demo_usm_equals_laplacian(g)
    demo_overshoot()
    demo_noise(g)
    demo_gradient(g)

    out = REPO / "Assets" / "results" / "sharpening-derivatives.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    save_derivative_figure(out)
    print(f"\n结果已保存: {out.relative_to(REPO)}")
    over = out.with_name("sharpening-overshoot.png")
    save_overshoot_figure(over)
    print(f"结果已保存: {over.relative_to(REPO)}")
    cmp_path = out.with_name("sharpening-compare.png")
    save_compare_figure(cmp_path, g)
    print(f"结果已保存: {cmp_path.relative_to(REPO)}")
    grad = out.with_name("gradient-compare.png")
    save_gradient_figure(grad, g)
    print(f"结果已保存: {grad.relative_to(REPO)}")

    if "--show" in sys.argv:
        plt.show()


if __name__ == "__main__":
    main()
