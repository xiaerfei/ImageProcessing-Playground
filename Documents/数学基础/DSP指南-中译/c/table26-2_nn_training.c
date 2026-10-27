/*
 * 表 26-2、26-3：神经网络训练（求权重）的 C 版本
 *
 * 网络结构同原书：101 个输入节点（100 个像素 + 1 个偏置节点）→ 10 个隐藏节点 → 1 个输出节点。
 * 任务：判断 10×10 图像里的字母是不是元音（A、E、I、O、U）。训练算法是最速下降法，
 * 每看一张图就按公式 26-3～26-5 更新一次全部 1020 个权重。
 *
 * 原书的数据库是扫描得到的 1300 张字母图（50 套 × 26 个大写字母），没有随书提供。
 * 这里用合成数据代替：为 26 个"字母"各随机生成一个 10×10 的黑白原型（墨迹约 40、纸面约 210），
 * 每张样本在原型上随机平移 0～1 个像素、再加标准差 25 的高斯噪声，像素值限制在 0～255。
 * 排列方式和原书一致：第 n 张图是第 n%26 个字母，前 260 张（每个字母 10 张）用于训练，
 * 后 1040 张用于测试。合成的"字母"不是真字母，所以这里只验证算法本身是否在学：
 * ESUM 是否随迭代下降、训练集和测试集上的分类效果如何。
 *
 * 用法：./table26-2_nn_training [迭代次数，默认 800] [随机种子，默认 1]
 * 编译运行：cc -O2 -o table26-2_nn_training table26-2_nn_training.c -lm && ./table26-2_nn_training
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define NPIX   100                          /* 每张图 10×10 像素 */
#define NIN    (NPIX + 1)                   /* 140 DIM X1[101]：100 个像素 + 偏置节点 */
#define NHID   10                           /* 150 DIM X2[10]：隐藏层 10 个节点 */
#define NIMG   1300                         /* 数据库共 1300 张图 */
#define NTRAIN 260                          /* 前 260 张用于训练 */

static const double MU = 0.000005;          /* 130：迭代步长 */

static double db[NIMG][NPIX];               /* 合成的图像数据库 */
static double x1[NIN], x2[NHID], x3;        /* 各层的值；x1[100] 是偏置节点，恒为 1 */
static double wh[NHID][NIN], wo[NHID];      /* 160、170：隐藏层权重、输出层权重 */
static double correct, elet;                /* 期望输出；本张图的误差 */

/* 可复现的均匀随机数，0～1 */
static unsigned long long rng_state = 1;
static double rnd(void)
{
    rng_state = rng_state * 6364136223846793005ULL + 1442695040888963407ULL;
    return (rng_state >> 11) * (1.0 / 9007199254740992.0);
}
static double gauss(void)                   /* Box-Muller 生成标准正态随机数 */
{
    double u1 = rnd(), u2 = rnd();
    if (u1 < 1e-300) u1 = 1e-300;
    return sqrt(-2.0 * log(u1)) * cos(2.0 * 3.14159265358979323846 * u2);
}

static int is_vowel(int letter) { return letter == 0 || letter == 4 || letter == 8 || letter == 14 || letter == 20; }

/* 生成合成数据库：26 个原型，每张样本 = 原型平移 + 噪声 */
static void build_database(void)
{
    static double proto[26][NPIX];
    for (int l = 0; l < 26; l++)
        for (int p = 0; p < NPIX; p++)
            proto[l][p] = (rnd() < 0.35) ? 40.0 : 210.0;
    for (int n = 0; n < NIMG; n++) {
        int l = n % 26;
        int dx = (int)(rnd() * 3) - 1, dy = (int)(rnd() * 3) - 1;   /* 平移 -1、0、+1 像素 */
        for (int r = 0; r < 10; r++)
            for (int c = 0; c < 10; c++) {
                int sr = r - dy, sc = c - dx;
                double v = (sr >= 0 && sr < 10 && sc >= 0 && sc < 10) ? proto[l][sr * 10 + sc] : 210.0;
                v += 25.0 * gauss();
                db[n][r * 10 + c] = v < 0 ? 0 : (v > 255 ? 255 : v);
            }
    }
}

/* 子程序 1000：把第 letter 张图载入 x1[]，偏置节点为 1，并给出期望输出 correct */
static void load_image(int letter)
{
    for (int p = 0; p < NPIX; p++) x1[p] = db[letter][p];
    x1[NPIX] = 1.0;                         /* 偏置节点恒为 1 */
    correct = is_vowel(letter % 26) ? 1.0 : 0.0;
}

