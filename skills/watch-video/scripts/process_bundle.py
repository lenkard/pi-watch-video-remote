#!/usr/bin/env python3
"""Process a staged media bundle into frames and transcript."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from media_source import resolve_bundle
from transcript import format_lines, in_range, read_vtt
from video_frames import choose_fps, extract_frames, human_time, parse_timestamp, probe
from whisper_api import transcribe


def render_report(
    source: dict,
    source_label: str,
    duration: float,
    effective_start: float,
    effective_end: float,
    effective_duration: float,
    focused: bool,
    meta: dict,
    frames: list[dict],
    fps: float,
    resolution: int,
    segments: list[dict],
    transcript_source: str | None,
    out_dir: Path,
) -> str:
    info = source.get("metadata") or {}
    lines = ["# Pi watch-video report", "", f"- **Source:** {source_label}"]
    if info.get("title"):
        lines.append(f"- **Title:** {info['title']}")
    if info.get("uploader"):
        lines.append(f"- **Uploader:** {info['uploader']}")
    lines.append(f"- **Duration:** {human_time(duration)} ({duration:.1f}s)")
    if focused:
        lines.append(f"- **Focus:** {human_time(effective_start)} → {human_time(effective_end)} ({effective_duration:.1f}s)")
    if meta.get("width") and meta.get("height"):
        lines.append(f"- **Video:** {meta['width']}x{meta['height']} ({meta.get('codec') or 'unknown codec'})")
    elif not meta.get("has_video"):
        lines.append("- **Video:** none (audio-only input)")
    lines.append(f"- **Frames:** {len(frames)}" + (f" at {fps:.3f} fps, {resolution}px wide" if frames else ""))
    lines.append(f"- **Transcript:** {len(segments)} segments" + (f" via {transcript_source}" if transcript_source else " (none)"))
    if not focused and duration > 600:
        lines.extend(["", "> Warning: this video is over 10 minutes, so frame coverage is sparse. Re-run with --start/--end for detailed analysis of a section."])

    lines.extend(["", "## Frames", "", "Read these image paths with Pi's `read` tool before answering visual questions:", ""])
    for frame in frames:
        lines.append(f"- `{frame['path']}` (t={human_time(frame['time'])})")

    lines.extend(["", "## Transcript", ""])
    if segments:
        lines.append(f"_Source: {transcript_source}._")
        lines.extend(["", "```", format_lines(segments), "```"])
    else:
        lines.append("_No transcript available. Use the frames only, or configure Whisper with `python3 scripts/setup.py --doctor`._")

    lines.extend(["", "---", f"_Result dir: `{out_dir}`._", ""])
    return "\n".join(lines)


def process_bundle(
    bundle_dir: Path,
    out_dir: Path,
    source_label: str | None = None,
    start: float | None = None,
    end: float | None = None,
    max_frames: int = 80,
    resolution: int = 512,
    fps_override: float | None = None,
    no_whisper: bool = False,
    transcription_language: str | None = None,
) -> Path:
    bundle_dir = Path(bundle_dir).expanduser().resolve()
    out_dir = Path(out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    source = resolve_bundle(bundle_dir)
    media_path = source["video"]
    meta = probe(media_path)
    duration = float(meta["duration"] or 0)

    if start is not None and start < 0:
        raise SystemExit("--start must be non-negative")
    if start is not None and duration and start >= duration:
        raise SystemExit(f"--start is beyond the media duration ({duration:.1f}s)")
    if start is not None and end is not None and end <= start:
        raise SystemExit("--end must be after --start")

    effective_start = start or 0.0
    effective_end = end if end is not None else duration
    effective_duration = max(0.001, effective_end - effective_start)
    focused = start is not None or end is not None
    fps, _target = choose_fps(effective_duration, focused, max(1, min(max_frames, 100)), fps_override)

    if meta.get("has_video"):
        frames = extract_frames(media_path, out_dir / "frames", fps, resolution, max_frames, start, end)
    else:
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

    if not segments and not no_whisper:
        try:
            all_segments, backend = transcribe(media_path, out_dir / "audio.mp3", None, transcription_language, start, end)
            if all_segments:
                segments = in_range(all_segments, start, end) if focused else all_segments
                transcript_source = f"whisper/{backend}"
        except SystemExit as exc:
            print(f"[pi-watch-video] whisper unavailable: {exc}", file=sys.stderr)

    report = render_report(
        source=source,
        source_label=source_label or (source.get("metadata") or {}).get("source") or source["video"],
        duration=duration,
        effective_start=effective_start,
        effective_end=effective_end,
        effective_duration=effective_duration,
        focused=focused,
        meta=meta,
        frames=frames,
        fps=fps,
        resolution=resolution,
        segments=segments,
        transcript_source=transcript_source,
        out_dir=out_dir,
    )
    report_path = out_dir / "report.md"
    report_path.write_text(report, encoding="utf-8")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Process a staged media bundle into frames and transcript.")
    parser.add_argument("bundle_dir", help="Directory containing source.* media and optional subtitles/info")
    parser.add_argument("--source-label", help="Original source label for the final report")
    parser.add_argument("--start", help="Start timestamp: SS, MM:SS, or HH:MM:SS")
    parser.add_argument("--end", help="End timestamp: SS, MM:SS, or HH:MM:SS")
    parser.add_argument("--max-frames", type=int, default=80, help="Frame cap, max 100 (default: 80)")
    parser.add_argument("--resolution", type=int, default=512, help="Frame width in px (default: 512)")
    parser.add_argument("--fps", type=float, help="Manual fps override, capped at 2")
    parser.add_argument("--out-dir", required=True, help="Directory to write frames, audio, and report into")
    parser.add_argument("--no-whisper", action="store_true", help="Do not call Whisper when captions are unavailable")
    parser.add_argument("--transcription-language", help="Optional transcription language hint, e.g. pt, en, auto")
    args = parser.parse_args()

    report_path = process_bundle(
        bundle_dir=Path(args.bundle_dir),
        out_dir=Path(args.out_dir),
        source_label=args.source_label,
        start=parse_timestamp(args.start),
        end=parse_timestamp(args.end),
        max_frames=max(1, min(args.max_frames, 100)),
        resolution=args.resolution,
        fps_override=args.fps,
        no_whisper=args.no_whisper,
        transcription_language=args.transcription_language,
    )
    print(report_path.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
