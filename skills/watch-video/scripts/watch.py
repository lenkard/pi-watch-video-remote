#!/usr/bin/env python3
"""Prepare media for Pi: fetch/stage it, process it, print the final report."""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from media_source import is_url, stage_source  # noqa: E402
from process_bundle import process_bundle  # noqa: E402
from remote_fetch import fetch_url, remote_fetch_enabled  # noqa: E402
from remote_process import process_bundle_remote, remote_process_enabled  # noqa: E402
from video_frames import parse_timestamp  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract sampled video frames and transcript for Pi.")
    parser.add_argument("source", help="Video URL or local media path")
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

    source_dir = work / "source"
    if is_url(args.source) and remote_fetch_enabled():
        print("[pi-watch-video] fetching URL on remote browser host", file=sys.stderr)
        fetch_url(args.source, source_dir)
    else:
        stage_source(args.source, source_dir)

    result_dir = work / "result"
    process_kwargs = {
        "source_label": args.source,
        "start": args.start,
        "end": args.end,
        "max_frames": max_frames,
        "resolution": args.resolution,
        "fps": args.fps,
        "no_whisper": args.no_whisper,
        "transcription_language": args.transcription_language,
    }
    if remote_process_enabled():
        print("[pi-watch-video] processing bundle on remote worker", file=sys.stderr)
        process_bundle_remote(source_dir, result_dir, **process_kwargs)
    else:
        process_bundle(
            bundle_dir=source_dir,
            out_dir=result_dir,
            source_label=args.source,
            start=parse_timestamp(args.start),
            end=parse_timestamp(args.end),
            max_frames=max_frames,
            resolution=args.resolution,
            fps_override=args.fps,
            no_whisper=args.no_whisper,
            transcription_language=args.transcription_language,
        )

    report_path = result_dir / "report.md"
    print(report_path.read_text(encoding="utf-8"))
    print(f"_Work dir: `{work}`. Delete it when no more follow-up questions need these files._")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
