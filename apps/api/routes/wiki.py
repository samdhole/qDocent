# pattern: Imperative Shell
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from apps.api.services import notebook_store, wiki_generator, wiki_store

router = APIRouter(prefix="/notebooks/{notebook_id}/wiki", tags=["wiki"])


@router.post("/generate", status_code=202)
def generate_wiki(notebook_id: str, background_tasks: BackgroundTasks):
    nb = notebook_store.get_notebook(notebook_id)
    if not nb:
        raise HTTPException(status_code=404, detail="Notebook not found")

    docs = notebook_store.list_documents(notebook_id)
    if not docs:
        raise HTTPException(
            status_code=422,
            detail="Cannot generate wiki: notebook has no documents",
        )

    job_id = uuid.uuid4().hex
    job = wiki_store.create_job(notebook_id, job_id, pages_total=0)
    wiki_store.mark_stale_jobs(notebook_id)

    background_tasks.add_task(
        wiki_generator.generate_wiki,
        notebook_id,
        nb.get("r2r_collection_id", ""),
        job_id,
    )
    return JSONResponse(status_code=202, content={"job_id": job_id, "status": "queued"})


@router.get("/jobs/{job_id}")
def get_wiki_job(notebook_id: str, job_id: str) -> dict:
    job = wiki_store.get_job(job_id)
    if not job or job["notebook_id"] != notebook_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("")
def get_wiki(notebook_id: str) -> dict:
    structure = wiki_store.get_structure(notebook_id)
    pages = wiki_store.list_pages(notebook_id)
    return {
        "notebook_id": notebook_id,
        "structure": structure,
        "pages": pages,
    }


@router.get("/{slug}")
def get_wiki_page(notebook_id: str, slug: str) -> dict:
    page = wiki_store.get_page(notebook_id, slug)
    if not page:
        raise HTTPException(status_code=404, detail=f"Wiki page '{slug}' not found")
    return page


@router.delete("", status_code=204)
def delete_wiki(notebook_id: str) -> None:
    wiki_store.delete_wiki(notebook_id)
