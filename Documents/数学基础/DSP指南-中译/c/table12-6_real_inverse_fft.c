/*
 * 表 12-6：实数信号的逆 FFT（BASIC 原程序的 C 版本）
 *
 * 进入时 REX[]、IMX[] 的 0～N/2 点是实数频谱，返回时 REX[] 是实时域信号，IMX[] 全为 0。
 * 做法：先补出负频率（同表 12-1），把实部和虚部相加，调用正向实数 FFT（表 12-7），
 * 再把结果的实部和虚部相加、除以 N。
 * 原书第 4160 行注释写「表 12-6」，实际调用的第 3000 行是表 12-7。
 *
 * 为什么「实部加虚部」能把正变换变成逆变换：设 H[k] = Re X[k] + Im X[k]，
 * 它的正变换的实部加虚部，恰好等于 N·x[n]（这是哈特利变换(Hartley transform)的性质，原书没有展开）。
 *
 * 测试：N = 8、64、1024 的随机实信号 → 实数 FFT（表 12-7）→ 本程序 → 与原信号比较。
 *
 * 编译运行：cc -O2 -o table12-6_real_inverse_fft table12-6_real_inverse_fft.c -lm && ./table12-6_real_inverse_fft
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define NMAX 1024

static const double PI = 3.14159265358979323846;

/* 1000：复数 FFT（同表 12-4） */
static void fft(double *rex, double *imx, int n)
{
    int nm1 = n - 1, nd2 = n / 2, m = (int)lround(log(n) / log(2)), j = nd2;
    for (int i = 1; i <= n - 2; i++) {
        if (i < j) {
            double tr = rex[j], ti = imx[j];
            rex[j] = rex[i]; imx[j] = imx[i];
            rex[i] = tr;     imx[i] = ti;
        }
        int k = nd2;
        while (k <= j) { j -= k; k /= 2; }
        j += k;
    }
    for (int l = 1; l <= m; l++) {
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

/* 3000：实数 FFT（同表 12-7） */
static void real_fft(double *rex, double *imx, int n)
{
    for (int i = 0; i <= n / 2 - 1; i++) {
        rex[i] = rex[2 * i];
        imx[i] = rex[2 * i + 1];
    }
    fft(rex, imx, n / 2);
    int nm1 = n - 1, nd2 = n / 2;
    for (int i = 1; i <= n / 4 - 1; i++) {
        int im = nd2 - i, ip2 = i + nd2, ipm = im + nd2;
        rex[ip2] = (imx[i] + imx[im]) / 2;
        rex[ipm] = rex[ip2];
        imx[ip2] = -(rex[i] - rex[im]) / 2;
        imx[ipm] = -imx[ip2];
        rex[i] = (rex[i] + rex[im]) / 2;
        rex[im] = rex[i];
        imx[i] = (imx[i] - imx[im]) / 2;
        imx[im] = -imx[i];
    }
    rex[n * 3 / 4] = imx[n / 4];
    rex[nd2] = imx[0];
    imx[n * 3 / 4] = imx[nd2] = imx[n / 4] = imx[0] = 0;
    int le = n, le2 = le / 2;
    double ur = 1.0, ui = 0.0, sr = cos(PI / le2), si = -sin(PI / le2);
    for (int j = 1; j <= le2; j++) {
        for (int i = j - 1; i <= nm1; i += le) {
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

/* 4000：实数逆 FFT */
static void real_inverse_fft(double *rex, double *imx, int n)
{
    for (int k = n / 2 + 1; k <= n - 1; k++) {  /* 4070～4100：让频域对称（同表 12-1） */
        rex[k] = rex[n - k];
        imx[k] = -imx[n - k];
    }

    for (int k = 0; k <= n - 1; k++)            /* 4120～4140：实部和虚部相加 */
        rex[k] = rex[k] + imx[k];

    real_fft(rex, imx, n);                      /* 4160：做正向实数 FFT（原书注释误写为表 12-6，实为表 12-7） */

    for (int i = 0; i <= n - 1; i++) {          /* 4180～4210：实部虚部相加，再除以 N */
        rex[i] = (rex[i] + imx[i]) / n;
        imx[i] = 0;
    }
}

int main(void)
{
    static double x[NMAX], rex[NMAX], imx[NMAX];
    int ns[] = {8, 64, 1024};

    srand(6);
    for (int t = 0; t < 3; t++) {
        int n = ns[t];
        for (int i = 0; i < n; i++) x[i] = rex[i] = rand() / (double)RAND_MAX - 0.5;
        real_fft(rex, imx, n);                  /* 得到频谱 */
        for (int k = n / 2 + 1; k < n; k++)     /* 只把 0～N/2 点交给逆变换，其余点写成垃圾值 */
            rex[k] = imx[k] = 999.0;
        real_inverse_fft(rex, imx, n);
        double err = 0.0;
        for (int i = 0; i < n; i++) err = fmax(err, fabs(rex[i] - x[i]));
        printf("N = %4d：实数 FFT → 实数逆 FFT 与原信号的最大偏差 = %.3g\n", n, err);
    }
    return 0;
}
