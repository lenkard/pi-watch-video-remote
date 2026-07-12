FROM debian:trixie-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates dbus-x11 ffmpeg firefox-esr iproute2 novnc openssh-client python3 python3-venv quickjs rsync websockify wireguard-tools x11vnc xauth xterm xvfb \
  && python3 -m venv /opt/yt-dlp \
  && /opt/yt-dlp/bin/pip install --no-cache-dir -U pip \
  && /opt/yt-dlp/bin/pip install --no-cache-dir -U 'yt-dlp[default]' \
  && ln -sf /opt/yt-dlp/bin/yt-dlp /usr/local/bin/yt-dlp \
  && rm -rf /var/lib/apt/lists/*

COPY browser/entrypoint.sh /usr/local/bin/browser-entrypoint
COPY browser/fetch.sh /usr/local/bin/fetch-url
COPY browser/launch-browser.sh /usr/local/bin/launch-browser
RUN chmod +x /usr/local/bin/browser-entrypoint /usr/local/bin/fetch-url /usr/local/bin/launch-browser

ENV PROFILE_DIR=/data/profile \
    JOBS_DIR=/data/jobs \
    BROWSER=firefox \
    WEB_PORT=14500 \
    DISPLAY=:100

VOLUME ["/data/profile", "/data/jobs", "/etc/wireguard"]
EXPOSE 14500 51820/udp
CMD ["/usr/local/bin/browser-entrypoint"]
