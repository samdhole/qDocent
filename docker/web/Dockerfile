# syntax=docker/dockerfile:1

# ── Stage 1: deps (install node_modules) ──────────────────────────────────────
FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Copy only the manifests needed to install dependencies
COPY apps/web/package.json apps/web/package-lock.json ./apps/web/

RUN cd apps/web && npm ci

# ── Stage 2: builder (bake env vars and build) ────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy installed node_modules from deps stage
COPY --from=deps /app/apps/web/node_modules ./apps/web/node_modules

# Copy all source (build context is project root)
COPY . .

# NEXT_PUBLIC_* vars are baked into the JS bundle at next build time.
# They CANNOT be changed at runtime without rebuilding the image.
# Pass real values via docker compose build args (in docker-compose.yml).
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

ARG NEXT_PUBLIC_DEMO_NOTEBOOK_ID
ENV NEXT_PUBLIC_DEMO_NOTEBOOK_ID=$NEXT_PUBLIC_DEMO_NOTEBOOK_ID

ENV NODE_ENV=production

# Build from the Next.js app directory
RUN cd apps/web && npm run build

# ── Stage 3: runner (minimal production image) ────────────────────────────────
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy public assets
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/public ./public

# Pre-create .next with correct ownership
RUN mkdir .next && chown nextjs:nodejs .next

# Flatten standalone output into WORKDIR — this contains server.js + node_modules
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/standalone ./

# Copy static client-side assets (JS chunks, CSS) into expected location
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/static ./.next/static

USER nextjs

EXPOSE 3000

# server.js is created by Next.js standalone output at WORKDIR/server.js
CMD ["node", "server.js"]
