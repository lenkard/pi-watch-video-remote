# Implementation notes: making `watch-video` work as the default media skill

This document explains what changed in this repo to make Pi handle video/audio URLs and local media with one repeatable workflow.

## Goal

Make this package cover the real deployment:

- Pi agent runs on `srvpri`
- gated video fetch happens on a separate browser host
- heavy processing happens on `kinkaid`
- Pi still reads the final report and frames locally on the agent host

## What was missing

The older repo already handled:

- local files
- public URLs via `yt-dlp`
- frame extraction via `ffmpeg`
- captions when present
- Whisper through one configured OpenAI-compatible endpoint

But for this deployment it was still missing two practical pieces:

1. a remote browser-backed fetch path for login-gated URLs
2. a remote processing path so the agent host does not need local `ffmpeg` or Whisper

## Main code changes

### 1) Shared config loader

Added:

- `skills/watch-video/scripts/config.py`

Why:

- one place to read `~/.config/pi-watch-video/.env`
- one place for integer parsing and boolean parsing

### 2) Split the pipeline into fetch and process stages

Added:

- `skills/watch-video/scripts/process_bundle.py`

Why:

- the old flow was too local-only
- `process_bundle.py` lets the source bundle be staged anywhere, then processed separately

What it does:

- reads `source.*`
- probes media
- extracts frames when video exists
- reads subtitles when present
- falls back to Whisper when needed
- writes `report.md`

### 3) Remote browser fetch support

Added:

- `skills/watch-video/scripts/remote_fetch.py`
- `browser/`

Why:

- the Pi agent container cannot reuse a desktop browser profile
- `yt-dlp --cookies-from-browser` works best when `yt-dlp` and the sacrificial browser profile live in the same environment

How it works:

- Pi SSHes to the browser host
- Pi runs `docker exec pi-watch-browser /usr/local/bin/fetch-url <url> <job-id>`
- the browser container downloads `source.*`, `source.info.json`, and subtitles into a job dir
- Pi rsyncs that job dir back

### 4) Remote worker processing support

Added:

- `skills/watch-video/scripts/remote_process.py`

Why:

- Kinkaid already has the heavy processing resources and Whisper endpoint

How it works:

- Pi rsyncs the staged source bundle to Kinkaid
- Pi runs `process_bundle.py` there over SSH
- Pi rsyncs the `result/` bundle back
- Pi reads the returned local frame paths

### 5) `watch.py` became an orchestrator

Changed:

- `skills/watch-video/scripts/watch.py`

Old shape:

- mostly local all-in-one behavior

New shape:

- choose local or remote fetch
- choose local or remote processing
- print the final local report

### 6) Local fetch script still works

Changed:

- `skills/watch-video/scripts/media_source.py`

Why:

- keep the simple path for public URLs and local files
- only switch to remote fetch when configured

## Browser host implementation

Added:

- `browser/Dockerfile`
- `browser/docker-compose.yml`
- `browser/entrypoint.sh`
- `browser/launch-browser.sh`
- `browser/fetch.sh`
- `browser/.env.example`
- `browser/README.md`

## Why the browser host uses noVNC instead of Xpra

The requested direction started with Xpra, but on the actual target stack:

- host architecture is arm64
- base image is Debian trixie
- `xpra` was not available as a usable package there

So the repo now uses the shortest working HTML5 browser path on trixie:

- `Xvfb`
- `x11vnc`
- `websockify`
- `noVNC`
- Firefox ESR

That keeps the browser host:

- HTML5-accessible
- browser-profile-persistent
- containerized
- compatible with WireGuard binding

## Why the browser host now uses Python `yt-dlp`

The Debian `yt-dlp` package on the target host was too old for current YouTube behavior and only returned storyboard images for some videos.

The practical fix is:

- install `quickjs`
- create a Python venv in the browser image
- install `yt-dlp[default]` there
- run it with `--js-runtimes quickjs`

Why this works:

- current `yt-dlp` ships the matching `yt_dlp_ejs` challenge solver package
- QuickJS satisfies yt-dlp's current YouTube JS challenge requirement
- the venv avoids Debian's system-package restrictions while staying simple

## Remote worker implementation

Kinkaid already had Whisper running in a container.

So the repo keeps the lazy split:

- Whisper stays containerized on Kinkaid
- `process_bundle.py` runs on the Kinkaid host

Why not add another container for `process_bundle.py` too?

- it would duplicate mounts and job plumbing
- the host script is enough because it only needs Python, `ffmpeg`, and access to the local Whisper endpoint

## Skill routing improvements

Changed:

- `skills/watch-video/SKILL.md`
- `prompts/watch.md`

Added:

- `prompts/transcribe.md`

Why:

Pi has no hard "default skill" switch.

So the repo biases routing the normal Pi way:

- make the skill description explicit for transcription/video-analysis use cases
- add `/watch`
- add `/transcribe`

That gives both:

- better automatic matching
- explicit commands when the user wants to force the skill

## Setup and docs changes

Changed:

- `skills/watch-video/scripts/setup.py`
- `README.md`
- `.gitignore`

Added:

- `docs/REMOTE_DEPLOY.md`
- this file

Why:

- the repo needed to explain the real three-host deployment
- the setup checker needed to understand local vs remote fetch/process modes
- browser job data and WireGuard config should stay ignored

## Resulting architecture

1. User asks Pi to transcribe or analyze a media URL/file.
2. Pi loads `watch-video`.
3. If needed, Pi fetches the URL on the browser host.
4. Pi stages a source bundle locally.
5. If configured, Pi ships the bundle to Kinkaid.
6. Kinkaid extracts frames and/or transcript.
7. Pi gets the result bundle back.
8. Pi reads local returned frame files and answers.

## What to use in Pi

Recommended commands:

- `/transcribe <url-or-path>`
- `/watch <url-or-path> [question]`
- `/skill:watch-video <url-or-path> [question]`

## Versioning note

This repo version should be bumped when these remote-fetch and remote-process changes are released, because this is a real capability expansion, not just a docs tweak.
