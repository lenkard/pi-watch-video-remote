# Remote deploy plan

## Goal

Keep the Pi agent on `srvpri`, use a private browser sidecar for gated fetches, and use Kinkaid as the heavy worker.

## Hosts

### `srvpri`
- Pi agent container
- this skill
- local final `result/` bundle that Pi reads

### browser host
- `browser/` Docker compose stack
- HTML5 browser sidecar
- Firefox profile on a persistent volume
- `yt-dlp` fetches via `--cookies-from-browser`
- WireGuard peer in the container

### `kinkaid`
- this repo checked out at `/opt/pi-watch-video`
- `ffmpeg` / `ffprobe`
- Whisper endpoint or local/private endpoint config
- runs `skills/watch-video/scripts/process_bundle.py`

## Flow

1. User runs `/skill:watch-video <url>` on the agent.
2. `watch.py` stages local files directly or calls `remote_fetch.py` for URLs when `PI_WATCH_FETCH_MODE=remote_browser`.
3. `remote_fetch.py` SSHes to the browser host and runs `docker exec <container> /usr/local/bin/fetch-url <url> <job-id>`.
4. The fetched `source.*` bundle is rsynced back to the agent work dir.
5. If `PI_WATCH_PROCESS_MODE=remote`, `remote_process.py` rsyncs that source bundle to Kinkaid.
6. Kinkaid runs `process_bundle.py` and writes `result/report.md` plus frames.
7. `remote_process.py` rsyncs `result/` back to the agent work dir.
8. Pi reads the local returned frame paths and answers.

## Deploy order

1. Deploy `browser/` on the browser host.
2. Log in once through the HTML5 browser session with the sacrificial browser account.
3. Deploy this repo on Kinkaid at `/opt/pi-watch-video`.
4. Install `ffmpeg`/`ffprobe` and Whisper access on Kinkaid.
5. Add SSH keys from the agent host to the browser host and Kinkaid.
6. Fill `~/.config/pi-watch-video/.env` on the agent host.
7. Run `python3 skills/watch-video/scripts/setup.py --doctor` on the agent host.
8. Run a small URL through `/skill:watch-video`.

## Minimum env on the agent host

```env
PI_WATCH_FETCH_MODE=remote_browser
PI_WATCH_REMOTE_FETCH_HOST=
PI_WATCH_REMOTE_FETCH_USER=
PI_WATCH_REMOTE_FETCH_PORT=22
PI_WATCH_REMOTE_FETCH_SSH_KEY=
PI_WATCH_REMOTE_FETCH_CONTAINER=pi-watch-browser
PI_WATCH_REMOTE_FETCH_HOST_JOBS_DIR=/opt/pi-watch-video/browser/data/jobs

PI_WATCH_PROCESS_MODE=remote
PI_WATCH_REMOTE_PROCESS_HOST=
PI_WATCH_REMOTE_PROCESS_USER=
PI_WATCH_REMOTE_PROCESS_PORT=22
PI_WATCH_REMOTE_PROCESS_SSH_KEY=
PI_WATCH_REMOTE_PROCESS_HOST_JOBS_DIR=/opt/pi-watch-video/jobs
PI_WATCH_REMOTE_PROCESS_SCRIPT=/opt/pi-watch-video/skills/watch-video/scripts/process_bundle.py
PI_WATCH_REMOTE_PROCESS_PYTHON=python3
```
