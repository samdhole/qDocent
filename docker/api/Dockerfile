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
#   libglib2.0-0 → base GNOME lib (glib/gthread, needed by pdfplumber/poppler)
#   build-essential → compile native extensions during pip install
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    tesseract-ocr-eng \
    ghostscript \
    poppler-utils \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create virtualenv
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Install Python deps from lock file.
# opencv-python-headless overrides camelot-py's opencv-python transitive dep,
# which requires OpenGL/UI libs absent in headless containers.
COPY requirements-lock.txt requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install \
    -r requirements-lock.txt \
    opencv-python-headless

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
    && rm -rf /var/lib/apt/lists/*

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy application source
COPY apps/ apps/
COPY packages/ packages/

# Create non-root user and set proper file ownership
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 appuser && \
    chown -R appuser:appgroup /opt/venv /app

USER appuser

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
