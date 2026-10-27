/*
 * 表 6-1：用输入端算法计算卷积（BASIC 原程序的 C 版本）
 *
 * 原书第 160 行用「虚构的子程序」载入信号。这里按图 6-3a 的设定生成：
 *   输入 x：81 点，三个周期的正弦波（高频）加一个缓慢上升的斜坡（低频），两端各有一段 0
 *   冲激响应 h：31 点平滑拱形（半个正弦周期，归一化到总和为 1），即低通滤波器
 * 卷积后正弦基本被滤掉、只剩斜坡，打印出来可以和图 6-3a 的输出对照。
 *
 * 和 table6-2_convolve_output_side.c 用的是同一组信号，两个程序的输出应逐点相同。
 *
 * 编译运行：cc -O2 -o table6-1_convolve_input_side table6-1_convolve_input_side.c -lm && ./table6-1_convolve_input_side
 */
#include <math.h>
#include <stdio.h>

#define NX 81                               /* 120 DIM X[80]：输入信号 81 点 */
#define NH 31                               /* 130 DIM H[30]：冲激响应 31 点 */
#define NY (NX + NH - 1)                    /* 140 DIM Y[110]：输出信号 111 点 */

static const double PI = 3.14159265358979323846;

/* 代替 160 GOSUB XXXX：载入 X[ ] 和 H[ ] */
static void load_signals(double *x, double *h)
{
    for (int n = 0; n < NX; n++) {          /* 第 8～72 点：斜坡从 0 升到 2.2，叠加 3 个周期、幅度 1.4 的正弦；两端为 0 */
        x[n] = 0.0;
        if (n < 8 || n > 72) continue;
        double t = (n - 8) / 64.0;
        x[n] = 2.2 * t - 1.4 * sin(2.0 * PI * 3.0 * t);
    }

    double sum = 0.0;
    for (int j = 0; j < NH; j++) {          /* 半个正弦周期的平滑拱形：两端为 0、中间最高 */
        h[j] = sin(PI * j / (NH - 1));
        sum += h[j];
    }
    for (int j = 0; j < NH; j++) h[j] /= sum;   /* 总和为 1：平坦部分（直流）的幅度不变，峰值约 0.05 */
}

/* 输入端算法：输入的每个点，都往输出里加一份缩放、平移后的冲激响应 */
static void convolve_input_side(const double *x, const double *h, double *y)
{
    for (int i = 0; i < NY; i++)            /* 180～200：输出数组清零，后面当累加器用 */
        y[i] = 0.0;

    for (int i = 0; i < NX; i++)            /* 220：遍历输入的每个点 */
        for (int j = 0; j < NH; j++)        /* 230：遍历冲激响应的每个点 */
            y[i + j] += x[i] * h[j];        /* 240：缩放（乘 x[i]）、平移（下标 +i）、累加 */
}

int main(void)
{
    double x[NX], h[NH], y[NY];
    load_signals(x, h);
    convolve_input_side(x, h, y);

    /* 代替 280 GOSUB XXXX：把输出存成「序号 值」两列，可直接拿去画图 */
    for (int i = 0; i < NY; i++)
        printf("%3d %.9f\n", i, y[i]);
    return 0;
}
