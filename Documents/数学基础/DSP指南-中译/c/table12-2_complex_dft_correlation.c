/*
 * 表 12-2：用相关法计算复数 DFT（BASIC 原程序的 C 版本）
 *
 * 把时域信号（实部 XR[]、虚部 XI[]）与每个频率的复正弦逐点做复数乘法再求和。
 * 这就是 FFT 要加速的那个算法，计算量正比于 N²。
 *
 * 测试：
 *   测试 1：冲激 x[0]=1 → 频谱应处处为 1+0j
 *   测试 2：复正弦 x[n] = e^{j2π·5n/N}（实部是余弦、虚部是正弦）→ 只有第 5 点为 N，其余为 0
 *   测试 3：实信号（虚部全 0）→ 频谱实部关于 0 和 N/2 偶对称、虚部奇对称（见图 12-10）
 *
 * 编译运行：cc -O2 -o table12-2_complex_dft_correlation table12-2_complex_dft_correlation.c -lm && ./table12-2_complex_dft_correlation
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define N 64

static const double PI = 3.14159265358979323846;

/* 5000：相关法复数 DFT。xr/xi 是时域，rex/imx 是频域，下标都是 0～n-1 */
static void complex_dft(const double *xr, const double *xi, int n, double *rex, double *imx)
{
    for (int k = 0; k < n; k++) {           /* 5080～5110：REX[]、IMX[] 清零，相关时当累加器用 */
        rex[k] = 0.0;
        imx[k] = 0.0;
    }
    for (int k = 0; k < n; k++)             /* 5130：遍历频域的每个点 */
        for (int i = 0; i < n; i++) {       /* 5140：与复正弦 SR、SI 做相关 */
            double sr = cos(2.0 * PI * k * i / n);      /* 5160～5170：算出复正弦 */
            double si = -sin(2.0 * PI * k * i / n);
            rex[k] += xr[i] * sr - xi[i] * si;          /* 5180～5190：复数乘法后累加 */
            imx[k] += xr[i] * si + xi[i] * sr;
        }
}

int main(void)
{
    double xr[N], xi[N], rex[N], imx[N], err;

    /* 测试 1：冲激 */
    for (int i = 0; i < N; i++) xr[i] = xi[i] = 0.0;
    xr[0] = 1.0;
    complex_dft(xr, xi, N, rex, imx);
    err = 0.0;
    for (int k = 0; k < N; k++) err = fmax(err, fmax(fabs(rex[k] - 1.0), fabs(imx[k])));
    printf("测试 1（冲激）：频谱与 1+0j 的最大偏差 = %.3g\n", err);

    /* 测试 2：频率为 5 的复正弦 */
    for (int i = 0; i < N; i++) {
        xr[i] = cos(2.0 * PI * 5 * i / N);
        xi[i] = sin(2.0 * PI * 5 * i / N);
    }
    complex_dft(xr, xi, N, rex, imx);
    err = 0.0;
    for (int k = 0; k < N; k++)
        if (k != 5) err = fmax(err, fmax(fabs(rex[k]), fabs(imx[k])));
    printf("测试 2（复正弦）：X[5] = %.6f%+.3gj，其余点的最大幅度 = %.3g\n", rex[5], imx[5], err);

    /* 测试 3：实信号的对称性 */
    srand(1);
    for (int i = 0; i < N; i++) {
        xr[i] = rand() / (double)RAND_MAX - 0.5;
        xi[i] = 0.0;
    }
    complex_dft(xr, xi, N, rex, imx);
    err = 0.0;
    for (int k = 1; k < N / 2; k++)
        err = fmax(err, fmax(fabs(rex[N - k] - rex[k]), fabs(imx[N - k] + imx[k])));
    printf("测试 3（实信号）：Re X[N-k]=Re X[k]、Im X[N-k]=-Im X[k] 的最大偏差 = %.3g\n", err);
    printf("        Im X[0] = %.3g，Im X[N/2] = %.3g（应为 0）\n", imx[0], imx[N / 2]);
    return 0;
}
