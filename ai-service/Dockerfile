# ============================================================
# SecureMed AI microservice — GLM assistant & case summaries
#   docker build -t securemed-ai ./ai-service
#   docker run -p 8100:8100 -e ZAI_API_KEY=... securemed-ai
# ============================================================
FROM node:20-alpine

ENV NODE_ENV=production \
    PORT=8100

WORKDIR /srv

# Install production dependencies first (better layer caching)
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev 2>/dev/null || npm install --omit=dev

COPY server.js ./

EXPOSE 8100

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
  CMD node -e "fetch('http://127.0.0.1:8100/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "server.js"]
