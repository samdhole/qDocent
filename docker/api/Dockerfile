# syntax=docker/dockerfile:1

# ── Builder ────────────────────────────────────────────────────────────────────
FROM python:3.11-slim-bookworm AS builder

# uv from official distroless image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

# System packages required for:
#   tesseract-ocr + tesseract-ocr-eng → pytesseract
#   ghostscript → camelot-py ghostscript backend
#   poppler-utils → camelot-py stream mode
#   libglib2.0-0 + libX* libs → Playwright/Chromium runtime
#   build-essential → compile native extensions during pip install
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    tesseract-ocr-eng \
    ghostscript \
    poppler-utils \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create virtualenv
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Install Python deps from lock file.
# --extra-index-url ensures docling's PyTorch dep installs CPU-only wheels
# (without this, Docker pulls CUDA wheels → image grows from ~2 GB to ~9 GB).
# opencv-python-headless overrides camelot-py's opencv-python dep which
# requires OpenGL/UI libs absent in headless containers.
#
# NOTE: requirements-lock.txt may have a UTF-8 BOM (EF BB BF) from its origin.
# Strip it before this stage to prevent pip parse errors on the first dependency line.
# Do this on the host before building (Step 1 below covers this).
COPY requirements-lock.txt requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements-lock.txt \
    opencv-python-headless

# Verify post-install CLI entry points exist before running them
RUN which crawl4ai-setup docling-tools

# Install Playwright Chromium browser for crawl4ai URL ingestion
RUN crawl4ai-setup && playwright install --with-deps chromium

# Pre-download docling layout models so first ingest request isn't slow
RUN docling-tools models download --all -o /opt/docling-models

# ── Runtime ────────────────────────────────────────────────────────────────────
FROM python:3.11-slim-bookworm

# Same runtime system packages as builder (minus build-essential).
# curl is included for the Docker health check (CMD-SHELL curl -f http://localhost:8000/health).
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tesseract-ocr \
    tesseract-ocr-eng \
    ghostscript \
    poppler-utils \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy venv, Playwright Chromium binary, and docling models from builder
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /root/.cache/ms-playwright /root/.cache/ms-playwright
COPY --from=builder /opt/docling-models /opt/docling-models

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    DOCLING_SERVE_ARTIFACTS_PATH=/opt/docling-models \
    # Playwright uses /root/.cache by default; this ensures it finds the binary
    PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright

WORKDIR /app

# Copy application source
COPY apps/ apps/
COPY packages/ packages/

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
