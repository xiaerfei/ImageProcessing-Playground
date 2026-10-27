/*
 * 表 16-1：低通加窗 sinc 滤波器（BASIC 原程序的 C 版本）
 *
 * 用 101 点的加窗 sinc 滤波器核（汉明窗，截止频率 0.14）对 5000 个采样滤波，
 * 得到 4900 个有效输出采样。这是正文 EEG 例子：采样率 100 Hz，
 * 截止 14 Hz，把 7～12 Hz 的 α 节律和 17～20 Hz 的 β 节律分开。
 *
 * 原书第 220 行用「虚构的子程序」载入 X[ ]。这里造一段假 EEG：
 * 10 Hz（α）正弦，幅度 1，加 18 Hz（β）正弦，幅度 1。
 * 滤波后应只剩 α：程序测量输出里两个分量各剩多少，
 * 并用直接计算的傅里叶变换检查滤波器核的频率响应。
 *
 * 编译运行：cc -O2 -o table16-1_lowpass_windowed_sinc table16-1_lowpass_windowed_sinc.c -lm && ./table16-1_lowpass_windowed_sinc
 */
#include <math.h>
#include <stdio.h>

#define NX 5000                             /* 140 DIM X[4999]：输入信号 5000 点 */
#define M  100                              /* 200 M% = 100：滤波器核 101 点 */

static const double PI = 3.14159265358979323846;

/* 代替 220 GOSUB XXXX：假 EEG，采样率 100 Hz，α 10 Hz + β 18 Hz */
static void load_signal(double *x)
{
    for (int n = 0; n < NX; n++)
        x[n] = sin(2.0 * PI * 0.10 * n) + sin(2.0 * PI * 0.18 * n);
}

/* 第 240～380 行：按公式 16-4 算低通滤波器核，再归一化到直流增益为 1 */
static void lowpass_kernel(double fc, double *h)
{
    for (int i = 0; i <= M; i++) {          /* 250 */
        if (i - M / 2 == 0) h[i] = 2.0 * PI * fc;                             /* 260：sinc 中心，避免除零 */
        else                h[i] = sin(2.0 * PI * fc * (i - M / 2)) / (i - M / 2); /* 270 */
        h[i] *= 0.54 - 0.46 * cos(2.0 * PI * i / M);                          /* 280：乘汉明窗（公式 16-1） */
    }

    double sum = 0.0;                       /* 310～340：求和 */
    for (int i = 0; i <= M; i++) sum += h[i];
    for (int i = 0; i <= M; i++) h[i] /= sum;   /* 360～380：归一化，直流增益为 1 */
}

/* 第 400～450 行：卷积，只算滤波器核完全浸没在输入里的输出点 */
static void convolve(const double *x, const double *h, double *y)
{
    for (int j = M; j < NX; j++) {          /* 400：FOR J% = 100 TO 4999 */
        y[j] = 0.0;                         /* 410 */
        for (int i = 0; i <= M; i++)        /* 420 */
            y[j] += x[j - i] * h[i];        /* 430 */
    }
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

/* 用相关法测输出里频率 f 的正弦还剩多大幅度 */
static double amplitude_at(const double *y, double f)
{
    double c = 0.0, s = 0.0;
    int n0 = M, n1 = NX;                    /* 只用有效输出点 */
    for (int n = n0; n < n1; n++) {
        c += y[n] * cos(2.0 * PI * f * n);
        s += y[n] * sin(2.0 * PI * f * n);
    }
    return 2.0 * sqrt(c * c + s * s) / (n1 - n0);
}

int main(void)
{
    static double x[NX], y[NX];
    double h[M + 1];
    load_signal(x);
    lowpass_kernel(0.14, h);                /* 190 FC = .14 */
    convolve(x, h, y);

    double sum = 0.0;
    for (int i = 0; i <= M; i++) sum += h[i];
    printf("滤波器核 101 点，系数和（直流增益）= %.12f\n", sum);
    printf("对称性：h[0]-h[100] = %.2e，h[49]-h[51] = %.2e\n", h[0] - h[M], h[49] - h[51]);

    printf("\n频率响应 |H(f)|：\n");
    const double fs[] = { 0.0, 0.10, 0.12, 0.14, 0.16, 0.18, 0.25, 0.40 };
    for (int k = 0; k < 8; k++) {
        double a = response(h, fs[k]);
        printf("  f = %.2f（%4.0f Hz）  %.6f  （%7.1f dB）\n", fs[k], fs[k] * 100, a, 20.0 * log10(a));
    }

    double worst = 0.0;                     /* 阻带最大残留：从 0.16+0.02 起 */
    for (double f = 0.18; f <= 0.5; f += 0.0005) {
        double a = response(h, f);
        if (a > worst) worst = a;
    }
    printf("  阻带（f ≥ 0.18）最大残留 = %.5f（%.1f dB）\n", worst, 20.0 * log10(worst));

    printf("\n滤波后（第 100～4999 点）各分量剩下的幅度（输入都是 1）：\n");
    printf("  α 10 Hz：%.6f\n", amplitude_at(y, 0.10));
    printf("  β 18 Hz：%.6f\n", amplitude_at(y, 0.18));
    return 0;
}
