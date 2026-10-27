/*
 * 表 17-1：自定义滤波器设计（BASIC 原程序的 C 版本）
 *
 * 原书程序只做中间一步：把 1024 点的"混叠冲激响应"（图 17-1b）平移 M/2 点、
 * 截断到 M+1 点、乘汉明窗，得到滤波器核（图 17-1c）。第 200 行用虚构的子程序载入信号。
 * 这里把前后两步也补上，完整走一遍图 17-1 的流程：
 *   1. 按图 17-1a 的形状定义 513 点期望频率响应，相位全为零；
 *   2. 逆 DFT 得到 1024 点混叠冲激响应（原书用逆 FFT，这里为了自包含直接按定义算，结果相同）；
 *   3. 表 17-1：平移、截断、加窗；
 *   4. 补零到 1024 点后做 DFT，得到实际频率响应，和期望值比较。
 * 对 M = 10、30、40、100、300、1000 各做一遍，误差应随 M 增大而减小（对应图 17-2）。
 * 最后演示 17.1 节末尾的论点：直接拿混叠冲激响应当滤波器核，在设计点上分毫不差，
 * 设计点之间却剧烈起伏；加窗之后，设计点之间变得平滑。
 *
 * 编译运行：cc -O2 -o table17-1_custom_filter table17-1_custom_filter.c -lm && ./table17-1_custom_filter
 */
#include <math.h>
#include <stdio.h>

#define N 1024                              /* 时域点数 */
#define NF (N / 2 + 1)                      /* 频域点数：513，覆盖 0～0.5 */

static const double PI = 3.14159265358979323846;

/* 第 1 步：图 17-1a 的期望幅度响应（形状照图估计，参数是我选的） */
static double desired(double f)
{
    if (f < 0.1)   return 0.5 + 0.3 * sin(2.0 * PI * f / 0.05);   /* 0～0.1：两个起伏 */
    if (f < 0.195) return 0.5 + 2.0 * (f - 0.1) / 0.095;           /* 0.1～0.195：从 0.5 斜升到 2.5 */
    if (f < 0.27)  return 1.0;                                     /* 0.195～0.27：平台 1 */
    if (f < 0.29)  return 0.0;                                     /* 0.27～0.29：窄的阻带 */
    if (f < 0.39)  return 1.0;                                     /* 0.29～0.39：平台 1 */
    return exp(-(f - 0.39) / 0.05);                                /* 0.39～0.5：指数下降 */
}

/* 第 2 步：零相位频谱的逆 DFT。相位为零时只有余弦项，结果左右对称（混叠在两端） */
static void inverse_dft_zero_phase(const double *mag, double *x)
{
    for (int n = 0; n < N; n++) {
        double s = mag[0] + mag[NF - 1] * cos(PI * n);      /* 第 0 点和第 N/2 点只算一次 */
        for (int k = 1; k < NF - 1; k++)
            s += 2.0 * mag[k] * cos(2.0 * PI * k * n / N);
        x[n] = s / N;
    }
}

/* 第 3 步：表 17-1 本体 */
static void custom_filter_kernel(double *rex, int m)
{
    double t[N];                            /* 150 DIM T[1023]：临时缓冲区 */

    for (int i = 0; i < N; i++) {           /* 220～260：把信号循环右移 M/2 点 */
        int index = i + m / 2;              /* 230 */
        if (index > N - 1) index -= N;      /* 240：超出末尾的绕回开头 */
        t[index] = rex[i];                  /* 250 */
    }
    for (int i = 0; i < N; i++)             /* 280～300：拷回 REX[ ] */
        rex[i] = t[i];

    for (int i = 0; i < N; i++) {           /* 320～350：截断并加窗 */
        if (i <= m) rex[i] *= 0.54 - 0.46 * cos(2.0 * PI * i / m);  /* 330：汉明窗 */
        else        rex[i] = 0.0;           /* 340：M 之后的点全部置零 */
    }
}                                           /* 360：滤波器核现在位于 REX[0]～REX[M] */

/* 第 4 步：在任意频率 f 处求滤波器核 h[0..len-1] 的幅度响应 */
static double response_at(const double *h, int len, double f)
{
    double re = 0.0, im = 0.0;
    for (int n = 0; n < len; n++) {
        re += h[n] * cos(2.0 * PI * f * n);
        im -= h[n] * sin(2.0 * PI * f * n);
    }
    return sqrt(re * re + im * im);
}

int main(void)
{
    double mag[NF], rex[N];
    for (int k = 0; k < NF; k++) mag[k] = desired((double)k / N);

    printf("M      设计点上 |实际-期望| 的均方根   最大偏差\n");
    const int ms[] = {10, 30, 40, 100, 300, 1000};
    for (int t = 0; t < 6; t++) {
        int m = ms[t];
        inverse_dft_zero_phase(mag, rex);   /* 图 17-1b */
        custom_filter_kernel(rex, m);       /* 图 17-1c */
        double se = 0.0, emax = 0.0;
        for (int k = 0; k < NF; k++) {      /* 图 17-1d：补零后的 1024 点 DFT，就是在 k/1024 处取值 */
            double e = fabs(response_at(rex, m + 1, (double)k / N) - mag[k]);
            se += e * e;
            if (e > emax) emax = e;
        }
        printf("%-5d  %.4f                         %.4f\n", m, sqrt(se / NF), emax);
    }

    /* "好"与"坏"的频率响应：比较设计点上和相邻设计点正中间的响应 */
    double raw[N], win[N];
    inverse_dft_zero_phase(mag, raw);       /* 直接拿混叠冲激响应当核（1024 点） */
    inverse_dft_zero_phase(mag, win);
    custom_filter_kernel(win, 1000);        /* 按表 17-1 加窗，M = 1000 */
    double on_raw = 0.0, mid_raw = 0.0, mid_win = 0.0;
    for (int k = 0; k < NF - 1; k++) {
        double ref = 0.5 * (mag[k] + mag[k + 1]);           /* 中点处的"平滑"参考值 */
        double e0 = fabs(response_at(raw, N, (double)k / N) - mag[k]);
        double e1 = fabs(response_at(raw, N, (k + 0.5) / N) - ref);
        double e2 = fabs(response_at(win, 1001, (k + 0.5) / N) - ref);
        if (e0 > on_raw)  on_raw = e0;
        if (e1 > mid_raw) mid_raw = e1;
        if (e2 > mid_win) mid_win = e2;
    }
    printf("\n直接用 1024 点混叠冲激响应：设计点上最大偏差 %.2g，设计点之间最大偏差 %.3f\n", on_raw, mid_raw);
    printf("加窗后的 M = 1000 滤波器核：设计点之间最大偏差 %.3f\n", mid_win);
    return 0;
}
