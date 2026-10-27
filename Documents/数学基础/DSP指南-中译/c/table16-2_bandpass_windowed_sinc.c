/*
 * 表 16-2：带通加窗 sinc 滤波器（BASIC 原程序的 C 版本）
 *
 * 算一个 801 点的带通滤波器核（布莱克曼窗），用于正文第二个例子：
 * 采样率 10 kHz，只留下以 2 kHz 为中心、宽 80 Hz 的频带（0.196～0.204）。
 * 做法是：两个低通（截止 0.196 和 0.204）→ 把后者频谱反转成高通
 * → 两者相加得到带阻 → 再频谱反转一次得到带通。
 *
 * 程序最后直接计算滤波器核的频率响应，检查通带中心、两个截止点和阻带。
 *
 * 编译运行：cc -O2 -o table16-2_bandpass_windowed_sinc table16-2_bandpass_windowed_sinc.c -lm && ./table16-2_bandpass_windowed_sinc
 */
#include <math.h>
#include <stdio.h>

#define M 800                               /* 180 M% = 800：滤波器核 801 点 */

static const double PI = 3.14159265358979323846;

/* 第 200～350 行（以及 360～510 行）：按公式 16-4 算低通核（布莱克曼窗），归一化到直流增益为 1 */
static void lowpass_kernel(double fc, double *a)
{
    for (int i = 0; i <= M; i++) {          /* 220 */
        if (i - M / 2 == 0) a[i] = 2.0 * PI * fc;                             /* 230 */
        else                a[i] = sin(2.0 * PI * fc * (i - M / 2)) / (i - M / 2); /* 240 */
        a[i] *= 0.42 - 0.5 * cos(2.0 * PI * i / M) + 0.08 * cos(4.0 * PI * i / M); /* 250：布莱克曼窗（公式 16-2） */
    }
    double sum = 0.0;                       /* 280～310 */
    for (int i = 0; i <= M; i++) sum += a[i];
    for (int i = 0; i <= M; i++) a[i] /= sum;   /* 330～350 */
}

/* 频谱反转：所有采样取反，再在对称中心加 1（低通 ↔ 高通，带阻 ↔ 带通） */
static void spectral_inversion(double *h)
{
    for (int i = 0; i <= M; i++) h[i] = -h[i];
    h[M / 2] += 1.0;
}

/* 直接计算频率 f 处的频率响应幅度 |H(f)| */
static double response(const double *h, double f)
{
    double re = 0.0, im = 0.0;
    for (int i = 0; i <= M; i++) {
        re += h[i] * cos(2.0 * PI * f * i);
        im -= h[i] * sin(2.0 * PI * f * i);
    }
    return sqrt(re * re + im * im);
}

int main(void)
{
    double a[M + 1], b[M + 1], h[M + 1];    /* 130～150 DIM A[800]、B[800]、H[800] */

    lowpass_kernel(0.196, a);               /* 210：第一个低通，截止 0.196，存在 A[ ] */
    lowpass_kernel(0.204, b);               /* 370：第二个低通，截止 0.204，存在 B[ ] */
    spectral_inversion(b);                  /* 530～560：B[ ] 反转成高通 */
    for (int i = 0; i <= M; i++)            /* 590～610：低通 + 高通 = 带阻，存在 H[ ] */
        h[i] = a[i] + b[i];
    spectral_inversion(h);                  /* 630～660：带阻反转成带通 */

    printf("带通滤波器核 801 点，频率响应 |H(f)|（采样率 10 kHz）：\n");
    const double fs[] = { 0.0, 0.180, 0.190, 0.1935, 0.196, 0.200, 0.204, 0.2065, 0.210, 0.220, 0.400 };
    for (int k = 0; k < 11; k++) {
        double v = response(h, fs[k]);
        printf("  f = %.4f（%6.0f Hz）  %.6f  （%7.1f dB）\n", fs[k], fs[k] * 10000, v, 20.0 * log10(v + 1e-300));
    }

    double worst = 0.0;                     /* 阻带最大残留：离截止点超过 0.005（50 Hz）以外 */
    for (double f = 0.0; f <= 0.5; f += 0.00005) {
        if (f > 0.191 && f < 0.209) continue;
        double v = response(h, f);
        if (v > worst) worst = v;
    }
    printf("  阻带（f ≤ 0.191 或 f ≥ 0.209）最大残留 = %.2e（%.1f dB）\n", worst, 20.0 * log10(worst));
    return 0;
}
