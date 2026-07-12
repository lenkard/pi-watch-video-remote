#!/bin/sh
set -eu

URL=${1:?usage: fetch-url <url> [job-id>]}
JOB_ID=${2:-job-$(date +%s)}
JOBS_DIR=${JOBS_DIR:-/data/jobs}
PROFILE_DIR=${PROFILE_DIR:-/data/profile}
BROWSER=${BROWSER:-firefox}
SUB_LANGS=${SUB_LANGS:-en,en-US,en-GB,en-orig}
OUTPUT_DIR="$JOBS_DIR/$JOB_ID"
TEMPLATE="$OUTPUT_DIR/source.%(ext)s"
FALLBACK_SCRIPT=${BROWSER_FETCH_FALLBACK_SCRIPT:-}

mkdir -p "$OUTPUT_DIR" "$PROFILE_DIR"
yt-dlp --version > "$OUTPUT_DIR/source.ytdlp-version.txt"

if [ -n "${YTDLP_BROWSER_SPEC:-}" ]; then
  COOKIE_SPEC=$YTDLP_BROWSER_SPEC
else
  case "$BROWSER" in
    firefox*) COOKIE_SPEC="firefox:$PROFILE_DIR" ;;
    chromium*|chrome*) COOKIE_SPEC="chromium:$PROFILE_DIR" ;;
    *) echo "unsupported BROWSER=$BROWSER" >&2; exit 2 ;;
  esac
fi

if yt-dlp \
  --js-runtimes quickjs \
  --no-playlist \
  --merge-output-format mp4 \
  -f "bv*[height<=720]+ba/b[height<=720]/bv+ba/b" \
  --write-info-json \
  --write-subs \
  --write-auto-subs \
  --sub-langs "$SUB_LANGS" \
  --sub-format vtt \
  --convert-subs vtt \
  --cookies-from-browser "$COOKIE_SPEC" \
  -o "$TEMPLATE" \
  "$URL"
then
  printf '%s\n' 'yt-dlp --cookies-from-browser' > "$OUTPUT_DIR/source.fetcher.txt"
  echo "$OUTPUT_DIR"
  exit 0
fi

if [ -n "$FALLBACK_SCRIPT" ] && [ -x "$FALLBACK_SCRIPT" ]; then
  echo "[pi-watch-video] yt-dlp failed, trying browser fallback: $FALLBACK_SCRIPT" >&2
  rm -rf "$OUTPUT_DIR"
  mkdir -p "$OUTPUT_DIR"
  yt-dlp --version > "$OUTPUT_DIR/source.ytdlp-version.txt"
  "$FALLBACK_SCRIPT" "$URL" "$OUTPUT_DIR"
  printf 'browser-fallback:%s\n' "$FALLBACK_SCRIPT" > "$OUTPUT_DIR/source.fetcher.txt"
  echo "$OUTPUT_DIR"
  exit 0
fi

exit 1
