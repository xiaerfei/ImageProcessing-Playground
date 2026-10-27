/*
 * 表 33-1：合并级联与并联的递归级（BASIC 原程序的 C 版本），附本章其余公式的数值验证
 *
 * 原书程序把两个级的递归系数 A1[]/B1[]、A2[]/B2[] 合并成一个系统的 A3[]/B3[]：
 * 先把递归系数改写成传递函数多项式（b 取负、b[0] 置 1），再用卷积做多项式乘法，
 * 最后把分母改回递归系数。级联与并联只差第 340 / 350 行这一行。
 *
 * 程序自带的测试（不带参数直接运行）：
 *   1) 公式 33-5（双二阶设计）算图 33-3 的陷波器系数，与书上 1.000 / -1.414 / 1.000 / 1.273 / -0.810 对比；
 *      公式 33-7、33-8 算出的 DC 与 0.5 频率增益，与直接代入传递函数的结果对比
 *   2) 级联：合并后的频率响应 = 两级之积；把随机信号逐级滤波，与用合并系数一次滤波逐点对比；
 *      再与书上第 617 页的展开式对比
 *   3) 并联：合并后的频率响应 = 两级之和；时域同样逐点对比
 *   4) 频谱反转：公式 33-6 与「和恒等系统并联」用表 33-1 算出的系数对比；重做图 33-6 的两个例子
 *   5) 公式 33-11（两极点双线性变换）：系数算出的 H(z) 与把 s 直接代入 H(s) 的结果对比
 *   6) 图 33-7 / 33-8 的切比雪夫-巴特沃斯设计：主程序第 360～440 行的「下标平移两位」紧凑写法，
 *      与改用表 33-1 逐级级联的结果对比
 *
 * 编译运行：cc -std=c99 -O2 -o table33-1_combine_stages table33-1_combine_stages.c -lm && ./table33-1_combine_stages
 */
#include <complex.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define N1 9                                /* 130～140 DIM A1[8] 等：每级下标 0～8 */
#define N3 17                               /* 150 DIM A3[16], B3[16]：合并后下标 0～16 */

static const double PI = 3.14159265358979323846;

/* 表 33-1：cp = 0 级联，cp = 1 并联。输入不改动，结果写进 a3[]、b3[] */
static void combine(const double *a1, const double *b1, const double *a2, const double *b2,
                    int cp, double *a3, double *b3)
{
    double t1[N1], t2[N1];
    for (int i = 0; i < N1; i++) {          /* 220～250：把递归系数改写成传递函数的分母 */
        t1[i] = -b1[i];
        t2[i] = -b2[i];
    }
    t1[0] = 1.0;                            /* 260～270：分母常数项为 1 */
    t2[0] = 1.0;

    for (int i = 0; i < N3; i++) {          /* 290：多项式相乘就是系数卷积 */
        a3[i] = 0.0;                        /* 300 */
        b3[i] = 0.0;                        /* 310 */
        for (int j = 0; j < N1; j++) {      /* 320 */
            if (i - j < 0 || i - j > N1 - 1) continue;   /* 330：越界的项不存在 */
            if (cp == 0) a3[i] += a1[j] * a2[i - j];      /* 340：级联，分子相乘 */
            if (cp == 1) a3[i] += a1[j] * t2[i - j] + a2[j] * t1[i - j];  /* 350：并联，分子交叉相乘再相加 */
            b3[i] += t1[j] * t2[i - j];                   /* 360：两种情况分母都相乘 */
        }
    }

    for (int i = 0; i < N3; i++)            /* 400～420：把分母改回递归系数 */
        b3[i] = -b3[i];
    b3[0] = 0.0;                            /* 430 */
}

/* 在频率 f（采样率的分数）处计算 H = Σa[k]e^{-jkΩ} / (1 - Σb[k]e^{-jkΩ})，即公式 33-3 在单位圆上取值 */
static double complex freq_resp(const double *a, const double *b, int n, double f)
{
    double complex num = 0.0, den = 1.0;
    for (int k = 0; k < n; k++) {
        double complex e = cexp(-I * 2.0 * PI * f * k);
        num += a[k] * e;
        if (k > 0) den -= b[k] * e;
    }
    return num / den;
}

/* 用递推式（公式 33-2）滤波：y[n] = Σa[k]x[n-k] + Σb[k]y[n-k] */
static void recursive_filter(const double *a, const double *b, int nc, const double *x, double *y, int len)
{
    for (int n = 0; n < len; n++) {
        double acc = 0.0;
        for (int k = 0; k < nc; k++) {
            if (n - k < 0) break;
            acc += a[k] * x[n - k];
            if (k > 0) acc += b[k] * y[n - k];
        }
        y[n] = acc;
    }
}

