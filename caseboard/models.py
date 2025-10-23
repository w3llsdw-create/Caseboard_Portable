from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import List, Optional, Dict, Any
import uuid

from .constants import normalize_case_type

DATE_FMT = "%Y-%m-%d"


def parse_date(value: str | date | None) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return datetime.strptime(value, DATE_FMT).date()


def date_str(d: Optional[date]) -> str:
    return d.strftime(DATE_FMT) if d else ""


@dataclass
class Deadline:
    due_date: date
    description: str
    resolved: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Deadline":
        due_date = parse_date(data.get("due_date"))
        if due_date is None:
            raise ValueError("due_date is required")
        return cls(
            due_date=due_date,
            description=data.get("description", ""),
            resolved=bool(data.get("resolved", False)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "due_date": date_str(self.due_date),
            "description": self.description,
            "resolved": self.resolved,
        }


@dataclass
class Case:
    id: str
    case_number: str
    county: str
    division: str
    judge: str
    case_name: str
    stage: str
    case_type: str = "Personal Injury"  # Case type for color coding
    opposing_counsel: str = ""
    opposing_firm: str = ""
    paralegal: str = ""
    current_task: str = ""
    attention: str = "waiting"  # waiting | needs attention
    sol_date: Optional[date] = None
    deadlines: List[Deadline] = field(default_factory=list)
    status: str = "open"  # open | closed | archived

    @classmethod
    def new(
        cls,
        case_number: str,
        county: str,
        division: str,
        judge: str,
        case_name: str,
        stage: str,
        case_type: str = "Personal Injury",
        opposing_counsel: str = "",
        opposing_firm: str = "",
        paralegal: str = "",
        current_task: str = "",
        attention: str = "waiting",
        sol_date: Optional[str | date] = None,
        status: str = "open",
    ) -> "Case":
        normalized_type = normalize_case_type(case_type) if case_type else "Personal Injury"
        return cls(
            id=str(uuid.uuid4()),
            case_number=case_number,
            county=county,
            division=division,
            judge=judge,
            case_name=case_name,
            stage=stage,
            case_type=normalized_type,
            opposing_counsel=opposing_counsel,
            opposing_firm=opposing_firm,
            paralegal=paralegal,
            current_task=current_task,
            attention=attention,
            sol_date=parse_date(sol_date) if sol_date else None,
            deadlines=[],
            status=status,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Case":
        deadlines = [Deadline.from_dict(d) for d in data.get("deadlines", [])]
        stored_type = data.get("case_type") or "Personal Injury"
        normalized_type = normalize_case_type(stored_type)
        return cls(
            id=data.get("id") or str(uuid.uuid4()),
            case_number=data.get("case_number", ""),
            county=data.get("county", ""),
            division=data.get("division", ""),
            judge=data.get("judge", ""),
            case_name=data.get("case_name", ""),
            stage=data.get("stage", ""),
            case_type=normalized_type,
            opposing_counsel=data.get("opposing_counsel", ""),
            opposing_firm=data.get("opposing_firm", ""),
            paralegal=data.get("paralegal", ""),
            current_task=data.get("current_task", ""),
            attention=data.get("attention", "waiting"),
            sol_date=parse_date(data.get("sol_date")) if data.get("sol_date") else None,
            deadlines=deadlines,
            status=data.get("status", "open"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "case_number": self.case_number,
            "county": self.county,
            "division": self.division,
            "judge": self.judge,
            "case_name": self.case_name,
            "stage": self.stage,
            "case_type": self.case_type,
            "opposing_counsel": self.opposing_counsel,
            "opposing_firm": self.opposing_firm,
            "paralegal": self.paralegal,
            "current_task": self.current_task,
            "attention": self.attention,
            "sol_date": date_str(self.sol_date) if self.sol_date else None,
            "deadlines": [d.to_dict() for d in self.deadlines],
            "status": self.status,
        }

    def next_deadline(self, as_of: Optional[date] = None) -> Optional[Deadline]:
        as_of = as_of or date.today()
        upcoming = [d for d in self.deadlines if not d.resolved and d.due_date >= as_of]
        upcoming.sort(key=lambda d: d.due_date)
        return upcoming[0] if upcoming else None

    def add_deadline(self, due_date: str | date, description: str) -> None:
        parsed_date = parse_date(due_date)
        if parsed_date is None:
            raise ValueError("due_date is required")
        self.deadlines.append(Deadline(due_date=parsed_date, description=description, resolved=False))