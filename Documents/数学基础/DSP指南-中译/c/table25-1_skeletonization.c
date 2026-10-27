/*
 * 表 25-1 + 表 25-2：二值图像骨架化（BASIC 原程序的 C 版本）
 *
 * 表 25-1 是主程序：做 6 轮迭代，每轮先逐像素调用表 25-2 的子程序判断能否删除
 * （能删的先标成 1），整轮判完后再把标记为 1 的像素统一改成白色 255。
 * 表 25-2 是子程序：四条规则全部满足，像素才会被标记删除。
 * 像素值约定和原书一样：0 = 黑（物体），255 = 白（背景），1 = 本轮已标记、待删除。
 *
 * 原书用「虚构的子程序」载入指纹图像，这里自己画一张 150×150 的测试图：
 * 几圈同心粗圆环、一条粗斜线和一个粗十字，线宽 5～9 像素，模仿指纹的粗脊线。
 * 验证三件事：
 *   1. 线条被削细：骨架里不应再有 2×2 的全黑方块（全黑方块说明某处还不止一像素宽）；
 *   2. 不断线：骨架的 8 连通黑色区域个数应与原图相同（规则四的作用）；
 *   3. 线条没被吃光：骨架像素数应明显少于原图、但不为 0。
 *
 * 编译运行：cc -O2 -o table25-1_skeletonization table25-1_skeletonization.c -lm && ./table25-1_skeletonization
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SIZE 150                            /* 140 DIM X%[149,149]：图像 150×150 */
#define BLACK 0
#define WHITE 255
#define MARK 1

static int X[SIZE][SIZE];

/* 代替 160 GOSUB XXXX：画测试图，四周留白边，保证 R±1、C±1 不越界 */
static void load_image(void)
{
    for (int r = 0; r < SIZE; r++)
        for (int c = 0; c < SIZE; c++) {
            double d = hypot(r - 75.0, c - 75.0);
            int black = 0;
            if (fabs(d - 20.0) < 3.5 || fabs(d - 38.0) < 4.5 || fabs(d - 58.0) < 3.0)
                black = 1;                                          /* 三圈粗圆环 */
            if (r > 10 && r < 140 && abs(r - c) < 4 && d > 64.0)
                black = 1;                                          /* 圆环外侧的粗斜线段 */
            if ((abs(r - 75) < 3 && abs(c - 75) < 12) || (abs(c - 75) < 3 && abs(r - 75) < 12))
                black = 1;                                          /* 圆心处的粗十字 */
            if (r < 3 || r > SIZE - 4 || c < 3 || c > SIZE - 4)
                black = 0;                                          /* 白边 */
            X[r][c] = black ? BLACK : WHITE;
        }
}

/* 表 25-2（第 5000～5430 行）：判断 X[r][c] 能否删除，能删就标成 1 */
static void evaluate_pixel(int r, int c)
{
    /* 5040～5050 规则一：已经是白的，什么都不做 */
    if (X[r][c] == WHITE) return;

    /* 5080～5090 规则二：上右下左四个近邻都不是白色（全黑或已标记），什么都不做 */
    if (X[r - 1][c] != WHITE && X[r][c + 1] != WHITE &&
        X[r + 1][c] != WHITE && X[r][c - 1] != WHITE) return;

    /* 5120～5220 规则三：八个邻居里只有一个是黑的（线段端点），什么都不做 */
    int count = 0;
    if (X[r - 1][c - 1] == BLACK) count++;  /* 5140：邻居 1 */
    if (X[r - 1][c]     == BLACK) count++;  /* 5150：邻居 2 */
    if (X[r - 1][c + 1] == BLACK) count++;  /* 5160：邻居 3 */
    if (X[r][c + 1]     == BLACK) count++;  /* 5170：邻居 4 */
    if (X[r + 1][c + 1] == BLACK) count++;  /* 5180：邻居 5 */
    if (X[r + 1][c]     == BLACK) count++;  /* 5190：邻居 6 */
    if (X[r + 1][c - 1] == BLACK) count++;  /* 5200：邻居 7 */
    if (X[r][c - 1]     == BLACK) count++;  /* 5210：邻居 8 */
    if (count == 1) return;                 /* 5220 */

    /* 5250～5370 规则四：顺时针数「黑→白」跳变，超过一次说明邻居不连通，什么都不做。
     * 远邻（1、3、5、7）后面紧跟一个近邻，只看下一个；
     * 近邻（2、4、6、8）后面要连跳过下一个远邻和再下一个近邻都为白才算一次跳变。 */
    count = 0;
    if (X[r - 1][c - 1] == BLACK && X[r - 1][c] > 0) count++;                          /* 5290：1→2 */
    if (X[r - 1][c] == BLACK && X[r - 1][c + 1] > 0 && X[r][c + 1] > 0) count++;       /* 5300：2→3,4 */
    if (X[r - 1][c + 1] == BLACK && X[r][c + 1] > 0) count++;                          /* 5310：3→4 */
    if (X[r][c + 1] == BLACK && X[r + 1][c + 1] > 0 && X[r + 1][c] > 0) count++;       /* 5320：4→5,6 */
    if (X[r + 1][c + 1] == BLACK && X[r + 1][c] > 0) count++;                          /* 5330：5→6 */
    if (X[r + 1][c] == BLACK && X[r + 1][c - 1] > 0 && X[r][c - 1] > 0) count++;       /* 5340：6→7,8 */
    if (X[r + 1][c - 1] == BLACK && X[r][c - 1] > 0) count++;                          /* 5350：7→8 */
    if (X[r][c - 1] == BLACK && X[r - 1][c - 1] > 0 && X[r - 1][c] > 0) count++;       /* 5360：8→1,2 */
    if (count > 1) return;                  /* 5370 */

    /* 5400～5410：四条规则都满足，标记为 1，本轮结束时再改成白色 */
    X[r][c] = MARK;
}

