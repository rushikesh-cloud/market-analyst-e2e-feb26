#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/uploads/documents /var/lib/nginx /var/log/nginx /tmp/nginx

python -m uvicorn market_analyst.api.app:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

cd /app/frontend
HOSTNAME=127.0.0.1 PORT=3000 npm run start -- --hostname 127.0.0.1 --port 3000 &
FRONTEND_PID=$!

nginx -g "daemon off;" &
NGINX_PID=$!

shutdown() {
    kill -TERM "$BACKEND_PID" "$FRONTEND_PID" "$NGINX_PID" 2>/dev/null || true
}

trap shutdown SIGTERM SIGINT

set +e
wait -n "$BACKEND_PID" "$FRONTEND_PID" "$NGINX_PID"
STATUS=$?
set -e

shutdown
wait || true
exit "$STATUS"
