import AppKit
import MetalKit

// DIPMetalEngine —— 图像算法实验场(第 1 周骨架)
// 运行:swift run [图片路径]
// 不带参数时默认显示仓库 Assets/test-images/astronaut.png

func defaultImageURL() -> URL {
    // #filePath = <repo>/Metal-Implementation/DIPMetalEngine/Sources/DIPMetalEngine/main.swift
    var url = URL(fileURLWithPath: #filePath)
    for _ in 0..<5 { url.deleteLastPathComponent() }  // 回到仓库根目录
    return url.appendingPathComponent("Assets/test-images/astronaut.png")
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var window: NSWindow!
    private var renderer: Renderer!

    func applicationDidFinishLaunching(_ notification: Notification) {
        guard let device = MTLCreateSystemDefaultDevice() else {
            fatalError("没有可用的 Metal 设备")
        }
        let imageURL = CommandLine.arguments.count > 1
            ? URL(fileURLWithPath: CommandLine.arguments[1])
            : defaultImageURL()

        do {
            renderer = try Renderer(device: device, imageURL: imageURL)
        } catch {
            fatalError("初始化失败(图片路径对吗?\(imageURL.path)): \(error)")
        }

        let view = MTKView(frame: .zero, device: device)
        view.clearColor = MTLClearColor(red: 0.1, green: 0.1, blue: 0.1, alpha: 1)
        view.delegate = renderer

        window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 800, height: 800),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered, defer: false)
        window.title = "DIPMetalEngine — \(imageURL.lastPathComponent)"
        window.contentView = view
        window.center()
        window.makeKeyAndOrderFront(nil)

        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
