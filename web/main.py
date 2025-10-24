from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Add caseboard module to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from caseboard.data_store import CaseDataStore

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "cases.json"
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Caseboard Web Dashboard", version="1.0.0")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=FileResponse)
async def root() -> FileResponse:
    """Serve the main dashboard shell."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/cases")
async def get_cases() -> dict[str, object]:
    """Return the raw case data along with a generated timestamp."""
    if not DATA_PATH.exists():
        raise HTTPException(status_code=404, detail="cases.json not found")

    try:
        with DATA_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail="Invalid cases.json format") from exc

    return {
        "meta": {
            "version": payload.get("version"),
            "saved_at": payload.get("saved_at"),
        },
        "cases": payload.get("cases", []),
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


@app.get("/cases/{case_id}/focus-history")
async def get_focus_history(case_id: str) -> dict[str, object]:
    """Return the focus history for a specific case."""
    try:
        # Load case data to get case_number
        if not DATA_PATH.exists():
            raise HTTPException(status_code=404, detail="cases.json not found")
        
        with DATA_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        
        # Find the case
        case_data = None
        for case in payload.get("cases", []):
            if case.get("id") == case_id:
                case_data = case
                break
        
        if not case_data:
            raise HTTPException(status_code=404, detail="Case not found")
        
        case_number = case_data.get("case_number", "")
        
        # Get focus history
        store = CaseDataStore()
        entries = store.get_focus_history(case_id, case_number)
        
        # Convert to JSON-serializable format
        history_entries = [
            {
                "timestamp": entry.timestamp.isoformat() + "Z",
                "focus_text": entry.focus_text,
                "actor": entry.actor
            }
            for entry in entries
        ]
        
        return {
            "case_id": case_id,
            "case_number": case_number,
            "case_name": case_data.get("case_name", ""),
            "entries": history_entries,
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
