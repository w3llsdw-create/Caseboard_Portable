from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, List

from .schema import CasePayload

CSV_FIELDS = [
    "case_number",
    "case_name",
    "case_type",
    "stage",
    "attention",
    "status",
    "paralegal",
    "current_task",
    "next_due",
]


def export_cases(path: Path, cases: Iterable[CasePayload]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for case in cases:
            row = {field: getattr(case, field) or "" for field in CSV_FIELDS}
            writer.writerow(row)
    return path


def import_cases(path: Path) -> List[CasePayload]:
    path = Path(path)
    cases: List[CasePayload] = []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            payload = CasePayload(
                case_number=row.get("case_number", ""),
                case_name=row.get("case_name", ""),
                case_type=row.get("case_type", ""),
                stage=row.get("stage", ""),
                attention=row.get("attention", "waiting"),
                status=row.get("status", "open"),
                paralegal=row.get("paralegal", ""),
                current_task=row.get("current_task", ""),
                next_due=row.get("next_due") or None,
                deadlines=[],
            )
            cases.append(payload)
    return cases


def dedupe_cases(cases: Iterable[CasePayload]) -> List[CasePayload]:
    seen: dict[str, CasePayload] = {}
    for case in cases:
        seen.setdefault(case.case_number, case)
    return list(seen.values())
