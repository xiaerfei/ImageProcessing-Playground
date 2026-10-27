/*
 * 表 8-2：用相关法计算 DFT（BASIC 原程序的 C 版本）
 *
 * 公式 8-4：Re X[k] = Σ x[i]·cos(2πki/N)，Im X[k] = −Σ x[i]·sin(2πki/N)。
 * 即把输入信号和每个基函数逐点相乘再求和（相关）。
 *
 * 原书第 210 行用「虚构的子程序」载入时域数据。这里换成书里有答案的例子：
 *   测试 1（图 8-6）：N=32，x[0]=32 的冲激 → Re X[] 应全为 32，Im X[] 全为 0
 *   测试 2（图 8-8a）：N=64，3 个周期的单位正弦 s3[] → Im X[3] 应为 −32（幅度 32，负号来自公式 8-4）
 *   测试 3（图 8-8b 的思路）：N=64，只含其他频率的正弦/余弦 → Im X[3] 应为 0
 *   测试 4：N=512 的随机信号做 DFT，再按公式 8-2、8-3 合成回去，检查能否还原
 *
 * 编译运行：cc -O2 -o table8-2_dft_correlation table8-2_dft_correlation.c -lm && ./table8-2_dft_correlation
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define NMAX 512                            /* 140 DIM XX[511]：原书 N=512 */

static const double PI = 3.14159265358979323846;

/* 相关法 DFT：每个频域点 = 输入信号与对应基函数的相关 */
static void dft(const double *xx, int n, double *rex, double *imx)
{
    for (int k = 0; k <= n / 2; k++) {     /* 240～270：REX[] 和 IMX[] 清零，当累加器用 */
        rex[k] = 0.0;
        imx[k] = 0.0;
    }
    for (int k = 0; k <= n / 2; k++)        /* 310：遍历频域每个点 */
        for (int i = 0; i < n; i++) {       /* 320：遍历时域每个点 */
            rex[k] += xx[i] * cos(2 * PI * k * i / n);  /* 340 */
            imx[k] -= xx[i] * sin(2 * PI * k * i / n);  /* 350：注意负号 */
        }
}

/* 逆 DFT（表 8-1 的做法），只用于测试 4 的往返检验 */
static void idft(const double *rex_in, const double *imx_in, int n, double *xx)
{
    double rex[NMAX / 2 + 1], imx[NMAX / 2 + 1];
    for (int k = 0; k <= n / 2; k++) {
        rex[k] = rex_in[k] / (n / 2);
        imx[k] = -imx_in[k] / (n / 2);
    }
    rex[0] /= 2;
    rex[n / 2] /= 2;
    for (int i = 0; i < n; i++) {
        xx[i] = 0.0;
        for (int k = 0; k <= n / 2; k++)
            xx[i] += rex[k] * cos(2 * PI * k * i / n) + imx[k] * sin(2 * PI * k * i / n);
    }
}

int main(void)
{
    double xx[NMAX], back[NMAX], rex[NMAX / 2 + 1], imx[NMAX / 2 + 1];

    /* 测试 1：图 8-6 */
    for (int i = 0; i < 32; i++) xx[i] = 0.0;
    xx[0] = 32;
    dft(xx, 32, rex, imx);
    double dre = 0.0, dim = 0.0;
    for (int k = 0; k <= 16; k++) {
        if (fabs(rex[k] - 32) > dre) dre = fabs(rex[k] - 32);
        if (fabs(imx[k]) > dim) dim = fabs(imx[k]);
    }
    printf("测试 1（图 8-6）：Re X[] 与 32 的最大偏差 = %.3g，|Im X[]| 最大 = %.3g\n", dre, dim);

    /* 测试 2：图 8-8a，x1[] = s3[] */
    for (int i = 0; i < 64; i++) xx[i] = sin(2 * PI * 3 * i / 64);
    dft(xx, 64, rex, imx);
    printf("测试 2（图 8-8a）：Im X[3] = %.6f，Re X[3] = %.3g\n", imx[3], rex[3]);

    /* 测试 3：图 8-8b 的思路，x2[] 里没有 3 个周期的分量 */
    for (int i = 0; i < 64; i++)
        xx[i] = 0.4 * sin(2 * PI * 1 * i / 64) + 0.3 * cos(2 * PI * 2 * i / 64)
              + 0.3 * sin(2 * PI * 7 * i / 64) + 0.2 * cos(2 * PI * 11 * i / 64);
    dft(xx, 64, rex, imx);
    printf("测试 3（图 8-8b）：Im X[3] = %.3g，Im X[7] = %.6f（0.3 的正弦 → −0.3·32）\n", imx[3], imx[7]);

    /* 测试 4：随机信号往返 */
    srand(1);
    for (int i = 0; i < NMAX; i++) xx[i] = (double)rand() / RAND_MAX - 0.5;
    dft(xx, NMAX, rex, imx);
    idft(rex, imx, NMAX, back);
    double err = 0.0;
    for (int i = 0; i < NMAX; i++)
        if (fabs(back[i] - xx[i]) > err) err = fabs(back[i] - xx[i]);
    printf("测试 4：N=512 随机信号 DFT 后再逆 DFT，与原信号最大误差 = %.3g\n", err);
    printf("        Im X[0] = %.3g，Im X[N/2] = %.3g（这两点恒为 0）\n", imx[0], imx[NMAX / 2]);
    return 0;
}
