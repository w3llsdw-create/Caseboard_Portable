from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import ValidationError as PydanticValidationError
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.events import Key
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Input, Select, Static

from .constants import CASE_TYPE_OPTIONS, ensure_case_type_options
from .csv_tools import dedupe_cases, export_cases, import_cases
from .data_store import CaseDataStore
from .exceptions import CorruptDataError, DataLockError, MigrationError
from .history import HistoryManager
from .schema import CasePayload

ATTENTION_CHOICES = [
    ("Waiting", "waiting"),
    ("Needs Attention", "needs_attention"),
]

STATUS_CHOICES = [
    ("Pre-Filing", "pre-filing"),
    ("Filed", "filed"),
    ("Active", "open"),
    ("Closed", "closed"),
]


class TextPrompt(ModalScreen[Optional[str]]):
    """Simple modal prompt returning user input."""

    def __init__(self, title: str, *, initial: str = "", placeholder: str = "") -> None:
        super().__init__()
        self._title = title
        self._initial = initial
        self._placeholder = placeholder

    def compose(self) -> ComposeResult:
        yield Container(
            Static(self._title, id="prompt-title"),
            Input(value=self._initial, placeholder=self._placeholder, id="prompt-input"),
            Horizontal(
                Button("Cancel", id="prompt-cancel"),
                Button("OK", id="prompt-ok", variant="primary"),
                id="prompt-actions",
            ),
            id="prompt-container",
        )

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "prompt-ok":
            self.dismiss(self.query_one(Input).value)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)


