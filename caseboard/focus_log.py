"""Focus history logging for case management."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class FocusEntry(BaseModel):
    """A single focus history entry."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    focus_text: str
    actor: str = "user"
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }


class FocusLog(BaseModel):
    """Focus history log for a single case."""
    case_id: str
    case_number: str
    entries: List[FocusEntry] = Field(default_factory=list)
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }


class FocusLogManager:
    """Manages focus history logs for cases."""
    
    def __init__(self, log_dir: Optional[Path] = None) -> None:
        """Initialize the focus log manager.
        
        Args:
            log_dir: Directory to store focus logs. Defaults to data/focus_logs/
        """
        if log_dir is None:
            log_dir = Path("data") / "focus_logs"
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_log_path(self, case_id: str) -> Path:
        """Get the path to a case's focus log file."""
        return self.log_dir / f"{case_id}.json"
    
    def load_log(self, case_id: str, case_number: str) -> FocusLog:
        """Load the focus log for a case.
        
        Args:
            case_id: The case ID
            case_number: The case number (for creating new logs)
            
        Returns:
            The focus log for the case
        """
        log_path = self._get_log_path(case_id)
        if not log_path.exists():
            return FocusLog(case_id=case_id, case_number=case_number, entries=[])
        
        try:
            with log_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return FocusLog.model_validate(data)
        except (json.JSONDecodeError, Exception):
            # If corrupted, start fresh
            return FocusLog(case_id=case_id, case_number=case_number, entries=[])
    
    def add_entry(
        self, 
        case_id: str, 
        case_number: str, 
        focus_text: str, 
        *, 
        actor: str = "user"
    ) -> None:
        """Add a focus entry to a case's log.
        
        Args:
            case_id: The case ID
            case_number: The case number
            focus_text: The focus text
            actor: Who made the change (default: "user")
        """
        # Don't log empty focus entries
        if not focus_text or not focus_text.strip():
            return
        
        log = self.load_log(case_id, case_number)
        
        # Don't log if the focus text is the same as the most recent entry
        if log.entries and log.entries[-1].focus_text == focus_text:
            return
        
        entry = FocusEntry(
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            focus_text=focus_text,
            actor=actor
        )
        log.entries.append(entry)
        
        self._save_log(log)
    
    def _save_log(self, log: FocusLog) -> None:
        """Save a focus log to disk."""
        log_path = self._get_log_path(log.case_id)
        
        # Convert to dict for JSON serialization
        data = {
            "case_id": log.case_id,
            "case_number": log.case_number,
            "entries": [
                {
                    "timestamp": (
                        entry.timestamp.isoformat() + "Z"
                        if entry.timestamp.tzinfo is None
                        else entry.timestamp.replace(tzinfo=None).isoformat() + "Z"
                    ),
                    "focus_text": entry.focus_text,
                    "actor": entry.actor
                }
                for entry in log.entries
            ]
        }
        
        # Write atomically
        tmp_path = log_path.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp_path.replace(log_path)
    
    def get_recent_entries(
        self, 
        case_id: str, 
        case_number: str, 
        limit: int = 10
    ) -> List[FocusEntry]:
        """Get the most recent focus entries for a case.
        
        Args:
            case_id: The case ID
            case_number: The case number
            limit: Maximum number of entries to return (default: 10)
            
        Returns:
            List of focus entries, most recent first
        """
        log = self.load_log(case_id, case_number)
        return list(reversed(log.entries[-limit:]))
    
    def get_all_entries(self, case_id: str, case_number: str) -> List[FocusEntry]:
        """Get all focus entries for a case.
        
        Args:
            case_id: The case ID
            case_number: The case number
            
        Returns:
            List of all focus entries, oldest first
        """
        log = self.load_log(case_id, case_number)
        return log.entries
