# docker/ — Containerisation Workspace

This directory holds the Dockerfiles for the two custom services in the 4-service
compose stack. The root `docker-compose.yml` wires them together.

## What "good output" means here

- `docker compose up -d` on a fresh Windows clone reaches all four services healthy
  with no manual terminal work beyond filling `.env` and running one pre-deploy chown.
- `docker compose down` (no `-v`) preserves all data; `docker compose up -d` again
  restores the prior state with no re-ingestion required.
- No process runs as root inside any container.

---

## Service Map

| Service  | Image / Dockerfile           | Port (host→container) | User              |
|----------|------------------------------|-----------------------|-------------------|
| postgres | pgvector/pgvector:pg16       | not exposed           | postgres (default)|
| r2r      | sciphiai/r2r:3.6.6           | 7272→**8000**         | r2r default       |
| api      | docker/api/Dockerfile        | 8000→8000             | appuser (uid 1001)|
| web      | docker/web/Dockerfile        | 3000→3000             | nextjs (uid 1001) |

> ⚠️ **R2R 3.6.6 internal port is 8000, not 7272.** The official docs (main branch) say 7272,
> but `docker inspect sciphiai/r2r:3.6.6` shows `{"8000/tcp":{}}` exposed and CMD runs
> `uvicorn ... --port $R2R_PORT` (default 8000). The host port stays 7272 for external compat.

---

## docker/api/Dockerfile — contracts and invariants

**Two-stage build** (builder → runtime, both on python:3.11-slim-bookworm).

| Contract | Value |
|----------|-------|
| venv | `/opt/venv` — copied from builder to runtime stage. |
| Non-root user | `appuser` (uid 1001, gid appgroup 1001). `/opt/venv` and `/app` are chowned before `USER appuser`. |
| OpenCV override | `opencv-python-headless` is installed explicitly after the lock file to override camelot-py's transitive `opencv-python` dep (which requires OpenGL/UI libs absent in headless containers). |
| Data bind-mount | `./data:/app/data` — host dir must be `chown -R 1001:1001 data` before first `docker compose up`. See deployment.md. |
| `HOME: /tmp` | Set in `docker-compose.yml` api service environment. System users get `HOME=/nonexistent` which breaks any library that writes to `~/.cache`. |

---

## docker/web/Dockerfile — contracts and invariants

**Three-stage build** (deps → builder → runner, all on node:20-alpine).

| Contract | Value |
|----------|-------|
| `output: "standalone"` | Must stay in `apps/web/next.config.ts`. Removing it breaks the runner stage — it copies from `.next/standalone/`. |
| Build args | `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_DEMO_NOTEBOOK_ID` are `ARG`s baked into the bundle at build time. Changing them at runtime has no effect — the image must be rebuilt. |
| Default `NEXT_PUBLIC_API_URL` | `http://localhost:8000`. VPS deployments must pass the server IP at build time via `docker compose build --build-arg NEXT_PUBLIC_API_URL=http://<ip>:8000`. |
| Non-root user | `nextjs` (uid 1001, gid nodejs 1001). |
| Static assets | `.next/static` and `public/` are copied separately into the runner stage — they are not included in the standalone bundle. |

---

## docker-compose.yml — healthcheck dependency chain

```
postgres (pg_isready) → r2r (curl /v3/health on :8000) → api (curl /health) → web
```

- **r2r** needs a long `start_period` (60 s) because it runs migrations on first boot.
- **r2r healthcheck** must use `curl`, not `wget` — `wget` is not in `sciphiai/r2r:3.6.6`.
- **r2r healthcheck URL** must hit `:8000`, not `:7272` (see service map note above).
- **api** depends on `r2r: service_healthy` — never remove this condition or the API
  will crash on cold starts before R2R is ready.
- **postgres** exposes no host port — connect through the compose network only.

### Environment variable bridging

R2R/litellm reads `GEMINI_API_KEY`, not `GOOGLE_API_KEY`. The compose file maps:

```yaml
environment:
  GEMINI_API_KEY: ${GOOGLE_API_KEY}
```

Do not remove this mapping or R2R will fall back to OpenAI defaults and fail.

---

## Key gotchas

1. **Bind-mount permissions** — forget the `chown -R 1001:1001 data` step and every
   SQLite write (`notebooks.db`, `ingest_jobs.db`, etc.) silently fails at runtime.
2. **NEXT_PUBLIC_* at runtime** — these look like env vars but they are compile-time
   constants. Runtime `docker run -e NEXT_PUBLIC_API_URL=...` does nothing.
3. **`.dockerignore`** — `COPY . .` in both Dockerfiles relies on `.dockerignore`
   excluding `.venv/`, `data/`, `external/`, `.env*`, `node_modules/`, and `reports/`.
   Removing `.dockerignore` sends the full repo (≥ 2 GB with `external/R2R/`) to the
   daemon and leaks local `.env` secrets into the image layer.
4. **Line endings** — all shell scripts in Docker images must be LF. `.gitattributes`
   enforces `* text=auto eol=lf` for this. A Windows clone without `.gitattributes`
   will produce `\r` shebangs and `exec format error` at runtime.
5. **R2R image version** — pinned to `sciphiai/r2r:3.6.6`. Bumping it may require
   re-validating the Gemini config and healthcheck path.
6. **`adduser --system` HOME=/nonexistent** — system users on Debian get `HOME=/nonexistent`,
   which breaks any library that writes to `~/.cache`. Fix applied: `HOME: /tmp` is set in
   the `api` service `environment` block in `docker-compose.yml`.
7. **OpenCV headless override** — `camelot-py` pulls `opencv-python` as a transitive dep, which
   requires `libGL.so.1`. The Dockerfile explicitly installs `opencv-python-headless` after the
   lock file, overriding the transitive `opencv-python` dep. This avoids needing `libgl1` as an
   additional apt package. Do not remove the `opencv-python-headless` override from the
   Dockerfile pip install step.
8. **WSL2 VHD space** — Docker Desktop on Windows uses a VHD (`docker_data.vhdx`). Large
   layers (pip install ~66s, venv copy ~90s) fill the VHD and cause daemon EOF crashes during
   image export. Run `docker builder prune -f` between failed builds to reclaim space.
   `.wslconfig` (at `C:\Users\<user>\`) controls WSL2 RAM/swap: `memory=6GB swap=4GB` is the
   minimum for this stack.
