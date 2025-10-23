from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
