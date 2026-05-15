#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"
TOML_FILE="${REPO_ROOT}/r2r_gemini.toml"
HEALTH_URL="http://localhost:8000/health"
APP_URL="http://localhost:3000"
HEALTH_TIMEOUT=60
POLL_INTERVAL=3

echo "====================================="
echo "  DocQuery Setup Wizard"
echo "====================================="
echo ""

# Check Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "Error: Docker is not running." >&2
    echo "Install Docker Engine: https://docs.docker.com/engine/install/" >&2
    echo "Then start it with: sudo systemctl start docker" >&2
    exit 1
fi

echo "Note: This script requires sudo to set data/ directory ownership."
echo ""

# Prompt: Google API key (masked input)
printf "Enter your Google API key: "
read -rs google_api_key
echo ""
if [ -z "${google_api_key}" ]; then
    echo "Error: Google API key cannot be empty." >&2
    exit 1
fi
if printf '%s' "${google_api_key}" | grep -q '[|\\&"#]'; then
    echo "Error: API key cannot contain |, \\, &, \", or # characters." >&2
    exit 1
fi

# Prompt: Admin email (default admin@example.com)
printf "Admin email [admin@example.com]: "
read -r admin_email
if [ -z "${admin_email}" ]; then
    admin_email="admin@example.com"
fi

# Prompt: Admin password (masked, confirm, min 8 chars)
while true; do
    printf "Admin password (min 8 characters): "
    read -rs admin_password
    echo ""

    if [ "${#admin_password}" -lt 8 ]; then
        echo "Error: Password must be at least 8 characters. Try again." >&2
        continue
    fi

    if printf '%s' "${admin_password}" | grep -q '[|\\&"#]'; then
        echo "Error: Password cannot contain |, \\, &, \", or # characters. Try again." >&2
        continue
    fi

    printf "Confirm admin password: "
    read -rs admin_password_confirm
    echo ""

    if [ "${admin_password}" != "${admin_password_confirm}" ]; then
        echo "Error: Passwords do not match. Try again." >&2
        continue
    fi

    break
done

# Overwrite guard: warn if config files already exist (default: No)
overwrite_needed=false
for f in "${ENV_FILE}" "${TOML_FILE}"; do
    if [ -f "${f}" ]; then
        overwrite_needed=true
        echo "Warning: ${f} already exists."
    fi
done

if [ "${overwrite_needed}" = "true" ]; then
    printf "Overwrite existing files? [y/N]: "
    read -r overwrite_answer
    case "${overwrite_answer}" in
        [yY]) ;;
        *)
            echo "Aborted — existing files not modified." >&2
            exit 0
            ;;
    esac
fi

# Write .env: copy example, substitute GOOGLE_API_KEY and R2R admin credentials
cp "${REPO_ROOT}/.env.example.client" "${ENV_FILE}"
sed -i "s|^GOOGLE_API_KEY=.*|GOOGLE_API_KEY=${google_api_key}|" "${ENV_FILE}"
sed -i "s|^R2R_ADMIN_EMAIL=.*|R2R_ADMIN_EMAIL=${admin_email}|" "${ENV_FILE}"
sed -i "s|^R2R_ADMIN_PASSWORD=.*|R2R_ADMIN_PASSWORD=${admin_password}|" "${ENV_FILE}"
echo "Written: .env"

# Write r2r_gemini.toml: copy example, substitute email and password
cp "${REPO_ROOT}/r2r_gemini.toml.example" "${TOML_FILE}"
sed -i "s|default_admin_email = \"admin@example.com\"|default_admin_email = \"${admin_email}\"|" "${TOML_FILE}"
sed -i "s|default_admin_password = \"CHANGE_ME\"|default_admin_password = \"${admin_password}\"|" "${TOML_FILE}"
echo "Written: r2r_gemini.toml"

# Chown data/ directory so Linux containers can write to it
echo "Setting data/ directory ownership (may prompt for sudo password)..."
sudo mkdir -p "${REPO_ROOT}/data"
sudo chown -R 1001:1001 "${REPO_ROOT}/data"
echo "Ownership set."

# Build Docker images
echo "Building Docker images (this may take several minutes)..."
cd "${REPO_ROOT}"
docker compose build

# Start stack
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

echo "API is healthy. Opening browser..."

# Open browser
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "${APP_URL}"
elif command -v open >/dev/null 2>&1; then
    open "${APP_URL}"
else
    echo "Open your browser at ${APP_URL}"
fi

echo ""
echo "Setup complete! Next time, just run: bash install/start.sh"
