#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "====================================="
echo "  DocQuery Uninstall"
echo "====================================="
echo ""
echo "This will:"
echo "  - Stop and remove all Docker containers"
echo "  - Remove Docker volumes (database will be wiped)"
echo "  - Remove built Docker images"
echo "  - Delete .env and r2r_gemini.toml"
echo ""
printf 'Type "uninstall" to confirm: '
read -r confirm
if [ "${confirm}" != "uninstall" ]; then
    echo "Aborted."
    exit 0
fi

cd "${REPO_ROOT}"

if docker info >/dev/null 2>&1; then
    echo "Stopping stack and removing containers, volumes, and images..."
    docker compose down -v --rmi local
    echo "Docker resources removed."
else
    echo "Warning: Docker is not running — skipping container/image removal." >&2
fi

for f in .env r2r_gemini.toml; do
    if [ -f "${REPO_ROOT}/${f}" ]; then
        rm -f "${REPO_ROOT}/${f}"
        echo "Deleted: ${f}"
    fi
done

echo ""
echo "Uninstall complete. To reinstall, run: bash install/setup.sh"