/* 子程序 2000：用当前权重算出网络输出 x3，并求本张图的误差 elet */
static void calc_error(void)
{
    for (int h = 0; h < NHID; h++) {        /* 2050：遍历每个隐藏节点 */
        double acc = 0.0;                   /* 2060 */
        for (int i = 0; i < NIN; i++)       /* 2070～2090：把每个输入节点加权求和 */
            acc += x1[i] * wh[h][i];
        x2[h] = 1.0 / (1.0 + exp(-acc));    /* 2100：送进 sigmoid */
    }
    double acc = 0.0;                       /* 2140 */
    for (int h = 0; h < NHID; h++)          /* 2150～2170：把每个隐藏节点加权求和 */
        acc += x2[h] * wo[h];
    x3 = 1.0 / (1.0 + exp(-acc));           /* 2180 */
    elet = correct - x3;                    /* 2210：本张图的误差 */
    if (correct == 1.0) elet *= 5.0;        /* 2220：目标（元音）的误差加权 5 倍 */
}

/* 子程序 3000：按最速下降法更新全部权重（公式 26-3～26-5） */
static void new_weights(void)
{
    for (int h = 0; h < NHID; h++)          /* 3050～3120：隐藏层权重 */
        for (int i = 0; i < NIN; i++) {
            double slopeo = x3 * (1.0 - x3);            /* 3070：输出 sigmoid 的斜率（公式 26-2） */
            double slopeh = x2[h] * (1.0 - x2[h]);      /* 3080：隐藏 sigmoid 的斜率 */
            double dx3dw = x1[i] * slopeh * wo[h] * slopeo;   /* 3090：公式 26-4 */
            wh[h][i] += dx3dw * elet * MU;              /* 3100：公式 26-5 */
        }
    for (int h = 0; h < NHID; h++) {        /* 3150～3190：输出层权重 */
        double slopeo = x3 * (1.0 - x3);    /* 3160 */
        double dx3dw = x2[h] * slopeo;      /* 3170：公式 26-3 */
        wo[h] += dx3dw * elet * MU;         /* 3180：公式 26-5 */
    }
}

/* 用当前权重统计一段图像的分类结果（阈值 0.5） */
static void evaluate(int from, int to, const char *name)
{
    int tp = 0, nt = 0, fp = 0, nn = 0;
    for (int n = from; n < to; n++) {
        load_image(n);
        calc_error();
        if (correct == 1.0) { nt++; if (x3 > 0.5) tp++; }
        else                { nn++; if (x3 > 0.5) fp++; }
    }
    printf("%s：元音检出 %d/%d（%.1f%%），非元音误报 %d/%d（%.1f%%）\n",
           name, tp, nt, 100.0 * tp / nt, fp, nn, 100.0 * fp / nn);
}

int main(int argc, char **argv)
{
    int niter = argc > 1 ? atoi(argv[1]) : 800;
    rng_state = argc > 2 ? strtoull(argv[2], NULL, 10) : 1;
    build_database();

    for (int h = 0; h < NHID; h++) {        /* 190～240：权重设为随机初值 */
        wo[h] = rnd() - 0.5;                /* 200：输出层权重 -0.5～0.5 */
        for (int i = 0; i < NIN; i++)
            wh[h][i] = (rnd() - 0.5) / 1000.0;  /* 220：隐藏层权重 -0.0005～0.0005 */
    }

    evaluate(0, NTRAIN, "训练前·训练集");
    for (int iter = 1; iter <= niter; iter++) { /* 270：迭代循环 */
        double esum = 0.0;                  /* 290：误差累加器清零 */
        for (int letter = 0; letter < NTRAIN; letter++) {   /* 310：遍历训练集每张图 */
            load_image(letter);             /* 320：GOSUB 1000 */
            calc_error();                   /* 330：GOSUB 2000 */
            esum += elet * elet;            /* 340：累加本次迭代的误差 */
            new_weights();                  /* 350：GOSUB 3000 */
        }
        if (iter == 1 || iter == 10 || iter % 100 == 0)
            printf("迭代 %4d  ESUM = %.2f\n", iter, esum);  /* 380：打印进度 */
    }
    evaluate(0, NTRAIN, "训练后·训练集（前 260 张）");
    evaluate(NTRAIN, NIMG, "训练后·测试集（后 1040 张）");
    return 0;
}
