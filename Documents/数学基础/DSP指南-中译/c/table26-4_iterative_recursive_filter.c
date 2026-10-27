/*
 * 表 26-4、26-5：用迭代法设计递归滤波器（C 版本）
 *
 * 思路和训练神经网络一样：从"恒等系统"（a0 = 1，其余系数为 0）出发，
 * 每次迭代用"把系数加一个小增量 DELTA、看误差变多少"的蛮力办法求出误差对每个系数的斜率，
 * 再让每个系数沿下坡方向走 MU × 斜率。误差 ER 是当前频率响应幅度与期望幅度 T[] 的均方根差。
 * 误差不降反升时，把 MU 减半（第 370 行）。
 *
 * 原书第 250 行用虚构子程序载入期望响应 T[]。这里按图 26-13a 的设定：截止频率约 0.31 的理想低通，
 * 8 个极点。子程序 1000 是表 12-4 的 FFT，这里附了一份自包含的实现。
 *
 * 用法：./table26-4_iterative_recursive_filter [迭代次数，默认 100（原书值）]
 * 编译运行：cc -O2 -o table26-4_iterative_recursive_filter table26-4_iterative_recursive_filter.c -lm && ./table26-4_iterative_recursive_filter
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define N  256                              /* 130：FFT 点数 */
#define NP 8                                /* 140：滤波器极点数 */

static const double DELTA = 0.00001;        /* 150：求斜率时的扰动增量 */
static const double PI = 3.14159265358979323846;
static double MU = 0.2;                     /* 160：迭代步长（会自动减半） */

static double rex[N], imx[N];               /* 170、180：FFT 用的实部、虚部 */
static double t[N / 2 + 1];                 /* 190：期望频率响应（只有幅度） */
static double a[NP + 1], b[NP + 1];         /* 200、210：递归系数 */
static double sa[NP + 1], sb[NP + 1];       /* 220、230：各系数的误差斜率 */
static double er, eold, enew;

/* 子程序 1000：表 12-4 的 FFT（位反转 + 蝶形运算），就地计算 rex[]、imx[] */
static void fft(void)
{
    int nm1 = N - 1, nd2 = N / 2, m = (int)(log(N) / log(2) + 0.5), j = nd2;
    for (int i = 1; i <= N - 2; i++) {      /* 位反转排序 */
        if (i < j) {
            double tr = rex[j], ti = imx[j];
            rex[j] = rex[i]; imx[j] = imx[i];
            rex[i] = tr;     imx[i] = ti;
        }
        int k = nd2;
        while (k <= j) { j -= k; k /= 2; }
        j += k;
    }
    for (int l = 1; l <= m; l++) {          /* 逐级做蝶形运算 */
        int le = 1 << l, le2 = le / 2;
        double ur = 1.0, ui = 0.0;
        double sr = cos(PI / le2), si = -sin(PI / le2);
        for (int jj = 1; jj <= le2; jj++) {
            for (int i = jj - 1; i <= nm1; i += le) {
                int ip = i + le2;
                double tr = rex[ip] * ur - imx[ip] * ui;
                double ti = rex[ip] * ui + imx[ip] * ur;
                rex[ip] = rex[i] - tr; imx[ip] = imx[i] - ti;
                rex[i] += tr;          imx[i] += ti;
            }
            double tr = ur;
            ur = tr * sr - ui * si;
            ui = tr * si + ui * sr;
        }
    }
}

