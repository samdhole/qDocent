# qDocent — Deployment Guide

> **For:** qDocent system owners and operators
>
> **Goal:** Start the full application stack on your machine using a single command.
>
> All commands are written for **Windows PowerShell**. Linux equivalents are noted in callouts.

---

## Prerequisites

Before you begin, install:

| Software | Download | Required version |
|---|---|---|
| Docker Desktop | https://www.docker.com/products/docker-desktop | 4.0+ |
| Git | https://git-scm.com/download/win | Any recent version |

**Docker Desktop setup (Windows only):**
1. Open Docker Desktop → Settings → General
2. Ensure **"Use the WSL 2 based engine"** is checked
3. Click Apply & Restart

Verify Docker is running:

```powershell
docker --version
docker compose version
```

Expected: version numbers print without errors.

> **Linux equivalent:** Install Docker Engine + Docker Compose plugin via your package manager (`apt`, `dnf`, etc.). No WSL2 needed.

---

## One-Time Setup

Do this once on a fresh clone.

### 1. Clone the repository

```powershell
git clone <repository-url>
cd qdocent
```

### 2. Set up environment configuration

Copy the client config template to `.env`:

```powershell
Copy-Item .env.example.client .env
```

Open `.env` in a text editor and fill in your Google API key:

```
GOOGLE_API_KEY=AIza...your-real-key-here...
```

Get a key at https://aistudio.google.com/app/apikey (free tier is sufficient for demo use).

> **⚠️ Important:** Never share `.env` or commit it to git. It is already in `.gitignore`.

### 3. Set up the R2R AI engine config

Copy the example config:

```powershell
Copy-Item r2r_gemini.toml.example r2r_gemini.toml
```

Open `r2r_gemini.toml` and find the `[auth]` section. Replace the placeholder password (the file ships with `CHANGE_ME`):

```toml
[auth]
default_admin_password = "CHANGE_ME"   # ← replace CHANGE_ME with a real password
```

> **⚠️ Required:** Replace `CHANGE_ME` with a strong password before starting. Leaving the default is a security risk.

---

## Starting the Application

### Build and start (first run, or after any code change)

```powershell
docker compose build
docker compose up -d
```

The first build takes **20–45 minutes** (the API image downloads Python packages + Playwright + docling AI models; the web image is faster at 2–5 minutes). Subsequent starts are fast.

### Check that all services are running

```powershell
docker compose ps
```

All four services should show status `running`:

```
NAME       STATUS
postgres   running (healthy)
r2r        running
api        running (healthy)
web        running
```

### Open the application

Open a browser and go to: **http://localhost:3000**

You should see the qDocent notebooks page.

> **Linux equivalent:** Same commands — `docker compose` works identically on Linux.

---

## Verifying the Stack

Quick health checks for each service:

```powershell
# Web UI
curl http://localhost:3000

# FastAPI backend
curl http://localhost:8000/health

# R2R AI engine
curl http://localhost:7272/v3/health
```

All three should return `200 OK` responses.

---

## Stopping and Restarting

### Stop all services (data is preserved)

```powershell
docker compose down
```

This stops all containers. Your documents, notebooks, and AI indexes are preserved.

### Start again after stopping

```powershell
docker compose up -d
```

### Restart a single service

```powershell
docker compose restart api
```

---

## ⚠️ Complete Data Wipe

> **Destructive — use with caution.**

To delete ALL data including ingested documents and AI vector indexes:

```powershell
docker compose down -v
```

The `-v` flag deletes the Docker volume containing the vector database. All ingested documents will need to be re-uploaded. Use this only to start completely fresh.

---

## VPS / Remote Server Deployment

To run qDocent on a remote server (e.g., a VPS or cloud VM):

### 1. Set the API URL to your server's IP or domain

Edit `.env` on the server:

```
NEXT_PUBLIC_API_URL=http://YOUR_SERVER_IP:8000
```

Replace `YOUR_SERVER_IP` with your server's public IP address or domain name.

### 2. Rebuild the web image with the new URL

> **⚠️ Required:** The API URL is baked into the browser bundle at build time. You MUST rebuild after changing it.

```powershell
docker compose build web
docker compose up -d
```

### 3. Configure CORS for the API

Edit `.env` and add your server's domain to `CORS_ORIGINS`:

```
CORS_ORIGINS=http://YOUR_SERVER_IP:3000
```

Then restart the API:

```powershell
docker compose restart api
```

### 4. Open firewall ports

Ensure ports 3000 and 8000 are accessible from the internet (your server's firewall settings).

> **Reminder:** Port 5432 (Postgres) is intentionally NOT exposed to the internet. Only open 3000 and 8000.

---

## Key Handoff (API Key Transfer)

When transferring the project to a new owner, follow this order to prevent service disruption:

1. **New owner generates and verifies their key first** — this ensures a working key is ready before the old key is removed.
2. **Old owner then rotates/deletes the original key** — only after confirming the new key is in place and working.

### The new owner does:

1. Create their own Google API key at https://aistudio.google.com/app/apikey
2. Edit `.env` and replace `GOOGLE_API_KEY` with their key:
   ```
   GOOGLE_API_KEY=AIza...new-owners-key...
   ```
3. Restart the services:
   ```powershell
   docker compose down
   docker compose up -d
   ```

### The previous owner does:

After confirming the new owner's key works, delete or rotate the original API key at https://aistudio.google.com/app/apikey to prevent unexpected charges.

---

## Security Note

### Demo corpus (Robinhood 10-K annual report)

The application ships with a sample document corpus based on Robinhood's publicly available 10-K annual report filing. This is a public document — using it for demonstration purposes requires no special data handling agreement.

### Using with real confidential documents

Before ingesting real client or confidential documents:

1. **Use your own API key.** The Google API key is the billing and access account for all AI queries. Transfer to your own key before processing sensitive data (see Key Handoff above).

2. **Security review.** The current deployment is configured for demonstration. Before processing confidential documents, review:
   - Network exposure (which ports are open, who can access them)
   - Access controls (R2R admin password, API key security)
   - Data residency (all data is stored locally; Google Gemini API calls send document text to Google's servers)

3. **License note.** This application includes PyMuPDF (AGPL-3.0 license). Distributing this software to end users as part of a closed-source product requires a commercial PyMuPDF license from Artifex Software. Contact Artifex at https://pymupdf.readthedocs.io/en/latest/about.html#license before commercial deployment.

---

## Troubleshooting

### "docker: command not found"
Docker Desktop is not installed or not running. Install it from https://www.docker.com/products/docker-desktop and restart.

### R2R crashes immediately on startup
Two common causes:
- **Missing GOOGLE_API_KEY:** Open `.env` and ensure `GOOGLE_API_KEY` has a real value (not blank).
- **Missing r2r_gemini.toml:** Run `Copy-Item r2r_gemini.toml.example r2r_gemini.toml` and set the admin password.

### Web UI shows "Failed to fetch" errors
`NEXT_PUBLIC_API_URL` was baked with the wrong value at build time. If you changed the API URL after building, rebuild:
```powershell
docker compose build web
docker compose up -d
```

### "port is already allocated" error
Another process is using port 3000, 7272, or 8000. Find and stop it, or change the host port mapping in `docker-compose.yml` (left side of the colon, e.g., `"3001:3000"`).

### Services keep restarting
Check logs for the failing service:
```powershell
docker compose logs r2r
docker compose logs api
```
