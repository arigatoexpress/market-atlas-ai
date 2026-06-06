# syntax=docker/dockerfile:1
# Multi-stage build for tradingview-mcp
# Runtime requires headless Playwright Chromium

# ─── Stage 1: Dependencies + Build ───
FROM node:20-slim AS builder

WORKDIR /app

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json* ./
RUN npm ci --ignore-scripts

COPY tsconfig.json ./
COPY src ./src
RUN npm run build

# ─── Stage 2: Runtime ───
FROM node:20-slim AS runtime

WORKDIR /app

# Install Playwright system dependencies for Chromium headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy compiled output and production dependencies
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev --ignore-scripts

# Install Playwright browsers
RUN npx playwright install chromium
RUN npx playwright install-deps chromium

COPY --from=builder /app/dist ./dist

# Non-root user for security
RUN groupadd -r tvuser && useradd -r -g tvuser tvuser \
    && chown -R tvuser:tvuser /app
USER tvuser

ENV NODE_ENV=production
ENV PLAYWRIGHT_BROWSERS_PATH=0

EXPOSE 3456

CMD ["node", "dist/index.js"]
