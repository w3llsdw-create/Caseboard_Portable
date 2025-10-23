from __future__ import annotations

from datetime import date, datetime, timezone
from typing import List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from .constants import normalize_case_type

MAX_FOCUS_LENGTH = 280
APP_SCHEMA_VERSION = 2


def _clean(text: Optional[str], *, max_length: Optional[int] = None) -> str:
    if text is None:
        return ""
    cleaned = " ".join(text.strip().split())
    if max_length is not None and len(cleaned) > max_length:
        return cleaned[:max_length]
    return cleaned


class DeadlinePayload(BaseModel):
    due_date: date
    description: str = ""
    resolved: bool = False

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }

    @field_validator("description")
    @classmethod
    def _trim_desc(cls, value: str) -> str:
        return _clean(value)


class CasePayload(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    case_number: str
    case_name: str = ""
    case_type: str = "Personal Injury"
    stage: str = ""
    attention: Literal["waiting", "needs_attention"] = "waiting"
    status: str = "open"
    paralegal: str = ""
    current_task: str = ""
    next_due: Optional[str] = None
    county: str = ""
    division: str = ""
    judge: str = ""
    opposing_counsel: str = ""
    opposing_firm: str = ""
    sol_date: Optional[date] = None
    deadlines: List[DeadlinePayload] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
        "json_encoders": {datetime: lambda value: value.isoformat()},
    }

    @field_validator("case_number", mode="before")
    @classmethod
    def _coerce_case_number(cls, value: str) -> str:
        cleaned = _clean(value)
        if not cleaned:
            raise ValueError("case number is required")
        return cleaned

    @field_validator("case_name", "stage", "paralegal", "county", "division", "judge", "opposing_counsel", "opposing_firm", mode="before")
    @classmethod
    def _trim_text_fields(cls, value: Optional[str]) -> str:
        return _clean(value)

    @field_validator("case_type", mode="before")
    @classmethod
    def _normalize_case_type(cls, value: Optional[str]) -> str:
        return normalize_case_type(value or "Personal Injury")

    @field_validator("current_task", mode="before")
    @classmethod
    def _cap_focus(cls, value: Optional[str]) -> str:
        return _clean(value, max_length=MAX_FOCUS_LENGTH)

    @field_validator("status")
    @classmethod
    def _normalize_status(cls, value: str) -> str:
        if value is None:
            return "open"
        cleaned = value.strip().lower()
        allowed = {"open", "filed", "pre-filing", "closed", "archived"}
        if cleaned not in allowed:
            raise ValueError(f"invalid status '{value}'")
        return cleaned

    @field_validator("next_due", mode="before")
    @classmethod
    def _coerce_next_due(cls, value: Optional[str]) -> Optional[str]:
        cleaned = _clean(value)
        if not cleaned:
            return None
        try:
            datetime.strptime(cleaned, "%Y-%m-%d")
        except ValueError as exc:  # pragma: no cover - validated upstream
            raise ValueError("next_due must be YYYY-MM-DD") from exc
        return cleaned

    @property
    def to_case_dict(self) -> dict:
        data = self.model_dump(exclude_none=True)
        data["attention"] = self.attention
        data["current_task"] = self.current_task
        data["deadlines"] = [deadline.model_dump(mode="json") for deadline in self.deadlines]
        if self.sol_date:
            data["sol_date"] = self.sol_date.isoformat()
        else:
            data["sol_date"] = None
        return data


class CaseFileModel(BaseModel):
    schema_version: int = Field(default=APP_SCHEMA_VERSION)
    version: int = 1
    saved_at: datetime = Field(default_factory=datetime.utcnow)
    cases: List[CasePayload] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }

    @field_validator("saved_at", mode="before")
    @classmethod
    def _normalise_saved_at(cls, value: object) -> datetime:
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            cleaned = value.strip()
            if cleaned.endswith("Z") and "+" in cleaned[:-1]:
                cleaned = cleaned[:-1]
            if cleaned.endswith("Z"):
                cleaned = cleaned[:-1] + "+00:00"
            try:
                parsed = datetime.fromisoformat(cleaned)
            except ValueError as exc:
                raise ValueError(f"Invalid saved_at value: {value}") from exc
        else:
            raise ValueError("saved_at must be datetime or ISO string")

        if parsed.tzinfo is not None:
            return parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

    def to_serialisable(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "version": self.version,
            "saved_at": self.saved_at.isoformat() + "Z",
            "cases": [case.to_case_dict for case in self.cases],
        }
