/*
 * 表 15-2：用递归实现移动平均滤波器（BASIC 原程序的 C 版本）
 *
 * 公式 15-3：y[i] = y[i-1] + x[i+p] - x[i-q]，p = (M-1)/2，q = p+1。
 * 先用普通求和算出第一个输出点，之后每点只需一次加法和一次减法。
 * 原书第 290 行写成 Y[I%] = ACC，漏了除以 101（第 250 行算 Y[50] 时是除了的），
 * 这里按 ACC/101 实现；第 250 行的 Y[[50] 多了一个括号，也是排版错误。
 *
 * 验证：
 *   1. 与表 15-1 的直接求和结果逐点比较；
 *   2. 书中说的「浮点累加漂移」：同样的递归，累加器用单精度 float 和双精度 double 各跑一遍，
 *      看末尾输出与直接求和差多少。为了让漂移明显，另做一个 1,000,000 点、带 100 直流偏置的
 *      长信号：偏置让累加器的值在 10100 左右，float 在这个量级的分辨率只有约 0.001，
 *      每次加减都丢掉一点尾数，误差随点数一路累积。
 *
 * 编译运行：cc -O2 -o table15-2_recursive_moving_average table15-2_recursive_moving_average.c -lm && ./table15-2_recursive_moving_average
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define HALF 50                             /* p = 50，q = 51 */
#define M    (2 * HALF + 1)                 /* 101 点 */

static const double PI = 3.14159265358979323846;

static double gauss(void)
{
    double u1 = (rand() + 1.0) / (RAND_MAX + 2.0);
    double u2 = (rand() + 1.0) / (RAND_MAX + 2.0);
    return sqrt(-2.0 * log(u1)) * cos(2.0 * PI * u2);
}

/* 代替 190 GOSUB XXXX：矩形脉冲加高斯白噪声，和表 15-1 的 C 版本相同 */
static void load_signal(float *x, int n, double offset)
{
    srand(1);
    for (int i = 0; i < n; i++)
        x[i] = (float)(offset + ((i >= 2000 && i < 3000) ? 1.0 : 0.0) + 0.5 * gauss());
}

/* 表 15-1 的直接求和，作为对照（累加用 double，当作「标准答案」） */
static void direct(const float *x, double *y, int n)
{
    for (int i = HALF; i < n - HALF; i++) {
        double s = 0.0;
        for (int j = -HALF; j <= HALF; j++) s += x[i + j];
        y[i] = s / M;
    }
}

/* 表 15-2：递归实现，累加器 ACC 用 double（第 170 行 DEFDBL ACC） */
static void recursive_double(const float *x, float *y, int n)
{
    double acc = 0.0;                       /* 210：ACC = 0 */
    for (int i = 0; i <= 2 * HALF; i++)     /* 220～240：先把 X[0]～X[100] 加起来 */
        acc += x[i];
    y[HALF] = (float)(acc / M);             /* 250：Y[50] = ACC/101 */
    for (int i = HALF + 1; i < n - HALF; i++) { /* 270：FOR I% = 51 TO 4949 */
        acc += x[i + HALF] - x[i - HALF - 1];   /* 280：加上新进窗口的点，减去刚出窗口的点 */
        y[i] = (float)(acc / M);            /* 290：原书漏了 /101，这里补上 */
    }
}

/* 同样的递归，但累加器用单精度 float，用来演示书中说的舍入漂移 */
static void recursive_float(const float *x, float *y, int n)
{
    float acc = 0.0f;
    for (int i = 0; i <= 2 * HALF; i++) acc += x[i];
    y[HALF] = acc / M;
    for (int i = HALF + 1; i < n - HALF; i++) {
        acc += x[i + HALF] - x[i - HALF - 1];
        y[i] = acc / M;
    }
}

/* 比较 y 与标准答案 ref 在 [HALF, n-HALF) 上的最大偏差，以及最后一个输出点的偏差 */
static void report(const char *name, const float *y, const double *ref, int n)
{
    double max_err = 0.0;
    for (int i = HALF; i < n - HALF; i++) {
        double e = fabs(y[i] - ref[i]);
        if (e > max_err) max_err = e;
    }
    printf("  %-22s 最大偏差 %.3g，最后一点偏差 %.3g\n",
           name, max_err, fabs(y[n - HALF - 1] - ref[n - HALF - 1]));
}

int main(void)
{
    int    sizes[]   = { 5000, 1000000 };   /* 5000 点是原书设定；100 万点用来放大漂移 */
    double offsets[] = { 0.0, 100.0 };      /* 长信号加 100 的直流偏置，让累加器数值变大 */
    for (int k = 0; k < 2; k++) {
        int n = sizes[k];
        float  *x  = malloc(n * sizeof *x);
        float  *yd = malloc(n * sizeof *yd);
        float  *yf = malloc(n * sizeof *yf);
        double *r  = malloc(n * sizeof *r);
        load_signal(x, n, offsets[k]);
        direct(x, r, n);
        recursive_double(x, yd, n);
        recursive_float(x, yf, n);
        printf("N = %d，直流偏置 %.0f，与直接求和比较：\n", n, offsets[k]);
        report("递归（double 累加器）", yd, r, n);
        report("递归（float 累加器）", yf, r, n);
        free(x); free(yd); free(yf); free(r);
    }
    return 0;
}
