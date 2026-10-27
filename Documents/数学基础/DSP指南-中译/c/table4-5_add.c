/*
 * 表 4-5：把 1234 和 4321 相加（BASIC 原程序的 C 版本）
 *
 * 表 4-3（机器码）和表 4-4（汇编）是同一件事在更低层次上的写法。
 * 想看 C 编译器把这几行变成了什么汇编，可以运行：
 *   cc -O0 -S -o - table4-5_add.c
 *
 * 编译运行：cc -O2 -o table4-5_add table4-5_add.c && ./table4-5_add
 */
#include <stdio.h>

int main(void)
{
    float a = 1234;                         /* 100 A = 1234（BASIC 默认单精度浮点） */
    float b = 4321;                         /* 110 B = 4321 */
    float c = a + b;                        /* 120 C = A+B */
    printf("C = %.0f\n", c);
    return 0;
}
