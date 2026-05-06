# Final report: remote transcription deployment plan implemented

## Summary

Implemented the planned OpenAI-compatible remote transcription architecture for `pi-watch-video`.

The project now supports:

- Native captions first.
- Configurable transcription provider priority.
- Remote OpenAI-compatible transcription endpoint.
- Existing Groq and OpenAI fallback support.
- Focused-range transcription for `--start` / `--end`.
- A Dockerized `whisper.cpp` transcription server intended for Oracle OCI ARM CPU.
- Production documentation for HTTPS exposure with Caddy or Cloudflare Tunnel.

## Client changes

Updated:

- `skills/watch-video/scripts/watch.py`
- `skills/watch-video/scripts/whisper_api.py`
- `skills/watch-video/scripts/setup.py`
- `skills/watch-video/SKILL.md`
- `README.md`

Added CLI options:

```bash
--transcription-provider remote|groq|openai
--transcription-language pt
```

Kept backward compatibility:

```bash
--whisper remote|groq|openai
```

If both are passed, `--transcription-provider` wins.

## Configuration

Primary config variables documented:

```env
PI_WATCH_TRANSCRIPTION_ORDER=remote,groq,openai
PI_WATCH_TRANSCRIPTION_ENDPOINT=https://transcribe.example.com/v1/audio/transcriptions
PI_WATCH_TRANSCRIPTION_API_KEY=your-secret
PI_WATCH_TRANSCRIPTION_MODEL=small
PI_WATCH_TRANSCRIPTION_LANGUAGE=auto
PI_WATCH_TRANSCRIPTION_TIMEOUT=1800
PI_WATCH_TRANSCRIPTION_FALLBACK_ON_BUSY=0
PI_WATCH_TRANSCRIPTION_PREFLIGHT=1
```

Short aliases are accepted. Existing `GROQ_API_KEY` and `OPENAI_API_KEY` still work.

## Focused transcription

When `--start` or `--end` is used, the script now extracts only the focused audio range before uploading it to a transcription provider. Returned segment timestamps are offset back to original video time.

This makes the free Oracle ARM CPU path much more practical for long videos.

## Server added

Added:

```text
server/
  Dockerfile
  docker-compose.yml
  docker-compose.caddy.yml
  Caddyfile.example
  .env.example
  README.md
  requirements.txt
  app/main.py
```

The server exposes:

```http
GET /health
GET /ready
GET /v1/models
POST /v1/audio/transcriptions
```

It accepts OpenAI-style multipart upload and supports:

```text
response_format=verbose_json
response_format=text
response_format=json
```

Unsupported formats return HTTP 400.

## Server backend

Phase 1 backend:

```text
whisper.cpp via whisper-cli subprocess
```

Docker builds `whisper.cpp` from a pinned tag.

Default model:

```text
small-q5_0
```

Auto-downloads:

```text
/models/ggml-small-q5_0.bin
```

Supported aliases:

```text
small, small-q5_0
base, base-q5_0
medium, medium-q5_0
```

Only the default model auto-downloads. Other model files must be mounted into `server/models/`.

## Server safety defaults

```env
MAX_UPLOAD_MB=200
MAX_AUDIO_SECONDS=3600
MAX_CONCURRENT=1 behavior via semaphore
KEEP_UPLOADS=0
```

If busy, the server returns HTTP 429. The client default is not to silently fallback to Groq/OpenAI on 429 unless configured.

Uploads and generated files are deleted by default.

## Production exposure

Documentation recommends HTTPS, not direct public HTTP:

- Caddy with a domain via `docker-compose.caddy.yml`
- Cloudflare Tunnel when no domain/open port is desired

Bearer-token auth is required by default.

## Validation performed

Ran Python syntax compilation:

```bash
python3 -m py_compile skills/watch-video/scripts/*.py server/app/main.py
```

Ran CLI/help checks:

```bash
python3 skills/watch-video/scripts/watch.py --help
python3 skills/watch-video/scripts/setup.py --json
```

## Credits

The README and skill docs continue to credit Brad Automates' `claude-video` as the inspiration, and `NOTICE.md` remains in place.

## Not included in Phase 1

- Kaggle endpoint implementation.
- `faster-whisper` GPU backend.
- Multi-arch image publishing pipeline.

The OpenAI-compatible API makes these straightforward future additions.
