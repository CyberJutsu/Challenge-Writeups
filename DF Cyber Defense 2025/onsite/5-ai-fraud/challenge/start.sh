#!/bin/sh

set -eu

log() {
  printf "[%s] %s\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

# --- Config with sane defaults (can be overridden by env) ---
DB_PATH=${DB_PATH:-/app/db.sqlite3}
GUNICORN_BIND=${GUNICORN_BIND:-0.0.0.0:8000}
GUNICORN_WORKERS=${GUNICORN_WORKERS:-2}
GUNICORN_CLASS=${GUNICORN_CLASS:-gthread}
GUNICORN_THREADS=${GUNICORN_THREADS:-4}
GUNICORN_TIMEOUT=${GUNICORN_TIMEOUT:-120}
GUNICORN_KEEPALIVE=${GUNICORN_KEEPALIVE:-5}
GUNICORN_MAX_REQUESTS=${GUNICORN_MAX_REQUESTS:-1000}
GUNICORN_MAX_REQUESTS_JITTER=${GUNICORN_MAX_REQUESTS_JITTER:-100}

log "Starting AI Fraud app"
log "DB_PATH=$DB_PATH"

# Ensure DB directory exists
DB_DIR=$(dirname "$DB_PATH")
mkdir -p "$DB_DIR"

# Initialize/seed SQLite (idempotent thanks to IF NOT EXISTS / INSERT OR IGNORE)
if [ -f "/app/init.sql" ]; then
  log "[init] applying /app/init.sql to $DB_PATH"
  if ! sqlite3 "$DB_PATH" ".read /app/init.sql"; then
    log "[init] sqlite init returned non-zero"
  fi
else
  log "[init] /app/init.sql not found; skipping DB seed"
fi

# Run the application via gunicorn
log "Launching gunicorn on ${GUNICORN_BIND} (workers=${GUNICORN_WORKERS}, threads=${GUNICORN_THREADS})"
exec gunicorn \
  -w "$GUNICORN_WORKERS" \
  -k "$GUNICORN_CLASS" \
  --threads "$GUNICORN_THREADS" \
  --timeout "$GUNICORN_TIMEOUT" \
  --keep-alive "$GUNICORN_KEEPALIVE" \
  --max-requests "$GUNICORN_MAX_REQUESTS" \
  --max-requests-jitter "$GUNICORN_MAX_REQUESTS_JITTER" \
  --bind "$GUNICORN_BIND" \
  app:app

