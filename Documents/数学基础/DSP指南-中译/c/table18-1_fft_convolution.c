/*
 * 表 18-1：FFT 卷积（BASIC 原程序的 C 版本）
 *
 * 按原书参数：400 点滤波器核，输入按每段 625 点切开，每段补零到 1024 点做 FFT，
 * 625 + 400 - 1 = 1024，所以不会发生循环卷积。各段输出用重叠相加法拼起来。
 * 原书处理 16000 段（1000 万点）；为了能和直接卷积逐点对比，这里默认只处理 160 段（10 万点），
 * 段数可以用命令行参数改，例如 ./table18-1_fft_convolution 16000。
 * 原书的 FFT、IFFT 都是「虚构的子程序」，这里用表 12-4 的复数 FFT 实现，
 * 逆 FFT 用「共轭 → FFT → 共轭 → 除以 N」的办法（同表 12-5）。
 * 原书行号 130 重复了一次，是排版错误。
 *
 * 测试：用随机输入信号和一个窗函数 sinc 低通核，把 FFT 卷积的输出与直接卷积（表 6-2 的输出端算法）
 * 逐点比较，并比较两者的耗时。
 *
 * 编译运行：cc -O2 -o table18-1_fft_convolution table18-1_fft_convolution.c -lm && ./table18-1_fft_convolution
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define NFFT 1024                           /* 140 DIM XX[1023]：FFT 长度 */
#define NSEG 625                            /* 每段输入的点数 */
#define NK   400                            /* 滤波器核的点数 */
#define NOL  (NK - 1)                       /* 190 DIM OLAP[398]：段与段之间重叠的 399 点 */

static const double PI = 3.14159265358979323846;

