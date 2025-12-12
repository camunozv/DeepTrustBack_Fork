from fastapi import APIRouter, HTTPException, Query
from app.services.log_service import LogService
from app.schemas.detection_log_schema import DetectionLog
from typing import List

log_handler = APIRouter(tags=["logs"])
log_service = LogService()

@log_handler.get(
    "/logs/get_by_id",
    response_model=DetectionLog,
    summary="Get a single log by id",
    description=(
        "## Input\n"
        "- **Query param**: `id` (integer)\n\n"
        "## What this endpoint does\n"
        "Fetches a single row from the `DetectionLog` table.\n\n"
        "## Output\n"
        "A single `DetectionLog` JSON object with:\n"
        "- `id`: primary key\n"
        "- `date`, `hour`: server timestamp at analysis time\n"
        "- `classification`: \"Bonafide\" | \"Deepfake\" (may be null for legacy rows)\n"
        "- `score`: 0..100 (may be null for legacy rows)\n"
    ),
    responses={404: {"description": "Log not found."}},
)
def get_log_by_id(
    id: int = Query(..., description="DetectionLog id (primary key).", examples=[1, 2, 123])
):
    log = log_service.get_log_by_id(id)
    if log is None:
        raise HTTPException(status_code=404, detail="Log not found")
    row = getattr(log, "_mapping", log)
    return DetectionLog(
        id=row["id"],
        date=row["date"],
        hour=row["hour"],
        classification=row.get("classification"),
        score=row.get("score"),
    )

@log_handler.get(
    "/logs/all",
    response_model=List[DetectionLog],
    summary="List all detection logs",
    description=(
        "## Input\n"
        "- No parameters\n\n"
        "## What this endpoint does\n"
        "Returns all rows from the `DetectionLog` table.\n\n"
        "## Output\n"
        "A JSON array of `DetectionLog` objects."
    ),
)
def get_all_logs():
    list_of_logs = log_service.get_all_logs()
    
    result = []
    for log in list_of_logs:
        row = getattr(log, "_mapping", log)
        result.append(DetectionLog(
            id=row["id"],
            date=row["date"],
            hour=row["hour"],
            classification=row.get("classification"),
            score=row.get("score"),
        ))
    
    return result


@log_handler.get(
    "/logs/by_state",
    response_model=List[DetectionLog],
    summary="List logs filtered by classification",
    description=(
        "## Input\n"
        "- **Query param**: `state`\n"
        "  - accepted values (case-insensitive): `deepfake`, `bonafide`\n\n"
        "## What this endpoint does\n"
        "Filters rows in `DetectionLog` by the `classification` column.\n\n"
        "## Output\n"
        "A JSON array of matching `DetectionLog` objects."
    ),
)
def get_logs_by_state(
    state: str = Query(..., description="Classification filter: deepfake|bonafide (case-insensitive).")
):
        
    # Backwards-compatible endpoint: accepts "deepfake" or "bonafide"
    normalized = state.strip().lower()
    if normalized not in ("deepfake", "bonafide"):
        return []

    list_of_logs = log_service.get_logs_by_classification(normalized.capitalize())
    
    result = []
    for log in list_of_logs:
        row = getattr(log, "_mapping", log)
        result.append(DetectionLog(
            id=row["id"],
            date=row["date"],
            hour=row["hour"],
            classification=row.get("classification"),
            score=row.get("score"),
        ))
    
    return result


@log_handler.delete(
    "/logs/delete_by_id",
    summary="Delete a log by id",
    description=(
        "## Input\n"
        "- **Query param**: `id` (integer)\n\n"
        "## What this endpoint does\n"
        "Deletes the row from `DetectionLog` whose primary key matches `id`.\n\n"
        "## Output\n"
        "Returns the DB driver result for the delete operation."
    ),
)
def delete_log(id: int = Query(..., description="DetectionLog id (primary key).")):
    return log_service.delete_log_by_id(id)
