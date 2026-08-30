//
//  IAAffineTransform.m
//  ImageAlgorithm
//
//  3x3 齐次矩阵 + 反向映射(Backward Mapping)的通用几何变换。
//
//  设计参考 Documents/数字图像处理自学路线规划.md 中的纯 C 实现,
//  这里扩展为 RGBA 四通道,并补上最近邻插值与自适应画布。
//  数学细节详见 Documents/MacOS-图像仿射变换与采样模块分析.md。
//
//  矩阵运算用 Apple 的 simd(系统框架,零依赖)。它同时也是 Metal 的矩阵类型,
//  以后把算法搬到 shader 时可以直接复用。实测每像素的矩阵×向量比手写循环快约 1.3 倍。
//
//  为什么用 3x3 而不是 2x2:
//    2x2 只能表达旋转/缩放/剪切(线性变换),平移无法用矩阵乘法表示。
//    升到齐次坐标 (x, y, 1) 后平移变成第三列 tx/ty,于是
//    "缩放 → 旋转 → 平移" 可以预先连乘成单个矩阵 M,每像素只算一次乘法;
//    求反向映射也只需对 M 求一次逆,不用手推逆公式。
//    最下行留作 [p q 1] 还能扩展到透视变换(本文件已按齐次坐标归一化处理)。
//
//  ┌─────────────────────────────────────────────────────────────────┐
//  │ 全文件只依赖两条基本约定,理解了它们,下面的代码都是直白的实现:    │
//  │                                                                   │
//  │ 1. 列向量右乘:v' = M · v                                          │
//  │    连乘 M = Mn·…·M2·M1 时,从右往左读才是施加顺序——                │
//  │    M1 最先作用于像素,Mn 最后作用。                                 │
//  │                                                                   │
//  │ 2. 位图坐标系 y 轴向下:                                           │
//  │    数学课本里的旋转矩阵在屏幕上看是顺时针;所有"以原点为基准"的      │
//  │    变换(旋转/缩放/镜像/转置)都要靠"三明治夹层法"搬回图像中心,      │
//  │    见 matrixWithParams:imageSize: 的逐步注释。                     │
//  └─────────────────────────────────────────────────────────────────┘
//

#import "IAAffineTransform.h"

#pragma mark - 矩阵构造

// simd_matrix_from_rows 允许按课本的行布局书写,内部虽是列主序但对调用方透明。

/// 平移矩阵:x' = x + tx, y' = y + ty
///
/// ┌ 1 0 tx ┐   ┌ x ┐   ┌ x + tx ┐
/// │ 0 1 ty │ · │ y │ = │ y + ty │
/// └ 0 0 1  ┘   └ 1 ┘   └   1    ┘
///
/// 平移量放在齐次坐标的第三列——这正是 2x2 矩阵做不到、必须升到 3x3 的原因:
/// 平移是"加法",不是绕原点的线性变换,只有引入齐次分量 w=1 才能并进乘法里。
simd_double3x3 IAMatrixTranslation(double tx, double ty) {
    return simd_matrix_from_rows((simd_double3){1.0, 0.0, tx},
                                 (simd_double3){0.0, 1.0, ty},
                                 (simd_double3){0.0, 0.0, 1.0});
}

/// 缩放矩阵:x' = sx·x, y' = sy·y
///
/// ┌ sx  0  0 ┐
/// │  0 sy  0 │    det = sx·sy
/// └  0  0  1 ┘
///
/// 纯缩放以坐标系原点 (0,0) 为不动点:放大时图像向右下"撑大",左上角不动。
/// 要"以图像中心缩放"得靠 matrixWithParams 里的三明治夹层法。
/// sx/sy 取负值即镜像(-1 = 翻转),两个方向都为 -1 时等价于旋转 180°。
simd_double3x3 IAMatrixScale(double sx, double sy) {
    return simd_matrix_from_rows((simd_double3){ sx, 0.0, 0.0},
                                 (simd_double3){0.0,  sy, 0.0},
                                 (simd_double3){0.0, 0.0, 1.0});
}

