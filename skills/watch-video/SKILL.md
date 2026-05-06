---
name: watch-video
description: Watch and analyze a video URL or local video file in Pi. Use when the user provides a video link/path and asks to summarize it, inspect visuals, diagnose a screen recording, or answer questions about what happens in the video.
license: MIT
compatibility: Requires Python 3 plus local ffmpeg/ffprobe and yt-dlp. Optional Whisper fallback uses GROQ_API_KEY or OPENAI_API_KEY.
---

# Watch Video for Pi

This skill turns a video into inputs Pi can inspect: sampled JPEG frames plus a timestamped transcript. It supports public URLs handled by `yt-dlp` and local video files.

## Workflow

1. Resolve the skill directory from this file's parent directory.
2. Run setup preflight:

```bash
python3 <skill-dir>/scripts/setup.py --check
```

If it exits non-zero, run the instructional doctor and show the user the actionable output:

```bash
python3 <skill-dir>/scripts/setup.py --doctor
```

Do not auto-install system packages. Ask the user to install missing dependencies or add optional Whisper keys if needed. If only the Whisper key is missing, you may continue; videos with captions and frames still work.

3. Run the watch script:

```bash
python3 <skill-dir>/scripts/watch.py "<video-url-or-path>"
```

Useful options:

- `--start T` / `--end T` focus on a timestamp range (`SS`, `MM:SS`, or `HH:MM:SS`). Use this for long videos or questions about a specific moment.
- `--max-frames N` lowers/raises the image budget, capped at 100.
- `--resolution W` changes frame width. Default is 512; use 1024 only when reading on-screen text matters.
- `--fps F` overrides automatic sampling, capped at 2 fps.
- `--whisper groq|openai` forces a transcription provider.
- `--no-whisper` skips audio transcription fallback.
- `--out-dir DIR` keeps outputs in a chosen working directory.

4. Read every listed frame path with Pi's `read` tool. Use parallel reads when possible. The frame list is chronological and includes timestamps.

5. Answer the user's question using both evidence streams:

- Frames: visual content on screen.
- Transcript: spoken content or captions.

Cite timestamps when useful. If the video is long and the first pass is sparse, say so and offer to re-run a focused range.

6. Cleanup: the report prints a work directory. Delete it with `rm -rf <dir>` when follow-up questions are unlikely. Keep it if the user may ask more about the same video.

## Usage examples

```bash
python3 <skill-dir>/scripts/watch.py "https://youtu.be/example" --start 0:00 --end 0:30
python3 <skill-dir>/scripts/watch.py "~/Movies/bug-repro.mov" --resolution 1024
python3 <skill-dir>/scripts/watch.py "$URL" --max-frames 40 --no-whisper
```

## Limits

- Visual accuracy is best under 10 minutes or with focused `--start`/`--end` ranges.
- Frame extraction is capped at 100 frames and 2 fps to protect context budget.
- URL downloads are limited to what `yt-dlp` can access without private login state.
- Whisper only receives extracted audio, not the full video, and only when captions are unavailable unless forced by user options.

## Security notes

This skill runs local Python scripts, `yt-dlp`, `ffmpeg`, and `ffprobe`. Optional Whisper fallback sends extracted audio to Groq or OpenAI depending on configured keys. API keys are read from environment variables or `~/.config/pi-watch-video/.env`.

## Credit

Inspired by Brad Automates' `claude-video`: https://github.com/bradautomates/claude-video. This is a Pi-oriented rewrite and package, not an official fork.
