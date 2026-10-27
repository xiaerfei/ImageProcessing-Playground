/*
 * 表 24-1：常规的图像卷积（BASIC 原程序的 C 版本）
 *
 * 原程序按公式 24-3 从输出端计算：100×100 的输入图像 X 与 29×29 的滤波器核 H 卷积，
 * 得到 128×128 的输出图像 Y。原书有两处问题，这里按公式 24-3 修正：
 *   1. 第 230 行写成 X[R%-J%,C%-J%]，列下标应为 C%-K%；
 *   2. 没有检查 R%-J%、C%-K% 是否越出 X 的 0～99 范围，这里越界的项按 0 处理（跳过）。
 *
 * 程序复现图 24-11～24-13 的思路，并做三项验证：
 *   测试 1：常规卷积与 FFT 卷积（补零到 128×128，见图 24-13）逐像素比较；
 *   测试 2：用卷积实现相关——把目标图案旋转 180° 当作核，找输出的最亮点，
 *           检查它是否落在目标图案在输入图像中的位置上；
 *   测试 3：可分离卷积（先行后列）与直接二维卷积在高斯核下逐像素比较，并比较耗时。
 *
 * 编译运行：cc -O2 -o table24-1_image_convolution table24-1_image_convolution.c -lm && ./table24-1_image_convolution
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define NX 100                              /* 120 DIM X[99,99]：输入图像 100×100 */
#define NH 29                               /* 130 DIM H[28,28]：滤波器核 29×29 */
#define NY 128                              /* 140 DIM Y[127,127]：输出图像 128×128（100+29-1=128） */

static const double PI = 3.14159265358979323846;

static double X[NX][NX], H[NH][NH], Y[NY][NY], Yfft[NY][NY];

/* 简单的线性同余随机数，保证每次运行结果相同 */
static unsigned rng_state = 12345u;
static double rnd(void)
{
    rng_state = rng_state * 1103515245u + 12345u;
    return ((rng_state >> 8) & 0xFFFFFF) / (double)0x1000000;
}

/* 常规卷积：公式 24-3 的直接实现，从输出端逐像素计算 */
static void convolve_direct(double y[NY][NY])
{
    for (int r = 0; r < NY; r++)            /* 160：遍历输出的每一行 */
        for (int c = 0; c < NY; c++) {      /* 170：遍历输出的每一列 */
            double acc = 0.0;               /* 190：累加器清零 */
            for (int j = 0; j < NH; j++)    /* 210：遍历核的每一行 */
                for (int k = 0; k < NH; k++) {  /* 220：遍历核的每一列 */
                    int rr = r - j, cc = c - k;
                    if (rr < 0 || rr >= NX || cc < 0 || cc >= NX) continue;  /* 原书缺的越界检查 */
                    acc += H[j][k] * X[rr][cc];  /* 230：原书误印为 X[R%-J%,C%-J%] */
                }
            y[r][c] = acc;
        }
}

/* 一维复数 FFT（基 2，原位），inverse 为 1 时做逆变换（含 1/N） */
static void fft1d(double *re, double *im, int n, int inverse)
{
    for (int i = 1, j = 0; i < n; i++) {    /* 位反转排序 */
        int bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j |= bit;
        if (i < j) {
            double t = re[i]; re[i] = re[j]; re[j] = t;
            t = im[i]; im[i] = im[j]; im[j] = t;
        }
    }
    for (int len = 2; len <= n; len <<= 1) {    /* 逐级做蝶形运算 */
        double ang = (inverse ? 2.0 : -2.0) * PI / len;
        for (int i = 0; i < n; i += len)
            for (int k = 0; k < len / 2; k++) {
                double wr = cos(ang * k), wi = sin(ang * k);
                int a = i + k, b = i + k + len / 2;
                double tr = re[b] * wr - im[b] * wi, ti = re[b] * wi + im[b] * wr;
                re[b] = re[a] - tr; im[b] = im[a] - ti;
                re[a] += tr;        im[a] += ti;
            }
    }
    if (inverse)
        for (int i = 0; i < n; i++) { re[i] /= n; im[i] /= n; }
}

/* 二维 FFT：先对每一行做一维 FFT，再对每一列做一维 FFT（正文"Fourier 图像分析"一节的做法） */
static void fft2d(double re[NY][NY], double im[NY][NY], int inverse)
{
    double cr[NY], ci[NY];
    for (int r = 0; r < NY; r++) fft1d(re[r], im[r], NY, inverse);
    for (int c = 0; c < NY; c++) {
        for (int r = 0; r < NY; r++) { cr[r] = re[r][c]; ci[r] = im[r][c]; }
        fft1d(cr, ci, NY, inverse);
        for (int r = 0; r < NY; r++) { re[r][c] = cr[r]; im[r][c] = ci[r]; }
    }
}

