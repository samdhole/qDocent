from fastapi import APIRouter, HTTPException

from apps.api.services import report_writer

router = APIRouter(prefix="/reports")


@router.get("/ingestion/{document_id}")
def ingestion_report(document_id: str) -> dict:
    """Return ingestion report JSON for a document. URL: /reports/ingestion/{id}."""
    report = report_writer.ingestion_report(document_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"No ingestion report for '{document_id}'.")
    return report