/* 复数 FFT（同表 12-4） */
static void fft(double *rex, double *imx, int n)
{
    int nm1 = n - 1, nd2 = n / 2, m = (int)lround(log(n) / log(2)), j = nd2;
    for (int i = 1; i <= n - 2; i++) {          /* 位反转排序 */
        if (i < j) {
            double tr = rex[j], ti = imx[j];
            rex[j] = rex[i]; imx[j] = imx[i];
            rex[i] = tr;     imx[i] = ti;
        }
        int k = nd2;
        while (k <= j) { j -= k; k /= 2; }
        j += k;
    }
    for (int l = 1; l <= m; l++) {              /* 逐级合成 */
        int le = 1 << l, le2 = le / 2;
        double ur = 1.0, ui = 0.0, sr = cos(PI / le2), si = -sin(PI / le2);
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

/* 逆 FFT（同表 12-5）：共轭 → FFT → 共轭并除以 N */
static void inverse_fft(double *rex, double *imx, int n)
{
    for (int k = 0; k < n; k++) imx[k] = -imx[k];
    fft(rex, imx, n);
    for (int i = 0; i < n; i++) { rex[i] /= n; imx[i] = -imx[i] / n; }
}

/* 代替 260 GOSUB XXXX：窗函数 sinc 低通核（截止 0.05，布莱克曼窗，总和归一化为 1） */
static void load_kernel(double *h)
{
    double sum = 0.0, fc = 0.05;
    for (int i = 0; i < NK; i++) {
        double t = i - (NK - 1) / 2.0;
        double w = 0.42 - 0.5 * cos(2 * PI * i / (NK - 1)) + 0.08 * cos(4 * PI * i / (NK - 1));
        h[i] = sin(2 * PI * fc * t) / (PI * t) * w;
        sum += h[i];
    }
    for (int i = 0; i < NK; i++) h[i] /= sum;
}

/* FFT 卷积主体，对应原书第 210～600 行。x 长 nseg*NSEG，y 长 nseg*NSEG + NOL */
static void fft_convolve(const double *x, const double *h, int nseg, double *y)
{
    static double xx[NFFT], imx[NFFT];          /* 140～160：XX[ ]、REX[ ]（与 XX 共用）、IMX[ ] */
    static double refr[NFFT], imfr[NFFT];       /* 170～180：滤波器的频率响应 */
    double olap[NOL];                           /* 190 */

    for (int i = 0; i < NOL; i++) olap[i] = 0;  /* 210～230：重叠数组清零 */

    for (int i = 0; i < NFFT; i++) {            /* 260：核放进 XX[0]～XX[399]，其余补零 */
        refr[i] = i < NK ? h[i] : 0.0;
        imfr[i] = 0.0;
    }
    fft(refr, imfr, NFFT);                      /* 270～310：求出并保存滤波器的频率响应 */

    for (int seg = 0; seg < nseg; seg++) {      /* 340：逐段处理 */
        for (int i = 0; i < NFFT; i++) {        /* 360：本段放进 XX[0]～XX[624]，其余补零 */
            xx[i] = i < NSEG ? x[seg * NSEG + i] : 0.0;
            imx[i] = 0.0;
        }
        fft(xx, imx, NFFT);                     /* 370：本段的频谱 */

        for (int f = 0; f < NFFT; f++) {        /* 390～430：频谱乘以频率响应（复数乘法，公式 9-1） */
            double temp = xx[f] * refr[f] - imx[f] * imfr[f];
            imx[f] = xx[f] * imfr[f] + imx[f] * refr[f];
            xx[f] = temp;                       /* 原书只乘 0～512 点（实数 FFT 的输出），这里用复数 FFT，0～1023 全乘 */
        }

        inverse_fft(xx, imx, NFFT);             /* 450：回到时域，得到 1024 点输出段 */

        for (int i = 0; i < NOL; i++)           /* 470～490：加上上一段留下的重叠部分 */
            xx[i] += olap[i];
        for (int i = NSEG; i < NFFT; i++)       /* 510～530：保存要和下一段重叠的 399 点 */
            olap[i - NSEG] = xx[i];
        for (int i = 0; i < NSEG; i++)          /* 550：输出 XX[0]～XX[624] */
            y[seg * NSEG + i] = xx[i];
    }
    for (int i = 0; i < NOL; i++)               /* 600：最后一段的重叠部分直接输出 */
        y[nseg * NSEG + i] = olap[i];
}

/* 直接卷积（表 6-2 的输出端算法），用来对照 */
static void direct_convolve(const double *x, int nx, const double *h, double *y)
{
    for (int i = 0; i < nx + NK - 1; i++) {
        double acc = 0.0;
        for (int j = 0; j < NK; j++) {
            int k = i - j;
            if (k >= 0 && k < nx) acc += h[j] * x[k];
        }
        y[i] = acc;
    }
}

int main(int argc, char **argv)
{
    int nseg = argc > 1 ? atoi(argv[1]) : 160;
    int nx = nseg * NSEG, ny = nx + NOL;
    double *x = malloc(sizeof(double) * nx);
    double *y1 = malloc(sizeof(double) * ny), *y2 = malloc(sizeof(double) * ny);
    double h[NK];

    srand(1);
    for (int i = 0; i < nx; i++) x[i] = 2.0 * rand() / RAND_MAX - 1.0;
    load_kernel(h);

    clock_t t0 = clock();
    fft_convolve(x, h, nseg, y1);
    clock_t t1 = clock();
    direct_convolve(x, nx, h, y2);
    clock_t t2 = clock();

    double max_err = 0.0, max_y = 0.0;
    for (int i = 0; i < ny; i++) {
        double e = fabs(y1[i] - y2[i]);
        if (e > max_err) max_err = e;
        if (fabs(y2[i]) > max_y) max_y = fabs(y2[i]);
    }
    printf("输入 %d 段 × %d 点 = %d 点，滤波器核 %d 点，输出 %d 点（= %d + %d - 1）\n",
           nseg, NSEG, nx, NK, ny, nx, NK);
    printf("FFT 卷积与直接卷积的最大偏差 = %.3g（输出最大幅度 %.3f）\n", max_err, max_y);
    printf("耗时：FFT 卷积 %.1f ms，直接卷积 %.1f ms\n",
           1000.0 * (t1 - t0) / CLOCKS_PER_SEC, 1000.0 * (t2 - t1) / CLOCKS_PER_SEC);
    free(x); free(y1); free(y2);
    return 0;
}
