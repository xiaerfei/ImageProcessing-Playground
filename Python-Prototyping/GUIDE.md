# Python 图像处理操作手册

写给「算法想得明白,但 Python 的样板代码不熟」的情况。
所有代码片段都可直接粘进脚本运行,里面的数字都是在本仓库实测出来的。

---

## 一、先建立一个心智模型:图像就是数组

这是**唯一需要真正记住的事**,后面所有操作都是它的推论。

```python
import cv2
img = cv2.imread("../Assets/test-images/coffee.png")
print(img.shape, img.dtype, img.nbytes)
# (400, 600, 3) uint8 720000
```

三个数分别是**高、宽、通道**。注意高在前 —— 这和「600×400 的图」的日常说法是反的,
但和内存里的实际排列一致:一行一行往下存,每行 600 个像素,每像素 3 个字节。

如果你写过这个项目里的 ObjC 版,下面这张对照表能直接接上:

| ObjC (`IAImageBuffer`) | Python (numpy) |
| :--- | :--- |
| `buffer.height` | `img.shape[0]` |
| `buffer.width` | `img.shape[1]` |
| `buffer.data[(y * w + x) * 4 + c]` | `img[y, x, c]` |
| `bytesPerRow = width * 4` | `img.strides[0]` |
| 手写 `for` 双重循环 | 几乎从不写(见第四节) |

**区别只有两处**:numpy 是 3 通道 BGR(不是 4 通道 RGBA),
以及索引顺序是 `[行, 列]` 而不是 `(x, y)`。

---

## 二、读、写、显示

```python
import cv2

bgr  = cv2.imread(path)                              # 3 通道,BGR 顺序
gray = cv2.imread(path, cv2.IMREAD_GRAYSCALE)        # 2 维,没有通道轴
rgba = cv2.imread(path, cv2.IMREAD_UNCHANGED)        # 保留 alpha

assert bgr is not None, f"读图失败:{path}"           # imread 失败不抛异常,只返回 None

cv2.imwrite("out.png", bgr)                          # 按扩展名决定格式
```

> **第一个坑:OpenCV 是 BGR。**
> `cv2.imread` / `imwrite` / `imshow` 三者内部一致,所以只用 OpenCV 时察觉不到。
> 一旦把数组交给 matplotlib 显示,红蓝就会对调。
> 转换:`cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)`,或者偷懒写 `bgr[:, :, ::-1]`(倒着取通道)。

显示有两条路:

```python
# 路线 A:OpenCV 窗口 —— 快,适合只看图
cv2.imshow("title", bgr)
cv2.waitKey(0)          # 0 = 一直等按键;30 = 等 30ms 后继续(做动画用)
cv2.destroyAllWindows()

# 路线 B:matplotlib —— 能同时画图表、能加滑块,本项目默认用它
import matplotlib.pyplot as plt
plt.imshow(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))     # 别忘了转 RGB
plt.axis("off")
plt.show()
```

---

## 三、索引与切片

Python 相对 C 最大的便利就在这里 —— 整片区域可以一次性操作。

```python
img[y, x]              # 一个像素,返回 [B, G, R]
img[y, x, 0]           # 该像素的 B 通道
img[:, :, 0]           # 整张图的 B 通道(2 维数组)
img[100:200, 50:150]   # 一块 ROI:第 100~199 行、第 50~149 列
img[::2, ::2]          # 隔行隔列取 —— 这就是最简单的降采样
img[:, ::-1]           # 左右镜像
img[::-1, :]           # 上下翻转
```

整片赋值同样可以:

```python
img[100:200, 50:150] = 0          # 挖一个黑方块
img[:, :, 2] = 255                # 红通道拉满
mask = gray > 128                 # 布尔数组,和图同样大小
img[mask] = [0, 0, 255]           # 把亮的地方涂红
```

> **第二个坑:切片是 view,不是副本。**
> ```python
> roi = gray[0:10, 0:10]
> roi[0, 0] = 0
> print(gray[0, 0])    # 0 —— 原图也被改了
> ```
> 这和 ObjC 里拿到 `data` 指针再偏移是一回事:你操作的是同一块内存。
> 要独立的一份就显式 `.copy()`。反过来说,想原地改就别 copy,省内存。

---

## 四、别写 for 循环

这是从 C 转过来最需要改的习惯。同一个 gamma 变换,三种写法在 400×600 灰度图上实测:

| 写法 | 耗时 | 相对 |
| :--- | ---: | ---: |
| 双重 `for` 循环 | 165.76 ms | 1× |
| numpy 向量化 | 3.44 ms | **48×** |
| `cv2.LUT` | 0.31 ms | **532×** |

三者结果逐像素完全一致。

