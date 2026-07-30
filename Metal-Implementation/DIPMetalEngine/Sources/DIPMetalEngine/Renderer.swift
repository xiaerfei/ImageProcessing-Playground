import MetalKit

final class Renderer: NSObject, MTKViewDelegate {
    private let queue: MTLCommandQueue
    private let pipeline: MTLRenderPipelineState
    private let texture: MTLTexture

    init(device: MTLDevice, imageURL: URL) throws {
        guard let queue = device.makeCommandQueue() else {
            throw RendererError.setup("makeCommandQueue 失败")
        }
        self.queue = queue

        // Shaders.metal 以资源形式打进 bundle,运行时编译。
        // (SwiftPM 对 .metal 的预编译支持不稳定,运行时编译最可靠;
        //  以后迁到 Xcode 工程时改回预编译的 default.metallib 即可)
        guard let shaderURL = Bundle.module.url(forResource: "Shaders", withExtension: "metal") else {
            throw RendererError.setup("bundle 里找不到 Shaders.metal")
        }
        let source = try String(contentsOf: shaderURL, encoding: .utf8)
        let library = try device.makeLibrary(source: source, options: nil)
        let desc = MTLRenderPipelineDescriptor()
        desc.vertexFunction = library.makeFunction(name: "fullscreenVertex")
        desc.fragmentFunction = library.makeFunction(name: "textureFragment")
        desc.colorAttachments[0].pixelFormat = .bgra8Unorm
        pipeline = try device.makeRenderPipelineState(descriptor: desc)

        // SRGB: false —— 按原始字节加载,显示是原样透传。
        // 等做滤波(第 7 周高斯模糊)时再回头处理 sRGB/线性空间问题(避坑清单 #6)。
        let loader = MTKTextureLoader(device: device)
        texture = try loader.newTexture(URL: imageURL, options: [.SRGB: false])
    }

    func mtkView(_ view: MTKView, drawableSizeWillChange size: CGSize) {}

    func draw(in view: MTKView) {
        guard let drawable = view.currentDrawable,
              let rpd = view.currentRenderPassDescriptor,
              let cmd = queue.makeCommandBuffer(),
              let enc = cmd.makeRenderCommandEncoder(descriptor: rpd) else { return }

        var scale = aspectFitScale(viewSize: view.drawableSize)
        enc.setRenderPipelineState(pipeline)
        enc.setVertexBytes(&scale, length: MemoryLayout<SIMD2<Float>>.size, index: 0)
        enc.setFragmentTexture(texture, index: 0)
        enc.drawPrimitives(type: .triangleStrip, vertexStart: 0, vertexCount: 4)
        enc.endEncoding()
        cmd.present(drawable)
        cmd.commit()
    }

    private func aspectFitScale(viewSize: CGSize) -> SIMD2<Float> {
        guard viewSize.width > 0, viewSize.height > 0 else { return .init(1, 1) }
        let imageAspect = Float(texture.width) / Float(texture.height)
        let viewAspect = Float(viewSize.width) / Float(viewSize.height)
        return imageAspect > viewAspect
            ? SIMD2(1, viewAspect / imageAspect)
            : SIMD2(imageAspect / viewAspect, 1)
    }
}

enum RendererError: Error {
    case setup(String)
}
