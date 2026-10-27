/*
 * 表 6-2：用输出端算法计算卷积（BASIC 原程序的 C 版本）
 *
 * 这是公式 6-1（卷积和）的直接实现：y[i] = Σ h[j]·x[i-j]，j 从 0 到 M-1。
 * 外层循环遍历输出的每个点，每个输出点都能独立算出。
 * x[i-j] 越界时（即卷积机伸到了输入信号外面），原书用 GOTO 跳过这一项，
 * 效果等同于把输入两端补零。
 *
 * 信号和 table6-1_convolve_input_side.c 完全相同，两个程序的输出应逐点相同，
 * 可以这样验证：
 *   ./table6-1_convolve_input_side > a.txt && ./table6-2_convolve_output_side > b.txt && diff a.txt b.txt
 *
 * 编译运行：cc -O2 -o table6-2_convolve_output_side table6-2_convolve_output_side.c -lm && ./table6-2_convolve_output_side
 */
#include <math.h>
#include <stdio.h>

#define NX 81                               /* 120 DIM X[80]：输入信号 81 点 */
#define NH 31                               /* 130 DIM H[30]：冲激响应 31 点 */
#define NY (NX + NH - 1)                    /* 140 DIM Y[110]：输出信号 111 点 */

static const double PI = 3.14159265358979323846;

/* 代替 160 GOSUB XXXX：和表 6-1 的 C 版本生成同样的信号 */
static void load_signals(double *x, double *h)
{
    for (int n = 0; n < NX; n++) {          /* 第 8～72 点：斜坡从 0 升到 2.2，叠加 3 个周期、幅度 1.4 的正弦；两端为 0 */
        x[n] = 0.0;
        if (n < 8 || n > 72) continue;
        double t = (n - 8) / 64.0;
        x[n] = 2.2 * t - 1.4 * sin(2.0 * PI * 3.0 * t);
    }

    double sum = 0.0;
    for (int j = 0; j < NH; j++) {          /* 半个正弦周期的平滑拱形：两端为 0、中间最高 */
        h[j] = sin(PI * j / (NH - 1));
        sum += h[j];
    }
    for (int j = 0; j < NH; j++) h[j] /= sum;   /* 总和为 1：平坦部分（直流）的幅度不变，峰值约 0.05 */
}

/* 输出端算法：公式 6-1 的直接实现，每个输出点独立算出 */
static void convolve_output_side(const double *x, const double *h, double *y)
{
    for (int i = 0; i < NY; i++) {          /* 180：遍历输出的每个点 */
        y[i] = 0.0;                         /* 190：这个输出点的累加器清零 */
        for (int j = 0; j < NH; j++) {      /* 200：遍历冲激响应的每个点 */
            if (i - j < 0) continue;        /* 210～220：x[i-j] 越界的项不存在，跳过 */
            if (i - j > NX - 1) continue;
            y[i] += h[j] * x[i - j];        /* 230：h[j]·x[i-j]，即卷积机里的一次乘加 */
        }
    }
}

int main(void)
{
    double x[NX], h[NH], y[NY];
    load_signals(x, h);
    convolve_output_side(x, h, y);

    /* 代替 270 GOSUB XXXX：把输出存成「序号 值」两列 */
    for (int i = 0; i < NY; i++)
        printf("%3d %.9f\n", i, y[i]);
    return 0;
}