```python
gamma = 2.2

# ① 双重循环 —— 能跑,但慢到没法交互
for y in range(h):
    for x in range(w):
        out[y, x] = min(255, int(255.0 * (g[y, x] / 255.0) ** gamma))

# ② 向量化 —— 把整个数组当一个数来算,循环在 C 层面跑
out = np.clip(255.0 * (g / 255.0) ** gamma, 0, 255).astype(np.uint8)

# ③ LUT —— 点运算的输出只取决于当前像素值,那就只有 256 种可能,
#    算 256 次而不是 24 万次,剩下的只是查表
lut = np.clip(255.0 * (np.arange(256) / 255.0) ** gamma, 0, 255).astype(np.uint8)
out = cv2.LUT(g, lut)
```

**判断标准**:只要输出只取决于当前像素(点运算),就用 LUT;
要看邻居(卷积、滤波)就用 OpenCV 现成函数或 `cv2.filter2D`。
只有在「想亲手写一遍看清每一步」时才用循环 —— 那时慢一点无所谓。

---

## 五、dtype 与溢出

**第三个坑,也是最容易静默出错的一个。**

```python
a = np.full((2,2), 200, np.uint8)
b = np.full((2,2), 100, np.uint8)

a + b                  # 44   ← 300 超出 uint8,回绕成 300-256
cv2.add(a, b)          # 255  ← 饱和,该有的行为

c, d = np.full((2,2),50,np.uint8), np.full((2,2),80,np.uint8)
c - d                  # 226  ← -30 回绕成 -30+256
cv2.subtract(c, d)     # 0    ← 饱和
```

亮度加 100 结果图上出现一片黑斑,十有八九就是这个。

**本项目的统一约定**(README 里也写了):

```python
f = img.astype(np.float64)          # 1. 进浮点
f = f * 1.2 + 30                    # 2. 随便算,不用担心溢出
out = np.clip(f, 0, 255).astype(np.uint8)   # 3. 出口截断 + 转回
```

`np.clip` 那一步就是 ObjC 里的 `clamp8()`。别省。

---

## 六、常用函数速查

按用途分组,只列真会用到的。

**色彩空间**
```python
cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)    # 用的就是 Rec.601 那套 0.299/0.587/0.114
cv2.cvtColor(img, cv2.COLOR_BGR2RGB)     # 给 matplotlib 看
cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)   # 注意是 YCrCb,Cr 在前
cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
cv2.split(img) / cv2.merge([b,g,r])      # 拆/合通道
```

**几何**
```python
cv2.resize(img, (w, h), interpolation=cv2.INTER_NEAREST)   # 最近邻,看锯齿
cv2.resize(img, (w, h), interpolation=cv2.INTER_LINEAR)    # 双线性,默认
cv2.resize(img, None, fx=0.5, fy=0.5)                      # 按比例
cv2.warpAffine(img, M, (w, h))            # M 是 2×3 矩阵
cv2.flip(img, 0/1/-1)                     # 上下/左右/both
np.rot90(img) / img.T                     # 旋转 90°/转置
```

**灰度与直方图**
```python
cv2.LUT(img, lut)                         # 查表,lut 是 256 项 uint8
cv2.equalizeHist(gray)                    # 全局均衡化(只吃单通道)
cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(gray)
np.bincount(gray.ravel(), minlength=256)  # 手写直方图,比 cv2.calcHist 好用
cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)
```

**滤波(第 6 周开始用)**
```python
cv2.GaussianBlur(img, (0,0), sigmaX=2.0)  # ksize 给 (0,0) 让它按 σ 自己算
cv2.blur(img, (5,5))                      # 均值
cv2.medianBlur(img, 5)                    # 中值,专治椒盐噪声
cv2.filter2D(img, -1, kernel)             # 自定义核,-1 = 输出类型同输入
cv2.Sobel / cv2.Laplacian / cv2.Canny
```
> 滤波都有 `borderType` 参数(边界怎么补)。和自己手写的实现对比时**必须统一**,
> 否则边缘几个像素对不上,会以为是算法写错了。默认是 `BORDER_REFLECT_101`。

**统计**
```python
img.mean(), img.std(), img.min(), img.max()
img.mean(axis=(0,1))                      # 每个通道各自的均值
np.percentile(gray, [1, 99])              # 百分位,做自动色阶用
np.count_nonzero(gray > 200)              # 有多少个亮像素
```

---

## 七、UI:滑块模板

拿去改,把 `apply()` 换成你自己的算法即可。完整的例子见
`Ch03_Spatial_Filtering/09_interactive_intensity.py`。

```python
import cv2, numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, RadioButtons, Button

img = cv2.imread("../Assets/test-images/coffee.png")
rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

fig, ax = plt.subplots(figsize=(8, 6))
plt.subplots_adjust(bottom=0.25)      # 给底部的滑块腾地方,不然会盖住图
im = ax.imshow(rgb)
ax.axis("off")

# add_axes([左, 下, 宽, 高]),四个数都是占整个窗口的比例
s_gamma = Slider(fig.add_axes([0.25, 0.10, 0.55, 0.03]), "γ", 0.1, 3.0, valinit=1.0)

def apply(_=None):
    g = s_gamma.val
    lut = np.clip(255.0 * (np.arange(256)/255.0) ** g, 0, 255).astype(np.uint8)
    out = cv2.LUT(img, lut)
    im.set_data(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))   # set_data 而不是重新 imshow
    fig.canvas.draw_idle()                              # 攒着一起重画,拖动才跟手

s_gamma.on_changed(apply)
apply()
plt.show()
```

