# pi-watch-video browser fetch host

Optional sidecar for gated URLs when the Pi agent runs on a headless server/container.

This container hosts:

- noVNC HTML5 client
- Firefox profile for sacrificial login
- Python `yt-dlp` in a venv, with QuickJS for current YouTube JS challenges
- `ffmpeg`
- `rsync`
- optional WireGuard peer inside the container

## What it is for

Use this only when the agent cannot read your browser session locally.

Flow:

1. Open the HTML5 browser session over the VPN.
2. Log in once in Firefox with a dedicated account/profile.
3. The Pi skill SSHes to this host.
4. The host runs `yt-dlp --cookies-from-browser ...` inside the same container.
5. Raw media/subtitles are rsynced to the processing worker.

## Deploy

```bash
cd /opt/pi-watch-video/browser
cp .env.example .env
mkdir -p data/profile data/jobs wireguard
# copy your private wg0.conf into browser/wireguard/wg0.conf
# do not commit it
docker compose up -d --build
```

## Open the browser

Point another VPN peer at:

```text
http://<wireguard-ip>:14500/vnc.html
```

The container starts Firefox automatically. Log in once, then keep the profile volume.

## Remote fetch contract

The skill expects:

- container name from `PI_WATCH_REMOTE_FETCH_CONTAINER`
- host job directory from `PI_WATCH_REMOTE_FETCH_HOST_JOBS_DIR` (default `/opt/pi-watch-video/browser/data/jobs`)
- fetch command `/usr/local/bin/fetch-url <url> <job-id>`

That command writes a job directory containing:

- `source.*`
- `source.info.json`
- `source*.vtt` when available

## Security

- Use a dedicated browser account/profile.
- Keep the service on WireGuard only.
- Do not commit `wireguard/wg0.conf`.
- Do not reuse your personal daily browser profile.
