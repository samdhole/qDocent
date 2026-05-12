# pattern: Imperative Shell
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from apps.api.routes import ask, conversations, documents, evals, ingest, reports, workflows
from apps.api.services import ingest_job_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    ingest_job_store.mark_stale_running_jobs()
    yield


app = FastAPI(
    title="qDocent API",
    description="RAG portfolio demo — wraps R2R and RAGAS.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ask.router)
app.include_router(conversations.router)
app.include_router(documents.router)
app.include_router(ingest.router)
app.include_router(evals.router)
app.include_router(reports.router)
app.include_router(workflows.router)

Path("data/figures").mkdir(parents=True, exist_ok=True)
app.mount("/figures", StaticFiles(directory="data/figures"), name="figures")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
