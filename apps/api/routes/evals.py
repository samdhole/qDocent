from fastapi import APIRouter, BackgroundTasks, HTTPException

from apps.api.services import ragas_runner, report_writer

router = APIRouter(prefix="/eval")


@router.get("/results")
def eval_results() -> list[dict]:
    rows = report_writer.latest_eval_results()
    if not rows:
        raise HTTPException(status_code=404, detail="No eval results found. Run POST /eval/run first.")
    return rows


@router.post("/run")
def eval_run(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(ragas_runner.run_and_save)
    return {"status": "started", "message": "Eval running in background. Check GET /eval/results when complete."}
