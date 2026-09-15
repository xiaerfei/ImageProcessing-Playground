#!/usr/bin/env python3
"""将录屏教学视频转换为图文 Markdown 文档。

流程：
  1. ffprobe 定位视频中的 I 帧时间戳，ffmpeg 逐帧截图；
  2. 用相邻帧灰度差分去掉画面没变化的重复截图（GOP 固定的视频，I 帧本质是
     "每隔 N 秒采样一次"，不是"画面变化时才采样"，所以必须去重）；
  3. ffmpeg 抽出音轨，交给本地 whisper.cpp（whisper-cli + ggml 模型）转文字；
  4. 按时间轴把截图和对应时间段的文字拼成一份 Markdown。

依赖：系统已安装 ffmpeg / ffprobe / whisper-cli（whisper.cpp 的命令行工具），
以及一个 ggml 格式的模型文件（如 ~/.whisper-models/ggml-large-v3-turbo.bin）。
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".flv", ".avi", ".webm"}


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------

def run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"命令失败: {' '.join(cmd)}\n{proc.stderr}")
    return proc.stdout


def check_tools(whisper_bin: str) -> None:
    for tool in ("ffmpeg", "ffprobe", whisper_bin):
        if shutil.which(tool) is None:
            raise RuntimeError(f"找不到可执行文件: {tool}，请先安装或检查 PATH")


def fmt_ts(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ---------------------------------------------------------------------------
# 第一步：抽 I 帧
# ---------------------------------------------------------------------------

def list_iframe_times(video: Path) -> list[float]:
    out = run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-skip_frame", "nokey",
        "-show_entries", "frame=pict_type,best_effort_timestamp_time",
        "-of", "csv=p=0", str(video),
    ])
    times = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        # ffprobe 实际输出的字段顺序未必与 -show_entries 里写的顺序一致，
        # 这里不假设列序，直接找出哪一列是 "I"、哪一列是时间戳
        parts = line.split(",")
        if "I" not in parts:
            continue
        ts = next((p for p in parts if p not in ("I", "P", "B") and p not in ("", "N/A")), None)
        if ts is None:
            continue
        times.append(float(ts))
    return sorted(set(times))


def extract_frame(video: Path, t: float, out_path: Path) -> None:
    run([
        "ffmpeg", "-y", "-ss", f"{t:.3f}", "-i", str(video),
        "-frames:v", "1", "-q:v", "3", str(out_path),
        "-loglevel", "error",
    ])


def frame_diff_ratio(a: Path, b: Path) -> float:
    """两张图的差异比例（0~1），用缩小灰度图做像素级平均差，不依赖 numpy。"""
    from PIL import Image, ImageChops

    size = (160, 90)
    with Image.open(a) as ia, Image.open(b) as ib:
        ga = ia.convert("L").resize(size)
        gb = ib.convert("L").resize(size)
    diff = ImageChops.difference(ga, gb)
    hist = diff.histogram()  # 256 个灰度差值的像素计数
    total_pixels = size[0] * size[1]
    weighted = sum(value * count for value, count in enumerate(hist))
    return weighted / (total_pixels * 255)


@dataclass
class Frame:
    time: float
    path: Path


def extract_deduped_frames(video: Path, assets_dir: Path, diff_threshold: float,
                            keep_all: bool) -> list[Frame]:
    assets_dir.mkdir(parents=True, exist_ok=True)
    times = list_iframe_times(video)
    if not times:
        return []

    kept: list[Frame] = []
    last_kept_path: Path | None = None
    for t in times:
        candidate = assets_dir / f"frame_{t:07.2f}s.jpg"
        extract_frame(video, t, candidate)

        if keep_all or last_kept_path is None:
            kept.append(Frame(t, candidate))
            last_kept_path = candidate
            continue

        ratio = frame_diff_ratio(last_kept_path, candidate)
        if ratio >= diff_threshold:
            kept.append(Frame(t, candidate))
            last_kept_path = candidate
        else:
            candidate.unlink(missing_ok=True)

    return kept


# ---------------------------------------------------------------------------
# 第二步：语音转文字
# ---------------------------------------------------------------------------

@dataclass
class Segment:
    start: float
    end: float
    text: str


def extract_audio(video: Path, wav_path: Path) -> None:
    run([
        "ffmpeg", "-y", "-i", str(video),
        "-vn", "-ac", "1", "-ar", "16000", str(wav_path),
        "-loglevel", "error",
    ])


def transcribe(wav_path: Path, model: str, lang: str, whisper_bin: str,
                threads: int, out_base: Path, prompt: str) -> list[Segment]:
    cmd = [
        whisper_bin, "-m", model, "-f", str(wav_path),
        "-l", lang, "-t", str(threads),
        "-oj", "-of", str(out_base), "-np",
    ]
    if prompt:
        cmd += ["--prompt", prompt]
    run(cmd)
    json_path = out_base.with_name(out_base.name + ".json")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    segments = []
    for item in data.get("transcription", []):
        start = item["offsets"]["from"] / 1000.0
        end = item["offsets"]["to"] / 1000.0
        text = item["text"].strip()
        if text:
            segments.append(Segment(start, end, text))
    return segments


# ---------------------------------------------------------------------------
# 第三步：拼 Markdown
# ---------------------------------------------------------------------------

def build_markdown(title: str, frames: list[Frame], segments: list[Segment],
                    assets_relname: str) -> str:
    lines = [f"# {title}", ""]

    if not frames:
        for seg in segments:
            lines.append(f"`{fmt_ts(seg.start)}` {seg.text}")
            lines.append("")
        return "\n".join(lines)

    # 视频开头、第一张截图之前的语音，单独放一段
    seg_idx = 0
    if segments and segments[0].start < frames[0].time:
        lines.append("## 片头")
        lines.append("")
        while seg_idx < len(segments) and segments[seg_idx].start < frames[0].time:
            lines.append(segments[seg_idx].text)
            seg_idx += 1
        lines.append("")

    for i, frame in enumerate(frames):
        next_time = frames[i + 1].time if i + 1 < len(frames) else float("inf")
        lines.append(f"## {fmt_ts(frame.time)}")
        lines.append("")
        lines.append(f"![{frame.path.stem}]({assets_relname}/{frame.path.name})")
        lines.append("")
        paragraph = []
        while seg_idx < len(segments) and segments[seg_idx].start < next_time:
            paragraph.append(segments[seg_idx].text)
            seg_idx += 1
        if paragraph:
            lines.append("".join(paragraph))
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def process_video(video: Path, out_dir: Path, model: str, lang: str,
                   whisper_bin: str, threads: int, diff_threshold: float,
                   keep_all: bool, skip_frames: bool, skip_transcribe: bool,
                   prompt: str) -> Path:
    stem = video.stem
    video_out_dir = out_dir / stem
    assets_dir = video_out_dir / "assets"
    video_out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[{stem}] 处理中 -> {video_out_dir}")

    frames: list[Frame] = []
    if not skip_frames:
        print(f"[{stem}] 抽取并去重 I 帧 ...")
        frames = extract_deduped_frames(video, assets_dir, diff_threshold, keep_all)
        print(f"[{stem}] 保留 {len(frames)} 张截图")

    segments: list[Segment] = []
    if not skip_transcribe:
        print(f"[{stem}] 提取音频并转写 ...")
        wav_path = video_out_dir / f"{stem}.wav"
        extract_audio(video, wav_path)
        segments = transcribe(wav_path, model, lang, whisper_bin, threads,
                               video_out_dir / stem, prompt)
        wav_path.unlink(missing_ok=True)
        print(f"[{stem}] 转写得到 {len(segments)} 段文字")

    md = build_markdown(stem, frames, segments, "assets")
    md_path = video_out_dir / f"{stem}.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"[{stem}] 完成: {md_path}")
    return md_path


def find_videos(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    return sorted(p for p in input_path.iterdir() if p.suffix.lower() in VIDEO_EXTS)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path, help="视频文件，或包含多个视频的目录")
    parser.add_argument("--out-dir", type=Path, default=None,
                         help="输出目录，默认与视频同目录")
    parser.add_argument("--model", default=str(Path.home() / ".whisper-models" / "ggml-large-v3-turbo.bin"),
                         help="whisper.cpp ggml 模型路径")
    parser.add_argument("--whisper-bin", default="whisper-cli", help="whisper.cpp 可执行文件名")
    parser.add_argument("--lang", default="zh", help="语音语言，如 zh / en / auto")
    parser.add_argument(
        "--prompt",
        default="直方图、均衡化、灰度值、灰度变换、灰度映射、对比度、像素、单调递增、累积分布函数。",
        help="传给 whisper 的领域词汇提示，用于减少专业术语的同音字识别错误；传空字符串可关闭",
    )
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--diff-threshold", type=float, default=0.03,
                         help="相邻截图的最小差异比例，低于此值视为重复帧而丢弃（0~1）")
    parser.add_argument("--keep-all-frames", action="store_true", help="不做去重，保留所有 I 帧截图")
    parser.add_argument("--skip-frames", action="store_true", help="跳过截图步骤")
    parser.add_argument("--skip-transcribe", action="store_true", help="跳过语音转写步骤")
    args = parser.parse_args()

    check_tools(args.whisper_bin)

    if not args.skip_transcribe and not Path(args.model).exists():
        parser.error(f"模型文件不存在: {args.model}")

    out_dir = args.out_dir or (args.input if args.input.is_dir() else args.input.parent)
    videos = find_videos(args.input)
    if not videos:
        parser.error(f"未找到视频文件: {args.input}")

    for video in videos:
        process_video(
            video=video,
            out_dir=out_dir,
            model=args.model,
            lang=args.lang,
            whisper_bin=args.whisper_bin,
            threads=args.threads,
            diff_threshold=args.diff_threshold,
            prompt=args.prompt,
            keep_all=args.keep_all_frames,
            skip_frames=args.skip_frames,
            skip_transcribe=args.skip_transcribe,
        )


if __name__ == "__main__":
    main()