/* 子程序 3000：求当前系数下的频域误差 er */
static void calc_error(void)
{
    for (int i = 0; i < N; i++) { rex[i] = 0.0; imx[i] = 0.0; }    /* 3040～3070 */
    imx[12] = 1.0;                          /* 3080：在 imx[12] 放一个冲激作为输入（平移 12 点，避免下标为负） */
    for (int i = 12; i < N; i++)            /* 3100～3140：用递归公式算冲激响应，输出放在 rex[] */
        for (int j = 0; j <= NP; j++)
            rex[i] += a[j] * imx[i - j] + b[j] * rex[i - j];
    imx[12] = 0.0;                          /* 3150：清掉输入，imx[] 交给 FFT 当虚部 */
    fft();                                  /* 3170：GOSUB 1000 */
    er = 0.0;                               /* 3200 */
    for (int i = 0; i <= N / 2; i++) {      /* 3210：遍历每个正频率 */
        double mag = sqrt(rex[i] * rex[i] + imx[i] * imx[i]);  /* 3220：直角坐标 → 幅度 */
        er += (mag - t[i]) * (mag - t[i]);  /* 3230：误差平方累加 */
    }
    er = sqrt(er / (N / 2 + 1));            /* 3250：均方根误差 */
}

/* 子程序 2000：求新的递归系数 */
static void new_coefficients(void)
{
    calc_error();                           /* 2040：当前误差 */
    eold = er;                              /* 2050 */
    for (int p = 0; p <= NP; p++) {         /* 2080～2130：每个 a 系数的斜率 */
        a[p] += DELTA;                      /* 2090：加一个小增量 */
        calc_error();                       /* 2100 */
        sa[p] = (er - eold) / DELTA;        /* 2110：误差斜率 */
        a[p] -= DELTA;                      /* 2120：恢复原值 */
    }
    for (int p = 1; p <= NP; p++) {         /* 2150～2200：每个 b 系数的斜率 */
        b[p] += DELTA;
        calc_error();
        sb[p] = (er - eold) / DELTA;
        b[p] -= DELTA;
    }
    for (int p = 0; p <= NP; p++) {         /* 2220～2250：沿下坡方向调整系数 */
        a[p] -= sa[p] * MU;
        b[p] -= sb[p] * MU;                 /* b[0] 的斜率恒为 0，不受影响 */
    }
    calc_error();                           /* 2270：新的误差 */
    enew = er;                              /* 2280 */
}

int main(int argc, char **argv)
{
    int niter = argc > 1 ? atoi(argv[1]) : 100;

    for (int i = 0; i <= N / 2; i++)        /* 代替 250 GOSUB XXXX：截止频率 0.31 的理想低通 */
        t[i] = (i / (double)N <= 0.31) ? 1.0 : 0.0;

    for (int p = 0; p <= NP; p++) { a[p] = 0.0; b[p] = 0.0; }   /* 270～300：恒等系统 */
    a[0] = 1.0;                             /* 310 */

    calc_error();
    printf("初始（恒等系统）误差 ER = %.6f\n", er);
    for (int iter = 1; iter <= niter; iter++) { /* 340：迭代循环 */
        new_coefficients();                 /* 350：GOSUB 2000 */
        if (iter <= 5 || iter % (niter / 10 > 0 ? niter / 10 : 1) == 0)
            printf("迭代 %5d  ENEW = %.6f  MU = %g\n", iter, enew, MU);   /* 360 */
        if (enew > eold) MU /= 2.0;         /* 370：误差变大就把步长减半 */
    }

    printf("系数：\n");                     /* 410～430 */
    for (int p = 0; p <= NP; p++)
        printf("  a%d = %12.8f   b%d = %12.8f\n", p, a[p], p, b[p]);

    /* 额外检查：通带（0～0.28）和阻带（0.34～0.5）的平均幅度 */
    calc_error();
    double pass = 0, stop = 0; int np = 0, ns = 0;
    for (int i = 0; i <= N / 2; i++) {
        double f = i / (double)N, mag = sqrt(rex[i] * rex[i] + imx[i] * imx[i]);
        if (f <= 0.28) { pass += mag; np++; }
        if (f >= 0.34) { stop += mag; ns++; }
    }
    printf("通带平均幅度 = %.3f（目标 1），阻带平均幅度 = %.3f（目标 0）\n", pass / np, stop / ns);
    return 0;
}
