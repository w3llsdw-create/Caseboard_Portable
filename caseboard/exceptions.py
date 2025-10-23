from __future__ import annotations

from typing import Any, Dict, Optional


class CaseboardError(Exception):
    """Base class for Caseboard-specific exceptions."""


class DataLockError(CaseboardError):
    """Raised when the data store cannot acquire the required file lock."""


class CorruptDataError(CaseboardError):
    """Raised when the primary data file cannot be parsed safely."""

    def __init__(self, message: str, *, backups: Optional[list[str]] = None) -> None:
        super().__init__(message)
        self.backups = backups or []


class MigrationError(CaseboardError):
    """Raised when a schema migration cannot be completed."""

    def __init__(self, message: str, *, context: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.context = context or {}


class ValidationError(CaseboardError):
    """Raised when user-provided data fails validation."""

    def __init__(self, message: str, *, field: Optional[str] = None) -> None:
        super().__init__(message)
        self.field = field
