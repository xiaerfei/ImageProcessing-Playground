/* 表 2-2  用滑动统计（running statistics）计算均值与标准差
 *
 * 对应 BASIC 程序：
 *   160-180 三个累加参数清零：N%、SUM、SUMSQUARES
 *   200-320 逐个采样更新这三个参数，并用公式 2-3 报告均值和标准差
 */
#include <stdio.h>
#include <math.h>

#define N 512

static double x[N];

/* 140 GOSUB XXXX：载入信号，与表 2-1 相同的测试信号 */
static void load_signal(void)
{
    unsigned int seed = 12345u;
    for (int i = 0; i < N; i++) {
        seed = seed * 1664525u + 1013904223u;
        double noise = ((seed >> 8) & 0xFFFF) / 65535.0;
        noise = (noise - 0.5) * 10.0;
        x[i] = 20.0 * sin(2.0 * 3.14159265358979 * i / 64.0) + noise;
    }
}

int main(void)
{
    load_signal();

    /* 160-180：三个滑动参数清零 */
    int n = 0;
    double sum = 0.0;
    double sumsquares = 0.0;

    /* 200 FOR I% = 0 TO 511 */
    for (int i = 0; i < N; i++) {
        /* 220-240：更新三个参数 */
        n = n + 1;
        sum = sum + x[i];
        sumsquares = sumsquares + x[i] * x[i];

        /* 260-280：用公式 2-3 计算均值和标准差
         * 注意：BASIC 原文在 n = 1 时会除以 (n-1) = 0，
         * 这里加一个判断，只有两个及以上采样时才计算。 */
        double mean = sum / n;
        double sd = 0.0;
        if (n > 1) {
            double variance = (sumsquares - sum * sum / n) / (n - 1);
            sd = sqrt(variance);
        }

        /* 300 PRINT MEAN SD */
        if (i == 0 || i == N - 1) {
            printf("表 2-2  第 %d 个采样后：均值 = %.6f  标准差 = %.6f\n",
                   n, mean, sd);
        }
    }
    return 0;
}
