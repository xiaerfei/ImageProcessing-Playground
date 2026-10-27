/*
 * 表 8-1：逆 DFT（BASIC 原程序的 C 版本）
 *
 * 先用公式 8-3 把频域值换算成余弦/正弦波的幅度，再用公式 8-2 把这些波加起来。
 * 原书给了两种合成写法（只是内外循环对调），这里两种都实现，并比对结果。
 *
 * 原书第 210 行用「虚构的子程序」载入频域数据。这里载入两组已知答案的频域：
 *   测试 1（图 8-6 的 N=512 版本）：Re X[k] 全为 N、Im X[k] 全为 0
 *          → 时域应是 x[0] = N 的单个冲激，其余全 0
 *   测试 2：x[i] = 1 + 0.5·cos(2π·5i/N) − 0.25·sin(2π·20i/N) 的频域
 *          → Re X[0] = N，Re X[5] = 0.5·N/2，Im X[20] = +0.25·N/2（公式 8-4 的负号让 Im 变号）
 *
 * 编译运行：cc -O2 -o table8-1_inverse_dft table8-1_inverse_dft.c -lm && ./table8-1_inverse_dft
 */
#include <math.h>
#include <stdio.h>

#define N  512                              /* 190 N% = 512：时域点数 */
#define NF (N / 2 + 1)                      /* 150～160 DIM REX[256]、IMX[256]：频域 N/2+1 点 */

static const double PI = 3.14159265358979323846;

/* 公式 8-3：频域值 → 合成用的余弦/正弦幅度（原地修改） */
static void to_amplitudes(double *rex, double *imx)
{
    for (int k = 0; k < NF; k++) {          /* 250～280 */
        rex[k] = rex[k] / (N / 2);          /* 260：除以 N/2 */
        imx[k] = -imx[k] / (N / 2);         /* 270：除以 N/2 并变号 */
    }
    rex[0] = rex[0] / 2;                    /* 300：首尾两点带宽只有一半，再除以 2 */
    rex[N / 2] = rex[N / 2] / 2;            /* 310 */
}

/* 合成方法 1：逐个频率，把整条余弦/正弦波加进累加器 */
static void synthesize_method1(const double *rex, const double *imx, double *xx)
{
    for (int i = 0; i < N; i++)             /* 340～360：累加器清零 */
        xx[i] = 0.0;
    for (int k = 0; k < NF; k++)            /* 420：遍历每个频率 */
        for (int i = 0; i < N; i++) {       /* 430：遍历时域每个点 */
            xx[i] += rex[k] * cos(2 * PI * k * i / N);  /* 450 */
            xx[i] += imx[k] * sin(2 * PI * k * i / N);  /* 460 */
        }
}

/* 合成方法 2：逐个时域点，把所有波在这一点的值加起来（内外循环对调） */
static void synthesize_method2(const double *rex, const double *imx, double *xx)
{
    for (int i = 0; i < N; i++) {           /* 420：遍历时域每个点 */
        xx[i] = 0.0;
        for (int k = 0; k < NF; k++) {      /* 430：遍历每个频率 */
            xx[i] += rex[k] * cos(2 * PI * k * i / N);  /* 450 */
            xx[i] += imx[k] * sin(2 * PI * k * i / N);  /* 460 */
        }
    }
}

static void run(const char *name, double *rex, double *imx, double (*expect)(int))
{
    double x1[N], x2[N];
    to_amplitudes(rex, imx);
    synthesize_method1(rex, imx, x1);
    synthesize_method2(rex, imx, x2);

    double err = 0.0, diff = 0.0;
    for (int i = 0; i < N; i++) {
        if (fabs(x1[i] - expect(i)) > err) err = fabs(x1[i] - expect(i));
        if (fabs(x1[i] - x2[i]) > diff) diff = fabs(x1[i] - x2[i]);
    }
    printf("%s\n", name);
    printf("  x[0..3] = %.6f %.6f %.6f %.6f\n", x1[0], x1[1], x1[2], x1[3]);
    printf("  与已知答案的最大误差 = %.3g，两种方法的最大差 = %.3g\n", err, diff);
}

static double expect_impulse(int i) { return i == 0 ? N : 0.0; }
static double expect_sines(int i)
{
    return 1 + 0.5 * cos(2 * PI * 5 * i / N) - 0.25 * sin(2 * PI * 20 * i / N);
}

int main(void)
{
    double rex[NF], imx[NF];

    for (int k = 0; k < NF; k++) { rex[k] = N; imx[k] = 0.0; }
    run("测试 1：Re X[] 全为 N → 冲激", rex, imx, expect_impulse);

    for (int k = 0; k < NF; k++) { rex[k] = 0.0; imx[k] = 0.0; }
    rex[0] = N;
    rex[5] = 0.5 * N / 2;
    imx[20] = 0.25 * N / 2;
    run("测试 2：三个分量合成", rex, imx, expect_sines);
    return 0;
}
