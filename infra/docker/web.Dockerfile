# =============================================================================
# RegimeX Web — Dockerfile
# =============================================================================
#
# Multi-stage build for the Next.js web application.
#
# Stages:
#   1. deps      — Install Node.js dependencies (reproducible via npm ci)
#   2. builder   — Build the Next.js application with standalone output
#   3. runtime   — Minimal production image using the standalone server
#
# Requires next.config.mjs to have:
#   output: 'standalone'
#
# Build (from repository root):
#   docker build -f infra/docker/web.Dockerfile -t regimex-web .
#
# Environment:
#   PORT               — TCP port the server binds to (default: 3000)
#   NEXT_PUBLIC_API_URL — Public base URL for the RegimeX FastAPI backend
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Dependencies — install Node.js packages
# ---------------------------------------------------------------------------
FROM node:20-alpine AS deps

# libc6-compat is required for certain native Node modules on Alpine.
# See: https://github.com/nodejs/docker-node/tree/b4117f9333da4138b03a546ec926ef50a31506c3#nodealpine
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Copy only package manifests to maximise layer cache reuse.
COPY apps/web/package.json apps/web/package-lock.json* ./

# Reproducible install of all dependencies (including devDependencies needed
# for the build step).  Production pruning happens in the runtime stage.
RUN npm ci

# ---------------------------------------------------------------------------
# Stage 2: Builder — build the Next.js application
# ---------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Bring in installed node_modules from the deps stage.
COPY --from=deps /app/node_modules ./node_modules

# Copy the entire web application source.
COPY apps/web/ .

# Disable Next.js anonymous telemetry during the build.
ENV NEXT_TELEMETRY_DISABLED=1

# Build the production application.
# NEXT_PUBLIC_API_URL is not embedded at build time — it is injected at
# runtime via the environment so that the same image works across
# development, staging, and production without rebuilding.
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 3: Runtime — minimal production image
# ---------------------------------------------------------------------------
FROM node:20-alpine AS runtime

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    # Default port; override via PORT at runtime.
    PORT=3000 \
    # Bind to all interfaces so the Docker network bridge is reachable.
    HOSTNAME=0.0.0.0

# Create a non-root user/group before writing application files.
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Copy the standalone server bundle produced by Next.js.
# The standalone output contains a self-contained server.js that does NOT
# require node_modules to be present — only the bundled files are needed.
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./

# Copy static assets (images, fonts, etc.) into the expected location.
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Copy the public/ directory (robots.txt, favicon, etc.).
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

# Liveness probe: lightweight HTTP check against the application root.
# Avoids wget — uses Node's built-in http module for zero extra dependencies.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD node -e "require('http').get('http://localhost:' + (process.env.PORT || 3000) + '/', (r) => { process.exit(r.statusCode < 500 ? 0 : 1) }).on('error', () => process.exit(1))"

# Start the standalone Next.js server.
# The PORT and HOSTNAME environment variables are read by server.js directly.
CMD ["node", "server.js"]
