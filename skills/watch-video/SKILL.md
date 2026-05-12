---
name: watch-video
description: Watch, transcribe, and analyze a video URL or local video/audio file in Pi. Use when the user provides a video/audio link/path and asks to transcribe audio, extract captions/subtitles, produce a timestamped transcript, summarize it, inspect visuals, diagnose a screen recording, or answer questions about what happens in the media.
license: MIT
compatibility: Requires Python 3 plus local ffmpeg/ffprobe and yt-dlp. Audio transcription for media without captions requires one configured OpenAI-compatible endpoint; no hosted fallback providers are used.
---

# Watch Video for Pi

This skill turns media into inputs Pi can inspect: sampled JPEG frames plus a timestamped transcript. It supports public URLs handled by `yt-dlp` and local media files, including audio-only files.

Native captions are preferred when available. If captions are unavailable, transcription uses exactly one configured OpenAI-compatible endpoint from the user's private config. Do not use or suggest Groq/OpenAI fallback providers for this skill version.

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

Do not auto-install system packages. Ask the user to install missing dependencies or configure their private transcription endpoint if needed. If only the endpoint is missing, you may continue for videos with native captions or with `--no-whisper`.

3. Run the watch script:

```bash
python3 <skill-dir>/scripts/watch.py "<video-url-or-path>"
```

Useful options:

- `--start T` / `--end T` focus on a timestamp range (`SS`, `MM:SS`, or `HH:MM:SS`). Focused ranges transcribe only the selected audio.
- `--max-frames N` lowers/raises the image budget, capped at 100.
- `--resolution W` changes frame width. Default is 512; use 1024 only when reading on-screen text matters.
- `--fps F` overrides automatic sampling, capped at 2 fps.
- `--transcription-language LANG` sends a language hint such as `pt`, `en`, or `auto`.
- `--no-whisper` skips endpoint transcription.
- `--out-dir DIR` keeps outputs in a chosen working directory.

Deprecated compatibility flags `--transcription-provider` and `--whisper` may be accepted only as `endpoint` or `remote`; they do not select fallbacks.

4. Read every listed frame path with Pi's `read` tool. Use parallel reads when possible. The frame list is chronological and includes timestamps. Audio-only media will have no frames.

5. Answer the user's question using available evidence:

- Frames: visual content on screen.
- Transcript: spoken content or captions.

Cite timestamps when useful. If the video is long and the first pass is sparse, say so and offer to re-run a focused range.

6. Cleanup: the report prints a work directory. Delete it with `rm -rf <dir>` when follow-up questions are unlikely. Keep it if the user may ask more about the same media.

## Endpoint configuration

Configuration lives only in the user's private file:

```bash
~/.config/pi-watch-video/.env
```

Template:

```env
PI_WATCH_TRANSCRIPTION_ENDPOINT=
PI_WATCH_TRANSCRIPTION_API_KEY=
PI_WATCH_TRANSCRIPTION_MODEL=whisper
PI_WATCH_TRANSCRIPTION_LANGUAGE=auto
PI_WATCH_TRANSCRIPTION_TIMEOUT=1800
PI_WATCH_TRANSCRIPTION_PREFLIGHT=1
PI_WATCH_YTDLP_COOKIES=
```

Never commit `.env` files, endpoint URLs/IPs/hostnames, or API keys to the repository. If documenting examples, use placeholders only.

## Usage examples

```bash
python3 <skill-dir>/scripts/watch.py "https://youtu.be/example" --start 0:00 --end 0:30
python3 <skill-dir>/scripts/watch.py "~/Movies/bug-repro.mov" --resolution 1024
python3 <skill-dir>/scripts/watch.py "~/Downloads/voice-note.mp3" --transcription-language pt
python3 <skill-dir>/scripts/watch.py "$URL" --max-frames 40 --no-whisper
```

## Limits

- Visual accuracy is best under 10 minutes or with focused `--start`/`--end` ranges.
- Frame extraction is capped at 100 frames and 2 fps to protect context budget.
- URL downloads are limited to what `yt-dlp` can access without private login state unless a private cookies file is configured.
- The configured transcription endpoint receives extracted audio, not the full video. Focused ranges upload only focused audio.

## Security notes

This skill runs local Python scripts, `yt-dlp`, `ffmpeg`, and `ffprobe`. Endpoint transcription sends extracted audio to the configured endpoint. API keys and endpoint URLs are read from environment variables or `~/.config/pi-watch-video/.env` and should never be committed.

The included Docker transcription server requires bearer-token auth and should be exposed only on trusted networks or behind HTTPS.

## Credit

Inspired by Brad Automates' `claude-video`: https://github.com/bradautomates/claude-video. This is a Pi-oriented rewrite and package, not an official fork.