/// 旋转矩阵:角度制入参
///
/// ┌ cosθ -sinθ  0 ┐    det = 1(纯旋转不改变面积)
/// │ sinθ  cosθ  0 │
/// └  0    0    1 ┘
///
/// 这是数学标准坐标系(Y 轴向上)里的逆时针旋转矩阵;但位图 y 轴向下,
/// y 被翻转后,屏幕上看起来就是顺时针——所以传入正角度,画面顺时针转。
simd_double3x3 IAMatrixRotation(double degrees) {
    double rad = degrees * M_PI / 180.0;
    double c = cos(rad), s = sin(rad);
    // 位图 y 轴向下,所以这个矩阵在屏幕上看起来是顺时针旋转
    return simd_matrix_from_rows((simd_double3){  c,  -s, 0.0},
                                 (simd_double3){  s,   c, 0.0},
                                 (simd_double3){0.0, 0.0, 1.0});
}

/// 转置矩阵:x' = y, y' = x
///
/// ┌ 0 1 0 ┐    det = -1(翻转类变换,改变手性)
/// │ 1 0 0 │
/// └ 0 0 1 ┘
///
/// 单独使用时图像沿 y=x 对角线镜像;在 matrixWithParams 的夹层中使用时,
/// 表现为绕图像中心沿主对角线翻转。行列式为 -1 说明它和镜像一样是"翻转",
/// 连续做两次转置回到原图(T·T = I)。
simd_double3x3 IAMatrixTranspose2D(void) {
    return simd_matrix_from_rows((simd_double3){0.0, 1.0, 0.0},
                                 (simd_double3){1.0, 0.0, 0.0},
                                 (simd_double3){0.0, 0.0, 1.0});
}

/// 默认参数 = 恒等变换:不平移、不旋转、不缩放(1.0 而不是 0.0)、不镜像
///
/// 注意 scale 的中性值是 1 不是 0——缩放 0 会把图像压成一条线,
/// 矩阵行列式变 0,直接不可逆(见 warpImage 里的 det 检查)。
IATransformParams IATransformParamsDefault(void) {
    return (IATransformParams){
        .translateX = 0.0, .translateY = 0.0,
        .rotationDegrees = 0.0,
        .scaleX = 1.0, .scaleY = 1.0,
        .mirrorHorizontal = NO, .mirrorVertical = NO, .transpose = NO,
    };
}

#pragma mark - 采样

// 反向映射反推出来的源坐标 (sx, sy) 是浮点数(例如 10.34, 25.82),
// 而像素只存在于整数网格上,所以需要插值策略决定"非整数位置取什么颜色"。
// 下面两个函数就是两种经典策略:最近邻(快、糙)与双线性(慢一点、平滑)。

/// 最近邻:四舍五入取整,越界返回透明
///
/// "谁离我最近就抄谁",三步:
///   1. lround 四舍五入,锁定最近的整数像素(5.7 → 6,12.2 → 12);
///   2. 越界检查:落在图外直接返回全透明,不做边缘拉回;
///   3. 指针寻址直接拷贝 RGBA 四字节。
/// 没有乘法、没有权重计算,速度最快;代价是放大/旋转时出现马赛克锯齿。
static inline void IASampleNearest(const uint8_t *src, NSInteger w, NSInteger h,
                                   double x, double y, uint8_t out[4]) {
    // 1) 四舍五入取整:锁定离浮点坐标最近的网格像素
    NSInteger sx = (NSInteger)lround(x);
    NSInteger sy = (NSInteger)lround(y);
    // 2) 越界判定:图像外 = 透明(而非黑),空出来的区域一眼可辨
    if (sx < 0 || sx >= w || sy < 0 || sy >= h) {
        out[0] = out[1] = out[2] = out[3] = 0;
        return;
    }
    // 3) 2D→1D 寻址:第 sy 行整行跳过(sy*w 个像素),行内再走 sx 个像素,
    //    每像素 4 字节(RGBA),所以乘 4 得到字节偏移
    const uint8_t *p = src + (sy * w + sx) * 4;
    out[0] = p[0]; out[1] = p[1]; out[2] = p[2]; out[3] = p[3];
}

