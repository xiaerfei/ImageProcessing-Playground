/*
 * 表 4-1：浮点误差的累积（BASIC 原程序的 C 版本）
 *
 * 循环里给 X 加上两个随机数再减回去，理想情况下 X 永远是 1。
 * 原书 BASIC 的浮点变量是单精度，所以这里 X、A、B 都用 float；
 * 换成 double，漂移会小到看不出来。
 *
 * 和原书结果的差别：现代 CPU 按 IEEE 754 默认「就近舍入」，
 * 每次舍入的误差有正有负、大体抵消，所以默认运行只会看到随机误差。
 * 原书图 4-4 那条笔直的「累加误差」，是每次舍入都偏向同一边造成的。
 * 加上 trunc 参数把舍入模式改成「向零截断」，就能复现这种累加误差。
 *
 * 用法：
 *   ./table4-1_float_error             就近舍入（现代默认），A、B 为 0～1 的均匀随机数
 *   ./table4-1_float_error trunc       向零截断舍入，复现图 4-4 的累加误差直线
 *   ./table4-1_float_error exp         A、B 改为 EXP(RND)，即原书生成「随机误差」曲线的做法
 *   ./table4-1_float_error trunc exp   两者同时
 *
 * 编译运行：cc -O2 -frounding-math -o table4-1_float_error table4-1_float_error.c -lm && ./table4-1_float_error trunc
 */
#include <fenv.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static float rnd(void) { return (float)(rand() / ((double)RAND_MAX + 1.0)); }

static int has_arg(int argc, char **argv, const char *s)
{
    for (int i = 1; i < argc; i++)
        if (strcmp(argv[i], s) == 0) return 1;
    return 0;
}

int main(int argc, char **argv)
{
    int use_exp = has_arg(argc, argv, "exp");
    int arith_mode = has_arg(argc, argv, "trunc") ? FE_TOWARDZERO : FE_TONEAREST;

    /* volatile：每步运算都老老实实写回单精度变量，也不会被优化挪到 fesetround 的另一侧 */
    volatile float x = 1.0f;                /* 100 X = 1 */

    srand(1);
    for (int i = 0; i <= 2000; i++) {       /* 120 FOR I% = 0 TO 2000 */
        fesetround(FE_TONEAREST);           /* 生成随机数时用默认舍入，只让下面的加减受舍入模式影响 */
        volatile float a = rnd();           /* 130～140 */
        volatile float b = rnd();
        if (use_exp) { a = expf(a); b = expf(b); }

        fesetround(arith_mode);
        x = x + a;                          /* 160～170：加上 A 和 B */
        x = x + b;
        x = x - a;                          /* 180～190：再减回去 */
        x = x - b;
        fesetround(FE_TONEAREST);           /* 恢复默认舍入再打印 */

        if (i % 250 == 0)                   /* 原书每次都打印；这里每 250 次打印一次，便于阅读 */
            printf("%4d  X = %.7f\n", i, x);   /* 210 PRINT X，理想值为 1 */
    }
    return 0;
}
