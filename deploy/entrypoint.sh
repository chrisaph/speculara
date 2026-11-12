#!/bin/sh
set -eu
desktop_pid=""
vnc_pid=""
api_pid=""
cleanup() {
    trap - EXIT INT TERM
    # Let the API close saved browser sessions before taking away its display.
    if [ -n "$api_pid" ]; then
        kill "$api_pid" 2>/dev/null || true
        wait "$api_pid" 2>/dev/null || true
    fi
    for pid in "$desktop_pid" "$vnc_pid" "$display_pid"; do
        if [ -n "$pid" ]; then kill "$pid" 2>/dev/null || true; fi
    done
    wait 2>/dev/null || true
}
Xvfb :99 -screen 0 1366x900x24 -nolisten tcp &
display_pid=$!
trap cleanup EXIT INT TERM
attempt=0
until xdpyinfo -display :99 >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 30 ]; then echo 'Virtual display failed to start.' >&2; exit 1; fi
    sleep 1
done
if [ "${ENABLE_REMOTE_DESKTOP:-0}" = "1" ]; then
    x11vnc -display :99 -listen 127.0.0.1 -rfbport 5900 -forever -shared -nopw &
    vnc_pid=$!
    websockify --web=/usr/share/novnc 0.0.0.0:6080 127.0.0.1:5900 &
    desktop_pid=$!
fi
cd /srv/backend
# Do not trust external forwarded client addresses for the local-only controls.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --no-proxy-headers --timeout-graceful-shutdown 15 &
api_pid=$!
wait "$api_pid"
