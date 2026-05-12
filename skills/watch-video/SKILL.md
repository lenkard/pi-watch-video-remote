---
name: watch-video
description: Watch, transcribe, and analyze a video URL or local video file in Pi. Use when the user provides a video link/path and asks to transcribe audio, extract captions/subtitles, produce a timestamped transcript, summarize it, inspect visuals, diagnose a screen recording, or answer questions about what happens in the video.
license: MIT
compatibility: Requires Python 3 plus local ffmpeg/ffprobe and yt-dlp. Optional transcription fallback uses an OpenAI-compatible remote endpoint, GROQ_API_KEY, or OPENAI_API_KEY.
---

# Watch Video for Pi

This skill turns a video into inputs Pi can inspect: sampled JPEG frames plus a timestamped transcript. It supports public URLs handled by `yt-dlp` and local video files. Treat this as the default video transcription skill whenever the user asks to transcribe, caption, subtitle, or extract spoken audio from a video.

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

Do not auto-install system packages. Ask the user to install missing dependencies or configure optional transcription fallback if needed. If only transcription fallback is missing, you may continue; videos with captions and frames still work.

3. Run the watch script:

```bash
python3 <skill-dir>/scripts/watch.py "<video-url-or-path>"
```

Useful options:

- `--start T` / `--end T` focus on a timestamp range (`SS`, `MM:SS`, or `HH:MM:SS`). Use this for long videos or questions about a specific moment. Focused ranges transcribe only the selected audio.
- `--max-frames N` lowers/raises the image budget, capped at 100.
- `--resolution W` changes frame width. Default is 512; use 1024 only when reading on-screen text matters.
- `--fps F` overrides automatic sampling, capped at 2 fps.
- `--transcription-provider remote|groq|openai` forces a transcription provider.
- `--transcription-language LANG` sends a language hint such as `pt`, `en`, or `auto`.
- `--whisper remote|groq|openai` is a backward-compatible alias for `--transcription-provider`.
- `--no-whisper` skips audio transcription fallback.
- `--out-dir DIR` keeps outputs in a chosen working directory.

4. Read every listed frame path with Pi's `read` tool. Use parallel reads when possible. The frame list is chronological and includes timestamps.

5. Answer the user's question using both evidence streams:

- Frames: visual content on screen.
- Transcript: spoken content or captions.

Cite timestamps when useful. If the video is long and the first pass is sparse, say so and offer to re-run a focused range.

6. Cleanup: the report prints a work directory. Delete it with `rm -rf <dir>` when follow-up questions are unlikely. Keep it if the user may ask more about the same video.

## Transcription provider decision guide

- Native captions are free, fast, and preferred when available.
- Remote Oracle/`whisper.cpp` is free and always-on if the user runs the included Docker server, but CPU transcription is slower.
- Groq is fast hosted Whisper; it requires an account/API key and free-tier/pricing can change.
- OpenAI is a reliable hosted fallback; it is usually paid API usage.
- Kaggle/local GPU can be added later by exposing the same OpenAI-compatible endpoint.

Recommended remote-first config in `~/.config/pi-watch-video/.env`:

```env
PI_WATCH_TRANSCRIPTION_ORDER=remote,groq,openai
PI_WATCH_TRANSCRIPTION_ENDPOINT=https://transcribe.example.com/v1/audio/transcriptions
PI_WATCH_TRANSCRIPTION_API_KEY=your-secret
PI_WATCH_TRANSCRIPTION_MODEL=small
PI_WATCH_TRANSCRIPTION_LANGUAGE=auto
PI_WATCH_TRANSCRIPTION_TIMEOUT=1800
PI_WATCH_TRANSCRIPTION_FALLBACK_ON_BUSY=0
PI_WATCH_TRANSCRIPTION_PREFLIGHT=1

GROQ_API_KEY=
OPENAI_API_KEY=
```

## Usage examples

```bash
python3 <skill-dir>/scripts/watch.py "https://youtu.be/example" --start 0:00 --end 0:30
python3 <skill-dir>/scripts/watch.py "~/Movies/bug-repro.mov" --resolution 1024
python3 <skill-dir>/scripts/watch.py "$URL" --max-frames 40 --no-whisper
python3 <skill-dir>/scripts/watch.py "$URL" --transcription-provider remote --transcription-language pt
```

## Limits

- Visual accuracy is best under 10 minutes or with focused `--start`/`--end` ranges.
- Frame extraction is capped at 100 frames and 2 fps to protect context budget.
- URL downloads are limited to what `yt-dlp` can access without private login state.
- Transcription providers receive extracted audio, not the full video. Focused ranges upload only focused audio.

## Security notes

This skill runs local Python scripts, `yt-dlp`, `ffmpeg`, and `ffprobe`. Optional transcription fallback sends extracted audio to the configured provider. API keys are read from environment variables or `~/.config/pi-watch-video/.env`.

The included Docker transcription server requires bearer-token auth and should be exposed with HTTPS through Caddy or Cloudflare Tunnel if used outside localhost.

## Credit

Inspired by Brad Automates' `claude-video`: https://github.com/bradautomates/claude-video. This is a Pi-oriented rewrite and package, not an official fork.
