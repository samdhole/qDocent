# DocQuery — Quick Start

## Windows

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and start it.
2. Open PowerShell and `cd` to this folder.
3. **First time only:** run `.\install\setup.ps1` — answers two prompts, builds images, opens the app.
4. **Daily use:** run `.\install\start.ps1` — starts the stack if needed, then opens the app.

## Linux

1. Install [Docker Engine](https://docs.docker.com/engine/install/) and ensure it is running (`sudo systemctl start docker`).
2. Open a terminal and `cd` to this folder.
3. **First time only:** run `bash install/setup.sh` — answers two prompts, builds images, opens the app.
4. **Daily use:** run `bash install/start.sh` — starts the stack if needed, then opens the app.

## Prerequisites

- Docker Desktop 4.x+ (Windows) or Docker Engine 24.0+ (Linux) with Compose V2
- A Google API key (you will be prompted for it during setup)

## Troubleshooting

See `docs/client-handoff/deployment.md` for advanced options, manual setup steps, and environment variable reference.
