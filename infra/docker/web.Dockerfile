# =============================================================================
# RegimeX Web — Dockerfile
# =============================================================================
#
# Multi-stage build for the Next.js web application.
#
# Stages:
#   1. deps      — Install Node.js dependencies
#   2. builder   — Build the Next.js application
#   3. runtime   — Minimal production image with standalone output
#
# V04: Foundation image. Full production configuration in V16+ (Platform Volume).
#
# Build:
#   docker build -f infra/docker/web.Dockerfile -t regimex-web .
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Dependencies
# ---------------------------------------------------------------------------
FROM node:20-alpine AS deps

# Check https://github.com/nodejs/docker-node/tree/b4117f9333da4138b03a546ec926ef50a31506c3#nodealpine
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Copy only package files for layer caching
COPY apps/web/package.json apps/web/package-lock.json* ./

RUN npm ci --only=production

# ---------------------------------------------------------------------------
# Stage 2: Builder
# ---------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY apps/web/ .

# Build the Next.js application
# NEXT_TELEMETRY_DISABLED disables anonymous telemetry
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# ---------------------------------------------------------------------------
# Stage 3: Runtime
# ---------------------------------------------------------------------------
FROM node:20-alpine AS runtime

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000

# Create non-root user
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Copy standalone output (requires next.config output: 'standalone')
# Note: Enable output: 'standalone' in next.config.ts when containerizing
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD wget -qO- http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