/* FFT 卷积（图 24-13）：两幅图都补零到 128×128，变换、相乘、逆变换 */
static void convolve_fft(double y[NY][NY])
{
    static double xr[NY][NY], xi[NY][NY], hr[NY][NY], hi[NY][NY];
    for (int r = 0; r < NY; r++)
        for (int c = 0; c < NY; c++) {
            xr[r][c] = (r < NX && c < NX) ? X[r][c] : 0.0;
            hr[r][c] = (r < NH && c < NH) ? H[r][c] : 0.0;
            xi[r][c] = hi[r][c] = 0.0;
        }
    fft2d(xr, xi, 0);
    fft2d(hr, hi, 0);
    for (int r = 0; r < NY; r++)            /* 频域逐点复数相乘（公式 9-1） */
        for (int c = 0; c < NY; c++) {
            double re = xr[r][c] * hr[r][c] - xi[r][c] * hi[r][c];
            double im = xr[r][c] * hi[r][c] + xi[r][c] * hr[r][c];
            xr[r][c] = re; xi[r][c] = im;
        }
    fft2d(xr, xi, 1);
    for (int r = 0; r < NY; r++)
        for (int c = 0; c < NY; c++) y[r][c] = xr[r][c];
}

int main(void)
{
    /* 造一个 29×29 的"目标图案"（不对称，模仿图 24-12 的人脸）和一幅 100×100 的含噪图像，
       把目标图案放在输入图像第 40 行、第 55 列开始的位置 */
    static double target[NH][NH];
    for (int r = 0; r < NH; r++)
        for (int c = 0; c < NH; c++) {
            double dr = (r - 12.0) / 6.0, dc = (c - 16.0) / 4.0;
            target[r][c] = exp(-(dr * dr + dc * dc)) - 0.6 * exp(-((r - 22.0) * (r - 22.0) + (c - 8.0) * (c - 8.0)) / 10.0);
        }
    const int R0 = 40, C0 = 55;
    for (int r = 0; r < NX; r++)
        for (int c = 0; c < NX; c++) X[r][c] = 0.5 * (rnd() - 0.5);
    for (int r = 0; r < NH; r++)
        for (int c = 0; c < NH; c++) X[R0 + r][C0 + c] += target[r][c];

    /* 图 24-12b：把目标图案旋转 180°（左右翻再上下翻）作为核，抵消卷积自带的翻转，
       使卷积变成相关（图 24-12c 的边缘检测这一步这里省略） */
    for (int r = 0; r < NH; r++)
        for (int c = 0; c < NH; c++) H[r][c] = target[NH - 1 - r][NH - 1 - c];

    clock_t t0 = clock();
    convolve_direct(Y);
    clock_t t1 = clock();
    convolve_fft(Yfft);
    clock_t t2 = clock();

    double maxdiff = 0.0, peak = -1e30;
    int pr = 0, pc = 0;
    for (int r = 0; r < NY; r++)
        for (int c = 0; c < NY; c++) {
            double d = fabs(Y[r][c] - Yfft[r][c]);
            if (d > maxdiff) maxdiff = d;
            if (Y[r][c] > peak) { peak = Y[r][c]; pr = r; pc = c; }
        }
    printf("测试 1：常规卷积与 FFT 卷积逐像素的最大偏差 = %.3g\n", maxdiff);
    printf("        耗时：常规卷积 %.1f ms，FFT 卷积 %.1f ms\n",
           1000.0 * (t1 - t0) / CLOCKS_PER_SEC, 1000.0 * (t2 - t1) / CLOCKS_PER_SEC);

    /* 核从 0 到 28 编号，输出第 [r,c] 点对应核右下角落在输入 [r,c] 上，
       所以目标左上角在 [R0,C0] 时，峰值应出现在 [R0+28, C0+28] */
    printf("测试 2：相关输出的最亮点在 [%d,%d]，值 %.3f；目标图案对应位置应为 [%d,%d]\n",
           pr, pc, peak, R0 + NH - 1, C0 + NH - 1);

    /* 测试 3：可分离的高斯核。二维核 = 竖直投影 × 水平投影（公式 24-1），
       可分离卷积先用水平投影卷每一行，再用竖直投影卷每一列 */
    double g[NH];
    for (int i = 0; i < NH; i++) g[i] = exp(-((i - 14.0) * (i - 14.0)) / (2.0 * 4.0 * 4.0));
    for (int r = 0; r < NH; r++)
        for (int c = 0; c < NH; c++) H[r][c] = g[r] * g[c];

    t0 = clock();
    convolve_direct(Y);
    t1 = clock();
    static double tmp[NX][NY];              /* 中间图像：行已卷积、列还没卷 */
    for (int r = 0; r < NX; r++)
        for (int c = 0; c < NY; c++) {
            double acc = 0.0;
            for (int k = 0; k < NH; k++)
                if (c - k >= 0 && c - k < NX) acc += g[k] * X[r][c - k];
            tmp[r][c] = acc;
        }
    for (int c = 0; c < NY; c++)
        for (int r = 0; r < NY; r++) {
            double acc = 0.0;
            for (int j = 0; j < NH; j++)
                if (r - j >= 0 && r - j < NX) acc += g[j] * tmp[r - j][c];
            Yfft[r][c] = acc;
        }
    t2 = clock();
    maxdiff = 0.0;
    for (int r = 0; r < NY; r++)
        for (int c = 0; c < NY; c++) {
            double d = fabs(Y[r][c] - Yfft[r][c]);
            if (d > maxdiff) maxdiff = d;
        }
    printf("测试 3：高斯核下，可分离卷积与直接二维卷积的最大偏差 = %.3g\n", maxdiff);
    printf("        耗时：直接二维卷积 %.1f ms，可分离卷积 %.2f ms\n",
           1000.0 * (t1 - t0) / CLOCKS_PER_SEC, 1000.0 * (t2 - t1) / CLOCKS_PER_SEC);
    return 0;
}
