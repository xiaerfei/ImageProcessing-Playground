/*
 * 表 20-4 + 表 20-5：切比雪夫递归滤波器的系数计算（BASIC 原程序的 C 版本）
 *
 * 表 20-4 是主程序，表 20-5 是它在第 340 行调用的子程序，两者合起来才是一个完整程序，
 * 所以合成一个 C 文件：chebyshev_stage() 对应表 20-5，chebyshev_design() 对应表 20-4。
 * 原书全程单精度（PI = 3.14159265），这里用 double，原书说双精度能用更多的极点。
 *
 * 用法：
 *   ./table20-4_chebyshev_design FC LH PR NP   按给定参数打印 a、b 系数
 *       FC：截止频率（0～0.5），LH：0 低通 / 1 高通，PR：纹波百分比（0～29），NP：极点数（2～20 的偶数）
 *   ./table20-4_chebyshev_design               不带参数时运行自检：
 *       1) 子程序的中间变量与表 20-6 的两组调试数据对比
 *       2) 若干组系数与表 20-1 / 20-2 对比
 *       3) 实测频率响应在截止频率处的幅度、通带纹波、阶跃响应过冲
 *
 * 编译运行：cc -O2 -o table20-4_chebyshev_design table20-4_chebyshev_design.c -lm && ./table20-4_chebyshev_design
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define NC 23                               /* 130～160 DIM A[22] 等：下标 0～22 */

static const double PI = 3.14159265358979323846;

/* 子程序算出的一个两极点级的系数，以及表 20-6 要对照的中间变量 */
typedef struct {
    double rp, ip, es, vx, kx;              /* 第 1200 行处的值 */
    double t, w, m, d, x0, x1, x2, y1, y2;  /* 第 1310 行处的值 */
    double a0, a1, a2, b1, b2;              /* 返回主程序的值 */
} Stage;

/* 表 20-5：计算第 p 个极点对（两极点级）的递归系数 */
static Stage chebyshev_stage(double fc, int lh, double pr, int np, int p)
{
    Stage s = {0};
    /* 1080～1090：极点在单位圆上的位置 */
    s.rp = -cos(PI / (np * 2) + (p - 1) * PI / np);
    s.ip =  sin(PI / (np * 2) + (p - 1) * PI / np);

    /* 1120～1180：有纹波时，把圆压成椭圆；纹波为 0 就是巴特沃斯，跳过 */
    if (pr != 0) {
        s.es = sqrt(pow(100.0 / (100.0 - pr), 2) - 1);
        s.vx = (1.0 / np) * log((1 / s.es) + sqrt((1 / (s.es * s.es)) + 1));
        s.kx = (1.0 / np) * log((1 / s.es) + sqrt((1 / (s.es * s.es)) - 1));
        s.kx = (exp(s.kx) + exp(-s.kx)) / 2;
        s.rp = s.rp * ((exp(s.vx) - exp(-s.vx)) / 2) / s.kx;
        s.ip = s.ip * ((exp(s.vx) + exp(-s.vx)) / 2) / s.kx;
    }

    /* 1210～1290：s 域到 z 域的转换 */
    s.t  = 2 * tan(0.5);
    s.w  = 2 * PI * fc;
    s.m  = s.rp * s.rp + s.ip * s.ip;
    s.d  = 4 - 4 * s.rp * s.t + s.m * s.t * s.t;
    s.x0 = s.t * s.t / s.d;
    s.x1 = 2 * s.t * s.t / s.d;
    s.x2 = s.t * s.t / s.d;
    s.y1 = (8 - 2 * s.m * s.t * s.t) / s.d;
    s.y2 = (-4 - 4 * s.rp * s.t - s.m * s.t * s.t) / s.d;

    /* 1320～1410：低通到低通，或低通到高通的变换 */
    double k = lh ? -cos(s.w / 2 + 0.5) / cos(s.w / 2 - 0.5)
                  :  sin(0.5 - s.w / 2) / sin(0.5 + s.w / 2);
    double d = 1 + s.y1 * k - s.y2 * k * k;
    s.a0 = (s.x0 - s.x1 * k + s.x2 * k * k) / d;
    s.a1 = (-2 * s.x0 * k + s.x1 + s.x1 * k * k - 2 * s.x2 * k) / d;
    s.a2 = (s.x0 * k * k - s.x1 * k + s.x2) / d;
    s.b1 = (2 * k + s.y1 + s.y1 * k * k - 2 * s.y2 * k) / d;
    s.b2 = (-(k * k) - s.y1 * k + s.y2) / d;
    if (lh) { s.a1 = -s.a1; s.b1 = -s.b1; }
    return s;
}

