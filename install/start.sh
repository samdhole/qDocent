#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"
HEALTH_URL="http://localhost:8000/health"
APP_URL="http://localhost:3000"
HEALTH_TIMEOUT=60
POLL_INTERVAL=3

# Check Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker Engine and try again." >&2
    exit 1
fi

# Check .env exists — run setup first if missing
if [ ! -f "${ENV_FILE}" ]; then
    echo "Error: .env not found. Run install/setup.sh first." >&2
    exit 1
fi

cd "${REPO_ROOT}"

# Check if API container is already running
if docker compose ps --status running 2>/dev/null | grep -q "api"; then
    echo "Stack is already running. Opening browser..."
else
    echo "Starting stack..."
    docker compose up -d

    # Health wait loop: poll every 3 s for up to 60 s
    elapsed=0
    healthy=false
    echo "Waiting for API to be healthy..."
    while [ "${elapsed}" -lt "${HEALTH_TIMEOUT}" ]; do
        if curl -sf "${HEALTH_URL}" >/dev/null 2>&1; then
            healthy=true
            break
        fi
        sleep "${POLL_INTERVAL}"
        elapsed=$((elapsed + POLL_INTERVAL))
    done

    if [ "${healthy}" != "true" ]; then
        echo "Error: API did not become healthy within ${HEALTH_TIMEOUT}s. Last logs:" >&2
        docker compose logs --tail=20 api >&2
        exit 1
    fi

    echo "API is healthy."
fi

# Open browser
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "${APP_URL}"
elif command -v open >/dev/null 2>&1; then
    open "${APP_URL}"
else
    echo "Open your browser at ${APP_URL}"
fi
