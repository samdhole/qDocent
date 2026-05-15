#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if ! docker info >/dev/null 2>&1; then
    echo "Error: Docker is not running." >&2
    exit 1
fi

cd "${REPO_ROOT}"

echo "Stopping DocQuery stack..."
docker compose down
echo "Stack stopped."