/* 表 20-4：把 np/2 个两极点级合成一组递归系数，结果 a[0..np]、b[1..np] */
static void chebyshev_design(double fc, int lh, double pr, int np, double *a, double *b)
{
    double ta[NC], tb[NC];
    for (int i = 0; i < NC; i++) a[i] = b[i] = 0;    /* 180～210 */
    a[2] = 1;                                        /* 230～240：从 1 开始做多项式乘法 */
    b[2] = 1;

    for (int p = 1; p <= np / 2; p++) {              /* 320：每个极点对循环一次 */
        Stage s = chebyshev_stage(fc, lh, pr, np, p);    /* 340：GOSUB 1000 */
        for (int i = 0; i < NC; i++) { ta[i] = a[i]; tb[i] = b[i]; }   /* 360～390 */
        for (int i = 2; i < NC; i++) {               /* 410～440：把这一级串进级联 */
            a[i] = s.a0 * ta[i] + s.a1 * ta[i - 1] + s.a2 * ta[i - 2];
            b[i] =        tb[i] - s.b1 * tb[i - 1] - s.b2 * tb[i - 2];
        }
    }

    b[2] = 0;                                        /* 480～520：收尾，下标左移 2 位，b 取反 */
    for (int i = 0; i <= 20; i++) { a[i] = a[i + 2]; b[i] = -b[i + 2]; }

    double sa = 0, sb = 0;                           /* 540～610：归一化增益 */
    for (int i = 0; i <= 20; i++) {
        double sign = (lh && (i & 1)) ? -1.0 : 1.0;  /* 高通在 0.5 处归一化，乘 (-1)^i */
        sa += a[i] * sign;
        sb += b[i] * sign;
    }
    double gain = sa / (1 - sb);                     /* 630 */
    for (int i = 0; i <= 20; i++) a[i] /= gain;      /* 650～670 */
}

/* 频率 f 处的幅度响应 |H| = |Σ a_k e^{-jωk}| / |1 − Σ b_k e^{-jωk}| */
static double magnitude(const double *a, const double *b, int np, double f)
{
    double nr = 0, ni = 0, dr = 1, di = 0, w = 2 * PI * f;
    for (int k = 0; k <= np; k++) {
        nr += a[k] * cos(w * k);  ni -= a[k] * sin(w * k);
        if (k > 0) { dr -= b[k] * cos(w * k);  di += b[k] * sin(w * k); }
    }
    return sqrt((nr * nr + ni * ni) / (dr * dr + di * di));
}

/* 阶跃响应的过冲百分比（按递归方程直接运行 2000 点） */
static double overshoot(const double *a, const double *b, int np)
{
    double x[2000], y[2000], peak = 0;
    for (int n = 0; n < 2000; n++) {
        x[n] = 1.0;
        y[n] = 0;
        for (int k = 0; k <= np && k <= n; k++) y[n] += a[k] * x[n - k];
        for (int k = 1; k <= np && k <= n; k++) y[n] += b[k] * y[n - k];
        if (y[n] > peak) peak = y[n];
    }
    return (peak - y[1999]) / y[1999] * 100;
}

static int check(const char *name, double got, double want, double tol)
{
    int ok = fabs(got - want) <= tol;
    printf("  %-3s 计算 %12.6f  表中 %12.6f  %s\n", name, got, want, ok ? "一致" : "不一致");
    return ok;
}

