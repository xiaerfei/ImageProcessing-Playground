/*
 * 表 12-1：生成负频率（BASIC 原程序的 C 版本）
 *
 * 实数 DFT 的频谱只有第 0～N/2 点。要用复数逆 DFT（比如逆 FFT）把它变回时域，
 * 必须先按对称关系补出第 N/2+1～N-1 点（负频率）：
 *   实部 Re X[N-k] = Re X[k]（偶对称），虚部 Im X[N-k] = -Im X[k]（奇对称）。
 *
 * 测试：取 64 点随机实信号，用相关法复数 DFT 算出完整频谱作为标准答案；
 * 然后只保留 0～N/2 点、把其余点清零，调用本子程序补回负频率，与标准答案比较；
 * 再做复数逆 DFT，检查时域虚部是否全为 0、实部是否还原原信号（原书建议的检查方法）。
 *
 * 编译运行：cc -O2 -o table12-1_negative_freq table12-1_negative_freq.c -lm && ./table12-1_negative_freq
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define N 64

static const double PI = 3.14159265358979323846;

/* 6000：由实数频域生成复数频域。进入时 rex/imx 的 0～n/2 点有效，返回时 0～n-1 点都有效 */
static void negative_frequency_generation(double *rex, double *imx, int n)
{
    for (int k = n / 2 + 1; k <= n - 1; k++) {  /* 6060：遍历负频率的每个点 */
        rex[k] = rex[n - k];                    /* 6070：实部偶对称 */
        imx[k] = -imx[n - k];                   /* 6080：虚部奇对称 */
    }
}

/* 相关法复数 DFT（同表 12-2）。sign = -1 为正变换；sign = +1 且除以 n 为逆变换 */
static void complex_dft(const double *xr, const double *xi, int n, int sign,
                        double *yr, double *yi)
{
    for (int k = 0; k < n; k++) {
        yr[k] = yi[k] = 0.0;
        for (int i = 0; i < n; i++) {
            double c = cos(2.0 * PI * k * i / n), s = sign * sin(2.0 * PI * k * i / n);
            yr[k] += xr[i] * c - xi[i] * s;
            yi[k] += xr[i] * s + xi[i] * c;
        }
        if (sign > 0) { yr[k] /= n; yi[k] /= n; }
    }
}

int main(void)
{
    double x[N], zero[N] = {0}, refr[N], refi[N], rex[N], imx[N], tr[N], ti[N];

    srand(12);
    for (int i = 0; i < N; i++) x[i] = rand() / (double)RAND_MAX - 0.5;
    complex_dft(x, zero, N, -1, refr, refi);    /* 完整的复数频谱，作为标准答案 */

    for (int k = 0; k < N; k++) {               /* 模拟「只有实数 DFT 的结果」：只留 0～N/2 点 */
        rex[k] = (k <= N / 2) ? refr[k] : 0.0;
        imx[k] = (k <= N / 2) ? refi[k] : 0.0;
    }
    negative_frequency_generation(rex, imx, N);

    double e_spec = 0.0;
    for (int k = 0; k < N; k++)
        e_spec = fmax(e_spec, fmax(fabs(rex[k] - refr[k]), fabs(imx[k] - refi[k])));
    printf("补出的负频率与完整频谱的最大偏差 = %.3g\n", e_spec);

    complex_dft(rex, imx, N, +1, tr, ti);       /* 复数逆 DFT 回到时域 */
    double e_re = 0.0, e_im = 0.0;
    for (int i = 0; i < N; i++) {
        e_re = fmax(e_re, fabs(tr[i] - x[i]));
        e_im = fmax(e_im, fabs(ti[i]));
    }
    printf("逆 DFT 后：实部与原信号最大偏差 = %.3g，虚部最大幅度 = %.3g（应为 0）\n", e_re, e_im);

    /* 反例：不补负频率（第 N/2+1～N-1 点保持为 0）直接做逆变换，虚部就不再是 0 */
    for (int k = N / 2 + 1; k < N; k++) rex[k] = imx[k] = 0.0;
    complex_dft(rex, imx, N, +1, tr, ti);
    e_im = 0.0;
    for (int i = 0; i < N; i++) e_im = fmax(e_im, fabs(ti[i]));
    printf("反例（没补负频率）：时域虚部最大幅度 = %.3g\n", e_im);
    return 0;
}
