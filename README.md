# pi-watch-video

A Pi package that lets Pi analyze videos by turning a URL or local video file into sampled image frames plus a timestamped transcript.

This project is inspired by Brad Automates' [`claude-video`](https://github.com/bradautomates/claude-video). See [NOTICE.md](NOTICE.md) for credits.

## What it does

`pi-watch-video` gives Pi a repeatable video-inspection workflow:

1. Download a public video URL with `yt-dlp`, or use a local video file.
2. Extract a duration-aware set of JPEG frames with `ffmpeg`.
3. Pull native captions when available.
4. Fall back to configurable transcription providers when captions are unavailable.
5. Ask Pi to read the generated frames and answer using visuals plus transcript.

Transcription providers now include:

- OpenAI-compatible remote endpoint, e.g. the Docker `whisper.cpp` server in [`server/`](server/)
- Groq Whisper API
- OpenAI Whisper API

## Install

```bash
pi install git:github.com/lenkard/pi-watch-video-remote
```

Or test from a local checkout:

```bash
pi install /path/to/pi-watch-video
```

## Requirements

Required locally:

- Python 3
- `ffmpeg` and `ffprobe`
- `yt-dlp`

Optional for videos without captions:

- `PI_WATCH_TRANSCRIPTION_ENDPOINT` for a remote OpenAI-compatible transcription server
- `GROQ_API_KEY` for Groq Whisper (`whisper-large-v3`)
- `OPENAI_API_KEY` for OpenAI Whisper (`whisper-1`)

Run the setup doctor for exact instructions:

```bash
python3 skills/watch-video/scripts/setup.py --doctor
```

The setup script is intentionally instructional only. It does not install system packages for you.

## Transcription provider guide

- **Native captions:** free, fast, and preferred when available.
- **Remote Oracle/`whisper.cpp`:** free and always-on if you run an Oracle OCI ARM server, but CPU transcription is slower.
- **Groq:** fast hosted Whisper; requires an account/API key and free-tier/pricing may change.
- **OpenAI:** reliable hosted fallback; usually paid API usage.
- **Kaggle/local GPU:** not implemented here, but any service that exposes the same OpenAI-compatible endpoint can be used later.

## Configure transcription fallback

Create or edit:

```bash
~/.config/pi-watch-video/.env
```

Recommended remote-first example:

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

Short aliases such as `TRANSCRIPTION_ENDPOINT` are also accepted, but the prefixed names above are recommended.

If no remote endpoint is configured, the default order remains Groq then OpenAI when keys exist.

## Optional free remote server

This repo includes an OpenAI-compatible Docker transcription server in [`server/`](server/). It builds `whisper.cpp`, auto-downloads `small-q5_0`, and is documented for Oracle OCI ARM CPU.

Quick start:

```bash
cd server
cp .env.example .env
# edit API_KEY
docker compose up -d --build
```

Use HTTPS in production, preferably Caddy with a domain or Cloudflare Tunnel. See [`server/README.md`](server/README.md).

## Usage in Pi

Primary skill:

```text
/skill:watch-video https://youtu.be/example summarize the hook and visual structure
```

The package also includes a `watch` prompt template as a lightweight alias/helper:

```text
/watch https://youtu.be/example what happens in the first 30 seconds?
```

The skill will run the local scripts, then Pi should read the generated frame images before answering.

## Script usage

```bash
python3 skills/watch-video/scripts/watch.py "https://youtu.be/example"
python3 skills/watch-video/scripts/watch.py "screen-recording.mov" --start 0:20 --end 0:45
python3 skills/watch-video/scripts/watch.py "$URL" --max-frames 40 --resolution 1024
python3 skills/watch-video/scripts/watch.py "$URL" --transcription-provider remote --transcription-language pt
```

Options:

| Option | Purpose |
|---|---|
| `--start T`, `--end T` | Focus on a timestamp range (`SS`, `MM:SS`, or `HH:MM:SS`) |
| `--max-frames N` | Frame budget, capped at 100 |
| `--resolution W` | Extract frames at W pixels wide, default 512 |
| `--fps F` | Override automatic sampling, capped at 2 fps |
| `--transcription-provider remote\|groq\|openai` | Force a transcription backend |
| `--transcription-language LANG` | Optional language hint, e.g. `pt`, `en`, `auto` |
| `--whisper remote\|groq\|openai` | Backward-compatible alias for `--transcription-provider` |
| `--no-whisper` | Disable audio transcription fallback |
| `--out-dir DIR` | Keep outputs in a specific directory |

When `--start`/`--end` is used, only the focused audio range is transcribed and returned timestamps are offset back to the original video time. This matters for slow CPU servers.

## Frame budget

Short videos get denser frame coverage. Long videos are sampled sparsely to protect context budget.

| Duration | Default target |
|---|---:|
| ≤30s | about one frame/second |
| 30-60s | about 40 frames |
| 1-3min | about 60 frames |
| 3-10min | about 80 frames |
| >10min | up to max frame cap |

Use `--start` and `--end` for long videos or precise questions.

## Privacy and security

- Videos are downloaded/read locally.
- Frames are written to a temporary work directory.
- API keys are never printed by the scripts.
- Transcription fallback uploads extracted audio only, not the full video.
- Focused ranges upload only the focused audio segment.
- The included remote server requires bearer-token auth and deletes uploads by default.
- No platform login or cookies are used by default.

## Roadmap

- Add a Pi extension that registers a dedicated `watch_video` tool.
- Add richer JSON output for custom automation.
- Add better subtitle language selection.
- Add tests around timestamp parsing and VTT cleanup.
- Add optional `faster-whisper` GPU endpoint compatible with Kaggle/local GPU.

## License

MIT. Credit to the original `claude-video` project is in [NOTICE.md](NOTICE.md).
