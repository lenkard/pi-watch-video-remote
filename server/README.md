# pi-watch-video transcription server

OpenAI-compatible transcription endpoint for `pi-watch-video`.

This server exposes:

- `GET /health`
- `GET /ready`
- `GET /v1/models`
- `POST /v1/audio/transcriptions`

The transcription endpoint accepts OpenAI-style multipart requests and returns `verbose_json` or `text`.

## Quick start

```bash
cd server
cp .env.example .env
# edit API_KEY and any local-only settings
nano .env
docker compose up -d --build
```

The first start downloads the default model into `server/models/`:

```text
ggml-small-q5_0.bin
```

Check readiness:

```bash
curl -H "Authorization: Bearer $API_KEY" http://localhost:8000/ready
```

Transcribe:

```bash
curl -s \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@audio.mp3 \
  -F model=small \
  -F response_format=verbose_json \
  http://localhost:8000/v1/audio/transcriptions
```

## Configure pi-watch-video

On the machine running Pi, configure the private file `~/.config/pi-watch-video/.env`:

```env
PI_WATCH_TRANSCRIPTION_ENDPOINT=https://your-private-endpoint.example/v1/audio/transcriptions
PI_WATCH_TRANSCRIPTION_API_KEY=your-server-api-key
PI_WATCH_TRANSCRIPTION_MODEL=small
PI_WATCH_TRANSCRIPTION_LANGUAGE=auto
PI_WATCH_TRANSCRIPTION_TIMEOUT=1800
PI_WATCH_TRANSCRIPTION_PREFLIGHT=1
```

Do not commit endpoint values or API keys. The repository must contain placeholders only.

## Production exposure

Do not expose the service over public plain HTTP. Use HTTPS plus bearer auth.

### Caddy with a domain

```bash
cd server
cp Caddyfile.example Caddyfile
# edit transcribe.example.com
docker compose -f docker-compose.caddy.yml up -d --build
```

### No domain / no open ports

Use a private network or tunnel and point it at `http://transcriber:8000` or `http://localhost:8000` depending on your setup.

## Models

Default aliases:

| Alias | File |
|---|---|
| `small`, `small-q5_0` | `/models/ggml-small-q5_0.bin` |
| `base`, `base-q5_0` | `/models/ggml-base-q5_0.bin` |
| `medium`, `medium-q5_0` | `/models/ggml-medium-q5_0.bin` |

Only `small-q5_0` is auto-downloaded by default. Mount other models into `server/models/` before requesting them.

## Limits and privacy

Defaults:

```env
MAX_UPLOAD_MB=200
MAX_AUDIO_SECONDS=3600
KEEP_UPLOADS=0
```

Uploads and intermediate files are deleted after each request unless `KEEP_UPLOADS=1`.

## Notes

- The server runs one transcription at a time. If busy, it returns HTTP 429.
- Uploaded audio is normalized to 16kHz mono WAV before `whisper-cli` runs.
- Any GPU/local implementation can replace this server if it exposes the same OpenAI-compatible API.
