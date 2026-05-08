from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes import ask, evals, ingest, reports, workflows

app = FastAPI(
    title="DocQuery API",
    description="RAG portfolio demo — wraps R2R and RAGAS.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ask.router)
app.include_router(ingest.router)
app.include_router(evals.router)
app.include_router(reports.router)
app.include_router(workflows.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
