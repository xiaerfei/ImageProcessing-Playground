/*
 * 表 15-1：用卷积实现移动平均滤波器（BASIC 原程序的 C 版本）
 *
 * 5000 点输入经 101 点对称移动平均，得到第 50～4949 点共 4900 个输出。
 * 原书第 170 行用「虚构的子程序」载入信号，这里按图 15-1a 的样子生成：
 * 第 2000～2999 点为幅度 1 的矩形脉冲，叠加标准差 0.5 的高斯白噪声。
 *
 * 验证两件事：
 *   1. 平坦区的噪声标准差应降为原来的 1/√101 ≈ 1/10（书中「降噪量等于点数的平方根」）；
 *   2. 脉冲边沿从 0 升到 1 正好用 101 点（阶跃响应是一条直线）。
 *
 * 编译运行：cc -O2 -o table15-1_moving_average table15-1_moving_average.c -lm && ./table15-1_moving_average
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define N    5000                           /* 140 DIM X[4999]：输入 5000 点 */
#define HALF 50                             /* 210：J% 从 -50 到 50，共 101 点 */
#define M    (2 * HALF + 1)

static const double PI = 3.14159265358979323846;

/* 标准正态随机数（Box-Muller），固定种子保证每次结果相同 */
static double gauss(void)
{
    double u1 = (rand() + 1.0) / (RAND_MAX + 2.0);
    double u2 = (rand() + 1.0) / (RAND_MAX + 2.0);
    return sqrt(-2.0 * log(u1)) * cos(2.0 * PI * u2);
}

/* 代替 170 GOSUB XXXX：载入 X[ ]；clean 为 1 时不加噪声，用来看阶跃响应 */
static void load_signal(float *x, int clean)
{
    srand(1);
    for (int i = 0; i < N; i++) {
        x[i] = (i >= 2000 && i < 3000) ? 1.0f : 0.0f;
        if (!clean) x[i] += (float)(0.5 * gauss());
    }
}

/* 190～250：每个输出点取输入中以它为中心的 101 点求平均 */
static void moving_average(const float *x, float *y)
{
    for (int i = 0; i < N; i++) y[i] = 0.0f; /* 两端 50 点没有完整窗口，不计算，置 0 */
    for (int i = HALF; i < N - HALF; i++) { /* 190：FOR I% = 50 TO 4949 */
        y[i] = 0.0f;                        /* 200：清零，当累加器用 */
        for (int j = -HALF; j <= HALF; j++) /* 210：FOR J% = -50 TO 50 */
            y[i] += x[i + j];               /* 220：原书印成 X(I%+J%]，括号不配对 */
        y[i] /= M;                          /* 240：除以 101 完成平均 */
    }
}

/* 求 a[from..to) 相对于 level 的标准差 */
static double noise_sd(const float *a, int from, int to, double level)
{
    double s = 0.0;
    for (int i = from; i < to; i++) s += (a[i] - level) * (a[i] - level);
    return sqrt(s / (to - from));
}

int main(void)
{
    static float x[N], y[N];

    load_signal(x, 0);
    moving_average(x, y);
    double sd_in  = noise_sd(x, 500, 1500, 0.0);   /* 远离脉冲边沿的平坦区 */
    double sd_out = noise_sd(y, 500, 1500, 0.0);
    printf("平坦区噪声标准差：输入 %.4f，输出 %.4f，降低 %.2f 倍（理论 √101 = %.2f）\n",
           sd_in, sd_out, sd_in / sd_out, sqrt((double)M));

    load_signal(x, 1);                      /* 不加噪声，看脉冲上升沿 */
    moving_average(x, y);
    int first = -1, last = -1;
    for (int i = HALF; i < N - HALF; i++) {
        if (first < 0 && y[i] > 1e-6f) first = i;
        if (last < 0 && y[i] > 1.0f - 1e-6f) last = i;
    }
    printf("无噪声时上升沿：第 %d 点开始离开 0，第 %d 点到达 1，共 %d 点\n",
           first, last, last - first + 1);
    printf("上升沿中点 y[2000] = %.4f（应为 51/101 = %.4f）\n", y[2000], 51.0 / 101.0);
    return 0;
}
