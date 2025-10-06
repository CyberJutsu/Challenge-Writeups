#!/usr/bin/env bash
set -euo pipefail

if [[ "${ENTRYPOINT_DEBUG:-0}" = "1" ]]; then
  set -x
  PS4='+ ${BASH_SOURCE}:${LINENO}: '
fi

echo "[entrypoint] Starting Gold Price service..."
exec node /app/src/server.js
