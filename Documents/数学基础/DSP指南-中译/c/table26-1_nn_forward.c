/*
 * 表 26-1：神经网络前向计算（图 26-5 流程图的 C 版本）
 *
 * 三层全连接网络：15 个输入节点（被动）→ 4 个隐藏节点 → 2 个输出节点（主动）。
 * 每个主动节点把输入加权求和，再送进 sigmoid：s(x) = 1/(1+e^-x)（公式 26-1）。
 *
 * 原书第 180、190 行用「虚构的子程序」载入输入数据和权重。这里做三组可以手算核对的测试：
 *   1. 权重全为 0：每个隐藏节点的和都是 0，s(0) = 0.5；输出节点的和是 4×0.5×0 = 0，也是 0.5。
 *   2. 只让输出节点 1 的权重全为 1、其余为 0：输出 1 = s(4×0.5) = s(2) ≈ 0.880797。
 *   3. 随机输入和权重：和逐元素手写的矩阵乘法结果比对。
 *
 * 编译运行：cc -O2 -o table26-1_nn_forward table26-1_nn_forward.c -lm && ./table26-1_nn_forward
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define NI 15                               /* 120 DIM X1[15]：输入层 15 个节点 */
#define NH 4                                /* 130 DIM X2[4]：隐藏层 4 个节点 */
#define NO 2                                /* 140 DIM X3[2]：输出层 2 个节点 */

/* 公式 26-1：sigmoid 函数 */
static double sigmoid(double x) { return 1.0 / (1.0 + exp(-x)); }

/* 第 210～370 行：输入 x1 经过隐藏层得到 x2，再经过输出层得到 x3 */
static void forward(const double x1[NI], double wh[NH][NI], double wo[NO][NH],
                    double x2[NH], double x3[NO])
{
    for (int j = 0; j < NH; j++) {          /* 220：遍历每个隐藏节点 */
        double acc = 0.0;                   /* 230：累加器清零 */
        for (int i = 0; i < NI; i++)        /* 240：把每个输入节点加权求和 */
            acc += x1[i] * wh[j][i];        /* 250 */
        x2[j] = sigmoid(acc);               /* 270：求和结果送进 sigmoid */
    }
    for (int j = 0; j < NO; j++) {          /* 310：遍历每个输出节点 */
        double acc = 0.0;                   /* 320 */
        for (int i = 0; i < NH; i++)        /* 330：把每个隐藏节点加权求和 */
            acc += x2[i] * wo[j][i];        /* 340 */
        x3[j] = sigmoid(acc);               /* 360 */
    }
}

int main(void)
{
    double x1[NI], wh[NH][NI], wo[NO][NH], x2[NH], x3[NO];

    /* 测试 1：权重全为 0 */
    for (int i = 0; i < NI; i++) x1[i] = i + 1.0;
    for (int j = 0; j < NH; j++) for (int i = 0; i < NI; i++) wh[j][i] = 0.0;
    for (int j = 0; j < NO; j++) for (int i = 0; i < NH; i++) wo[j][i] = 0.0;
    forward(x1, wh, wo, x2, x3);
    printf("测试 1（权重全 0）：X3 = %.6f %.6f（应为 0.5 0.5）\n", x3[0], x3[1]);

    /* 测试 2：输出节点 1 的权重全为 1 */
    for (int i = 0; i < NH; i++) wo[0][i] = 1.0;
    forward(x1, wh, wo, x2, x3);
    printf("测试 2：X3[1] = %.6f（应为 s(2) = %.6f），X3[2] = %.6f\n", x3[0], sigmoid(2.0), x3[1]);

    /* 测试 3：随机输入和权重，与另写的一遍计算比对 */
    srand(1);
    for (int i = 0; i < NI; i++) x1[i] = rand() / (double)RAND_MAX;
    for (int j = 0; j < NH; j++) for (int i = 0; i < NI; i++) wh[j][i] = rand() / (double)RAND_MAX - 0.5;
    for (int j = 0; j < NO; j++) for (int i = 0; i < NH; i++) wo[j][i] = 2.0 * rand() / RAND_MAX - 1.0;
    forward(x1, wh, wo, x2, x3);
    double maxd = 0.0;
    for (int j = 0; j < NO; j++) {
        double s = 0.0;
        for (int h = 0; h < NH; h++) {
            double t = 0.0;
            for (int i = 0; i < NI; i++) t += wh[h][i] * x1[i];
            s += wo[j][h] / (1.0 + exp(-t));
        }
        double d = fabs(x3[j] - 1.0 / (1.0 + exp(-s)));
        if (d > maxd) maxd = d;
    }
    printf("测试 3（随机）：X3 = %.6f %.6f，与另一遍计算的最大差 = %.3g\n", x3[0], x3[1], maxd);
    return 0;
}
