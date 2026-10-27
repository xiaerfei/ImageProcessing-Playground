/*
 * 表 8-4：相位展开（BASIC 原程序的 C 版本）
 *
 * 反正切算出的相位总被折回 −π～π 之间，曲线上会出现跳变（图 8-12 上方的锯齿）。
 * 展开的做法：每一点加上 2π 的整数倍，整数取「让它离前一点最近」的那个。
 *
 * 原书第 170 行用「虚构的子程序」载入相位。这里按图 8-12 的样子生成：
 * 一条从 0 线性降到约 −31.4（即 −10π）的真实相位（相当于延迟 10 个采样点），
 * 把它折回 −π～π 当作输入，展开后应和真实相位一致。
 *
 * 编译运行：cc -O2 -o table8-4_phase_unwrap table8-4_phase_unwrap.c -lm && ./table8-4_phase_unwrap
 */
#include <math.h>
#include <stdio.h>

#define NF 257                              /* 120～130 DIM PHASE[256]、UWPHASE[256] */

static const double PI = 3.14159265358979323846;

int main(void)
{
    double truth[NF], phase[NF], uwphase[NF];

    for (int k = 0; k < NF; k++) {          /* 代替 170 GOSUB XXXX */
        truth[k] = -2 * PI * 10 * k / 512.0;            /* 频率 k/512，延迟 10 点的线性相位 */
        phase[k] = atan2(sin(truth[k]), cos(truth[k])); /* 折回 −π～π，即「卷绕」的相位 */
    }

    uwphase[0] = 0;                         /* 190：所有相位信号的第一点都是 0 */
    for (int k = 1; k < NF; k++) {          /* 220 */
        /* 230：CINT 是四舍五入取整，算出要补几个 2π */
        long c = lround((uwphase[k - 1] - phase[k]) / (2 * PI));
        uwphase[k] = phase[k] + c * 2 * PI; /* 240 */
    }

    double err = 0.0;
    for (int k = 0; k < NF; k++)
        if (fabs(uwphase[k] - truth[k]) > err) err = fabs(uwphase[k] - truth[k]);
    printf("卷绕相位范围：%.4f ～ %.4f\n", -PI, PI);
    printf("展开后最后一点（频率 0.5）= %.4f，真实值 = %.4f\n", uwphase[NF - 1], truth[NF - 1]);
    printf("展开相位与真实相位的最大误差 = %.3g\n", err);
    return 0;
}
