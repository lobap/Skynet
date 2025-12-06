# ============================================
# STAGE 1: Frontend Builder
# ============================================
FROM node:20-slim AS frontend-builder

WORKDIR /frontend

# Copy only package files first for caching
COPY frontend/package*.json ./

RUN npm install

# Copy frontend source
COPY frontend/ .

# Build static assets
RUN npm run build

# ============================================
# STAGE 2: Python Runtime
# ============================================
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Install minimal system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    unzip \
    sudo \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for Astro dev server
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install --with-deps chromium

# Copy built frontend from stage 1
COPY --from=frontend-builder /frontend /app/frontend

# Copy entrypoint
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 8000 4321

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
