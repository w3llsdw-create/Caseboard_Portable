from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from filelock import FileLock, Timeout
from pydantic import ValidationError as PydanticValidationError

from .exceptions import CorruptDataError, DataLockError, MigrationError, ValidationError
from .schema import APP_SCHEMA_VERSION, CaseFileModel, CasePayload

DATA_DIR = Path("data")
BACKUP_DIR = DATA_DIR / "backups"
MIGRATIONS_DIR = DATA_DIR / "migrations"
SUMMARY_FILE = DATA_DIR / "summary.json"
AUDIT_LOG = DATA_DIR / "audit.log"
BUMP_FILE = DATA_DIR / ".bump"
CASES_FILE = DATA_DIR / "cases.json"

BACKUP_DIR.mkdir(parents=True, exist_ok=True)
MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class SaveResult:
    saved_at: datetime
    audit_entries: List[str]
    summary: Dict[str, object]
    file_path: Path


class CaseDataStore:
    """Coordinate all on-disk interactions for Caseboard data."""

    def __init__(self, data_file: Path = CASES_FILE, lock_timeout: float = 5.0) -> None:
        self.data_file = Path(data_file)
        lock_name = f"{self.data_file.name}.lock"
        self.lock = FileLock(str(self.data_file.parent / lock_name))
        self.lock_timeout = lock_timeout
        self.current_model: Optional[CaseFileModel] = None
        self.last_loaded_raw: Optional[str] = None

    # ------------------------------------------------------------------
    # Load / backup / migrations
    # ------------------------------------------------------------------
    def load(self, *, create_backup: bool = True) -> CaseFileModel:
        """Load the case file from disk with validation and migrations."""
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.data_file.exists():
            empty_model = CaseFileModel(schema_version=APP_SCHEMA_VERSION)
            self._write_atomic(empty_model.to_serialisable())

        try:
            with self.lock.acquire(timeout=self.lock_timeout):
                raw_text = self.data_file.read_text(encoding="utf-8")
                if create_backup:
                    self._create_backup(raw_text)
        except Timeout as exc:  # pragma: no cover - depends on runtime contention
            raise DataLockError("Unable to acquire data lock") from exc

        self.last_loaded_raw = raw_text

        try:
            document = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise CorruptDataError("cases.json is corrupted", backups=self._list_backups()) from exc

        schema_version = int(document.get("schema_version", 1))
        migrated_model: CaseFileModel

        if schema_version < APP_SCHEMA_VERSION:
            migrated_model = self._migrate(document, raw_text, schema_version)
            self.current_model = migrated_model
            return migrated_model

        try:
            model = CaseFileModel.model_validate(document)
        except PydanticValidationError as exc:
            raise ValidationError("Data file validation failed") from exc

        self.current_model = model
        return model

    def _create_backup(self, raw_text: str) -> None:
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        backup_path = BACKUP_DIR / f"cases-{timestamp}.json"
        backup_path.write_text(raw_text, encoding="utf-8")

    def _list_backups(self) -> List[str]:
        return sorted(str(path) for path in BACKUP_DIR.glob("cases-*.json"))

    def _migrate(self, document: Dict[str, object], raw_text: str, from_version: int) -> CaseFileModel:
        """Perform schema migrations and persist diff output."""
        doc = dict(document)
        try:
            if from_version < 2:
                doc.setdefault("version", document.get("version", 1))
                doc["schema_version"] = APP_SCHEMA_VERSION
                # Ensure saved_at exists
                if "saved_at" not in doc:
                    doc["saved_at"] = datetime.utcnow().isoformat() + "Z"
                # Normalize case payloads
                cases = []
                for item in doc.get("cases", []):  # type: ignore[arg-type]
                    try:
                        cases.append(CasePayload.model_validate(item).model_dump())
                    except PydanticValidationError as exc:
                        raise MigrationError("Failed to normalise case payload", context={"case": item}) from exc
                doc["cases"] = cases
        except Exception as exc:  # pragma: no cover - defensive
            raise MigrationError("Schema migration failed", context={"version": from_version}) from exc

        migrated_model = CaseFileModel.model_validate(doc)
        migrated_json = json.dumps(migrated_model.to_serialisable(), indent=2)
        self._write_migration_diff(raw_text, migrated_json)
        self._write_atomic(migrated_model.to_serialisable())
        return migrated_model

    def _write_migration_diff(self, original: str, migrated: str) -> None:
        import difflib

        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        diff_path = MIGRATIONS_DIR / f"cases-{timestamp}.diff"
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            migrated.splitlines(keepends=True),
            fromfile="cases.json (old)",
            tofile="cases.json (new)",
        )
        diff_path.write_text("".join(diff), encoding="utf-8")

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def save(
        self,
        cases: Sequence[CasePayload],
        *,
        actor: str = "system",
        action: str = "autosave",
        previous: Optional[CaseFileModel] = None,
    ) -> SaveResult:
        if previous is None:
            previous = self.current_model

        if previous is None:
            # Load to establish baseline
            previous = self.load(create_backup=False)

        resolved_cases = self._hydrate_identifiers(cases, previous)
        model = CaseFileModel(
            schema_version=APP_SCHEMA_VERSION,
            version=previous.version,
            saved_at=datetime.utcnow(),
            cases=resolved_cases,
        )

        payload = model.to_serialisable()

        summary: Dict[str, object] = {}
        audit_entries: List[str] = []

        try:
            with self.lock.acquire(timeout=self.lock_timeout):
                self._write_atomic(payload)
                summary = self._write_summary(model)
                audit_entries = self._append_audit(previous, model, actor=actor, action=action)
                self._touch_bump()
        except Timeout as exc:  # pragma: no cover - depends on runtime contention
            raise DataLockError("Unable to acquire data lock for save") from exc

        self.current_model = model

        return SaveResult(
            saved_at=model.saved_at,
            audit_entries=audit_entries,
            summary=summary,
            file_path=self.data_file,
        )

    def _hydrate_identifiers(self, cases: Sequence[CasePayload], previous: CaseFileModel) -> List[CasePayload]:
        by_case_no: Dict[str, CasePayload] = {case.case_number: case for case in previous.cases}
        hydrated: List[CasePayload] = []
        seen: set[str] = set()

        for payload in cases:
            case_number = payload.case_number
            seen.add(case_number)
            base = by_case_no.get(case_number)
            if base and not payload.id:
                payload.id = base.id
            elif base and payload.id != base.id:
                # Keep established stable id
                payload.id = base.id
            hydrated.append(payload)

        # Preserve existing cases that were not part of new payload (should represent deletions)
        return hydrated

    def _write_atomic(self, payload: Dict[str, object]) -> None:
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.data_file.with_suffix(".tmp")
        json_text = json.dumps(payload, indent=2)
        tmp_path.write_text(json_text, encoding="utf-8")
        os.replace(tmp_path, self.data_file)

    def _write_summary(self, model: CaseFileModel) -> Dict[str, object]:
        total = len(model.cases)
        active = sum(1 for case in model.cases if case.status in {"open", "filed", "pre-filing"})
        needs_attention = sum(1 for case in model.cases if case.attention == "needs_attention")

        upcoming_deadlines: List[Tuple[str, str]] = []
        for case in model.cases:
            for deadline in case.deadlines:
                if deadline.resolved:
                    continue
                upcoming_deadlines.append((case.case_number, deadline.due_date.isoformat()))

        upcoming_deadlines.sort(key=lambda item: item[1])
        summary_payload = {
            "total": total,
            "active": active,
            "needs_attention": needs_attention,
            "upcoming": upcoming_deadlines[:5],
            "saved_at": model.saved_at.isoformat() + "Z",
        }

        tmp_path = SUMMARY_FILE.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
        try:
            os.replace(tmp_path, SUMMARY_FILE)
        except PermissionError:
            try:
                SUMMARY_FILE.unlink(missing_ok=True)
                os.replace(tmp_path, SUMMARY_FILE)
            except PermissionError:
                SUMMARY_FILE.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
                tmp_path.unlink(missing_ok=True)
        return summary_payload

    def _touch_bump(self) -> None:
        BUMP_FILE.write_text(datetime.utcnow().isoformat() + "Z", encoding="utf-8")

    def _append_audit(self, previous: CaseFileModel, current: CaseFileModel, *, actor: str, action: str) -> List[str]:
        log_lines: List[str] = []
        timestamp = current.saved_at.isoformat() + "Z"

        previous_map = {case.case_number: case for case in previous.cases}
        current_map = {case.case_number: case for case in current.cases}

        # Detect deletions
        for case_no in sorted(previous_map.keys() - current_map.keys()):
            log_lines.append(f"{timestamp} | {actor} | deleted | {case_no}")

        # Detect additions and updates
        for case_no, case in current_map.items():
            if case_no not in previous_map:
                log_lines.append(f"{timestamp} | {actor} | created | {case_no}")
                continue

            diffs = self._diff_case(previous_map[case_no], case)
            if diffs:
                diff_text = "; ".join(f"{field}:{before}->{after}" for field, before, after in diffs)
                log_lines.append(f"{timestamp} | {actor} | updated | {case_no} | {diff_text}")

        if not log_lines:
            return []

        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG.open("a", encoding="utf-8") as handle:
            for line in log_lines:
                handle.write(line + "\n")

        return log_lines

    def _diff_case(self, previous: CasePayload, current: CasePayload) -> List[Tuple[str, str, str]]:
        fields = [
            "case_name",
            "case_type",
            "stage",
            "attention",
            "status",
            "paralegal",
            "current_task",
            "next_due",
            "county",
            "division",
            "judge",
            "opposing_counsel",
            "opposing_firm",
        ]
        diffs: List[Tuple[str, str, str]] = []
        for field_name in fields:
            old_value = getattr(previous, field_name)
            new_value = getattr(current, field_name)
            if old_value != new_value:
                diffs.append((field_name, self._format_diff_value(old_value), self._format_diff_value(new_value)))
        return diffs

    @staticmethod
    def _format_diff_value(value: object) -> str:
        if value is None:
            return "∅"
        if isinstance(value, str) and len(value) > 64:
            return value[:61] + "…"
        return str(value)


def load_cases() -> List[CasePayload]:
    store = CaseDataStore()
    model = store.load()
    return list(model.cases)


def save_cases(cases: Iterable[CasePayload]) -> SaveResult:
    store = CaseDataStore()
    model = store.load(create_backup=False)
    return store.save(list(cases), previous=model)
