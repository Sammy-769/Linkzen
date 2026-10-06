#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$PROJECT_DIR/.venv/bin/python"
HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
export HF_HOME
URL="http://127.0.0.1:8000"

server_is_ready() {
    "$PYTHON" -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/api/settings", timeout=2)' >/dev/null 2>&1
}

if [[ ! -x "$PYTHON" ]]; then
    printf 'Linkzen virtual environment is missing: %s\n' "$PYTHON" >&2
    exit 1
fi

if server_is_ready; then
    printf 'Linkzen is already running at %s\n' "$URL"
    xdg-open "$URL" >/dev/null 2>&1 || true
    printf 'Press Enter to close this launcher window. The existing server was not started here.\n'
    read -r
    exit 0
fi

cd "$PROJECT_DIR"
"$PYTHON" -m uvicorn server:app --host 127.0.0.1 --port 8000 &
SERVER_PID=$!

stop_server() {
    if kill -0 "$SERVER_PID" 2>/dev/null; then
        kill -TERM "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
}
trap stop_server EXIT INT TERM

printf 'Starting Linkzen...\n'
for attempt in {1..120}; do
    if server_is_ready; then
        printf 'Linkzen is ready at %s\n' "$URL"
        xdg-open "$URL" >/dev/null 2>&1 || true
        printf 'Keep this window open while using Linkzen. Press Ctrl+C to stop the server.\n'
        wait "$SERVER_PID"
        exit $?
    fi

    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        wait "$SERVER_PID"
        exit $?
    fi
    sleep 1
done

printf 'Linkzen did not become ready within 120 seconds.\n' >&2
exit 1
