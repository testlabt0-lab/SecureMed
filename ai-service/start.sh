#!/usr/bin/env bash
# ============================================================
# SecureMed — start step for the RETIRED AI sidecar
#
# The platform no longer uses this service; the AI endpoints are Django views
# under /api/v1/ai/ (backend/apps/ai/). Do not deploy this as a public Render
# service — see the header of server.js for why.
#
# Writes the z-ai-web-dev-sdk config file from env vars, then starts the
# Express server.
#
# Required env:
#   AI_SERVICE_TOKEN — 32+ random chars; the server refuses to start without it
#   ZAI_BASE_URL     — e.g. https://api.z.ai/v1
#   ZAI_API_KEY      — your Z.ai API key
# Optional:
#   HOST             — defaults to 127.0.0.1 (loopback); set only behind a proxy
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

if [ -z "${AI_SERVICE_TOKEN:-}" ]; then
  echo "!! AI_SERVICE_TOKEN is not set — server.js will refuse to start"
fi

if [ -n "${ZAI_BASE_URL:-}" ] && [ -n "${ZAI_API_KEY:-}" ]; then
  echo "==> Writing .z-ai-config from environment"
  node -e "require('fs').writeFileSync('.z-ai-config', JSON.stringify({baseUrl: process.env.ZAI_BASE_URL, apiKey: process.env.ZAI_API_KEY}))"
else
  echo "!! ZAI_BASE_URL / ZAI_API_KEY not set — assistant will fail until they are provided"
fi

exec node server.js