要点只有三条:
1. `subplots_adjust(bottom=...)` 先把地方腾出来
2. 更新画面用 `set_data`,**不要**重新 `imshow`(那会越堆越多、越来越卡)
3. 回调末尾 `draw_idle()`

**另一个选择 `cv2.createTrackbar`** 代码更短,但滑块只支持整数
(小数得靠 `"gamma x100"` 这种土办法绕),而且画不了图表:

```python
cv2.namedWindow("demo")
cv2.createTrackbar("gamma x100", "demo", 100, 300, lambda v: None)
while True:
    g = max(cv2.getTrackbarPos("gamma x100", "demo"), 1) / 100.0
    ...
    cv2.imshow("demo", out)
    if cv2.waitKey(30) == 27: break     # Esc 退出
```

---

## 八、图表模板

**多图并排**

```python
fig, axes = plt.subplots(1, 3, figsize=(13, 4))
for ax, (title, im) in zip(axes, [("原图", a), ("处理后", b), ("差值", c)]):
    ax.imshow(im, cmap="gray", vmin=0, vmax=255)   # 灰度图这两个参数必须给
    ax.set_title(title, fontsize=10)
    ax.axis("off")
fig.tight_layout()
```

> `vmin/vmax` 不给的话,matplotlib 会按当前图的最小最大值自动拉伸,
> 于是「一张全黑的图」也会被显示成有明暗层次的 —— 看着像算法生效了,其实没有。
> **对比两张图时尤其要给死**,否则两张图的映射尺度不同,根本没法比。

**直方图**

```python
h = np.bincount(gray.ravel(), minlength=256) / gray.size    # 归一化成 PDF
ax.fill_between(np.arange(256), h, color="0.6")
ax.set_xlim(0, 255)

cdf = np.cumsum(h)                                           # CDF 就是前缀和
ax2 = ax.twinx()                                             # 共享横轴的第二套纵轴
ax2.plot(cdf, color="tab:blue")
```

**曲线 / 映射表**

```python
ax.plot([0,255], [0,255], color="0.78", lw=3.0)   # 参考对角线画粗
ax.plot(lut, color="tab:orange", lw=1.4)          # 实际曲线画细
ax.set_xlim(0,255); ax.set_ylim(0,255)
ax.set_aspect("equal")                            # 正方形,斜率才不会被拉变形
```
> 参考线画粗、数据线画细:两者重合时(比如 γ=1)才分得出是「压在一起」
> 还是「参考线根本没画出来」。

**中文标签**(macOS)

不设的话,标题里的中文会显示成方框,同时终端刷一串:

```
UserWarning: Glyph 21407 (\N{CJK UNIFIED IDEOGRAPH-539F}) missing from font(s) DejaVu Sans.
```

matplotlib 默认字体 DejaVu Sans 不含汉字。加这两行:

```python
import matplotlib
matplotlib.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti SC", "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False    # 否则负号也显示成方框
```

**无窗口环境保存图片**

```python
import matplotlib
matplotlib.use("Agg")          # 必须在 import pyplot 之前
import matplotlib.pyplot as plt
...
fig.savefig("out.png", dpi=110)
```

---

## 九、调试

把这个函数贴进脚本,遇事先打一下:

```python
def info(name, a):
    print(f"{name:12s} shape={a.shape} dtype={a.dtype} "
          f"范围=[{a.min()}, {a.max()}] 均值={a.mean():.1f}")
```

八成的问题在打完这一行之后就明白了:

| 症状 | 十有八九是 |
| :--- | :--- |
| 图全黑 / 全白 | dtype 成了 float 而值域还是 0~255(matplotlib 期望 float 是 0~1) |
| 红蓝颠倒 | 忘了 BGR→RGB |
| 出现莫名的黑白斑点 | uint8 回绕(第五节) |
| 结果图有明暗但原图应该全黑 | `imshow` 没给 `vmin/vmax`(第八节) |
| `NoneType has no attribute` | `imread` 路径错了,它失败时返回 None 不报错 |
| 改了 A,B 也跟着变 | 切片是 view,该 `.copy()` |
| 滑块拖着卡 | 回调里重新 `imshow` 了,应该用 `set_data` |
| 中文标题变方框 + 满屏 `Glyph ... missing` | 没设 `font.sans-serif`(第八节) |

---

## 十、跑脚本

```bash
cd Python-Prototyping
.venv/bin/python Ch03_Spatial_Filtering/09_interactive_intensity.py
```

不用每次 `source activate` —— 直接用 `.venv/bin/python` 这个路径就行。

新脚本建议照抄现有的开头:文档字符串写清楚「验证什么 + 怎么用」,
`REPO = Path(__file__).resolve().parents[2]` 定位仓库根,
`--save` 走 Agg 后端出静态图、不带参数则开交互窗口。
