#include <metal_stdlib>
using namespace metal;

// 第 1 周:全屏 quad 显示一张纹理。
// 这个 vertex/fragment 对是后续所有滤镜实验的底座:
// 以后每周的算法只需要换 fragment(或插入 compute pass)。

struct VOut {
    float4 pos [[position]];
    float2 uv;
};

// 无顶点缓冲:用 vertex_id 直接生成 4 个角(triangle strip)。
// scale 用于 aspect-fit(等比缩放留黑边),避免图像被拉伸。
vertex VOut fullscreenVertex(uint vid [[vertex_id]],
                             constant float2 &scale [[buffer(0)]]) {
    const float2 quad[4] = { {-1.0, -1.0}, {1.0, -1.0}, {-1.0, 1.0}, {1.0, 1.0} };
    float2 p = quad[vid];
    VOut out;
    out.pos = float4(p * scale, 0.0, 1.0);
    // NDC 的 y 向上,纹理 v 向下,所以翻转 v
    out.uv = float2((p.x + 1.0) * 0.5, 1.0 - (p.y + 1.0) * 0.5);
    return out;
}

fragment float4 textureFragment(VOut in [[stage_in]],
                                texture2d<float> tex [[texture(0)]]) {
    constexpr sampler s(mag_filter::linear, min_filter::linear);
    return tex.sample(s, in.uv);
}
