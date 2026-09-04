#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../backend"

echo "==> Starting Celery Worker"
exec celery -A config worker -l info