/// 双线性:相邻 4 点按距离加权
///
/// 原理:反推坐标 (x, y) 落在 4 个相邻像素围成的 1x1 格子内,
/// 先横着做一次线性插值(Lerp),再竖着做一次,展开后就是 4 个面积权重:
///
///   上边插值:Vtop    = (1-dx)·p00 + dx·p10
///   下边插值:Vbottom = (1-dx)·p01 + dx·p11
///   纵向插值:Vfinal  = (1-dy)·Vtop + dy·Vbottom
///   展开合并 → w00=(1-dx)(1-dy)  w10=dx(1-dy)  w01=(1-dx)dy  w11=dx·dy
///
/// 其中 dx = x - x0 是从左邻居 x0 到目标点的距离(0~1),1-dx 则是到右邻居的距离。
/// 权重的几何意义是目标点把 1x1 格子切出的 4 块"对角矩形面积"——
/// 离谁近,谁的权重就大;四个权重之和恒等于 1。
///
/// 与参考实现的区别:参考用 `x >= width - 1` 直接判越界,会把最右一列/最下一行
/// 整条丢掉;这里改为把 4 个采样点各自 clamp 到边界内,保留边缘像素。
static inline void IASampleBilinear(const uint8_t *src, NSInteger w, NSInteger h,
                                    double x, double y, uint8_t out[4]) {
    // ① 粗筛越界:像素中心语义下,合法范围是 [-0.5, w-0.5]。
    //    超出半个像素宽就整个格子都在图外,直接透明,后面的 clamp 救不回来。
    if (x < -0.5 || x > (double)w - 0.5 || y < -0.5 || y > (double)h - 0.5) {
        out[0] = out[1] = out[2] = out[3] = 0;
        return;
    }

    // ② 定位左上邻居与小数偏移:floor 向下取整,
    //    dx/dy ∈ [0,1) 是目标点相对左上邻居的偏移距离
    NSInteger x0 = (NSInteger)floor(x);
    NSInteger y0 = (NSInteger)floor(y);
    double dx = x - (double)x0;
    double dy = y - (double)y0;

    // ③ 右/下邻居初值 +1;随后把 4 个点各自 clamp 到 [0, w-1]/[0, h-1]。
    //    例如 x=9.2(w=10):x0=9 合法,x1=10 越界 → 被拉回 9,
    //    于是左右两点重合——公式照常运转,既不越界读内存,
    //    也不会像"直接判越界"那样把最右一列像素整条裁掉。
    NSInteger x1 = x0 + 1, y1 = y0 + 1;
    if (x0 < 0) { x0 = 0; }  if (x0 > w - 1) { x0 = w - 1; }
    if (y0 < 0) { y0 = 0; }  if (y0 > h - 1) { y0 = h - 1; }
    if (x1 < 0) { x1 = 0; }  if (x1 > w - 1) { x1 = w - 1; }
    if (y1 < 0) { y1 = 0; }  if (y1 > h - 1) { y1 = h - 1; }

    // ④ 取出 4 个邻居的颜色起始地址(p00=左上 p10=右上 p01=左下 p11=右下)
    const uint8_t *p00 = src + (y0 * w + x0) * 4;
    const uint8_t *p10 = src + (y0 * w + x1) * 4;
    const uint8_t *p01 = src + (y1 * w + x0) * 4;
    const uint8_t *p11 = src + (y1 * w + x1) * 4;

    // ⑤ 面积权重:横向权重(1-dx / dx) × 纵向权重(1-dy / dy),
    //    相邻像素网格间距恒为 1,所以 lerp 的分母 x1-x0 = 1 被直接消掉
    double w00 = (1.0 - dx) * (1.0 - dy);
    double w10 = dx         * (1.0 - dy);
    double w01 = (1.0 - dx) * dy;
    double w11 = dx         * dy;

    // ⑥ RGBA 四通道分别加权求和,再限幅+四舍五入转回字节。
    //    fmax/fmin 是浮点精度保险(理论上权重和为 1,不会越界,
    //    但 -0.00001 / 255.00001 这类误差直接转整会出问题)
    for (int c = 0; c < 4; c++) {
        double v = w00 * p00[c] + w10 * p10[c] + w01 * p01[c] + w11 * p11[c];
        out[c] = (uint8_t)lround(fmin(fmax(v, 0.0), 255.0));
    }
}

#pragma mark - IAAffineTransform

@implementation IAAffineTransform

