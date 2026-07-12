#!/bin/sh
set -eu

PROFILE_DIR=${PROFILE_DIR:-/data/profile}
BROWSER=${BROWSER:-firefox}
mkdir -p "$PROFILE_DIR"

case "$BROWSER" in
  firefox*)
    exec firefox-esr --no-remote --profile "$PROFILE_DIR"
    ;;
  chromium*|chrome*)
    exec chromium --user-data-dir="$PROFILE_DIR" --password-store=basic --no-first-run --no-default-browser-check
    ;;
  *)
    echo "unsupported BROWSER=$BROWSER" >&2
    exit 2
    ;;
esac
