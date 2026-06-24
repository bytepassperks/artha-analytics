#!/usr/bin/env bash
set -e

JAR="metabase.jar"
DBURL="${SCALINGO_POSTGRESQL_URL:-$DATABASE_URL}"
nopre="${DBURL#*://}"
creds="${nopre%%@*}"
hostportdb="${nopre#*@}"
DB_USER="${creds%%:*}"
DB_PASS="${creds#*:}"
hostport="${hostportdb%%/*}"
DB_NAME="${hostportdb#*/}"
DB_NAME="${DB_NAME%%\?*}"
DB_HOST="${hostport%%:*}"
DB_PORT="${hostport#*:}"
[ "$DB_PORT" = "$DB_HOST" ] && DB_PORT=5432

export MB_DB_TYPE=postgres
export MB_DB_HOST="$DB_HOST"
export MB_DB_PORT="$DB_PORT"
export MB_DB_USER="$DB_USER"
export MB_DB_PASS="$DB_PASS"
export MB_DB_DBNAME="$DB_NAME"
export MB_DB_ADDITIONAL_OPTIONS="ssl=true&sslmode=require"
export MB_JETTY_HOST=0.0.0.0
export MB_JETTY_PORT=3001

PROXY_PORT="${PORT:-3000}"
export PORT="$PROXY_PORT"

echo "[artha] starting Metabase on :3001, proxy on :$PROXY_PORT"
java ${JAVA_OPTS:--Xmx1400m} -Dlog4j2.formatMsgNoLookups=true -jar "$JAR" &
MB_PID=$!

# Wait for Metabase to be ready
echo "[artha] waiting for Metabase to start..."
for i in $(seq 1 120); do
  if curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:3001/api/health" 2>/dev/null | grep -q '200'; then
    echo "[artha] Metabase ready after ${i}s"
    break
  fi
  sleep 1
done

# Start the reverse proxy (injects branding overrides + strips CSP)
echo "[artha] starting branding proxy on :$PROXY_PORT"
python3 artha-proxy.py &
PROXY_PID=$!

# If either dies, kill both
trap "kill $MB_PID $PROXY_PID 2>/dev/null; exit" EXIT SIGTERM SIGINT
wait -n $MB_PID $PROXY_PID
kill $MB_PID $PROXY_PID 2>/dev/null
exit 1