/* 表 25-1 第 180～320 行：6 轮迭代，返回每轮删掉的像素数 */
static void skeletonize(int removed[6])
{
    for (int iter = 0; iter < 6; iter++) {  /* 180：FOR ITER% = 0 TO 5 */
        for (int r = 1; r < SIZE - 1; r++)  /* 200～240：逐像素判断，最外一圈不判（没有完整邻居） */
            for (int c = 1; c < SIZE - 1; c++)
                evaluate_pixel(r, c);       /* 220：GOSUB 5000 */

        removed[iter] = 0;
        for (int r = 0; r < SIZE; r++)      /* 260～300：标记过的像素统一改成白色 */
            for (int c = 0; c < SIZE; c++)
                if (X[r][c] == MARK) { X[r][c] = WHITE; removed[iter]++; }
    }
}

/* 下面是验证用的工具函数，不属于原程序 */
static int count_black(void)
{
    int n = 0;
    for (int r = 0; r < SIZE; r++)
        for (int c = 0; c < SIZE; c++)
            if (X[r][c] == BLACK) n++;
    return n;
}

static int count_2x2_blocks(void)
{
    int n = 0;
    for (int r = 0; r < SIZE - 1; r++)
        for (int c = 0; c < SIZE - 1; c++)
            if (X[r][c] == BLACK && X[r + 1][c] == BLACK && X[r][c + 1] == BLACK && X[r + 1][c + 1] == BLACK)
                n++;
    return n;
}

/* 8 连通黑色区域计数（用显式栈做填充，避免递归过深） */
static int count_components(void)
{
    static unsigned char seen[SIZE][SIZE];
    static int stack[SIZE * SIZE][2];
    memset(seen, 0, sizeof seen);
    int n = 0;
    for (int r = 0; r < SIZE; r++)
        for (int c = 0; c < SIZE; c++) {
            if (X[r][c] != BLACK || seen[r][c]) continue;
            n++;
            int top = 0;
            stack[top][0] = r; stack[top][1] = c; top++;
            seen[r][c] = 1;
            while (top > 0) {
                top--;
                int y = stack[top][0], x = stack[top][1];
                for (int dy = -1; dy <= 1; dy++)
                    for (int dx = -1; dx <= 1; dx++) {
                        int yy = y + dy, xx = x + dx;
                        if (yy < 0 || yy >= SIZE || xx < 0 || xx >= SIZE) continue;
                        if (X[yy][xx] != BLACK || seen[yy][xx]) continue;
                        seen[yy][xx] = 1;
                        stack[top][0] = yy; stack[top][1] = xx; top++;
                    }
            }
        }
    return n;
}

int main(void)
{
    load_image();
    int black0 = count_black(), blocks0 = count_2x2_blocks(), comp0 = count_components();

    int removed[6];
    skeletonize(removed);

    int black1 = count_black(), blocks1 = count_2x2_blocks(), comp1 = count_components();

    printf("每轮删掉的像素数：");
    for (int i = 0; i < 6; i++) printf("%d ", removed[i]);
    printf("\n");
    printf("            黑像素数   2×2 全黑方块数   8 连通区域数\n");
    printf("原图       %8d   %14d   %12d\n", black0, blocks0, comp0);
    printf("骨架化后   %8d   %14d   %12d\n", black1, blocks1, comp1);
    printf("连通区域数是否不变：%s\n", comp0 == comp1 ? "是" : "否");
    return 0;
}
