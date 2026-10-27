/*
 * 表 12-4：BASIC 版 FFT（按时间抽取，decimation in time）的 C 版本
 *
 * 结构对应图 12-7：先位反转排序（时域分解），再用三重循环逐级合成频谱
 * （外层遍历 log2 N 级，中层遍历每个子 DFT，内层遍历每个蝶形）。
 * REX[]、IMX[] 进为时域、出为频域，下标 0～N-1，原地计算(in-place computation)。
 *
 * 测试：
 *   测试 1：16 点信号 x[i] = i，打印位反转排序后的顺序，与图 12-3 对照
 *   测试 2：N = 16、256、4096 的随机复信号，与相关法复数 DFT（表 12-2）逐点比较，并比较耗时
 *
 * 编译运行：cc -O2 -o table12-4_fft table12-4_fft.c -lm && ./table12-4_fft
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define NMAX 4096

static const double PI = 3.14159265358979323846;

/* 1110～1250：位反转排序 */
static void bit_reversal_sort(double *rex, double *imx, int n)
{
    int nd2 = n / 2, j = nd2;                   /* 1070、1090：ND2% = N%/2，J% = ND2% */
    for (int i = 1; i <= n - 2; i++) {          /* 1110：第 0 点和第 N-1 点不用动 */
        if (i < j) {                            /* 1120：I% >= J% 时跳过，保证每对只交换一次 */
            double tr = rex[j], ti = imx[j];    /* 1130～1180：交换第 I、J 点 */
            rex[j] = rex[i];
            imx[j] = imx[i];
            rex[i] = tr;
            imx[i] = ti;
        }
        int k = nd2;                            /* 1190 */
        while (k <= j) {                        /* 1200：K% > J% 时跳出 */
            j -= k;                             /* 1210 */
            k /= 2;                             /* 1220～1230 */
        }
        j += k;                                 /* 1240：J 是 I+1 的位反转值 */
    }
}

/* 1000：FFT */
static void fft(double *rex, double *imx, int n)
{
    int nm1 = n - 1;                            /* 1060 */
    int m = (int)lround(log(n) / log(2));       /* 1080：M% = log2 N，级数 */

    bit_reversal_sort(rex, imx, n);

    for (int l = 1; l <= m; l++) {              /* 1270：遍历每一级 */
        int le = 1 << l;                        /* 1280：本级合成后每个频谱的点数 */
        int le2 = le / 2;                       /* 1290 */
        double ur = 1.0, ui = 0.0;              /* 1300～1310：正弦因子 U 从 1 开始 */
        double sr = cos(PI / le2);              /* 1320～1330：每步把 U 转过的角度 */
        double si = -sin(PI / le2);
        for (int j = 1; j <= le2; j++) {        /* 1340：遍历每个子 DFT 中的点位 */
            int jm1 = j - 1;                    /* 1350 */
            for (int i = jm1; i <= nm1; i += le) {      /* 1360：遍历每个蝶形 */
                int ip = i + le2;                       /* 1370 */
                double tr = rex[ip] * ur - imx[ip] * ui;    /* 1380～1390：下面那个点乘正弦（图 12-6 的 ×S） */
                double ti = rex[ip] * ui + imx[ip] * ur;
                rex[ip] = rex[i] - tr;                  /* 1400～1410：蝶形的减法分支 */
                imx[ip] = imx[i] - ti;
                rex[i] = rex[i] + tr;                   /* 1420～1430：蝶形的加法分支 */
                imx[i] = imx[i] + ti;
            }
            double tr = ur;                     /* 1450～1470：U 乘以 S，转到下一个角度 */
            ur = tr * sr - ui * si;
            ui = tr * si + ui * sr;
        }
    }
}

/* 相关法复数 DFT（表 12-2），作为对照 */
static void complex_dft(const double *xr, const double *xi, int n, double *rex, double *imx)
{
    for (int k = 0; k < n; k++) {
        rex[k] = imx[k] = 0.0;
        for (int i = 0; i < n; i++) {
            double sr = cos(2.0 * PI * k * i / n), si = -sin(2.0 * PI * k * i / n);
            rex[k] += xr[i] * sr - xi[i] * si;
            imx[k] += xr[i] * si + xi[i] * sr;
        }
    }
}

int main(void)
{
    static double xr[NMAX], xi[NMAX], rex[NMAX], imx[NMAX], refr[NMAX], refi[NMAX];

    /* 测试 1：位反转顺序 */
    for (int i = 0; i < 16; i++) { rex[i] = i; imx[i] = 0.0; }
    bit_reversal_sort(rex, imx, 16);
    printf("测试 1：16 点位反转排序后的顺序：");
    for (int i = 0; i < 16; i++) printf("%d ", (int)rex[i]);
    printf("\n");

    /* 测试 2：与相关法比较 */
    int ns[] = {16, 256, 4096};
    srand(4);
    for (int t = 0; t < 3; t++) {
        int n = ns[t];
        for (int i = 0; i < n; i++) {
            xr[i] = rex[i] = rand() / (double)RAND_MAX - 0.5;
            xi[i] = imx[i] = rand() / (double)RAND_MAX - 0.5;
        }
        clock_t c0 = clock();
        fft(rex, imx, n);
        clock_t c1 = clock();
        complex_dft(xr, xi, n, refr, refi);
        clock_t c2 = clock();
        double err = 0.0;
        for (int k = 0; k < n; k++) err = fmax(err, fmax(fabs(rex[k] - refr[k]), fabs(imx[k] - refi[k])));
        printf("测试 2：N = %4d，FFT 与相关法 DFT 最大偏差 = %.3g，耗时 FFT %.3f ms / 相关法 %.3f ms\n",
               n, err, 1000.0 * (c1 - c0) / CLOCKS_PER_SEC, 1000.0 * (c2 - c1) / CLOCKS_PER_SEC);
    }
    return 0;
}