/// 按 "缩放 → 转置 → 镜像 → 旋转 → 平移" 的顺序复合出正向矩阵。
/// 旋转/缩放都绕图像中心进行,所以前后各夹了一次到原点的平移。
///
/// ── 三明治夹层法(Sandwich Composition)───────────────────────────
/// 缩放/转置/镜像/旋转这些算子在数学上全部以坐标系原点 (0,0) 为基准:
/// 直接施加的话,旋转会绕左上角转、放大时图像向右下撑大、镜像绕 y 轴翻——
/// 画面全部"飞出"画布。解决方法是前后各夹一层平移:
///
///   M = T(center) · [S · Tr · F · R] · T(-center)
///
/// 从右往左读,对每个像素的实际执行顺序:
///   1. T(-cx,-cy):把图像几何中心搬到原点;
///   2. 在原点处做缩放/转置/镜像/旋转——此时中心与原点重合,
///      这些"原点基准"的变换全部表现为绕图像中心操作;
///   3. T(cx+tx, cy+ty):把中心搬回原位,并叠加用户平移量。
///
/// ── 为什么中心是 (width-1)/2 而不是 width/2 ─────────────────────
/// 像素是离散网格:宽 2 的图像索引只有 0 和 1,
///   width/2   = 1.0 → 落在像素 1 的右边界,偏了半个像素;
///   (2-1)/2   = 0.5 → 正好是两个像素的中点。
/// 奇数宽同理:宽 3 时 (3-1)/2 = 1.0,精确落在中间像素上。
/// 用对了中心,旋转/缩放才不会产生半像素的系统性偏移(抖动/发虚)。
///
/// ── 乘法顺序 ────────────────────────────────────────────────────
/// 列向量右乘 v'=M·v,所以代码里每行"左乘一个新矩阵"= 在变换链最前面
/// 加一道工序;最终矩阵从右往左读才是真正的施加顺序。
+ (simd_double3x3)matrixWithParams:(IATransformParams)params imageSize:(NSSize)size {
    // 离散像素网格的几何中心:索引 0 ~ w-1 的中点(见上方推导)
    double cx = (size.width  - 1.0) * 0.5;
    double cy = (size.height - 1.0) * 0.5;

    // 从右往左读 = 施加顺序:先移到原点,缩放/转置/镜像/旋转,再移回中心,最后平移
    // ① 最先施加:中心 → 原点
    simd_double3x3 M = IAMatrixTranslation(-cx, -cy);
    // ② 缩放(中心已在原点,即"以中心缩放")
    M = simd_mul(IAMatrixScale(params.scaleX, params.scaleY), M);
    // ③ 可选:转置(沿中心的主对角线翻转);NO 时跳过,省一次矩阵乘法
    if (params.transpose) {
        M = simd_mul(IAMatrixTranspose2D(), M);
    }
    // ④ 可选:镜像 = 负缩放。水平镜像 sx=-1(绕垂直中轴线翻),
    //    垂直镜像 sy=-1(绕水平中轴线翻);两轴都翻 = 旋转 180°
    double mx = params.mirrorHorizontal ? -1.0 : 1.0;
    double my = params.mirrorVertical   ? -1.0 : 1.0;
    if (mx < 0.0 || my < 0.0) {
        M = simd_mul(IAMatrixScale(mx, my), M);
    }
    // ⑤ 旋转(绕图像中心;正角度 = 屏幕顺时针,见 IAMatrixRotation 注释)
    M = simd_mul(IAMatrixRotation(params.rotationDegrees), M);
    // ⑥ 最后施加:原点 → 中心,并叠加用户平移量 tx/ty
    M = simd_mul(IAMatrixTranslation(cx + params.translateX, cy + params.translateY), M);
    return M;
}

