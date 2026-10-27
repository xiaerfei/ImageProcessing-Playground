/*
 * 表 7-1：一阶差分与累加和（BASIC 原程序的 C 版本）
 *
 * 原书左右两段程序分别算一阶差分（公式 7-4）和累加和（公式 7-5）。
 * 原书一阶差分第 120 行印成了 Y[I%] = X[I%] - Y[I%-1]，按公式 7-4 应为
 * X[I%] - X[I%-1]，这里按公式实现。原书行号 110、120 各重复了一次，也是排版错误。
 *
 * 信号按图 7-3a 的形状生成：0 → 斜率 0.03 → 斜率 0.07 → 平台 1.0 → 斜率 -0.18
 * → 指数回到 0。程序先求一阶差分（应得到图 7-3b 那样的分段常数），
 * 再对差分求累加和，检查能否还原出原信号——两者互为逆运算。
 *
 * 编译运行：cc -O2 -o table7-1_difference_running_sum table7-1_difference_running_sum.c -lm && ./table7-1_difference_running_sum
 */
#include <math.h>
#include <stdio.h>

#define N 81                                /* 图 7-3 的横轴：第 0～80 点 */

/* 按图 7-3a 生成原信号 */
static void load_signal(double *x)
{
    for (int n = 0; n < N; n++) {
        if (n <= 10)      x[n] = 0.0;                           /* 0～10：平坦的 0 */
        else if (n <= 20) x[n] = 0.03 * (n - 10);               /* 10～20：斜率 0.03，升到 0.3 */
        else if (n <= 30) x[n] = 0.3 + 0.07 * (n - 20);         /* 20～30：斜率 0.07，升到 1.0 */
        else if (n <= 40) x[n] = 1.0;                           /* 30～40：平台 */
        else if (n <= 50) x[n] = 1.0 - 0.18 * (n - 40);         /* 40～50：斜率 -0.18，降到 -0.8 */
        else              x[n] = -0.8 * exp(-(n - 50) / 5.0);   /* 50 以后：指数回到 0 */
    }
}

/* 左段程序：一阶差分，y[n] = x[n] - x[n-1]（公式 7-4） */
static void first_difference(const double *x, double *y)
{
    y[0] = 0.0;                             /* 110：第 0 点左边没有点，差分定为 0 */
    for (int i = 1; i < N; i++)             /* 110（原书重号）：FOR I% = 1 TO N%-1 */
        y[i] = x[i] - x[i - 1];             /* 120：按公式 7-4，原书误印为 X[I%] - Y[I%-1] */
}

/* 右段程序：累加和，y[n] = x[n] + y[n-1]（公式 7-5） */
static void running_sum(const double *x, double *y)
{
    y[0] = x[0];                            /* 110：第 0 点的累加和就是它自己 */
    for (int i = 1; i < N; i++)             /* 120：FOR I% = 1 TO N%-1 */
        y[i] = y[i - 1] + x[i];             /* 120（原书重号）：前一点的累加和再加上当前点 */
}

int main(void)
{
    double x[N], d[N], r[N];
    load_signal(x);
    first_difference(x, d);                 /* 图 7-3 向下的箭头：原信号 → 一阶差分 */
    running_sum(d, r);                      /* 图 7-3 向上的箭头：一阶差分 → 累加和，应回到原信号 */

    double max_err = 0.0;
    printf("  n   原信号 x     一阶差分     差分的累加和\n");
    for (int n = 0; n < N; n++) {
        double e = fabs(r[n] - x[n]);
        if (e > max_err) max_err = e;
        if (n % 5 == 0 || n == 41 || n == 51)
            printf("%3d  %10.6f  %10.6f  %10.6f\n", n, x[n], d[n], r[n]);
    }
    printf("累加和与原信号的最大偏差：%.3g\n", max_err);
    return 0;
}