/* 公式 33-5：由极点 rp∠wp、零点 r0∠w0 求双二阶系数 */
static void biquad(double r0, double w0, double rp, double wp, double *a, double *b)
{
    for (int i = 0; i < N1; i++) a[i] = b[i] = 0.0;
    a[0] = 1.0;
    a[1] = -2.0 * r0 * cos(w0);
    a[2] = r0 * r0;
    b[1] = 2.0 * rp * cos(wp);
    b[2] = -rp * rp;
}

/* 公式 33-7 / 33-8：从递归系数直接求 DC 与 0.5 频率处的增益 */
static double gain_dc(const double *a, const double *b, int n)
{
    double sa = 0.0, sb = 0.0;
    for (int k = 0; k < n; k++) { sa += a[k]; sb += b[k]; }
    return sa / (1.0 - sb);
}
static double gain_nyquist(const double *a, const double *b, int n)
{
    double sa = 0.0, sb = 0.0;
    for (int k = 0; k < n; k++) {
        double s = (k % 2 == 0) ? 1.0 : -1.0;   /* (-1)^k */
        sa += a[k] * s;
        sb += b[k] * s;
    }
    return sa / (1.0 - sb);
}

/* 图 33-8 的子程序（与表 20-5 相同）：第 p 个极点对的五个系数 */
static void cheb_stage(double fc, int lh, double pr, int np, int p, double c[5])
{
    double rp = -cos(PI / (np * 2) + (p - 1) * PI / np);    /* 1080 */
    double ip =  sin(PI / (np * 2) + (p - 1) * PI / np);    /* 1090 */
    if (pr != 0.0) {                                        /* 1120：PR = 0 时跳过，即巴特沃斯 */
        double es = sqrt(pow(100.0 / (100.0 - pr), 2) - 1.0);           /* 1130：公式 33-9 的 ε */
        double vx = (1.0 / np) * log(1.0 / es + sqrt(1.0 / (es * es) + 1.0));   /* 1140：v */
        double kx = (1.0 / np) * log(1.0 / es + sqrt(1.0 / (es * es) - 1.0));   /* 1150 */
        kx = (exp(kx) + exp(-kx)) / 2.0;                    /* 1160：k */
        rp *= ((exp(vx) - exp(-vx)) / 2.0) / kx;            /* 1170：σ' = σ sinh(v)/k */
        ip *= ((exp(vx) + exp(-vx)) / 2.0) / kx;            /* 1180：ω' = ω cosh(v)/k */
    }
    double t = 2.0 * tan(0.5);                              /* 1210：公式 33-11 的 T */
    double w = 2.0 * PI * fc;                               /* 1220 */
    double m = rp * rp + ip * ip;                           /* 1230 */
    double d = 4.0 - 4.0 * rp * t + m * t * t;              /* 1240 */
    double x0 = t * t / d, x1 = 2.0 * t * t / d, x2 = t * t / d;   /* 1250～1270 */
    double y1 = (8.0 - 2.0 * m * t * t) / d;                /* 1280 */
    double y2 = (-4.0 - 4.0 * rp * t - m * t * t) / d;      /* 1290 */
    double k = (lh == 1) ? -cos(w / 2.0 + 0.5) / cos(w / 2.0 - 0.5)   /* 1320：公式 33-14 */
                         :  sin(0.5 - w / 2.0) / sin(0.5 + w / 2.0);  /* 1330：公式 33-12 */
    d = 1.0 + y1 * k - y2 * k * k;                          /* 1340：公式 33-13 */
    c[0] = (x0 - x1 * k + x2 * k * k) / d;                  /* 1350：A0 */
    c[1] = (-2.0 * x0 * k + x1 + x1 * k * k - 2.0 * x2 * k) / d;   /* 1360：A1 */
    c[2] = (x0 * k * k - x1 * k + x2) / d;                  /* 1370：A2 */
    c[3] = (2.0 * k + y1 + y1 * k * k - 2.0 * y2 * k) / d;  /* 1380：B1 */
    c[4] = (-k * k - y1 * k + y2) / d;                      /* 1390：B2 */
    if (lh == 1) { c[1] = -c[1]; c[3] = -c[3]; }            /* 1400～1410 */
}

