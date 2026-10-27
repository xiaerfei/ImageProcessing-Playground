/*
 * 表 12-3：FORTRAN 版 FFT（按频率抽取，decimation in frequency）的 C 版本
 *
 * 与表 12-4 的 BASIC 版（按时间抽取）不同，这里先做三重循环的蝶形运算，最后才做位反转排序。
 * 数据放在复数数组 X(1)～X(N) 里，下标从 1 开始；参数 M = log2 N。
 * 为了逐行对照，C 版本也用 1 开始的下标（x[0] 闲置不用），复数用 C99 的 double complex。
 *
 * 测试：N = 8、64、1024 的随机复信号，与相关法复数 DFT（表 12-2）逐点比较。
 *
 * 编译运行：cc -O2 -o table12-3_fft_fortran table12-3_fft_fortran.c -lm && ./table12-3_fft_fortran
 */
#include <complex.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define NMAX 1024

static const double PI = 3.14159265358979323846;

/* SUBROUTINE FFT(X,M)：x[1]～x[n] 进为时域、出为频域 */
static void fft_fortran(double complex *x, int m)
{
    int n = 1 << m;                                         /* N=2**M */
    for (int l = 1; l <= m; l++) {                          /* DO 20 L=1,M：遍历每一级 */
        int le = 1 << (m + 1 - l);                          /* LE=2**(M+1-L)：本级子 DFT 的长度，从 N 开始逐级减半 */
        int le2 = le / 2;
        double complex u = 1.0;                             /* U=(1.0,0.0) */
        double complex s = cos(PI / le2) - I * sin(PI / le2);   /* S=CMPLX(COS(PI/LE2),-SIN(PI/LE2)) */
        for (int j = 1; j <= le2; j++) {                    /* DO 20 J=1,LE2 */
            for (int i = j; i <= n; i += le) {              /* DO 10 I=J,N,LE：遍历每个蝶形 */
                int ip = i + le2;
                double complex t = x[i] + x[ip];            /* T=X(I)+X(IP) */
                x[ip] = (x[i] - x[ip]) * u;                 /* X(IP)=(X(I)-X(IP))*U：先相减再乘正弦，与按时间抽取的蝶形相反 */
                x[i] = t;                                   /* 10 X(I)=T */
            }
            u = u * s;                                      /* 20 U=U*S：标号 20 属于 J 循环，每个 J 转一次 */
        }
    }

    int nd2 = n / 2, nm1 = n - 1, j = 1;                    /* ND2=N/2，NM1=N-1，J=1 */
    for (int i = 1; i <= nm1; i++) {                        /* DO 50 I=1,NM1：位反转排序 */
        if (i < j) {                                        /* IF(I.GE.J) GO TO 30 */
            double complex t = x[j];
            x[j] = x[i];
            x[i] = t;
        }
        int k = nd2;                                        /* 30 K=ND2 */
        while (k < j) {                                     /* 40 IF(K.GE.J) GO TO 50 */
            j -= k;                                         /* J=J-K */
            k /= 2;                                         /* K=K/2，GO TO 40 */
        }
        j += k;                                             /* 50 J=J+K */
    }
}

/* 相关法复数 DFT（表 12-2），下标 0～n-1，作为对照 */
static void complex_dft(const double complex *x, int n, double complex *y)
{
    for (int k = 0; k < n; k++) {
        y[k] = 0.0;
        for (int i = 0; i < n; i++)
            y[k] += x[i] * (cos(2.0 * PI * k * i / n) - I * sin(2.0 * PI * k * i / n));
    }
}

int main(void)
{
    static double complex x1[NMAX + 1], x0[NMAX], ref[NMAX];
    int ms[] = {3, 6, 10};

    srand(3);
    for (int t = 0; t < 3; t++) {
        int m = ms[t], n = 1 << m;
        for (int i = 0; i < n; i++) {
            x0[i] = (rand() / (double)RAND_MAX - 0.5) + I * (rand() / (double)RAND_MAX - 0.5);
            x1[i + 1] = x0[i];                              /* FORTRAN 下标：X(1) 对应 x[0] */
        }
        fft_fortran(x1, m);
        complex_dft(x0, n, ref);
        double err = 0.0;
        for (int k = 0; k < n; k++) err = fmax(err, cabs(x1[k + 1] - ref[k]));
        printf("N = %4d（M = %2d）：FFT 与相关法 DFT 的最大偏差 = %.3g\n", n, m, err);
    }
    return 0;
}
