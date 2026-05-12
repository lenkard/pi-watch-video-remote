# pi-watch-video

A Pi package that lets Pi analyze videos by turning a URL or local video file into sampled image frames plus a timestamped transcript.

This project is inspired by Brad Automates' [`claude-video`](https://github.com/bradautomates/claude-video). See [NOTICE.md](NOTICE.md) for credits.

## What it does

`pi-watch-video` gives Pi a repeatable video-inspection workflow:

1. Download a public video URL with `yt-dlp`, or use a local media file.
2. Extract a duration-aware set of JPEG frames with `ffmpeg` when video is present.
3. Pull native captions when available.
4. If captions are unavailable, transcribe audio with exactly one configured OpenAI-compatible endpoint.
5. Ask Pi to read the generated frames and answer using visuals plus transcript.

There are no hosted fallback providers in the skill. Configure your own local/private endpoint once, and the skill uses only that endpoint for audio transcription.

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

Required for videos without captions:

- `PI_WATCH_TRANSCRIPTION_ENDPOINT` pointing at an OpenAI-compatible `/v1/audio/transcriptions` endpoint
- `PI_WATCH_TRANSCRIPTION_API_KEY` if the endpoint requires bearer auth

Run the setup doctor for exact instructions:

```bash
python3 skills/watch-video/scripts/setup.py --doctor
```

The setup script is instructional only. It does not install system packages or write endpoint secrets into the repository.

## Configure transcription

Create or edit this private file on the machine running Pi:

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

# Optional yt-dlp cookies file for private/subscriber videos.
PI_WATCH_YTDLP_COOKIES=
```

Security rules:

- Do not commit `.env` files.
- Do not commit private endpoint IPs, hostnames, URLs, or API keys.
- Use HTTPS plus bearer auth if the endpoint is reachable outside a private machine/network.

## Optional local/private endpoint server

This repo includes an OpenAI-compatible Docker transcription server in [`server/`](server/). It builds `whisper.cpp`, exposes `/v1/audio/transcriptions`, and can run on a local/private CPU machine. A GPU implementation can also be used as long as it exposes the same OpenAI-compatible API.

Quick start:

```bash
cd server
cp .env.example .env
# edit API_KEY and other local-only values
docker compose up -d --build
```

Do not commit `server/.env`. See [`server/README.md`](server/README.md).

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
python3 skills/watch-video/scripts/watch.py "$URL" --transcription-language pt
python3 skills/watch-video/scripts/watch.py "audio.mp3" --no-whisper
```

Options:

| Option | Purpose |
|---|---|
| `--start T`, `--end T` | Focus on a timestamp range (`SS`, `MM:SS`, or `HH:MM:SS`) |
| `--max-frames N` | Frame budget, capped at 100 |
| `--resolution W` | Extract frames at W pixels wide, default 512 |
| `--fps F` | Override automatic sampling, capped at 2 fps |
| `--transcription-language LANG` | Optional language hint, e.g. `pt`, `en`, `auto` |
| `--no-whisper` | Disable audio transcription when captions are unavailable |
| `--out-dir DIR` | Keep outputs in a specific directory |

`--transcription-provider` and `--whisper` are retained only as deprecated aliases; this version supports only the configured endpoint.

When `--start`/`--end` is used, only the focused audio range is transcribed and returned timestamps are offset back to the original video time.

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
- Audio transcription sends extracted audio only to your configured endpoint, not to any fallback provider.
- Focused ranges upload only the focused audio segment.
- No platform login or cookies are used by default.
- Optional cookies are loaded only from your private `PI_WATCH_YTDLP_COOKIES` path.

## Roadmap

- Add a Pi extension that registers a dedicated `watch_video` tool.
- Add richer JSON output for custom automation.
- Add better subtitle language selection.
- Add tests around timestamp parsing and VTT cleanup.

## License

MIT. Credit to the original `claude-video` project is in [NOTICE.md](NOTICE.md).
