/* 表 2-1  用两遍法计算均值与标准差
 *
 * 对应 BASIC 程序（行号见注释）：
 *   120 DIM X[511]
 *   130 N% = 512
 *   150 GOSUB XXXX           ' 载入信号（虚构子程序）
 *   170-210 公式 2-1 求均值
 *   230-280 公式 2-2 求标准差
 */
#include <stdio.h>
#include <math.h>

#define N 512 /* 130 N% = 512，X[0] 到 X[511] */

static double x[N];

/* 150 GOSUB XXXX：原书用一个虚构子程序载入信号，
 * 这里改为产生一个可复现的测试信号：正弦 + 均匀噪声 */
static void load_signal(void)
{
    unsigned int seed = 12345u;
    for (int i = 0; i < N; i++) {
        seed = seed * 1664525u + 1013904223u;             /* 线性同余随机数 */
        double noise = ((seed >> 8) & 0xFFFF) / 65535.0;  /* 0 到 1 */
        noise = (noise - 0.5) * 10.0;                     /* -5 到 +5 */
        x[i] = 20.0 * sin(2.0 * 3.14159265358979 * i / 64.0) + noise;
    }
}

int main(void)
{
    load_signal();

    /* 170-210：用公式 2-1 求均值 */
    double mean = 0.0;
    for (int i = 0; i < N; i++) {
        mean = mean + x[i];
    }
    mean = mean / N;

    /* 230-280：用公式 2-2 求标准差 */
    double variance = 0.0;
    for (int i = 0; i < N; i++) {
        double d = x[i] - mean;
        variance = variance + d * d;
    }
    variance = variance / (N - 1);
    double sd = sqrt(variance);

    /* 300 PRINT MEAN SD */
    printf("表 2-1  均值 = %.6f  标准差 = %.6f\n", mean, sd);
    return 0;
}
