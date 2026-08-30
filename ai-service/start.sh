#!/usr/bin/env bash
# ============================================================
# SecureMed — Render start step (AI service)
# Writes the z-ai-web-dev-sdk config file from env vars, then
# starts the Express server. Render injects $PORT automatically.
#
# Required env (set in the Render dashboard):
#   ZAI_BASE_URL — e.g. https://api.z.ai/v1
#   ZAI_API_KEY  — your Z.ai API key
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

if [ -n "${ZAI_BASE_URL:-}" ] && [ -n "${ZAI_API_KEY:-}" ]; then
  echo "==> Writing .z-ai-config from environment"
  node -e "require('fs').writeFileSync('.z-ai-config', JSON.stringify({baseUrl: process.env.ZAI_BASE_URL, apiKey: process.env.ZAI_API_KEY}))"
else
  echo "!! ZAI_BASE_URL / ZAI_API_KEY not set — assistant will fail until they are provided"
fi

exec node server.js
