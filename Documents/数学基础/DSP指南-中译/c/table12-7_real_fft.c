/*
 * 表 12-7：实数信号的 FFT（BASIC 原程序的 C 版本）
 *
 * 思路（原书第 241 页）：N 点实信号按奇偶交错拆开，偶数点放进实部、奇数点放进虚部，
 * 只做一次 N/2 点的复数 FFT；再用偶/奇分解把两个交错信号的频谱分开；
 * 最后像 FFT 的最后一级那样，把两个 N/2 点频谱合成 N 点频谱。
 * 原书第 3120 行注释写「GOSUB 1000 是表 12-3 的 FFT」，实为表 12-4。
 *
 * 测试：N = 8、64、1024 的随机实信号，与普通复数 FFT（表 12-4，虚部填 0）的输出逐点比较，并比较耗时。
 *
 * 编译运行：cc -O2 -o table12-7_real_fft table12-7_real_fft.c -lm && ./table12-7_real_fft
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define NMAX 1024

static const double PI = 3.14159265358979323846;

/* 1000：复数 FFT（同表 12-4） */
static void fft(double *rex, double *imx, int n)
{
    int nm1 = n - 1, nd2 = n / 2, m = (int)lround(log(n) / log(2)), j = nd2;
    for (int i = 1; i <= n - 2; i++) {          /* 1110～1250：位反转排序 */
        if (i < j) {
            double tr = rex[j], ti = imx[j];
            rex[j] = rex[i]; imx[j] = imx[i];
            rex[i] = tr;     imx[i] = ti;
        }
        int k = nd2;
        while (k <= j) { j -= k; k /= 2; }
        j += k;
    }
    for (int l = 1; l <= m; l++) {              /* 1270～1490：逐级合成 */
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

/* 3000：实数 FFT。进入时 rex[] 是实信号（imx[] 内容忽略），返回时 rex/imx 是 0～n-1 的完整频谱 */
static void real_fft(double *rex, double *imx, int n)
{
    int nh = n / 2 - 1;                         /* 3050：拆开偶数点和奇数点 */
    for (int i = 0; i <= nh; i++) {             /* 3060～3090：偶数点进实部，奇数点进虚部 */
        rex[i] = rex[2 * i];                    /* 从小下标往上写，不会覆盖还没读的点 */
        imx[i] = rex[2 * i + 1];
    }

    fft(rex, imx, n / 2);                       /* 3110～3130：做 N/2 点 FFT */

    int nm1 = n - 1, nd2 = n / 2, n4 = n / 4 - 1;   /* 3150～3170：频域的偶/奇分解 */
    for (int i = 1; i <= n4; i++) {             /* 3180：每次处理一对对称点 I 和 N/2-I */
        int im = nd2 - i;                       /* 3190 */
        int ip2 = i + nd2;                      /* 3200 */
        int ipm = im + nd2;                     /* 3210 */
        rex[ip2] = (imx[i] + imx[im]) / 2;      /* 3220～3250：奇数点信号的频谱，放在后半段 */
        rex[ipm] = rex[ip2];
        imx[ip2] = -(rex[i] - rex[im]) / 2;
        imx[ipm] = -imx[ip2];
        rex[i] = (rex[i] + rex[im]) / 2;        /* 3260～3290：偶数点信号的频谱，留在前半段 */
        rex[im] = rex[i];
        imx[i] = (imx[i] - imx[im]) / 2;
        imx[im] = -imx[i];
    }
    rex[n * 3 / 4] = imx[n / 4];                /* 3310～3360：自身对称的 0 和 N/4 两点单独处理 */
    rex[nd2] = imx[0];
    imx[n * 3 / 4] = 0;
    imx[nd2] = 0;
    imx[n / 4] = 0;
    imx[0] = 0;

    int l = (int)lround(log(n) / log(2));       /* 3380～3600：补做 FFT 的最后一级 */
    int le = 1 << l;                            /* 3400：最后一级 LE = N */
    int le2 = le / 2;
    double ur = 1.0, ui = 0.0, sr = cos(PI / le2), si = -sin(PI / le2);
    for (int j = 1; j <= le2; j++) {            /* 3460 */
        int jm1 = j - 1;
        for (int i = jm1; i <= nm1; i += le) {  /* 3480：最后一级每个 J 只有一个蝶形 */
            int ip = i + le2;
            double tr = rex[ip] * ur - imx[ip] * ui;    /* 3500～3550：蝶形运算 */
            double ti = rex[ip] * ui + imx[ip] * ur;
            rex[ip] = rex[i] - tr;
            imx[ip] = imx[i] - ti;
            rex[i] = rex[i] + tr;
            imx[i] = imx[i] + ti;
        }
        double tr = ur;                         /* 3570～3590 */
        ur = tr * sr - ui * si;
        ui = tr * si + ui * sr;
    }
}

int main(void)
{
    static double ar[NMAX], ai[NMAX], br[NMAX], bi[NMAX];
    int ns[] = {8, 64, 1024};

    srand(7);
    for (int t = 0; t < 3; t++) {
        int n = ns[t];
        for (int i = 0; i < n; i++) {
            ar[i] = br[i] = rand() / (double)RAND_MAX - 0.5;
            ai[i] = 0.0;
            bi[i] = 12345.0;                    /* 实数 FFT 应忽略进入时 IMX[] 里的内容 */
        }
        fft(ar, ai, n);
        real_fft(br, bi, n);
        double err = 0.0;
        for (int k = 0; k < n; k++) err = fmax(err, fmax(fabs(ar[k] - br[k]), fabs(ai[k] - bi[k])));
        printf("N = %4d：实数 FFT 与复数 FFT 的最大偏差 = %.3g\n", n, err);
    }

    /* 粗测速度：同一个 1024 点信号各算 20000 次 */
    int n = 1024, reps = 20000;
    clock_t c0 = clock();
    for (int r = 0; r < reps; r++) {
        for (int i = 0; i < n; i++) { ar[i] = (i % 17) * 0.1; ai[i] = 0.0; }
        fft(ar, ai, n);
    }
    clock_t c1 = clock();
    for (int r = 0; r < reps; r++) {
        for (int i = 0; i < n; i++) br[i] = (i % 17) * 0.1;
        real_fft(br, bi, n);
    }
    clock_t c2 = clock();
    printf("1024 点各算 %d 次：复数 FFT %.0f ms，实数 FFT %.0f ms\n",
           reps, 1000.0 * (c1 - c0) / CLOCKS_PER_SEC, 1000.0 * (c2 - c1) / CLOCKS_PER_SEC);
    return 0;
}
