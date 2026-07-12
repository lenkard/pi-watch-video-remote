---
name: watch-video
description: Default media transcription and video-understanding skill for Pi. Use whenever the user provides a video/audio URL or local media file and asks to transcribe speech, extract captions/subtitles, produce a timestamped transcript, summarize a video, inspect visuals, diagnose a screen recording, or answer questions about what happens in the media.
license: MIT
compatibility: Requires Python 3 plus local ffmpeg/ffprobe and yt-dlp for local mode. Remote mode can fetch through an HTML5 browser host and process through a worker like Kinkaid.
---

# Watch Video for Pi

This skill turns media into inputs Pi can inspect: sampled JPEG frames plus a timestamped transcript. It supports public URLs handled by `yt-dlp`, local media files, and remote browser-backed fetching for gated URLs.

Native captions are preferred when available. If captions are unavailable, transcription uses exactly one configured OpenAI-compatible endpoint unless heavy processing has been delegated to a remote worker.

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

Do not auto-install system packages.

3. Run the watch script:

```bash
python3 <skill-dir>/scripts/watch.py "<video-url-or-path>"
```

Useful options:

- `--start T` / `--end T` focus on a timestamp range (`SS`, `MM:SS`, or `HH:MM:SS`).
- `--max-frames N` lowers/raises the image budget, capped at 100.
- `--resolution W` changes frame width. Default is 512; use 1024 only when reading on-screen text matters.
- `--fps F` overrides automatic sampling, capped at 2 fps.
- `--transcription-language LANG` sends a language hint such as `pt`, `en`, or `auto`.
- `--no-whisper` skips endpoint transcription.
- `--out-dir DIR` keeps outputs in a chosen working directory.

4. Read every listed frame path with Pi's `read` tool. Use parallel reads when possible. The frame list is chronological and includes timestamps. Audio-only media will have no frames.

5. Default delivery rules:

- If the user asked to transcribe, deliver the generated `transcript.srt` path first.
- Only inspect/read frames when the user asked for visual analysis or a video question.
- Use `transcript.txt` or the report only as helpers.

If the user asked a question beyond transcription, answer it using:

- Frames: visual content on screen.
- Transcript: spoken content or captions.

Cite timestamps when useful. If the video is long and the first pass is sparse, say so and offer to re-run a focused range.

6. Cleanup: the report prints a work directory. Delete it with `rm -rf <dir>` when follow-up questions are unlikely. Keep it if the user may ask more about the same media.

## Remote browser fetch mode

Set this when the agent runs in a headless container and cannot reuse a browser session:

```env
PI_WATCH_FETCH_MODE=remote_browser
PI_WATCH_REMOTE_FETCH_HOST=
PI_WATCH_REMOTE_FETCH_USER=
PI_WATCH_REMOTE_FETCH_PORT=22
PI_WATCH_REMOTE_FETCH_SSH_KEY=
PI_WATCH_REMOTE_FETCH_CONTAINER=
PI_WATCH_REMOTE_FETCH_HOST_JOBS_DIR=/opt/pi-watch-video/browser/data/jobs
```

The skill SSHes to the browser host, runs `docker exec <container> /usr/local/bin/fetch-url <url> <job-id>`, then rsyncs the fetched `source.*` bundle back.

## Remote processing mode

Set this when a worker like Kinkaid should do frame extraction/transcription:

```env
PI_WATCH_PROCESS_MODE=remote
PI_WATCH_REMOTE_PROCESS_HOST=
PI_WATCH_REMOTE_PROCESS_USER=
PI_WATCH_REMOTE_PROCESS_PORT=22
PI_WATCH_REMOTE_PROCESS_SSH_KEY=
PI_WATCH_REMOTE_PROCESS_HOST_JOBS_DIR=/opt/pi-watch-video/jobs
PI_WATCH_REMOTE_PROCESS_SCRIPT=/opt/pi-watch-video/skills/watch-video/scripts/process_bundle.py
PI_WATCH_REMOTE_PROCESS_PYTHON=python3
```

The agent rsyncs the staged bundle to the worker, the worker runs `process_bundle.py`, and the result bundle is rsynced back so Pi can read the frames locally.

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

Never commit `.env` files, endpoint URLs/IPs/hostnames, browser profiles, VPN configs, or API keys to the repository.

## Limits

- Visual accuracy is best under 10 minutes or with focused `--start`/`--end` ranges.
- Frame extraction is capped at 100 frames and 2 fps to protect context budget.
- URL downloads are limited to what `yt-dlp` can access without private login state unless a private cookies file is configured or remote browser mode is enabled.
- Browser-host mode still depends on the remote browser session staying logged in.
- DRM-protected sites remain out of scope.

## Security notes

This skill runs local Python scripts, `yt-dlp`, `ffmpeg`, and `ffprobe`, plus optional `ssh`/`rsync` to private hosts. Endpoint transcription sends extracted audio to the configured endpoint. API keys, browser profiles, SSH keys, and VPN configs should never be committed.

The included browser sidecar should be reachable only over trusted networking such as WireGuard.

## Credit

Inspired by Brad Automates' `claude-video`: https://github.com/bradautomates/claude-video. This is a Pi-oriented rewrite and package, not an official fork.