/* 图 33-7 主程序：第 360～440 行「下标平移两位」的紧凑合并写法，再归一化增益 */
static void cheb_design_compact(double fc, int lh, double pr, int np, double *a, double *b)
{
    double A[23] = {0}, B[23] = {0}, TA[23], TB[23];
    A[2] = 1.0;                             /* 230～240：先放恒等系统，否则全零永远乘不出东西 */
    B[2] = 1.0;
    for (int p = 1; p <= np / 2; p++) {     /* 320 */
        double c[5];
        cheb_stage(fc, lh, pr, np, p, c);   /* 340 */
        for (int i = 0; i < 23; i++) { TA[i] = A[i]; TB[i] = B[i]; }   /* 360～390 */
        for (int i = 2; i < 23; i++) {      /* 410～440 */
            A[i] = c[0] * TA[i] + c[1] * TA[i - 1] + c[2] * TA[i - 2];
            B[i] = TB[i] - c[3] * TB[i - 1] - c[4] * TB[i - 2];
        }
    }
    B[2] = 0.0;                             /* 480 */
    for (int i = 0; i < 21; i++) { a[i] = A[i + 2]; b[i] = -B[i + 2]; }   /* 490～520 */
    double g = (lh == 0) ? gain_dc(a, b, 21) : gain_nyquist(a, b, 21);    /* 540～630 */
    for (int i = 0; i < 21; i++) a[i] /= g; /* 650～670 */
}

/* 同一设计，改用表 33-1 逐级级联（每次把已有系统与新的一级合并） */
static void cheb_design_table33(double fc, int lh, double pr, int np, double *a, double *b)
{
    double acc_a[N3] = {0}, acc_b[N3] = {0};
    acc_a[0] = 1.0;                         /* 恒等系统 */
    for (int p = 1; p <= np / 2; p++) {
        double c[5], sa[N1] = {0}, sb[N1] = {0}, ta[N1], tb[N1], na[N3], nb[N3];
        cheb_stage(fc, lh, pr, np, p, c);
        sa[0] = c[0]; sa[1] = c[1]; sa[2] = c[2]; sb[1] = c[3]; sb[2] = c[4];
        for (int i = 0; i < N1; i++) { ta[i] = acc_a[i]; tb[i] = acc_b[i]; }
        combine(ta, tb, sa, sb, 0, na, nb);
        for (int i = 0; i < N3; i++) { acc_a[i] = na[i]; acc_b[i] = nb[i]; }
    }
    for (int i = 0; i < 21; i++) { a[i] = (i < N3) ? acc_a[i] : 0.0; b[i] = (i < N3) ? acc_b[i] : 0.0; }
    double g = (lh == 0) ? gain_dc(a, b, 21) : gain_nyquist(a, b, 21);
    for (int i = 0; i < 21; i++) a[i] /= g;
}

static double frand(void) { return rand() / (double)RAND_MAX * 2.0 - 1.0; }

