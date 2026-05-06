# pi-watch-video

A Pi package that lets Pi analyze videos by turning a URL or local video file into sampled image frames plus a timestamped transcript.

This project is inspired by Brad Automates' [`claude-video`](https://github.com/bradautomates/claude-video). See [NOTICE.md](NOTICE.md) for credits.

## What it does

`pi-watch-video` gives Pi a repeatable video-inspection workflow:

1. Download a public video URL with `yt-dlp`, or use a local video file.
2. Extract a duration-aware set of JPEG frames with `ffmpeg`.
3. Pull native captions when available.
4. Fall back to Whisper transcription through Groq or OpenAI when configured.
5. Ask Pi to read the generated frames and answer using visuals plus transcript.

## Install

```bash
pi install git:github.com/lenkard/pi-watch-video
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

- `GROQ_API_KEY` for Groq Whisper (`whisper-large-v3`), preferred
- `OPENAI_API_KEY` for OpenAI Whisper (`whisper-1`), fallback

Run the setup doctor for exact instructions:

```bash
python3 skills/watch-video/scripts/setup.py --doctor
```

The setup script is intentionally instructional only. It does not install system packages for you.

## Configure Whisper fallback

Create or edit:

```bash
~/.config/pi-watch-video/.env
```

Example:

```env
GROQ_API_KEY=
OPENAI_API_KEY=
```

Environment variables with the same names also work. Whisper is used only when captions are unavailable, unless you force a provider with `--whisper`.

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
```

Options:

| Option | Purpose |
|---|---|
| `--start T`, `--end T` | Focus on a timestamp range (`SS`, `MM:SS`, `HH:MM:SS`) |
| `--max-frames N` | Frame budget, capped at 100 |
| `--resolution W` | Extract frames at W pixels wide, default 512 |
| `--fps F` | Override automatic sampling, capped at 2 fps |
| `--whisper groq\|openai` | Force a transcription backend |
| `--no-whisper` | Disable audio transcription fallback |
| `--out-dir DIR` | Keep outputs in a specific directory |

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
- Whisper fallback uploads extracted audio only, not the full video.
- No platform login or cookies are used by default.

## Roadmap

- Add a Pi extension that registers a dedicated `watch_video` tool.
- Add richer JSON output for custom automation.
- Add better subtitle language selection.
- Add tests around timestamp parsing and VTT cleanup.

## License

MIT. Credit to the original `claude-video` project is in [NOTICE.md](NOTICE.md).
