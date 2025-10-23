from __future__ import annotations

from typing import List, Sequence

from .schema import CasePayload


class HistoryManager:
    """Maintain undo/redo stacks for case mutations."""

    def __init__(self, max_size: int = 50) -> None:
        self.max_size = max_size
        self._undo: List[List[CasePayload]] = []
        self._redo: List[List[CasePayload]] = []

    def snapshot(self, cases: Sequence[CasePayload]) -> None:
        snapshot = [case.model_copy(deep=True) for case in cases]
        self._undo.append(snapshot)
        if len(self._undo) > self.max_size:
            self._undo.pop(0)
        self._redo.clear()

    def undo(self, current: Sequence[CasePayload]) -> List[CasePayload] | None:
        if not self._undo:
            return None
        self._redo.append([case.model_copy(deep=True) for case in current])
        return self._undo.pop()

    def redo(self, current: Sequence[CasePayload]) -> List[CasePayload] | None:
        if not self._redo:
            return None
        self._undo.append([case.model_copy(deep=True) for case in current])
        return self._redo.pop()

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()