int main(int argc, char **argv)
{
    double a[NC], b[NC];

    if (argc == 5) {                                 /* 270～300：从命令行输入四个参数 */
        double fc = atof(argv[1]), pr = atof(argv[3]);
        int lh = atoi(argv[2]), np = atoi(argv[4]);
        chebyshev_design(fc, lh, pr, np, a, b);
        for (int i = 0; i <= np; i++) {              /* 680：最终系数在 A[ ] 和 B[ ] 中，按原书表格的排法打印 */
            printf("a%-2d = % .6E", i, a[i]);
            if (i > 0) printf("   b%-2d = % .6E", i, b[i]);
            printf("\n");
        }
        return 0;
    }

    int bad = 0;
    printf("自检 1：子程序与表 20-6 的调试数据对比（容差 1e-6，原书 PI 取 3.141592）\n");
    Stage s1 = chebyshev_stage(0.1, 0, 0, 4, 1);
    Stage s2 = chebyshev_stage(0.1, 1, 10, 4, 2);
    /* 顺序：RP IP ES VX KX T W M D X0 X1 X2 Y1 Y2 A0 A1 A2 B1 B2 */
    double g1[] = {s1.rp,s1.ip,0,0,0,s1.t,s1.w,s1.m,s1.d,s1.x0,s1.x1,s1.x2,s1.y1,s1.y2,s1.a0,s1.a1,s1.a2,s1.b1,s1.b2};
    double w1[] = {-0.923879,0.382683,0,0,0,1.092605,0.628318,1.0,9.231528,0.129316,0.258632,0.129316,0.607963,-0.125227,0.061885,0.123770,0.061885,1.048600,-0.296140};
    double g2[] = {s2.rp,s2.ip,s2.es,s2.vx,s2.kx,s2.t,s2.w,s2.m,s2.d,s2.x0,s2.x1,s2.x2,s2.y1,s2.y2,s2.a0,s2.a1,s2.a2,s2.b1,s2.b2};
    double w2[] = {-0.136178,0.933223,0.484322,0.368054,1.057802,1.092605,0.628318,0.889450,5.656972,0.211029,0.422058,0.211029,1.038784,-0.789584,0.922919,-1.845840,0.922919,1.446913,-0.836653};
    double e1 = 0, e2 = 0;
    for (int i = 0; i < 19; i++) {
        if (i < 2 || i > 4) e1 = fmax(e1, fabs(g1[i] - w1[i]));    /* 第一组纹波为 0，ES/VX/KX 不用 */
        e2 = fmax(e2, fabs(g2[i] - w2[i]));
    }
    printf("  数据组 1（低通，纹波 0%%）：19 个变量与表的最大差 %.2g\n", e1);
    printf("  数据组 2（高通，纹波 10%%）：19 个变量与表的最大差 %.2g\n", e2);
    bad += (e1 > 1e-6) + (e2 > 1e-6);

    printf("\n自检 2：与表 20-1（低通）、表 20-2（高通）对比，纹波 0.5%%，相对容差 1e-5\n");
    chebyshev_design(0.1, 0, 0.5, 4, a, b);
    printf("低通 fc=0.1，4 极点：\n");
    bad += !check("a0", a[0], 2.780755E-03, 3e-8);
    bad += !check("a2", a[2], 1.668453E-02, 2e-7);
    bad += !check("b1", b[1], 2.764031E+00, 3e-5);
    bad += !check("b4", b[4], -3.502232E-01, 4e-6);
    chebyshev_design(0.25, 1, 0.5, 6, a, b);
    printf("高通 fc=0.25，6 极点：\n");
    bad += !check("a0", a[0], 1.434450E-02, 2e-7);
    bad += !check("a3", a[3], -2.868900E-01, 3e-6);
    bad += !check("b1", b[1], -1.076051E+00, 1e-5);
    bad += !check("b6", b[6], -5.722250E-02, 6e-7);

    printf("\n自检 3：实测频率响应和阶跃响应（纹波 0.5%%）\n");
    printf("  类型  极点  fc     |H(fc)|   通带最小值  通带最大值  阻带 fc±0.1 处(dB)  阶跃过冲\n");
    int nps[] = {2, 4, 6};
    for (int lh = 0; lh <= 1; lh++)
        for (int i = 0; i < 3; i++) {
            double fc = 0.1;
            chebyshev_design(fc, lh, 0.5, nps[i], a, b);
            double lo = 1e9, hi = 0;
            for (int j = 0; j <= 1000; j++) {        /* 通带：低通 0～fc 的前 80%，高通 fc 之后 */
                double f = lh ? fc + (0.5 - fc) * (0.2 + 0.8 * j / 1000.0) : fc * 0.8 * j / 1000.0;
                double m = magnitude(a, b, nps[i], f);
                lo = fmin(lo, m); hi = fmax(hi, m);
            }
            double fs = lh ? fc - 0.08 : fc + 0.1;   /* 高通取 0.02，避开 0 附近 */
            printf("  %s  %2d   %.2f  %.4f    %.4f      %.4f      %8.1f           ",
                   lh ? "高通" : "低通", nps[i], fc, magnitude(a, b, nps[i], fc), lo, hi,
                   20 * log10(magnitude(a, b, nps[i], fs)));
            if (lh) printf("  -\n");                 /* 高通的阶跃响应最终趋于 0，不算过冲 */
            else    printf("%.1f%%\n", overshoot(a, b, nps[i]));
        }
    chebyshev_design(0.05, 0, 0.5, 4, a, b);
    printf("  图 20-3a 的设定（低通 fc=0.05，0.5%% 纹波）：4 极点过冲 %.1f%%", overshoot(a, b, 4));
    chebyshev_design(0.05, 0, 0.5, 2, a, b);
    printf("，2 极点过冲 %.1f%%\n", overshoot(a, b, 2));

    printf("\n%s\n", bad ? "有不一致的项" : "全部一致");
    return bad != 0;
}
