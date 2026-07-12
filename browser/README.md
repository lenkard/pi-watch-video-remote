# pi-watch-video browser fetch host

Optional sidecar for gated URLs when the Pi agent runs on a headless server/container.

This container hosts:

- noVNC HTML5 client
- Firefox profile for sacrificial login
- Python `yt-dlp` in a venv, with QuickJS for current YouTube JS challenges and `curl_cffi` impersonation support
- `ffmpeg`
- `rsync`
- optional WireGuard peer inside the container

## What it is for

Use this only when the agent cannot read your browser session locally.

This is a `yt-dlp` fetch container, not a browser-first downloader. Firefox exists here mainly to hold the dedicated logged-in profile that `yt-dlp` reads for credentials. A browser-native fetch path is optional fallback only.

Flow:

1. Open the HTML5 browser session over the VPN.
2. Log in once in Firefox with a dedicated account/profile.
3. The Pi skill SSHes to this host.
4. The host runs `yt-dlp --cookies-from-browser ...` inside the same container, using the dedicated Firefox profile as the credential source.
5. If `yt-dlp` fails and `BROWSER_FETCH_FALLBACK_SCRIPT` points to an executable, that browser-native fallback runs second.
6. Raw media/subtitles are rsynced to the processing worker.

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

Optional browser-native fallback:

- set `BROWSER_FETCH_FALLBACK_SCRIPT` to an executable path inside the container
- it will be called as `<script> <url> <output-dir>` only after `yt-dlp` fails
- leave it empty to keep the repo on pure `yt-dlp` fetches

That command writes a job directory containing:

- `source.*`
- `source.info.json`
- `source*.vtt` when available

## Security

- Use a dedicated browser account/profile.
- Keep the service on WireGuard only.
- Do not commit `wireguard/wg0.conf`.
- Do not reuse your personal daily browser profile.
