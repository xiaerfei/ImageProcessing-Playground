/*
 * 表 19-1：递归滤波器（BASIC 原程序的 C 版本）
 *
 * 原书程序只有核心一行：按公式 19-1 用 A0、A1、A2、B1、B2 五个递归系数逐点算输出。
 * 系数和输入由「虚构的子程序」给出，这里换成本章各设计公式（19-2、19-3、19-6、
 * 19-7、19-8），再逐一检查结果是否符合书中描述：
 *   1. 单极点低通（图 19-2）、高通（图 19-3）的阶跃响应
 *   2. 公式 19-4 的时间常数、公式 19-5 的截止频率
 *   3. 公式 19-6 的四级低通系数是否等于四个单极点低通级联
 *   4. 带通（公式 19-7）、带阻（公式 19-8）在中心频率处的增益
 *   5. 双向滤波（图 19-8）得到的输出是否左右对称（零相位）
 *
 * 编译运行：cc -O2 -o table19-1_recursive_filter table19-1_recursive_filter.c -lm && ./table19-1_recursive_filter
 */
#include <math.h>
#include <stdio.h>

#define N 500                               /* 120～130 DIM X[499]、Y[499]：500 点 */

static const double PI = 3.14159265358979323846;

typedef struct { double a0, a1, a2, b1, b2; } Coef;   /* 150 行虚构子程序给出的五个系数 */

/* 原书第 200～220 行：公式 19-1 截到 a2、b2 的递归滤波 */
static void recursive_filter(const Coef *c, const double *x, double *y, int n)
{
    y[0] = c->a0 * x[0];                    /* 原书从第 2 点算起，前两点没定义；这里把 n<0 的项当 0 补上 */
    if (n > 1) y[1] = c->a0 * x[1] + c->a1 * x[0] + c->b1 * y[0];
    for (int i = 2; i < n; i++)             /* 200：FOR I% = 2 TO 499 */
        y[i] = c->a0 * x[i] + c->a1 * x[i - 1] + c->a2 * x[i - 2]
             + c->b1 * y[i - 1] + c->b2 * y[i - 2];   /* 210 */
}

/* 由递归系数直接算频率 f 处的幅度：|Σa·e^{-j2πfk}| / |1 − Σb·e^{-j2πfk}| */
static double gain(const double *a, int na, const double *b, int nb, double f)
{
    double nr = 0, ni = 0, dr = 1, di = 0;
    for (int k = 0; k < na; k++) { nr += a[k] * cos(2 * PI * f * k); ni -= a[k] * sin(2 * PI * f * k); }
    for (int k = 1; k <= nb; k++) { dr -= b[k] * cos(2 * PI * f * k); di += b[k] * sin(2 * PI * f * k); }
    return sqrt((nr * nr + ni * ni) / (dr * dr + di * di));
}

static double gain_c(const Coef *c, double f)
{
    double a[3] = { c->a0, c->a1, c->a2 }, b[3] = { 0, c->b1, c->b2 };
    return gain(a, 3, b, 2, f);
}

/* 公式 19-7、19-8 共用的中间量 R、K */
static void rk(double f, double bw, double *R, double *K)
{
    *R = 1 - 3 * bw;
    *K = (1 - 2 * *R * cos(2 * PI * f) + *R * *R) / (2 - 2 * cos(2 * PI * f));
}

