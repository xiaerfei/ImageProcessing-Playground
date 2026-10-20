# 交互实验

**直接用浏览器打开 `.html` 就能跑,不需要装任何东西、不需要起服务器、不联网也能用。**
(只有字体会去 Google Fonts 拿;拿不到会自动退回系统字体,不影响使用。)

```bash
open Interactive/高斯收敛实验.html          # macOS
open Interactive/USM分步演示.html
open Interactive/一二阶导数手感.html
open Interactive/频谱涂抹.html
```

| 文件 | 配合哪一篇 | 干什么 |
| :--- | :--- | :--- |
| [高斯收敛实验.html](高斯收敛实验.html) | [02-smoothing.md](../Documents/05-spatial-filtering/02-smoothing.md) 第二节 | 点一下做一遍邻域平均,看白点怎么自己长成钟形 |
| [USM分步演示.html](USM分步演示.html) | [03-sharpening.md](../Documents/05-spatial-filtering/03-sharpening.md) 第三节 | 一步一步走 USM 的四步,看细节图为什么有正有负、光晕从哪一档开始冒出来 |
| [一二阶导数手感.html](一二阶导数手感.html) | [03-sharpening.md](../Documents/05-spatial-filtering/03-sharpening.md) 第一节 | 自己拖一行像素的灰度,看一阶、二阶怎么跟着变;再涂一张图,看一阶是亮线、二阶是一红一蓝 |
| [频谱涂抹.html](频谱涂抹.html) | [快速路线 2.理解傅里叶变换](../Documents/数学基础/快速路线/2.理解傅里叶变换.md)、[5.从症状找原因](../Documents/数学基础/快速路线/5.从症状找原因.md) | 在频谱上涂掉或放回频率,实时看拼回的图:低通变糊、高通剩边缘、理想低通振铃、涂掉两个亮点去条纹;可上传自己的图 |

## 为什么单独放一个目录

这些页面**不进 PDF** —— PDF 生成只扫 `Documents/**/*.md`,
而交互这件事印在纸上等于没有。放在这儿是为了跟正文分开:
正文负责讲明白,这儿负责让你亲手拨一拨。

写新的时候沿用同一套约定:
配色跟 `Python-Prototyping/figkit.py` 里的图一致(蓝 `#2c6fbb`、红 `#c4442a`、
橙 `#d95f02`、绿 `#2a8f4a`),数值算法跟对应的 Python 脚本保持一致并在页脚注明是哪一个 ——
**两边对不上就是 bug。**
