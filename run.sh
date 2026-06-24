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
export MB_JETTY_PORT="${PORT:-3000}"

echo "[artha] starting Metabase: host=$DB_HOST port=$DB_PORT db=$DB_NAME jetty_port=$MB_JETTY_PORT"
exec java ${JAVA_OPTS:--Xmx1400m} -Dlog4j2.formatMsgNoLookups=true -jar "$JAR"
