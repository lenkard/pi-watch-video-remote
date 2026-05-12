#!/usr/bin/env python3
"""Prepare a video for Pi: frames plus timestamped transcript."""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from media_source import resolve_source  # noqa: E402
from transcript import format_lines, in_range, read_vtt  # noqa: E402
from video_frames import choose_fps, extract_frames, human_time, parse_timestamp, probe  # noqa: E402
from whisper_api import transcribe  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract sampled video frames and transcript for Pi.")
    parser.add_argument("source", help="Video URL or local video path")
    parser.add_argument("--start", help="Start timestamp: SS, MM:SS, or HH:MM:SS")
    parser.add_argument("--end", help="End timestamp: SS, MM:SS, or HH:MM:SS")
    parser.add_argument("--max-frames", type=int, default=80, help="Frame cap, max 100 (default: 80)")
    parser.add_argument("--resolution", type=int, default=512, help="Frame width in px (default: 512)")
    parser.add_argument("--fps", type=float, help="Manual fps override, capped at 2")
    parser.add_argument("--out-dir", help="Working directory to keep outputs")
    parser.add_argument("--no-whisper", action="store_true", help="Do not call the configured transcription endpoint when captions are unavailable")
    parser.add_argument("--whisper", choices=["endpoint", "remote"], help="Deprecated alias; only the configured endpoint is supported")
    parser.add_argument("--transcription-provider", choices=["endpoint", "remote"], help="Deprecated; only the configured endpoint is supported")
    parser.add_argument("--transcription-language", help="Optional transcription language hint, e.g. pt, en, auto")
    args = parser.parse_args()

    max_frames = max(1, min(args.max_frames, 100))
    work = Path(args.out_dir).expanduser().resolve() if args.out_dir else Path(tempfile.mkdtemp(prefix="pi-watch-video-"))
    work.mkdir(parents=True, exist_ok=True)
    print(f"[pi-watch-video] work dir: {work}", file=sys.stderr)

    source = resolve_source(args.source, work / "source")
    video = source["video"]
    meta = probe(video)

    start = parse_timestamp(args.start)
    end = parse_timestamp(args.end)
    duration = float(meta["duration"] or 0)
    if start is not None and start < 0:
        raise SystemExit("--start must be non-negative")
    if start is not None and duration and start >= duration:
        raise SystemExit(f"--start is beyond the video duration ({duration:.1f}s)")
    if start is not None and end is not None and end <= start:
        raise SystemExit("--end must be after --start")

    effective_start = start or 0.0
    effective_end = end if end is not None else duration
    effective_duration = max(0.001, effective_end - effective_start)
    focused = start is not None or end is not None
    fps, target = choose_fps(effective_duration, focused, max_frames, args.fps)

    if meta.get("has_video"):
        print(f"[pi-watch-video] extracting frames: target≈{target}, fps={fps:.3f}", file=sys.stderr)
        frames = extract_frames(video, work / "frames", fps, args.resolution, max_frames, start, end)
    else:
        print("[pi-watch-video] audio-only input: skipping frame extraction", file=sys.stderr)
        frames = []

    transcript_source = None
    segments: list[dict] = []
    if source.get("subtitles"):
        try:
            segments = read_vtt(source["subtitles"])
            segments = in_range(segments, start, end) if focused else segments
            transcript_source = "captions"
        except Exception as exc:
            print(f"[pi-watch-video] captions could not be parsed: {exc}", file=sys.stderr)

    if not segments and not args.no_whisper:
        try:
            provider = args.transcription_provider or args.whisper
            audio_start = start if focused else None
            audio_end = end if focused else None
            all_segments, backend = transcribe(video, work / "audio.mp3", provider, args.transcription_language, audio_start, audio_end)
            if all_segments:
                segments = in_range(all_segments, start, end) if focused else all_segments
                transcript_source = f"whisper/{backend}"
        except SystemExit as exc:
            print(f"[pi-watch-video] whisper unavailable: {exc}", file=sys.stderr)

    info = source.get("metadata") or {}
    print("\n# Pi watch-video report\n")
    print(f"- **Source:** {args.source}")
    if info.get("title"):
        print(f"- **Title:** {info['title']}")
    if info.get("uploader"):
        print(f"- **Uploader:** {info['uploader']}")
    print(f"- **Duration:** {human_time(duration)} ({duration:.1f}s)")
    if focused:
        print(f"- **Focus:** {human_time(effective_start)} → {human_time(effective_end)} ({effective_duration:.1f}s)")
    if meta.get("width") and meta.get("height"):
        print(f"- **Video:** {meta['width']}x{meta['height']} ({meta.get('codec') or 'unknown codec'})")
    elif not meta.get("has_video"):
        print("- **Video:** none (audio-only input)")
    print(f"- **Frames:** {len(frames)}" + (f" at {fps:.3f} fps, {args.resolution}px wide" if frames else ""))
    print(f"- **Transcript:** {len(segments)} segments" + (f" via {transcript_source}" if transcript_source else " (none)"))
    if not focused and duration > 600:
        print("\n> Warning: this video is over 10 minutes, so frame coverage is sparse. Re-run with --start/--end for detailed analysis of a section.")

    print("\n## Frames\n")
    print("Read these image paths with Pi's `read` tool before answering visual questions:\n")
    for frame in frames:
        print(f"- `{frame['path']}` (t={human_time(frame['time'])})")

    print("\n## Transcript\n")
    if segments:
        print(f"_Source: {transcript_source}._\n")
        print("```")
        print(format_lines(segments))
        print("```")
    else:
        print("_No transcript available. Use the frames only, or configure Whisper with `python3 scripts/setup.py --doctor`._")

    print("\n---")
    print(f"_Work dir: `{work}`. Delete it when no more follow-up questions need these frames._")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
