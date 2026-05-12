# pi-watch-video 0.2.0 final report

## Summary

Version 0.2.0 changes the transcription model from provider fallback chains to a single configured OpenAI-compatible endpoint.

The package now:

- uses native captions first when they exist,
- otherwise sends extracted audio only to `PI_WATCH_TRANSCRIPTION_ENDPOINT`,
- does not contain Groq/OpenAI/local faster-whisper fallback selection,
- supports audio-only local files,
- keeps endpoint URLs, IPs, API keys, and `.env` files out of the repository.

## Configuration

Private user config belongs in:

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

Do not commit filled config files or local endpoint values.

## Changed files

- `skills/watch-video/scripts/whisper_api.py`
  - Replaced provider-order/fallback code with one endpoint client.
  - Removed hosted provider constants and local faster-whisper execution path.
  - Fails fast if the endpoint is missing or returns an error.

- `skills/watch-video/scripts/setup.py`
  - Doctor now checks for one configured endpoint.
  - Generated config template no longer includes fallback providers.

- `skills/watch-video/scripts/watch.py`
  - CLI help now describes the configured endpoint.
  - Deprecated provider flags accept only `endpoint`/`remote` compatibility aliases.
  - Audio-only media remains supported.

- `skills/watch-video/scripts/media_source.py`
  - Supports optional private `PI_WATCH_YTDLP_COOKIES` without committing cookies.

- `skills/watch-video/scripts/video_frames.py`
  - Reports whether media actually has video, allowing audio-only files to skip frame extraction.

- `README.md`, `skills/watch-video/SKILL.md`, `server/README.md`, `docs/ANALYSIS.md`
  - Updated docs to describe the single-endpoint design and security rules.

- `package.json`, `package-lock.json`
  - Version set to `0.2.0`.

## Tests run

```bash
python3 -m py_compile skills/watch-video/scripts/*.py
python3 skills/watch-video/scripts/setup.py --check
python3 skills/watch-video/scripts/watch.py /home/coder/SABRINA/watch-test-fixed/audio.mp3 --transcription-language pt --out-dir /tmp/pi-watch-v020-test
python3 skills/watch-video/scripts/watch.py /tmp/pi-watch-v020-sample.mp4 --transcription-language pt --max-frames 3 --out-dir /tmp/pi-watch-v020-video-test
```

Results:

- Python compile: passed.
- Setup preflight: passed with private local endpoint config present.
- Audio-only transcription: passed, transcript source `whisper/endpoint`.
- Video + frames + transcription: passed, 3 frames extracted and transcript source `whisper/endpoint`.
- Repository scan: no private endpoint IP, host name, GPU model, API key assignment, or committed `.env` file found.

## Release

Release tag: `v0.2.0`
