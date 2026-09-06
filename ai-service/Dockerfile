# ============================================================
# SecureMed AI microservice — RETIRED (see server.js header)
#
# Superseded by backend/apps/ai/ (Django + Gemini, behind JWT and per-role
# permission checks). Kept as reference only; no compose file or Render
# blueprint builds it any more.
#
#   docker build -t securemed-ai ./ai-service
#   docker run -p 127.0.0.1:8100:8100 \
#     -e AI_SERVICE_TOKEN=<32+ random chars> -e ZAI_API_KEY=... securemed-ai
#
# Publish it to a public interface and you have an unauthenticated-by-design
# relay of patient data to a third-party model, outside the platform's audit
# trail — the bearer token is the only thing standing in the way.
# ============================================================
FROM node:20-alpine

# HOST=0.0.0.0 is safe *inside* a container (its own network namespace); what
# the host exposes is decided by -p above. server.js defaults to loopback for
# the bare-metal case.
ENV NODE_ENV=production \
    PORT=8100 \
    HOST=0.0.0.0

WORKDIR /srv

# Install production dependencies first (better layer caching)
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev 2>/dev/null || npm install --omit=dev

COPY server.js ./

EXPOSE 8100

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
  CMD node -e "fetch('http://127.0.0.1:8100/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "server.js"]
