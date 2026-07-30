// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "DIPMetalEngine",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(
            name: "DIPMetalEngine",
            resources: [.copy("Shaders.metal")]
        )
    ]
)
