#!/bin/sh
set -eu
desktop_pid=""
vnc_pid=""
api_pid=""
gateway_pid=""
cleanup() {
    trap - EXIT INT TERM
    if [ -n "$gateway_pid" ]; then kill "$gateway_pid" 2>/dev/null || true; fi
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
    desktop_host=0.0.0.0
    if [ "${SPECULARA_RENDER_GATEWAY:-0}" = "1" ]; then desktop_host=127.0.0.1; fi
    websockify --web=/usr/share/novnc "$desktop_host:6080" 127.0.0.1:5900 &
    desktop_pid=$!
fi
cd /srv/backend
# Do not trust external forwarded client addresses for the local-only controls.
api_port="${SPECULARA_INTERNAL_API_PORT:-${PORT:-8000}}"
api_host=0.0.0.0
if [ "${SPECULARA_RENDER_GATEWAY:-0}" = "1" ]; then
    : "${OPERATOR_ACCESS_TOKEN:?Set OPERATOR_ACCESS_TOKEN}"
    : "${DEMO_ACCESS_TOKEN:?Set DEMO_ACCESS_TOKEN}"
    # Read the secret on stdin, never in a process argument or log.
    OPERATOR_PASSWORD_HASH=$(printf '%s' "$OPERATOR_ACCESS_TOKEN" | caddy hash-password --algorithm bcrypt)
    export OPERATOR_PASSWORD_HASH
    api_host=127.0.0.1
fi
python -m uvicorn app.main:app --host "$api_host" --port "$api_port" --workers 1 --no-proxy-headers --timeout-graceful-shutdown 15 &
api_pid=$!
if [ "${SPECULARA_RENDER_GATEWAY:-0}" = "1" ]; then
    caddy run --config /srv/RenderCaddyfile --adapter caddyfile &
    gateway_pid=$!
    while kill -0 "$api_pid" 2>/dev/null && kill -0 "$gateway_pid" 2>/dev/null; do sleep 1; done
    exit 1
fi
wait "$api_pid"
