/* 表 2-3  用直方图计算均值与标准差
 *
 * 对应 BASIC 程序：
 *   160-180 直方图清零
 *   220-240 统计 25001 个点的直方图
 *   260-300 公式 2-6 求均值
 *   320-370 公式 2-7 求标准差
 */
#include <stdio.h>
#include <math.h>

#define NUM_POINTS 25001 /* 140 N% = 25001，X%[0] 到 X%[25000] */
#define NUM_LEVELS 256   /* 150 DIM H%[255]，8 比特信号 */

static int x[NUM_POINTS];
static int h[NUM_LEVELS];

/* 200 GOSUB XXXX：载入整数信号，这里用 0 到 255 均匀分布的测试数据 */
static void load_signal(void)
{
    unsigned int seed = 54321u;
    for (int i = 0; i < NUM_POINTS; i++) {
        seed = seed * 1664525u + 1013904223u;
        x[i] = (int)((seed >> 8) % NUM_LEVELS);
    }
}

int main(void)
{
    /* 160-180：把直方图清零，以便用作累加器 */
    for (int i = 0; i < NUM_LEVELS; i++) {
        h[i] = 0;
    }

    load_signal();

    /* 220-240：计算 25001 个点的直方图 */
    for (int i = 0; i < NUM_POINTS; i++) {
        h[x[i]] = h[x[i]] + 1;
    }

    /* 260-300：用公式 2-6 计算均值 */
    double mean = 0.0;
    for (int i = 0; i < NUM_LEVELS; i++) {
        mean = mean + i * h[i];
    }
    mean = mean / NUM_POINTS;

    /* 320-370：用公式 2-7 计算标准差 */
    double variance = 0.0;
    for (int i = 0; i < NUM_LEVELS; i++) {
        double d = i - mean;
        variance = variance + h[i] * d * d;
    }
    variance = variance / (NUM_POINTS - 1);
    double sd = sqrt(variance);

    /* 390 PRINT MEAN SD */
    printf("表 2-3  均值 = %.6f  标准差 = %.6f\n", mean, sd);
    return 0;
}