class ConfirmDialog(ModalScreen[bool]):
    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        yield Container(
            Static(self._message, id="confirm-message"),
            Horizontal(
                Button("Cancel", id="confirm-cancel"),
                Button("Delete", id="confirm-ok", variant="error"),
                id="confirm-actions",
            ),
            id="confirm-container",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-ok")


class AddCaseDialog(ModalScreen[Optional[Dict[str, str]]]):
    def compose(self) -> ComposeResult:
        yield Container(
            Static("Add Case", id="add-title"),
            Input(placeholder="Case Number", id="add-case-number"),
            Input(placeholder="Case Name", id="add-case-name"),
            Horizontal(
                Button("Cancel", id="add-cancel"),
                Button("Create", id="add-create", variant="primary"),
                id="add-actions",
            ),
            id="add-container",
        )

    def on_mount(self) -> None:
        self.query_one("#add-case-number", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-create":
            number = self.query_one("#add-case-number", Input).value.strip()
            name = self.query_one("#add-case-name", Input).value.strip()
            if not number:
                self.bell()
                return
            self.dismiss({"case_number": number, "case_name": name})
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "add-case-number":
            self.query_one("#add-case-name", Input).focus()
        else:
            self.on_button_pressed(Button.Pressed(self.query_one("#add-create", Button)))


class HelpDialog(ModalScreen[None]):
    def compose(self) -> ComposeResult:
        lines = [
            "[bold]Keyboard Shortcuts[/]",
            "a Add  •  e Edit focus  •  f Quick Focus",
            "n Needs Attention  •  d Delete  •  / Filter",
            "Ctrl+S Save  •  Ctrl+Z/Y Undo/Redo",
            "Ctrl+Up/Down Reorder  •  Ctrl+I Import  •  Ctrl+E Export",
            "Ctrl+Shift+D Dedupe  •  ? Close help",
        ]
        yield Container(
            Static("\n".join(lines), id="help-text"),
            Button("Close", id="help-close", variant="primary"),
            id="help-container",
        )

    def on_button_pressed(self, _: Button.Pressed) -> None:
        self.dismiss(None)

    def on_key(self, event: Key) -> None:
        if event.key in {"escape", "?"}:
            self.dismiss(None)


class CaseboardApp(App):
    CSS = """
    Screen { background: #050b18; color: #d8e5ff; }
    #layout { height: 1fr; }
    #table-pane { width: 2fr; border-right: solid #0f1d33; padding: 1 0 1 1; }
    #editor-pane { width: 1fr; padding: 1; }
    #status-line { height: 3; padding: 0 1; background: #071226; color: #aabfff; }
    DataTable { height: 1fr; }
    Input, Select { background: #0b1628; color: #d8e5ff; border: round #13284f; }
    Input:focus, Select:focus { border: solid #47a0ff; }
    #editor-fields { height: 1fr; overflow-y: auto; }
    #validation { color: #ff8080; min-height: 1; }
    #prompt-container, #confirm-container, #add-container, #help-container {
        width: 60;
        border: round #1b335c;
        background: #061022;
        padding: 2;
        align: center middle;
    }
    #prompt-actions, #confirm-actions, #add-actions { padding-top: 1; align: center middle; }
    #help-text { padding-bottom: 1; }
    """

    BINDINGS = [
        Binding("a", "add_case", "Add", show=True),
        Binding("e", "edit_field", "Edit", show=False),
        Binding("f", "quick_focus", "Focus", show=True),
        Binding("h", "view_focus_history", "History", show=True),
        Binding("n", "toggle_attention", "Needs Attention", show=True),
        Binding("d", "delete_case", "Delete", show=True),
        Binding("/", "filter_cases", "Filter", show=True),
        Binding("ctrl+s", "save_now", "Save", show=True),
        Binding("ctrl+z", "undo", "Undo", show=True),
        Binding("ctrl+y", "redo", "Redo", show=True),
        Binding("ctrl+up", "move_up", "Move Up", show=False),
        Binding("ctrl+down", "move_down", "Move Down", show=False),
        Binding("ctrl+i", "import_csv", "Import CSV", show=True),
        Binding("ctrl+e", "export_csv", "Export CSV", show=True),
        Binding("ctrl+shift+d", "dedupe", "Dedupe", show=True),
        Binding("?", "help", "Help", show=True),
    ]

    auto_save_label = reactive("Not saved", layout=True)

    def __init__(self) -> None:
        super().__init__()
        self.store = CaseDataStore()
        self.history = HistoryManager()
        self.cases: List[CasePayload] = []
        self.filtered_indices: List[int] = []
        self.selected_row = 0
        self.table: Optional[DataTable] = None
        self.status_line: Optional[Static] = None
        self.validation_label: Optional[Static] = None
        self.inputs: Dict[str, Input | Select] = {}
        self.actor = os.environ.get("USERNAME") or os.environ.get("USER") or "user"
        self.filter_text = ""
        self.dirty = False

    # ------------------------------------------------------------------
    # Layout & lifecycle
    # ------------------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, time_format="%I:%M:%S %p")
        with Horizontal(id="layout"):
            with Vertical(id="table-pane"):
                yield Static("Active Caseload", id="table-title")
                self.table = DataTable(id="case-table", zebra_stripes=True)
                yield self.table
            with Vertical(id="editor-pane"):
                yield Static("Case Editor", id="editor-title")
                with Vertical(id="editor-fields"):
                    self.inputs["case_number"] = Input(placeholder="Case Number", id="input-case-number")
                    yield self.inputs["case_number"]
                    self.inputs["case_name"] = Input(placeholder="Case Name", id="input-case-name")
                    yield self.inputs["case_name"]
                    self.inputs["case_type"] = Select(options=CASE_TYPE_OPTIONS, id="select-case-type")
                    yield self.inputs["case_type"]
                    self.inputs["stage"] = Input(placeholder="Stage", id="input-stage")
                    yield self.inputs["stage"]
                    self.inputs["attention"] = Select(options=ATTENTION_CHOICES, id="select-attention")
                    yield self.inputs["attention"]
                    self.inputs["status"] = Select(options=STATUS_CHOICES, id="select-status")
                    yield self.inputs["status"]
                    self.inputs["paralegal"] = Input(placeholder="Paralegal", id="input-paralegal")
                    yield self.inputs["paralegal"]
                    self.inputs["current_task"] = Input(placeholder="Next action", id="input-focus")
                    yield self.inputs["current_task"]
                    self.inputs["next_due"] = Input(placeholder="Next due YYYY-MM-DD", id="input-next-due")
                    yield self.inputs["next_due"]
                self.validation_label = Static("", id="validation")
                yield self.validation_label
        self.status_line = Static("Loading…", id="status-line")
        yield self.status_line
        yield Footer()

    def on_mount(self) -> None:
        if not self.table:
            return
        self._configure_table()
        self._load_cases()
        self.set_interval(30.0, self._autosave_tick)

    def _configure_table(self) -> None:
        assert self.table is not None
        table = self.table
        table.cursor_type = "row"
        table.show_header = True
        table.show_cursor = True
        table.zebra_stripes = True
        table.add_column("Case #", key="case_number", width=14)
        table.add_column("Name", key="case_name", width=24)
        table.add_column("Type", key="case_type", width=16)
        table.add_column("Stage", key="stage", width=16)
        table.add_column("Attention", key="attention", width=12)
        table.add_column("Status", key="status", width=12)
        table.add_column("Paralegal", key="paralegal", width=16)
        table.add_column("Focus", key="current_task", width=32)
        table.add_column("Next Due", key="next_due", width=14)

    # ------------------------------------------------------------------
    # Data loading & persistence
    # ------------------------------------------------------------------
    def _load_cases(self) -> None:
        try:
            model = self.store.load()
        except (CorruptDataError, MigrationError, DataLockError) as exc:
            self._update_status(f"Load failed: {exc}")
            self.bell()
            return

        self.cases = [case.model_copy(deep=True) for case in model.cases]
        self._rebuild_filter()
        self.history.clear()
        self.history.snapshot(self.cases)
        self.auto_save_label = f"Saved {model.saved_at:%H:%M:%S}" if model.cases else "Loaded"
        self._refresh_table()
        self._select_row(0)
        self._update_status("Loaded cases")

    def _persist(self, reason: str, *, force: bool = False) -> None:
        if not (self.dirty or force):
            return
        try:
            result = self.store.save(self.cases, actor=self.actor, action=reason)
        except DataLockError as exc:
            self._update_status(f"Save failed: {exc}")
            self.bell()
            return
        self.auto_save_label = f"Saved {result.saved_at:%H:%M:%S}"
        self.dirty = False

    def _autosave_tick(self) -> None:
        self._persist("autosave")

    # ------------------------------------------------------------------
    # Table helpers
    # ------------------------------------------------------------------
    def _refresh_table(self) -> None:
        assert self.table is not None
        table = self.table
        table.clear()
        for display_index, case_index in enumerate(self.filtered_indices):
            case = self.cases[case_index]
            attention_label = "Needs" if case.attention == "needs_attention" else "Waiting"
            next_due = case.next_due or "—"
            focus_text = (case.current_task or "").strip()
            if len(focus_text) > 60:
                focus_text = focus_text[:57] + "…"
            row_key = f"{case.id}-{case_index}"
            table.add_row(
                case.case_number,
                case.case_name,
                case.case_type,
                case.stage,
                attention_label,
                case.status,
                case.paralegal,
                focus_text,
                next_due,
                key=row_key,
            )

        if self.filtered_indices:
            self.selected_row = max(0, min(self.selected_row, len(self.filtered_indices) - 1))
            table.show_cursor = True
            table.move_cursor(row=self.selected_row, column=0, animate=False, scroll=True)
        else:
            table.show_cursor = False
        self.refresh(layout=True)

    def _select_row(self, position: int, *, update_cursor: bool = True) -> None:
        if not self.filtered_indices:
            self.selected_row = 0
            self._populate_editor(None)
            return
        self.selected_row = max(0, min(position, len(self.filtered_indices) - 1))
        case = self.cases[self.filtered_indices[self.selected_row]]
        if update_cursor and self.table:
            self.table.move_cursor(row=self.selected_row, column=0, animate=False, scroll=True)
        self._populate_editor(case)

    def _focus_case(self, case_id: str) -> None:
        for pos, index in enumerate(self.filtered_indices):
            if self.cases[index].id == case_id:
                self.selected_row = pos
                self._select_row(pos)
                return
        self._select_row(0)

    def _populate_editor(self, case: Optional[CasePayload]) -> None:
        if case is None:
            for widget in self.inputs.values():
                if isinstance(widget, Input):
                    widget.value = ""
                elif isinstance(widget, Select):
                    widget.value = None
            if self.validation_label:
                self.validation_label.update("")
            return

        if isinstance(self.inputs["case_number"], Input):
            self.inputs["case_number"].value = case.case_number  # type: ignore[assignment]
        if isinstance(self.inputs["case_name"], Input):
            self.inputs["case_name"].value = case.case_name  # type: ignore[assignment]
        if isinstance(self.inputs["case_type"], Select):
            # Only update options if they might have changed
            current_options = self.inputs["case_type"]._options  # type: ignore[attr-defined]
            if not current_options or case.case_type not in [opt[1] for opt in current_options]:
                options = ensure_case_type_options([c.case_type for c in self.cases])
                self.inputs["case_type"].set_options(options)
            self.inputs["case_type"].value = case.case_type  # type: ignore[assignment]
        if isinstance(self.inputs["stage"], Input):
            self.inputs["stage"].value = case.stage  # type: ignore[assignment]
        if isinstance(self.inputs["attention"], Select):
            self.inputs["attention"].value = case.attention  # type: ignore[assignment]
        if isinstance(self.inputs["status"], Select):
            self.inputs["status"].value = case.status  # type: ignore[assignment]
        if isinstance(self.inputs["paralegal"], Input):
            self.inputs["paralegal"].value = case.paralegal  # type: ignore[assignment]
        if isinstance(self.inputs["current_task"], Input):
            self.inputs["current_task"].value = case.current_task  # type: ignore[assignment]
        if isinstance(self.inputs["next_due"], Input):
            self.inputs["next_due"].value = case.next_due or ""  # type: ignore[assignment]
        if self.validation_label:
            self.validation_label.update("")

    def _case_tokens(self, case: CasePayload) -> str:
        parts = [
            case.case_number,
            case.case_name,
            case.case_type,
            case.stage,
            case.paralegal,
            case.current_task,
            case.status,
        ]
        return " ".join(filter(None, parts)).lower()

    def _rebuild_filter(self) -> None:
        if not self.filter_text:
            self.filtered_indices = list(range(len(self.cases)))
            return
        tokens = self.filter_text.split()
        matches: List[int] = []
        for idx, case in enumerate(self.cases):
            haystack = self._case_tokens(case)
            if all(token in haystack for token in tokens):
                matches.append(idx)
        self.filtered_indices = matches

    # ------------------------------------------------------------------
    # Editing handlers
    # ------------------------------------------------------------------
    def on_input_blurred(self, event: Input.Blurred) -> None:
        try:
            self._apply_change(event.input.id, event.value)
        except Exception as exc:
            # Prevent crashes from unexpected errors during field updates
            if self.validation_label:
                self.validation_label.update(f"Error: {exc}")
            self.bell()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        try:
            self._apply_change(event.input.id, event.value)
        except Exception as exc:
            # Prevent crashes from unexpected errors during field updates
            if self.validation_label:
                self.validation_label.update(f"Error: {exc}")
            self.bell()

    def on_select_changed(self, event: Select.Changed) -> None:
        try:
            self._apply_change(event.select.id, event.value)
        except Exception as exc:
            # Prevent crashes from unexpected errors during field updates
            if self.validation_label:
                self.validation_label.update(f"Error: {exc}")
            self.bell()

    def _apply_change(self, widget_id: str | None, value: Optional[str]) -> None:
        if not widget_id or not self.filtered_indices:
            return
        field_map = {
            "input-case-number": "case_number",
            "input-case-name": "case_name",
            "select-case-type": "case_type",
            "input-stage": "stage",
            "select-attention": "attention",
            "select-status": "status",
            "input-paralegal": "paralegal",
            "input-focus": "current_task",
            "input-next-due": "next_due",
        }
        field = field_map.get(widget_id)
        if not field:
            return

        case_index = self.filtered_indices[self.selected_row]
        current = self.cases[case_index]
        update_payload = {field: value or ""}
        if field == "next_due" and not value:
            update_payload[field] = None

        try:
            updated = current.model_copy(update=update_payload)
        except PydanticValidationError as exc:
            message = exc.errors()[0]["msg"] if exc.errors() else str(exc)
            if self.validation_label:
                self.validation_label.update(message)
            self.bell()
            return

        target_id = updated.id
        self.history.snapshot(self.cases)
        self.cases[case_index] = updated
        self.dirty = True
        if self.validation_label:
            self.validation_label.update("")
        self._rebuild_filter()
        self._refresh_table()
        self._focus_case(target_id)
        self._persist("field-change", force=True)
        self._update_status(f"Updated {field}")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_add_case(self) -> None:
        def _complete(result: Optional[Dict[str, str]]) -> None:
            if not result:
                return
            payload = CasePayload(
                case_number=result["case_number"],
                case_name=result.get("case_name", ""),
                case_type="Personal Injury",
                stage="Intake",
                attention="waiting",
                status="open",
                paralegal="",
                current_task="",
                next_due=None,
                deadlines=[],
            )
            self.history.snapshot(self.cases)
            self.cases.append(payload)
            self.dirty = True
            self.filter_text = ""
            self._rebuild_filter()
            self.selected_row = len(self.filtered_indices) - 1
            self._refresh_table()
            self._focus_case(payload.id)
            self._persist("add-case", force=True)
            self._update_status(f"Added {payload.case_number}")

        self.push_screen(AddCaseDialog(), _complete)

    def action_edit_field(self) -> None:
        widget = self.inputs.get("current_task")
        if isinstance(widget, Input):
            widget.focus()

    def action_quick_focus(self) -> None:
        if not self.filtered_indices:
            return
        current_value = ""
        widget = self.inputs.get("current_task")
        if isinstance(widget, Input):
            current_value = widget.value

        def _complete(value: Optional[str]) -> None:
            if value is None:
                return
            if isinstance(widget, Input):
                widget.value = value
            self._apply_change("input-focus", value)

        self.push_screen(TextPrompt("Update focus", initial=current_value), _complete)

    def action_view_focus_history(self) -> None:
        """View focus history for the selected case."""
        if not self.filtered_indices:
            return
        case = self.cases[self.filtered_indices[self.selected_row]]
        
        # Import here to avoid circular import
        from .screens import FocusHistoryScreen
        
        self.push_screen(FocusHistoryScreen(case.id, case.case_number, case.case_name))

    def action_toggle_attention(self) -> None:
        if not self.filtered_indices:
            return
        case = self.cases[self.filtered_indices[self.selected_row]]
        new_value = "waiting" if case.attention == "needs_attention" else "needs_attention"
        self._apply_change("select-attention", new_value)

    def action_delete_case(self) -> None:
        if not self.filtered_indices:
            return
        case = self.cases[self.filtered_indices[self.selected_row]]

        def _done(result: bool) -> None:
            if not result:
                return
            self.history.snapshot(self.cases)
            self.cases.pop(self.filtered_indices[self.selected_row])
            self.dirty = True
            self._rebuild_filter()
            self.selected_row = min(self.selected_row, len(self.filtered_indices) - 1)
            self._refresh_table()
            self._select_row(self.selected_row)
            self._persist("delete", force=True)
            self._update_status(f"Deleted {case.case_number}")

        self.push_screen(ConfirmDialog(f"Delete {case.case_number}?"), _done)

    def action_filter_cases(self) -> None:
        def _complete(value: Optional[str]) -> None:
            self.filter_text = (value or "").strip().lower()
            self._rebuild_filter()
            self.selected_row = 0
            self._refresh_table()
            self._select_row(0)
            self._update_status(f"Filter '{self.filter_text}'" if self.filter_text else "Filter cleared")

        self.push_screen(TextPrompt("Filter cases", initial=self.filter_text), _complete)

    def action_save_now(self) -> None:
        self._persist("manual", force=True)
        self._update_status("Saved")

    def action_undo(self) -> None:
        snapshot = self.history.undo(self.cases)
        if snapshot is None:
            self.bell()
            return
        self.cases = [case.model_copy(deep=True) for case in snapshot]
        self.dirty = True
        self._rebuild_filter()
        self._refresh_table()
        self._select_row(self.selected_row)
        self._persist("undo", force=True)
        self._update_status("Undo")

    def action_redo(self) -> None:
        snapshot = self.history.redo(self.cases)
        if snapshot is None:
            self.bell()
            return
        self.cases = [case.model_copy(deep=True) for case in snapshot]
        self.dirty = True
        self._rebuild_filter()
        self._refresh_table()
        self._select_row(self.selected_row)
        self._persist("redo", force=True)
        self._update_status("Redo")

    def action_move_up(self) -> None:
        self._reorder_case(-1)

    def action_move_down(self) -> None:
        self._reorder_case(1)

    def _reorder_case(self, delta: int) -> None:
        if self.filter_text:
            self._update_status("Clear filter to reorder")
            self.bell()
            return
        if not self.filtered_indices:
            return
        source_index = self.filtered_indices[self.selected_row]
        target_index = source_index + delta
        if target_index < 0 or target_index >= len(self.cases):
            return

        self.history.snapshot(self.cases)
        case = self.cases.pop(source_index)
        if target_index > source_index:
            target_index -= 1
        self.cases.insert(target_index, case)
        self.dirty = True
        self._rebuild_filter()
        self._refresh_table()
        self._focus_case(case.id)
        self._persist("reorder", force=True)
        self._update_status("Reordered cases")

    def action_import_csv(self) -> None:
        def _complete(path_str: Optional[str]) -> None:
            if not path_str:
                return
            try:
                imported = import_cases(Path(path_str).expanduser())
            except FileNotFoundError:
                self._update_status("CSV not found")
                self.bell()
                return
            if not imported:
                self._update_status("No cases imported")
                return
            self.history.snapshot(self.cases)
            index_map = {case.case_number: idx for idx, case in enumerate(self.cases)}
            last_case_id = imported[-1].id
            for payload in imported:
                if payload.case_number in index_map:
                    idx = index_map[payload.case_number]
                    payload.id = self.cases[idx].id
                    self.cases[idx] = payload
                else:
                    self.cases.append(payload)
                    index_map[payload.case_number] = len(self.cases) - 1
                    last_case_id = payload.id
            self.dirty = True
            self._rebuild_filter()
            self._refresh_table()
            if self.filtered_indices:
                self._focus_case(last_case_id)
            self._persist("import", force=True)
            self._update_status(f"Imported {len(imported)} cases")

        self.push_screen(TextPrompt("Import CSV path", placeholder="C:/path/to/cases.csv"), _complete)

    def action_export_csv(self) -> None:
        def _complete(path_str: Optional[str]) -> None:
            if not path_str:
                return
            path = Path(path_str).expanduser()
            export_cases(path, self.cases)
            self._update_status(f"Exported to {path}")

        self.push_screen(TextPrompt("Export CSV path", placeholder="C:/path/to/export.csv"), _complete)

    def action_dedupe(self) -> None:
        deduped = dedupe_cases(self.cases)
        if len(deduped) == len(self.cases):
            self._update_status("No duplicates found")
            return
        self.history.snapshot(self.cases)
        self.cases = deduped
        self.dirty = True
        self._rebuild_filter()
        self._refresh_table()
        if self.filtered_indices:
            focus_id = self.cases[self.filtered_indices[0]].id
            self._focus_case(focus_id)
        else:
            self._populate_editor(None)
        self._persist("dedupe", force=True)
        self._update_status("Removed duplicate case numbers")

    def action_help(self) -> None:
        self.push_screen(HelpDialog())

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._select_row(event.cursor_row, update_cursor=False)

    # ------------------------------------------------------------------
    # Status line
    # ------------------------------------------------------------------
    def _update_status(self, message: str) -> None:
        if not self.status_line:
            return
        total = len(self.cases)
        active = sum(1 for case in self.cases if case.status in {"open", "filed", "pre-filing"})
        attention = sum(1 for case in self.cases if case.attention == "needs_attention")
        self.status_line.update(
            f"{message} • Total {total} • Active {active} • Needs {attention} • {self.auto_save_label}"
        )


__all__ = ["CaseboardApp"]