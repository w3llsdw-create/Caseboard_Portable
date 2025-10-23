from __future__ import annotations
from pathlib import Path
from typing import Iterable, List

from .data_store import CaseDataStore, CasePayload
from .models import Case
from .schema import DeadlinePayload

DEFAULT_DATA_DIR = Path("data")
DEFAULT_DATA_FILE = DEFAULT_DATA_DIR / "cases.json"


def _to_payload(case: Case) -> CasePayload:
    deadlines = [
        DeadlinePayload(due_date=d.due_date, description=d.description, resolved=d.resolved)
        for d in case.deadlines
    ]

    next_deadline = case.next_deadline()
    next_due = next_deadline.due_date.isoformat() if next_deadline else None

    payload = CasePayload(
        id=case.id,
        case_number=case.case_number,
        case_name=case.case_name,
        case_type=case.case_type,
        stage=case.stage,
        attention=case.attention,
        status=case.status,
        paralegal=case.paralegal,
        current_task=case.current_task,
        next_due=next_due,
        county=case.county,
        division=case.division,
        judge=case.judge,
        opposing_counsel=case.opposing_counsel,
        opposing_firm=case.opposing_firm,
        sol_date=case.sol_date,
        deadlines=deadlines,
    )
    return payload


def load_cases(file_path: Path = DEFAULT_DATA_FILE) -> List[Case]:
    store = CaseDataStore(file_path)
    model = store.load()
    cases: List[Case] = []
    for payload in model.cases:
        case_dict = payload.to_case_dict()
        cases.append(Case.from_dict(case_dict))
    return cases


def save_cases(cases: Iterable[Case], file_path: Path = DEFAULT_DATA_FILE) -> None:
    store = CaseDataStore(file_path)
    current = store.load(create_backup=False)
    payloads = [_to_payload(case) for case in cases]
    store.save(payloads, previous=current)