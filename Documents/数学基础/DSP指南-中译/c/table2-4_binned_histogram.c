/* 表 2-4  计算分箱直方图（binned histogram）
 *
 * 对应 BASIC 程序：
 *   160-180 分箱直方图清零
 *   220-250 计算 25001 个点的分箱直方图
 *
 * 原文 230 行写作 BINNUM% = INT( X[I%] * .01 )，按正文“每箱宽 0.01”
 * 的设定应为乘以 100（即除以 0.01）。这里采用译注修正后的写法。
 * 另外采样值 10.0 会算出箱号 1000，越过最后一个箱，故做上限保护。
 */
#include <stdio.h>

#define NUM_POINTS 25001 /* X[0] 到 X[25000] */
#define NUM_BINS 1000    /* H%[0] 到 H%[999] */

static double x[NUM_POINTS];
static int h[NUM_BINS];

/* 200 GOSUB XXXX：载入 0.0 到 10.0 的浮点测试信号 */
static void load_signal(void)
{
    unsigned int seed = 98765u;
    for (int i = 0; i < NUM_POINTS; i++) {
        seed = seed * 1664525u + 1013904223u;
        x[i] = 10.0 * ((seed >> 8) & 0xFFFF) / 65536.0;
    }
}

int main(void)
{
    /* 160-180：把分箱直方图清零，以便用作累加器 */
    for (int i = 0; i < NUM_BINS; i++) {
        h[i] = 0;
    }

    load_signal();

    /* 220-250：计算 25001 个点的分箱直方图 */
    for (int i = 0; i < NUM_POINTS; i++) {
        /* 230 BINNUM% = INT( X[I%] * 100 ) */
        int binnum = (int)(x[i] * 100.0);
        if (binnum < 0) binnum = 0;
        if (binnum > NUM_BINS - 1) binnum = NUM_BINS - 1;
        /* 240 累加该箱的计数 */
        h[binnum] = h[binnum] + 1;
    }

    /* 打印几个箱的计数，验证分箱结果 */
    printf("表 2-4  分箱直方图（每箱宽 0.01，共 %d 箱）\n", NUM_BINS);
    for (int bin = 0; bin < NUM_BINS; bin += 100) {
        printf("  箱 %3d [%.2f, %.2f) : %d\n",
               bin, bin / 100.0, (bin + 1) / 100.0, h[bin]);
    }
    return 0;
}