/// 反向映射执行变换:遍历目标画布每个像素,用逆矩阵反推源坐标再采样。
/// 落在源图之外的像素填透明(而非黑),空出来的区域一眼可辨。
///
/// ── 为什么必须"反向映射"而不是"正向投射"─────────────────────────
/// 正向做法是遍历源图像素、用 M 把它投射到目标画布上。放大 2 倍时,
/// 源图 1 个像素只能覆盖目标 4 个像素中的 1 个,其余 3 个没人写 → 空洞。
/// 反向做法反过来问:"目标画布上的这个像素,该从源图哪里取色?"
/// 每个目标像素都有答案,画布必然被填满,一个洞都没有。
///
/// ── 数学:如何用逆矩阵反推 ──────────────────────────────────────
/// 正向关系  P_target = M · P_source
/// 两边左乘 M⁻¹:M⁻¹·M = I,于是  P_source = M⁻¹ · P_target
/// 逆矩阵只求一次(下面循环外),循环内每像素只做一次 3x3 矩阵×向量。
///
/// ── 前置条件:矩阵必须可逆 ──────────────────────────────────────
/// 不是任何矩阵都有逆:必须方阵,且行列式 ≠ 0(奇异矩阵不可逆)。
/// 典型例子:scaleX = 0 时整张图被压成一条线,不同位置的像素重叠到
/// 同一点上,信息已丢失,无中生有地"撑回"2D 图像是不可能的。
/// 所以先用 simd_determinant 拦截,避免 simd_inverse 产出垃圾结果。
+ (nullable IAImageBuffer *)warpImage:(IAImageBuffer *)src
                               matrix:(simd_double3x3)forward
                        interpolation:(IAInterpolation)interpolation
                           canvasMode:(IACanvasMode)canvasMode {
    if (!src) { return nil; }

    NSInteger sw = src.width, sh = src.height;
    NSInteger dw = sw, dh = sh;
    double offsetX = 0.0, offsetY = 0.0;

    if (canvasMode == IACanvasModeFit) {
        // 自适应画布:旋转后图像会伸出原画布,需要先算出"新画布该多大"。
        // 做法:把源图 4 个角用正向矩阵 M 推到目标平面,取包围盒。
        double xs[4], ys[4];
        double cornerX[4] = {0.0, (double)sw - 1.0, 0.0,             (double)sw - 1.0};
        double cornerY[4] = {0.0, 0.0,              (double)sh - 1.0, (double)sh - 1.0};
        for (int i = 0; i < 4; i++) {
            // 齐次坐标除以 w 分量:仿射变换下 w 恒为 1,
            // 这里除法是为将来的透视变换预留的通用性
            simd_double3 p = simd_mul(forward, (simd_double3){cornerX[i], cornerY[i], 1.0});
            double wgt = (fabs(p.z) < 1e-12) ? 1.0 : p.z;
            xs[i] = p.x / wgt;
            ys[i] = p.y / wgt;
        }
        // 包围盒:minX/minY 通常为负(转出去的部分),所以新画布除了尺寸
        // 还要记一个偏移量——目标像素 (xd,yd) 对应的真实世界坐标是
        // (xd+offsetX, yd+offsetY),反向映射时要把它加回去
        double minX = xs[0], maxX = xs[0], minY = ys[0], maxY = ys[0];
        for (int i = 1; i < 4; i++) {
            minX = fmin(minX, xs[i]); maxX = fmax(maxX, xs[i]);
            minY = fmin(minY, ys[i]); maxY = fmax(maxY, ys[i]);
        }
        dw = (NSInteger)ceil(maxX - minX) + 1;
        dh = (NSInteger)ceil(maxY - minY) + 1;
        offsetX = minX;
        offsetY = minY;

        const NSInteger kMaxSide = 8192;   // 防止缩放调得过大把内存吃光
        if (dw <= 0 || dh <= 0 || dw > kMaxSide || dh > kMaxSide) { return nil; }
    }

    // 奇异矩阵(例如某方向缩放为 0)信息已丢失,无法反推
    // 行列式 = 0 ⇔ 变换把 2D 平面"压扁降维"(面积塌缩为 0),不可逆
    if (fabs(simd_determinant(forward)) < 1e-12) { return nil; }
    simd_double3x3 inverse = simd_inverse(forward);

    IAImageBuffer *dst = [IAImageBuffer bufferWithWidth:dw height:dh];
    if (!dst) { return nil; }

    const uint8_t *sp = src.data;
    uint8_t *dp = dst.data;

    // 反向映射:遍历目标画布,反推源坐标。
    // 若改成遍历源图正向投射,放大时目标画布会出现没被写到的空洞。
    for (NSInteger yd = 0; yd < dh; yd++) {
        for (NSInteger xd = 0; xd < dw; xd++) {
            // 目标像素 (xd,yd) 在 Fit 模式下对应世界坐标 (xd+offsetX, yd+offsetY),
            // 齐次分量固定为 1;左乘 M⁻¹ 反推它在源图中的位置
            simd_double3 ps = simd_mul(inverse, (simd_double3){ (double)xd + offsetX,
                                                                (double)yd + offsetY, 1.0 });

            // 齐次归一化(Perspective Division):仿射变换下 z 恒为 1,
            // 这步除法在仿射时是空操作;换成透视变换(第三行不再是 [0 0 1])
            // 时 z 才不等于 1,除法把齐次坐标变回普通 2D 坐标
            double wgt = (fabs(ps.z) < 1e-12) ? 1.0 : ps.z;
            double sx = ps.x / wgt;
            double sy = ps.y / wgt;

            // 反推坐标是浮点数(如 10.34, 25.82),交给插值器决定取色策略:
            // 最近邻 = 快、有锯齿;双线性 = 4 邻居加权平均、平滑
            uint8_t *out = dp + (yd * dw + xd) * 4;
            if (interpolation == IAInterpolationNearest) {
                IASampleNearest(sp, sw, sh, sx, sy, out);
            } else {
                IASampleBilinear(sp, sw, sh, sx, sy, out);
            }
        }
    }
    return dst;
}

@end
