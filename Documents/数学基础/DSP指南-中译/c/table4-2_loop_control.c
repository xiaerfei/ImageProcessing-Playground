/*
 * 表 4-2：用浮点数和整数控制循环的对比（两段 BASIC 原程序的 C 版本）
 *
 * 两段都想打印 0 到 10 之间等间距的 1001 个数。
 * 左边用 float 做循环变量，每次加 0.01，舍入误差会累积，
 * 最后一次本该是 10.00，却因为超过终止值而被跳过。
 * 右边用整数做循环变量，再换算成 X，不会漏掉最后一个值。
 *
 * 为便于对照，只打印每段的前 4 个和后 4 个值，以及实际循环次数。
 *
 * 编译运行：cc -O2 -o table4-2_loop_control table4-2_loop_control.c && ./table4-2_loop_control
 */
#include <stdio.h>

static void show(int k, float x, int count_hint)
{
    if (k < 4 || k >= count_hint - 4) printf("  %.6f\n", x);
    else if (k == 4) printf("  ...\n");
}

int main(void)
{
    /* 左：Floating Point Loop Control（110 FOR X = 0 TO 10 STEP 0.01） */
    int count = 0;
    for (float x = 0.0f; x <= 10.0f; x += 0.01f) count++;   /* 先数一遍有几次，好决定打印哪几行 */
    printf("浮点数控制循环：共执行 %d 次（应为 1001）\n", count);
    int k = 0;
    for (float x = 0.0f; x <= 10.0f; x += 0.01f) show(k++, x, count);

    /* 右：Integer Loop Control（110 FOR I% = 0 TO 1000，120 X = I%/100） */
    printf("整数控制循环：共执行 1001 次\n");
    for (int i = 0; i <= 1000; i++) {
        float x = i / 100.0f;
        show(i, x, 1001);
    }
    return 0;
}