int main(void)
{
    static double x[N], y[N], z[N];

    /* 测试 1：图 19-2 单极点低通，a0 = 0.15、b1 = 0.85，第 10 点起加阶跃 */
    Coef lp = { 0.15, 0, 0, 0.85, 0 };
    for (int i = 0; i < N; i++) x[i] = i >= 10 ? 1.0 : 0.0;
    recursive_filter(&lp, x, y, N);
    printf("测试 1（图 19-2 低通阶跃）：y[10]=%.4f y[20]=%.4f y[40]=%.4f（理论 1−0.85^(n−9)：%.4f %.4f %.4f）\n",
           y[10], y[20], y[40], 1 - pow(0.85, 1), 1 - pow(0.85, 11), 1 - pow(0.85, 31));

    /* 图 19-3 单极点高通：公式 19-3，x = 0.86 */
    double xd = 0.86;
    Coef hp = { (1 + xd) / 2, -(1 + xd) / 2, 0, xd, 0 };
    recursive_filter(&hp, x, y, N);
    printf("        （图 19-3 高通阶跃）：a0=%.2f a1=%.2f；y[10]=%.4f，y[11]/y[10]=%.4f（应等于 x=0.86）\n",
           hp.a0, hp.a1, y[10], y[11] / y[10]);

    /* 测试 2：公式 19-4 时间常数、公式 19-5 截止频率 */
    printf("测试 2：x=0.86 → 时间常数 d = −1/ln x = %.2f 个采样（书上 6.63）\n", -1 / log(0.86));
    for (double fc = 0.01; fc < 0.3; fc *= 5) {
        double xx = exp(-2 * PI * fc);
        Coef c = { 1 - xx, 0, 0, xx, 0 };
        printf("        低通 fc=%.2f：x=%.4f，|H(fc)|=%.4f（−3 dB 应为 0.7071）\n", fc, xx, gain_c(&c, fc));
    }

    /* 测试 3：公式 19-6 四级低通 vs 四个单极点低通级联 */
    double xx = 0.9, a4[1] = { pow(1 - xx, 4) };
    double b4[5] = { 0, 4 * xx, -6 * xx * xx, 4 * xx * xx * xx, -pow(xx, 4) };
    Coef one = { 1 - xx, 0, 0, xx, 0 };
    double maxd = 0;
    for (double f = 0; f <= 0.5; f += 0.005) {
        double d = fabs(gain(a4, 1, b4, 4, f) - pow(gain_c(&one, f), 4));
        if (d > maxd) maxd = d;
    }
    printf("测试 3：公式 19-6 与四个单极点低通级联的频率响应最大差 = %.2g\n", maxd);

    /* 测试 4：带通（公式 19-7）、带阻（公式 19-8），f = 0.2，BW = 0.0066（图 19-6） */
    double f = 0.2, bw = 0.0066, R, K;
    rk(f, bw, &R, &K);
    Coef bp = { 1 - K, 2 * (K - R) * cos(2 * PI * f), R * R - K, 2 * R * cos(2 * PI * f), -R * R };
    Coef br = { K, -2 * K * cos(2 * PI * f), K, 2 * R * cos(2 * PI * f), -R * R };
    printf("测试 4：带通 |H(0.2)|=%.4f，|H(0.2±BW/2)|=%.4f / %.4f，|H(0)|=%.4f\n",
           gain_c(&bp, f), gain_c(&bp, f - bw / 2), gain_c(&bp, f + bw / 2), gain_c(&bp, 0));
    printf("        带阻 |H(0.2)|=%.2g，|H(0)|=%.4f，|H(0.5)|=%.4f\n",
           gain_c(&br, f), gain_c(&br, 0), gain_c(&br, 0.5));

    /* 测试 5：图 19-8 双向滤波。151 点，第 50～100 点为 1 的矩形脉冲 */
    int n = 151;
    Coef lp8 = { 0.1, 0, 0, 0.9, 0 };
    for (int i = 0; i < n; i++) x[i] = (i >= 50 && i <= 100) ? 1.0 : 0.0;
    recursive_filter(&lp8, x, y, n);                         /* 从左往右：图 19-8b */
    for (int i = 0; i < n; i++) z[i] = y[n - 1 - i];         /* 翻转后再滤一次，等于从右往左（公式 19-9） */
    recursive_filter(&lp8, z, x, n);
    for (int i = 0; i < n; i++) z[i] = x[n - 1 - i];         /* 翻回来：图 19-8d */
    double asym_one = 0, asym_bi = 0;
    for (int k = 0; k <= 75; k++) {
        double d1 = fabs(y[75 - k] - y[75 + k]), d2 = fabs(z[75 - k] - z[75 + k]);
        if (d1 > asym_one) asym_one = d1;
        if (d2 > asym_bi)  asym_bi = d2;
    }
    printf("测试 5：以第 75 点为中心的左右最大差：单向 %.4f，双向 %.2g\n", asym_one, asym_bi);
    return 0;
}