int main(void)
{
    /* 测试 1：图 33-3 的陷波器 */
    double na[N1], nb[N1];
    biquad(1.0, PI / 4, 0.9, PI / 4, na, nb);
    printf("测试 1（图 33-3 陷波器，公式 33-5）：a0=%.3f a1=%.3f a2=%.3f b1=%.3f b2=%.3f\n",
           na[0], na[1], na[2], nb[1], nb[2]);
    printf("        |H| 在 0.125 处 = %.2e，在 0 处 = %.4f，在 0.5 处 = %.4f\n",
           cabs(freq_resp(na, nb, N1, 0.125)), cabs(freq_resp(na, nb, N1, 0.0)), cabs(freq_resp(na, nb, N1, 0.5)));
    printf("        公式 33-7 DC 增益 = %.6f（直接代入 %.6f），公式 33-8 0.5 处增益 = %.6f（直接代入 %.6f）\n",
           gain_dc(na, nb, N1), creal(freq_resp(na, nb, N1, 0.0)),
           gain_nyquist(na, nb, N1), creal(freq_resp(na, nb, N1, 0.5)));

    /* 第二级：两极点切比雪夫低通 fc=0.2、纹波 0.5% */
    double c[5], la[N1] = {0}, lb[N1] = {0};
    cheb_stage(0.2, 0, 0.5, 2, 1, c);
    la[0] = c[0]; la[1] = c[1]; la[2] = c[2]; lb[1] = c[3]; lb[2] = c[4];

    /* 测试 2、3：级联与并联 */
    for (int cp = 0; cp <= 1; cp++) {
        double a3[N3], b3[N3];
        combine(na, nb, la, lb, cp, a3, b3);
        double max_f = 0.0;
        for (int i = 0; i <= 500; i++) {
            double f = 0.5 * i / 500;
            double complex h1 = freq_resp(na, nb, N1, f), h2 = freq_resp(la, lb, N1, f);
            double complex want = (cp == 0) ? h1 * h2 : h1 + h2;
            double e = cabs(freq_resp(a3, b3, N3, f) - want);
            if (e > max_f) max_f = e;
        }
        enum { L = 2000 };
        static double x[L], y1[L], y2[L], y3[L];
        srand(1);
        for (int n = 0; n < L; n++) x[n] = frand();
        if (cp == 0) {
            recursive_filter(na, nb, N1, x, y1, L);      /* 第一级 */
            recursive_filter(la, lb, N1, y1, y2, L);     /* 第二级 */
        } else {
            recursive_filter(na, nb, N1, x, y1, L);
            recursive_filter(la, lb, N1, x, y2, L);
            for (int n = 0; n < L; n++) y2[n] += y1[n];  /* 并联：两路输出相加 */
        }
        recursive_filter(a3, b3, N3, x, y3, L);
        double max_t = 0.0;
        for (int n = 0; n < L; n++) if (fabs(y3[n] - y2[n]) > max_t) max_t = fabs(y3[n] - y2[n]);
        printf("测试 %d（%s）：合并后的频率响应与%s的最大差 = %.2e，2000 点随机信号时域最大差 = %.2e\n",
               cp + 2, cp == 0 ? "级联" : "并联", cp == 0 ? "两级之积" : "两级之和", max_f, max_t);
        if (cp == 0) {                      /* 第 617 页的展开式 */
            double e[9] = {
                fabs(a3[0] - na[0] * la[0]),
                fabs(a3[1] - (na[0] * la[1] + na[1] * la[0])),
                fabs(a3[2] - (na[0] * la[2] + na[1] * la[1] + na[2] * la[0])),
                fabs(a3[3] - (na[1] * la[2] + na[2] * la[1])),
                fabs(a3[4] - na[2] * la[2]),
                fabs(b3[1] - (nb[1] + lb[1])),
                fabs(b3[2] - (nb[2] + lb[2] - nb[1] * lb[1])),
                fabs(b3[3] - (-nb[1] * lb[2] - nb[2] * lb[1])),
                fabs(b3[4] - (-nb[2] * lb[2])) };
            double m = 0.0;
            for (int i = 0; i < 9; i++) if (e[i] > m) m = e[i];
            printf("        与书上第 617 页级联展开式的最大差 = %.2e\n", m);
        }
    }

    /* 测试 4：频谱反转 */
    {
        double ia[N1] = {1.0}, ib[N1] = {0}, ma[N1], a3[N3], b3[N3], ea[N1];
        for (int i = 0; i < N1; i++) ma[i] = -na[i];     /* 原系统取负，再与恒等系统并联 = 原信号减去输出 */
        combine(ia, ib, ma, nb, 1, a3, b3);
        for (int i = 0; i < N1; i++) ea[i] = -na[i] - nb[i];  /* 公式 33-6 */
        ea[0] = 1.0 - na[0];
        double m = 0.0;
        for (int i = 0; i < N1; i++) {
            if (fabs(a3[i] - ea[i]) > m) m = fabs(a3[i] - ea[i]);
            if (fabs(b3[i] - nb[i]) > m) m = fabs(b3[i] - nb[i]);
        }
        printf("测试 4（频谱反转）：公式 33-6 与表 33-1 并联恒等系统的系数最大差 = %.2e（b 系数不变）\n", m);

        /* 重做图 33-6a/b：6 极点巴特沃斯低通，截止 0.3 */
        double ba[21], bb[21];
        cheb_design_compact(0.3, 0, 0.0, 6, ba, bb);
        double inv_a[21];
        for (int i = 0; i < 21; i++) inv_a[i] = -ba[i] - bb[i];
        inv_a[0] = 1.0 - ba[0];
        double peak = 0.0, fpk = 0.0, dip = 9.0, fdp = 0.0;
        for (int i = 0; i <= 1000; i++) {
            double f = 0.5 * i / 1000, h = cabs(freq_resp(inv_a, bb, 21, f));
            if (h > peak) { peak = h; fpk = f; }
            if (f > fpk && f < 0.4 && h < dip) { dip = h; fdp = f; }
        }
        printf("        图 33-6b：反转后的「高通」在 %.3f 处达到 %.3f，在 %.3f 处回落到 %.3f，0.5 处为 %.3f（理想高通应在 0.3 以上恒为 1）\n",
               fpk, peak, fdp, dip, cabs(freq_resp(inv_a, bb, 21, 0.5)));

        /* 重做图 33-6c/d：零点在单位圆上 0.2 处、极点半径 0.95 的陷波器 */
        double qa[N1], qb[N1], qi[N1];
        biquad(1.0, 2 * PI * 0.2, 0.95, 2 * PI * 0.2, qa, qb);
        double g = gain_dc(qa, qb, N1);
        for (int i = 0; i < N1; i++) qa[i] /= g;          /* 增益调整：a 系数整体除以 DC 增益 */
        for (int i = 0; i < N1; i++) qi[i] = -qa[i] - qb[i];
        qi[0] = 1.0 - qa[0];
        printf("        图 33-6d：陷波器反转后，|H| 在 0.2 处 = %.3f，0.18 处 = %.3f，0.1 处 = %.3f，0 处 = %.3f\n",
               cabs(freq_resp(qi, qb, N1, 0.2)), cabs(freq_resp(qi, qb, N1, 0.18)),
               cabs(freq_resp(qi, qb, N1, 0.1)), cabs(freq_resp(qi, qb, N1, 0.0)));
    }

    /* 测试 5：公式 33-11 */
    {
        double sg = -0.7071067811865476, om = 0.7071067811865476;   /* 两极点巴特沃斯的极点 */
        double t = 2.0 * tan(0.5), m = sg * sg + om * om, d = 4.0 - 4.0 * sg * t + m * t * t;
        double a[N1] = {0}, b[N1] = {0};
        a[0] = t * t / d; a[1] = 2.0 * t * t / d; a[2] = t * t / d;
        b[1] = (8.0 - 2.0 * m * t * t) / d;
        b[2] = (-4.0 - 4.0 * sg * t - m * t * t) / d;
        double maxe = 0.0;
        for (int i = 1; i < 500; i++) {
            double f = 0.5 * i / 500;
            double complex z1 = cexp(-I * 2.0 * PI * f);           /* z^-1 */
            double complex s = 2.0 * (1.0 - z1) / (t * (1.0 + z1)); /* 公式 33-10 */
            double complex hs = 1.0 / ((s - (sg + I * om)) * (s - (sg - I * om)));
            double e = cabs(freq_resp(a, b, N1, f) - hs);
            if (e > maxe) maxe = e;
        }
        double f1 = 1.0 / (2.0 * PI);       /* 数字角频率 1 弧度对应的 f */
        printf("测试 5（公式 33-11）：系数算出的 H(z) 与把 s 直接代入 H(s) 的最大差 = %.2e\n", maxe);
        printf("        截止：数字角频率 1 弧度（f=%.4f）处 |H| = %.4f（模拟原型在 ω=1 处为 0.7071）\n",
               f1, cabs(freq_resp(a, b, N1, f1)));
    }

    /* 测试 6：图 33-7 的紧凑写法 vs 表 33-1 逐级级联 */
    {
        /* 表 33-1 每级的数组只到下标 8，逐级级联时已有系统最多 8 阶，所以极点数最多取 10 */
        double cfg[][4] = { {0.1, 0, 0.5, 4}, {0.25, 1, 10.0, 6}, {0.05, 0, 0.0, 8}, {0.4, 1, 0.5, 10} };
        double m = 0.0;
        for (int t = 0; t < 4; t++) {
            double a1[21], b1[21], a2[21], b2[21];
            cheb_design_compact(cfg[t][0], (int)cfg[t][1], cfg[t][2], (int)cfg[t][3], a1, b1);
            cheb_design_table33(cfg[t][0], (int)cfg[t][1], cfg[t][2], (int)cfg[t][3], a2, b2);
            for (int i = 0; i < 17; i++) {  /* 表 33-1 的数组到下标 16 为止 */
                double e = fabs(a1[i] - a2[i]) + fabs(b1[i] - b2[i]);
                if (e > m) m = e;
            }
        }
        printf("测试 6（图 33-7）：「下标平移两位」紧凑写法与表 33-1 逐级级联，4 组参数下系数最大差 = %.2e\n", m);
        double a[21], b[21];
        cheb_design_compact(0.1, 0, 0.5, 4, a, b);
        printf("        低通 FC=0.1 PR=0.5 NP=4：a0..a4 = %.6e %.6e %.6e %.6e %.6e\n", a[0], a[1], a[2], a[3], a[4]);
        printf("                                 b1..b4 = %.6f %.6f %.6f %.6f\n", b[1], b[2], b[3], b[4]);
    }
    return 0;
}
