# pi-watch-video

A Pi package that lets Pi analyze videos by turning a URL or local media file into sampled image frames plus a timestamped transcript.

This project is inspired by Brad Automates' [`claude-video`](https://github.com/bradautomates/claude-video). See [NOTICE.md](NOTICE.md) for credits.

## What it does

`pi-watch-video` gives Pi a repeatable video-inspection workflow:

1. Fetch a public video URL with `yt-dlp`, or use a local media file.
2. Optionally fetch a gated URL on a remote browser host that keeps a sacrificial Firefox profile.
3. Optionally offload heavy processing to a remote worker like Kinkaid.
4. Extract a duration-aware set of JPEG frames with `ffmpeg` when video is present.
5. Pull native captions when available.
6. If captions are unavailable, transcribe audio with exactly one configured OpenAI-compatible endpoint.
7. Ask Pi to read the generated frames and answer using visuals plus transcript.

There are no hosted fallback providers in the skill. Configure your own local/private endpoint once, and the skill uses only that endpoint for audio transcription.

## Install

```bash
pi install git:github.com/lenkard/pi-watch-video-remote
```

Or test from a local checkout:

```bash
pi install /path/to/pi-watch-video
```

## Modes

### 1) Local only

Everything runs where the Pi agent runs:

- local files
- public URLs
- `yt-dlp`
- `ffmpeg`
- `ffprobe`
- local/private transcription endpoint

### 2) Remote browser fetch

Use this when the Pi agent runs in a headless container and cannot reuse a local browser profile.

- HTML5 Firefox sidecar keeps a dedicated logged-in profile
- `yt-dlp --cookies-from-browser` runs inside that same browser container
- the skill rsyncs the fetched `source.*` bundle back to the agent or onward to a worker

See [`browser/README.md`](browser/README.md), [`docs/REMOTE_DEPLOY.md`](docs/REMOTE_DEPLOY.md), and [`docs/IMPLEMENTATION.md`](docs/IMPLEMENTATION.md).

### 3) Remote processing worker

Use this when the Pi agent should stay small and a worker like Kinkaid should do the heavy lifting.

- the agent stages or fetches the source bundle
- the bundle is rsynced to the worker
- the worker runs `process_bundle.py`
- frames/report are rsynced back so Pi can read them locally

## Requirements

### Local-only mode

- Python 3
- `ffmpeg` and `ffprobe`
- `yt-dlp`

### Remote browser fetch mode

On the agent host:

- Python 3
- `ssh`
- `rsync`

On the browser host:

- Docker
- browser sidecar from [`browser/`](browser/)

### Remote processing mode

On the agent host:

- Python 3
- `ssh`
- `rsync`

On the worker host:

- Python 3
- `ffmpeg` and `ffprobe`
- this repo checked out under `/opt/pi-watch-video` or set `PI_WATCH_REMOTE_PROCESS_SCRIPT` to the actual path
- Whisper access there, either through the existing endpoint config or the worker's own environment

Run the setup doctor for exact instructions:

```bash
python3 skills/watch-video/scripts/setup.py --doctor
```

## Configure the skill

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

PI_WATCH_YTDLP_COOKIES=

PI_WATCH_FETCH_MODE=local
PI_WATCH_REMOTE_FETCH_HOST=
PI_WATCH_REMOTE_FETCH_USER=
PI_WATCH_REMOTE_FETCH_PORT=22
PI_WATCH_REMOTE_FETCH_SSH_KEY=
PI_WATCH_REMOTE_FETCH_CONTAINER=
PI_WATCH_REMOTE_FETCH_HOST_JOBS_DIR=/opt/pi-watch-video/browser/data/jobs
PI_WATCH_REMOTE_FETCH_SCRIPT=/usr/local/bin/fetch-url
PI_WATCH_REMOTE_FETCH_KEEP=0

PI_WATCH_PROCESS_MODE=local
PI_WATCH_REMOTE_PROCESS_HOST=
PI_WATCH_REMOTE_PROCESS_USER=
PI_WATCH_REMOTE_PROCESS_PORT=22
PI_WATCH_REMOTE_PROCESS_SSH_KEY=
PI_WATCH_REMOTE_PROCESS_HOST_JOBS_DIR=/opt/pi-watch-video/jobs
PI_WATCH_REMOTE_PROCESS_SCRIPT=/opt/pi-watch-video/skills/watch-video/scripts/process_bundle.py
PI_WATCH_REMOTE_PROCESS_PYTHON=python3
PI_WATCH_REMOTE_PROCESS_KEEP=0
```

Security rules:

- Do not commit `.env` files.
- Do not commit browser profiles, cookies, VPN configs, SSH keys, endpoint URLs, or API keys.
- Use WireGuard/private networking for the browser host.
- Use a dedicated browser account/profile for gated sites.

## Browser host deployment

Quick start:

```bash
cd browser
cp .env.example .env
mkdir -p data/profile data/jobs wireguard
# copy your private wg0.conf to browser/wireguard/wg0.conf if the container owns WireGuard
docker compose up -d --build
```

Then open:

```text
http://<wireguard-ip>:14500/vnc.html
```

Log in once in Firefox. The fetch host keeps that profile and the skill reuses it through `yt-dlp --cookies-from-browser`.

## Optional local/private endpoint server

This repo also includes an OpenAI-compatible Docker transcription server in [`server/`](server/). It builds `whisper.cpp`, exposes `/v1/audio/transcriptions`, and can run on a local/private CPU machine.

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

The package also includes lightweight prompt aliases/helpers:

```text
/watch https://youtu.be/example what happens in the first 30 seconds?
/transcribe https://youtu.be/example summarize the spoken content
```

The skill will fetch/stage the media, generate a local `report.md`, and Pi should read the listed frame images before answering.

## Script usage

```bash
python3 skills/watch-video/scripts/watch.py "https://youtu.be/example"
python3 skills/watch-video/scripts/watch.py "screen-recording.mov" --start 0:20 --end 0:45
python3 skills/watch-video/scripts/watch.py "$URL" --max-frames 40 --resolution 1024
python3 skills/watch-video/scripts/watch.py "$URL" --transcription-language pt
python3 skills/watch-video/scripts/watch.py "audio.mp3" --no-whisper
```

Worker script:

```bash
python3 skills/watch-video/scripts/process_bundle.py /tmp/source-bundle --out-dir /tmp/result
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

## Remote architecture map

For the setup discussed here:

1. Pi agent stays on `srvpri`.
2. `/skill:watch-video URL` runs on the agent.
3. If `PI_WATCH_FETCH_MODE=remote_browser`, the skill SSHes to the browser host.
4. The browser host runs `docker exec <container> /usr/local/bin/fetch-url <url> <job-id>`.
5. The fetched `source.*` bundle is rsynced back or onward.
6. If `PI_WATCH_PROCESS_MODE=remote`, the skill rsyncs that bundle to Kinkaid.
7. Kinkaid runs `process_bundle.py` and returns `result/report.md` plus frames.
8. Pi reads the local returned frame paths and answers.

## Privacy and security

- Videos are downloaded/read locally or on your private browser host.
- Frames are written to a temporary work directory.
- API keys are never printed by the scripts.
- Audio transcription sends extracted audio only to your configured endpoint, not to any fallback provider.
- No platform login is used by default.
- Optional cookies are loaded only from your private config.
- Browser-host mode keeps the login inside a separate sacrificial profile.

## License

MIT. Credit to the original `claude-video` project is in [NOTICE.md](NOTICE.md).
