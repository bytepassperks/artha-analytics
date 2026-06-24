#!/usr/bin/env bash
set -e

JAR="metabase.jar"
MB_VERSION="${MB_VERSION:-v0.62.2}"

# Download if not present
if [ ! -f "$JAR" ]; then
  echo "[artha] downloading Metabase ${MB_VERSION} JAR..."
  curl -fsSL --retry 3 -o "$JAR" "https://downloads.metabase.com/${MB_VERSION}/metabase.jar"
  echo "[artha] download complete: $(du -h $JAR | cut -f1)"
fi

# Apply branding patches (only once per download)
if [ ! -f ".artha-patched" ]; then
  echo "[artha] Applying branding patches..."

  # Extract frontend files
  mkdir -p /tmp/mb-patch
  cd /tmp/mb-patch
  jar xf /app/$JAR frontend_client/app/dist/

  # Patch defaults in app-main JS
  MAIN_JS=$(find frontend_client/app/dist -name "app-main.*.js" 2>/dev/null | head -1)
  if [ -n "$MAIN_JS" ]; then
    echo "[artha] Patching $MAIN_JS"
    sed -i 's/"help-link":"metabase"/"help-link":"hidden"/g' "$MAIN_JS"
    sed -i 's/"show-metabase-links":!0/"show-metabase-links":!1/g' "$MAIN_JS"
  fi

  # Patch metabase.com/learn links
  for f in frontend_client/app/dist/*.js; do
    if grep -q 'metabase\.com/learn' "$f" 2>/dev/null; then
      sed -i 's|metabase\.com/learn|arthasuite.com/docs|g' "$f"
    fi
  done

  # Update JAR
  jar uf /app/$JAR frontend_client/
  cd /app
  rm -rf /tmp/mb-patch
  touch .artha-patched
  echo "[artha] Branding patches applied"
fi

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
