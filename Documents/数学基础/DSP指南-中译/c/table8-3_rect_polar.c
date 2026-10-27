/*
 * 表 8-3：直角坐标与极坐标互相转换（BASIC 原程序的 C 版本）
 *
 * 直角 → 极：公式 8-6，Mag = √(Re² + Im²)，Phase = arctan(Im/Re)，
 *   并按原书处理两个麻烦：实部为 0 时除零（麻烦 2），实部为负时反正切差 π（麻烦 3）。
 * 极 → 直角：公式 8-7，Re = Mag·cos(Phase)，Im = Mag·sin(Phase)。
 *
 * 原书第 190 行用「虚构的子程序」载入数据。这里载入书中讨论过的几个典型点
 * （含 Re=1,Im=1 与 Re=−1,Im=−1、实部为 0 等），再加一批随机点；
 * 把相位与 C 标准库的 atan2() 对照，并检查转过去再转回来能否还原。
 *
 * 编译运行：cc -O2 -o table8-3_rect_polar table8-3_rect_polar.c -lm && ./table8-3_rect_polar
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define NF 257                              /* 120～150 DIM REX[256] 等：频域 257 点 */

static const double PI = 3.14159265358979323846;

/* 直角 → 极坐标（公式 8-6），rex[] 可能被改成 1e-20，与原书一致 */
static void rect_to_polar(double *rex, const double *imx, double *mag, double *phase)
{
    for (int k = 0; k < NF; k++) {          /* 230 */
        mag[k] = sqrt(rex[k] * rex[k] + imx[k] * imx[k]);   /* 240 */
        if (rex[k] == 0) rex[k] = 1e-20;    /* 250：防止除零（麻烦 2） */
        phase[k] = atan(imx[k] / rex[k]);   /* 260 */
        /* 270～290：修正反正切（麻烦 3），实部为负时补 ±π */
        if (rex[k] < 0 && imx[k] < 0)  phase[k] = phase[k] - PI;  /* 280 */
        if (rex[k] < 0 && imx[k] >= 0) phase[k] = phase[k] + PI;  /* 290 */
    }
}

/* 极 → 直角坐标（公式 8-7） */
static void polar_to_rect(const double *mag, const double *phase, double *rex, double *imx)
{
    for (int k = 0; k < NF; k++) {          /* 340 */
        rex[k] = mag[k] * cos(phase[k]);    /* 350 */
        imx[k] = mag[k] * sin(phase[k]);    /* 360 */
    }
}

int main(void)
{
    double rex[NF], imx[NF], mag[NF], phase[NF], re0[NF], im0[NF];
    const double demo[][2] = { {1, 1}, {-1, -1}, {-1, 1}, {0, 2}, {0, -2}, {-3, 0} };
    const int ND = sizeof demo / sizeof demo[0];

    srand(1);
    for (int k = 0; k < NF; k++) {          /* 代替 190 GOSUB XXXX */
        if (k < ND) { rex[k] = demo[k][0]; imx[k] = demo[k][1]; }
        else { rex[k] = (double)rand() / RAND_MAX * 4 - 2; imx[k] = (double)rand() / RAND_MAX * 4 - 2; }
        re0[k] = rex[k];
        im0[k] = imx[k];
    }

    rect_to_polar(rex, imx, mag, phase);
    for (int k = 0; k < ND; k++)
        printf("Re=%5.1f Im=%5.1f → Mag=%.3f Phase=%8.3f°（atan2 给出 %8.3f°）\n",
               re0[k], im0[k], mag[k], phase[k] * 180 / PI, atan2(im0[k], re0[k]) * 180 / PI);

    double dphase = 0.0;
    for (int k = 0; k < NF; k++) {
        double d = fabs(phase[k] - atan2(im0[k], re0[k]));
        if (d > dphase) dphase = d;
    }

    polar_to_rect(mag, phase, rex, imx);
    double err = 0.0;
    for (int k = 0; k < NF; k++) {
        if (fabs(rex[k] - re0[k]) > err) err = fabs(rex[k] - re0[k]);
        if (fabs(imx[k] - im0[k]) > err) err = fabs(imx[k] - im0[k]);
    }
    printf("257 点相位与 atan2() 的最大差 = %.3g 弧度\n", dphase);
    printf("直角 → 极 → 直角 往返的最大误差 = %.3g\n", err);
    return 0;
}
