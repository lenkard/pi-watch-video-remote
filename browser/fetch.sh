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

mkdir -p "$OUTPUT_DIR" "$PROFILE_DIR"

if [ -n "${YTDLP_BROWSER_SPEC:-}" ]; then
  COOKIE_SPEC=$YTDLP_BROWSER_SPEC
else
  case "$BROWSER" in
    firefox*) COOKIE_SPEC="firefox:$PROFILE_DIR" ;;
    chromium*|chrome*) COOKIE_SPEC="chromium:$PROFILE_DIR" ;;
    *) echo "unsupported BROWSER=$BROWSER" >&2; exit 2 ;;
  esac
fi

run_fetch() {
  yt-dlp \
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
    "$@" \
    -o "$TEMPLATE" \
    "$URL"
}

echo "[pi-watch-video] trying yt-dlp without browser cookies" >&2
if ! run_fetch; then
  echo "[pi-watch-video] yt-dlp failed, retrying with browser cookies" >&2
  rm -rf "$OUTPUT_DIR"
  mkdir -p "$OUTPUT_DIR"
  run_fetch --cookies-from-browser "$COOKIE_SPEC"
fi

echo "$OUTPUT_DIR"
