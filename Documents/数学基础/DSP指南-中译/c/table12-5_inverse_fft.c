/*
 * 表 12-5：逆 FFT（BASIC 原程序的 C 版本）
 *
 * 复数 DFT 的正、逆变换几乎一样，所以逆 FFT 直接借用正向 FFT：
 * 先把频域虚部取反，做一次正向 FFT，再把结果除以 N、虚部再取反。
 *
 * 原书用单精度浮点数，这里也用 float（real_t），以便重做图 12-9 的精度实验：
 * 随机信号 → 正变换 → 逆变换，原信号与还原信号之差的标准差（单位：百万分之一，ppm），
 * 分别用 FFT/逆 FFT 和相关法 DFT/逆 DFT 计算，N 从 16 到 1024。
 * 正弦、余弦及其角度也全部按单精度计算，与原书 BASIC 一致；相关法要算 sin(2πki/N)，
 * 角度最大接近 2πN，单精度表示这么大的角度本身就有舍入误差，这是它误差随 N 增长的主要来源。
 *
 * 编译运行：cc -O2 -o table12-5_inverse_fft table12-5_inverse_fft.c -lm && ./table12-5_inverse_fft
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define NMAX 1024

typedef float real_t;                           /* 原书 BASIC 默认是单精度 */

static const real_t PI_F = 3.14159265f;      /* 原书 PI = 3.14159265，单精度 */

/* 1000：FFT（同表 12-4，这里用单精度） */
static void fft(real_t *rex, real_t *imx, int n)
{
    int nm1 = n - 1, nd2 = n / 2, m = (int)lround(log(n) / log(2)), j = nd2;
    for (int i = 1; i <= n - 2; i++) {          /* 1110～1250：位反转排序 */
        if (i < j) {
            real_t tr = rex[j], ti = imx[j];
            rex[j] = rex[i]; imx[j] = imx[i];
            rex[i] = tr;     imx[i] = ti;
        }
        int k = nd2;
        while (k <= j) { j -= k; k /= 2; }
        j += k;
    }
    for (int l = 1; l <= m; l++) {              /* 1270～1490：逐级合成 */
        int le = 1 << l, le2 = le / 2;
        real_t ur = 1, ui = 0;
        real_t sr = cosf(PI_F / le2), si = -sinf(PI_F / le2);
        for (int jj = 1; jj <= le2; jj++) {
            for (int i = jj - 1; i <= nm1; i += le) {
                int ip = i + le2;
                real_t tr = rex[ip] * ur - imx[ip] * ui;
                real_t ti = rex[ip] * ui + imx[ip] * ur;
                rex[ip] = rex[i] - tr; imx[ip] = imx[i] - ti;
                rex[i] += tr;          imx[i] += ti;
            }
            real_t tr = ur;
            ur = tr * sr - ui * si;
            ui = tr * si + ui * sr;
        }
    }
}

/* 2000：逆 FFT */
static void inverse_fft(real_t *rex, real_t *imx, int n)
{
    for (int k = 0; k < n; k++)                 /* 2060～2080：IMX[] 取反 */
        imx[k] = -imx[k];

    fft(rex, imx, n);                           /* 2100：做一次正向 FFT（原书注释写的是表 12-3，实为表 12-4） */

    for (int i = 0; i < n; i++) {               /* 2120～2150：时域除以 N，IMX[] 再取反 */
        rex[i] = rex[i] / n;
        imx[i] = -imx[i] / n;
    }
}

/* 相关法复数 DFT（表 12-2），sign=-1 正变换，sign=+1 逆变换（逆变换再除以 n），单精度 */
static void complex_dft(const real_t *xr, const real_t *xi, int n, int sign, real_t *yr, real_t *yi)
{
    for (int k = 0; k < n; k++) {
        real_t ar = 0, ai = 0;
        for (int i = 0; i < n; i++) {
            real_t arg = 2 * PI_F * k * i / n;  /* 像原书 BASIC 一样在单精度下算角度，角度可大到 2πN，舍入误差随之变大 */
            real_t c = cosf(arg), s = sign * sinf(arg);
            ar += xr[i] * c - xi[i] * s;
            ai += xr[i] * s + xi[i] * c;
        }
        yr[k] = (sign > 0) ? ar / n : ar;
        yi[k] = (sign > 0) ? ai / n : ai;
    }
}

/* 原信号与还原信号之差的标准差，单位 ppm */
static double error_ppm(const real_t *a, const real_t *b, int n)
{
    double mean = 0.0, var = 0.0;
    for (int i = 0; i < n; i++) mean += (double)a[i] - b[i];
    mean /= n;
    for (int i = 0; i < n; i++) { double d = (double)a[i] - b[i] - mean; var += d * d; }
    return 1e6 * sqrt(var / (n - 1));
}

int main(void)
{
    static real_t x[NMAX], zero[NMAX], rex[NMAX], imx[NMAX], fr[NMAX], fi[NMAX], tr[NMAX], ti[NMAX];

    srand(5);
    printf("    N   FFT 还原误差(ppm)   相关法还原误差(ppm)   FFT 后时域虚部最大值\n");
    for (int n = 16; n <= NMAX; n *= 2) {
        for (int i = 0; i < n; i++) { x[i] = (real_t)(rand() / (double)RAND_MAX); zero[i] = 0; }

        for (int i = 0; i < n; i++) { rex[i] = x[i]; imx[i] = 0; }
        fft(rex, imx, n);                       /* 正向 FFT */
        inverse_fft(rex, imx, n);               /* 逆 FFT 还原 */
        double imax = 0.0;
        for (int i = 0; i < n; i++) imax = fmax(imax, fabs(imx[i]));

        complex_dft(x, zero, n, -1, fr, fi);    /* 相关法正变换 */
        complex_dft(fr, fi, n, +1, tr, ti);     /* 相关法逆变换 */

        printf("%5d   %12.3f        %12.3f            %.3g\n",
               n, error_ppm(x, rex, n), error_ppm(x, tr, n), imax);
    }
    return 0;
}
