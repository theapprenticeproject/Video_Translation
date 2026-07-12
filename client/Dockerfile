# ── Dev stage ─────────────────────────────────────────────────────────────────
# Used by compose.yaml for local development (HMR, hot reload)
FROM node:24-alpine AS dev

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@latest --activate

COPY package.json pnpm-lock.yaml ./
ENV CI=true
RUN pnpm install

COPY . .

EXPOSE 5173
CMD ["pnpm", "run", "dev", "--host"]


# ── Builder stage ──────────────────────────────────────────────────────────────
# Builds the React app into static files
FROM dev AS builder

# VITE_API_SERVER_URL is injected at build time.
# Leave empty in prod: nginx proxies /api → backend:8000, so relative URLs work.
ARG VITE_API_SERVER_URL=""
ENV VITE_API_SERVER_URL=$VITE_API_SERVER_URL

# Clerk publishable key — safe to embed in the bundle (public key)
ARG VITE_CLERK_PUBLISHABLE_KEY=""
ENV VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PUBLISHABLE_KEY

RUN pnpm run build


# ── Prod stage ─────────────────────────────────────────────────────────────────
FROM nginx:alpine AS prod

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
