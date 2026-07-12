#!/bin/sh
set -eu

WG_CONF=${WG_CONF:-/etc/wireguard/wg0.conf}
WG_AUTO_UP=${WG_AUTO_UP:-1}
WEB_BIND_IP=${WEB_BIND_IP:-}
WEB_PORT=${WEB_PORT:-14500}
DISPLAY_NUM=${DISPLAY:-:100}

cleanup() {
  kill 0 >/dev/null 2>&1 || true
  if [ "$WG_AUTO_UP" = "1" ] && [ -f "$WG_CONF" ] && ip link show wg0 >/dev/null 2>&1; then
    wg-quick down "$WG_CONF" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

mkdir -p /data/profile /data/jobs

if [ "$WG_AUTO_UP" = "1" ] && [ -f "$WG_CONF" ]; then
  wg-quick up "$WG_CONF"
fi

if [ -z "$WEB_BIND_IP" ] && ip -4 addr show wg0 >/dev/null 2>&1; then
  WEB_BIND_IP=$(ip -4 addr show dev wg0 | awk '/inet / {print $2}' | cut -d/ -f1 | head -n1)
fi
WEB_BIND_IP=${WEB_BIND_IP:-0.0.0.0}
export DISPLAY="$DISPLAY_NUM"

Xvfb "$DISPLAY_NUM" -screen 0 1280x800x24 >/tmp/xvfb.log 2>&1 &
/usr/local/bin/launch-browser >/tmp/browser.log 2>&1 &
x11vnc -display "$DISPLAY_NUM" -rfbport 5900 -localhost -forever -shared -nopw >/tmp/x11vnc.log 2>&1 &

exec websockify --web=/usr/share/novnc/ "$WEB_BIND_IP:$WEB_PORT" localhost:5900
