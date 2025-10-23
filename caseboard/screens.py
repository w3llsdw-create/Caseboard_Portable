from __future__ import annotations
from textual.screen import Screen
from textual.widgets import (
    Input,
    Button,
    Label,
    Footer,
    Select,
    Header,
    Static,
)
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual import on
from datetime import date
from typing import Callable, Optional

from .models import Case, parse_date
from .constants import CASE_TYPE_OPTIONS, normalize_case_type


class ConfirmDialog(Screen):
    """A simple confirmation dialog."""
    
    def __init__(self, message: str, on_confirm: Callable[[], None]) -> None:
        super().__init__()
        self.message = message
        self._on_confirm = on_confirm

    def compose(self):
        yield Container(
            Vertical(
                Label(self.message, id="confirm-message"),
                Horizontal(
                    Button.error("Delete", id="confirm-yes"),
                    Button("Cancel", id="confirm-no"),
                    id="confirm-buttons",
                ),
                id="confirm-dialog",
            ),
            id="confirm-container",
        )

    @on(Button.Pressed, "#confirm-yes")
    def confirm_yes(self) -> None:
        self._on_confirm()
        self.app.pop_screen()

    @on(Button.Pressed, "#confirm-no") 
    def confirm_no(self) -> None:
        self.app.pop_screen()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()
        elif event.key == "enter":
            self._on_confirm()
            self.app.pop_screen()


class EditCaseScreen(Screen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Cancel"),
        ("ctrl+s", "save", "Save"),
    ]

    def __init__(self, on_save: Callable[[Case], None], existing_case: Case | None = None) -> None:
        super().__init__()
        self._on_save = on_save
        self.existing_case = existing_case
        self.is_editing = existing_case is not None

    def compose(self):
        title_text = "Edit Case" if self.is_editing else "Add New Case"
        initial_case_type = (
            normalize_case_type(self.existing_case.case_type)
            if self.existing_case and self.existing_case.case_type
            else CASE_TYPE_OPTIONS[0][1]
        )

        yield Header(show_clock=False)
        yield Container(
            Vertical(
                Label(title_text, id="title"),
                Static("Tab through the fields; everything you need is in view.", id="form-hint"),
                VerticalScroll(
                    Horizontal(
                        Vertical(
                            Horizontal(Label("Case Number:"), Input(placeholder="e.g., 60CV-2024-1234", id="case_number"), classes="form-row"),
                            Horizontal(Label("Case Name:"), Input(placeholder="e.g., Doe v. Acme", id="case_name"), classes="form-row"),
                            Horizontal(Label("Case Type:"),
                                Select(
                                    id="case_type",
                                    options=CASE_TYPE_OPTIONS,
                                    value=initial_case_type,
                                ),
                                classes="form-row",
                            ),
                            Horizontal(Label("County:"), Input(placeholder="e.g., Pulaski", id="county"), classes="form-row"),
                            Horizontal(Label("Division:"), Input(placeholder="e.g., Civil", id="division"), classes="form-row"),
                            Horizontal(Label("Judge:"), Input(placeholder="e.g., Hon. Smith", id="judge"), classes="form-row"),
                            Horizontal(Label("Stage:"),
                                Select(
                                    id="stage",
                                    options=[
                                        ("Discovery", "Discovery"),
                                        ("Pretrial", "Pretrial"),
                                        ("Trial Ready", "Trial Ready"),
                                        ("Appeal", "Appeal"),
                                        ("Other", "Other"),
                                    ],
                                    value="Discovery",
                                ),
                                classes="form-row",
                            ),
                            Horizontal(Label("Attention:"),
                                Select(
                                    id="attention",
                                    options=[
                                        ("Waiting", "waiting"),
                                        ("Needs Attention", "needs_attention"),
                                    ],
                                    value="waiting",
                                ),
                                classes="form-row",
                            ),
                            classes="form-column form-column-left",
                        ),
                        Vertical(
                            Horizontal(Label("Paralegal:"), Input(placeholder="e.g., Jane Smith", id="paralegal"), classes="form-row"),
                            Horizontal(Label("Opposing Counsel:"), Input(placeholder="e.g., John Doe, Esq.", id="opposing_counsel"), classes="form-row"),
                            Horizontal(Label("Opposing Firm:"), Input(placeholder="e.g., Smith & Associates", id="opposing_firm"), classes="form-row"),
                            Horizontal(Label("Status:"),
                                Select(
                                    id="status",
                                    options=[
                                        ("Pre-Filing", "pre-filing"),
                                        ("Filed", "filed"),
                                        ("Active", "open"),
                                        ("Closed", "closed"),
                                    ],
                                    value="pre-filing",
                                ),
                                classes="form-row",
                            ),
                            Horizontal(Label("Current Focus:"), Input(placeholder="What is happening next?", id="current_task"), classes="form-row"),
                            Horizontal(Label("Statute of Limitations:"), Input(placeholder="YYYY-MM-DD (optional)", id="sol_date"), classes="form-row"),
                            Horizontal(Label("Next Deadline:"), Input(placeholder="YYYY-MM-DD (optional)", id="next_deadline"), classes="form-row"),
                            classes="form-column",
                        ),
                        id="form-fields",
                    ),
                    id="form-scroll",
                ),
                Horizontal(
                    Button.success("Save (Ctrl+S)", id="save"),
                    Button("Cancel (Esc)", id="cancel"),
                    id="buttons",
                ),
                id="form",
            ),
            id="form-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Focus the first input field and populate form if editing."""
        # Ensure all inputs are enabled and focusable
        for input_widget in self.query(Input):
            input_widget.disabled = False
        
        self.query_one("#case_number", Input).focus()
        
        if self.is_editing and self.existing_case:
            # Populate form fields with existing case data
            self.query_one("#case_number", Input).value = self.existing_case.case_number
            self.query_one("#case_name", Input).value = self.existing_case.case_name
            normalized_type = (
                normalize_case_type(self.existing_case.case_type)
                if self.existing_case.case_type
                else CASE_TYPE_OPTIONS[0][1]
            )
            self.query_one("#case_type", Select).value = normalized_type
            self.query_one("#county", Input).value = self.existing_case.county
            self.query_one("#division", Input).value = self.existing_case.division
            self.query_one("#judge", Input).value = self.existing_case.judge
            self.query_one("#paralegal", Input).value = self.existing_case.paralegal
            self.query_one("#opposing_counsel", Input).value = self.existing_case.opposing_counsel
            self.query_one("#opposing_firm", Input).value = self.existing_case.opposing_firm
            self.query_one("#stage", Select).value = self.existing_case.stage
            self.query_one("#status", Select).value = self.existing_case.status
            self.query_one("#current_task", Input).value = self.existing_case.current_task
            self.query_one("#attention", Select).value = self.existing_case.attention
            if self.existing_case.sol_date:
                self.query_one("#sol_date", Input).value = self.existing_case.sol_date.strftime("%Y-%m-%d")
            next_deadline_obj = self.existing_case.next_deadline()
            if next_deadline_obj and next_deadline_obj.due_date:
                self.query_one("#next_deadline", Input).value = next_deadline_obj.due_date.strftime("%Y-%m-%d")

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#save")
    def save_button(self) -> None:
        self.action_save()

    def action_save(self) -> None:
        case_number = self.query_one("#case_number", Input).value.strip()
        case_name = self.query_one("#case_name", Input).value.strip()
        case_type_value = self.query_one("#case_type", Select).value
        default_case_type = CASE_TYPE_OPTIONS[0][1]
        case_type = str(case_type_value) if case_type_value else default_case_type
        county = self.query_one("#county", Input).value.strip()
        division = self.query_one("#division", Input).value.strip()
        judge = self.query_one("#judge", Input).value.strip()
        paralegal = self.query_one("#paralegal", Input).value.strip()
        opposing_counsel = self.query_one("#opposing_counsel", Input).value.strip()
        opposing_firm = self.query_one("#opposing_firm", Input).value.strip()
        stage_value = self.query_one("#stage", Select).value
        stage = str(stage_value) if stage_value else "Discovery"
        attention_value = self.query_one("#attention", Select).value
        attention = str(attention_value) if attention_value else "waiting"
        status_value = self.query_one("#status", Select).value
        status = str(status_value) if status_value else "pre-filing"
        current_task = self.query_one("#current_task", Input).value.strip()
        sol_text = self.query_one("#sol_date", Input).value.strip() or None
        next_deadline_text = self.query_one("#next_deadline", Input).value.strip() or None

        if not case_number or not case_name:
            self.app.bell()
            return

        if self.is_editing and self.existing_case:
            # Update existing case
            case = Case(
                id=self.existing_case.id,
                case_number=case_number,
                case_name=case_name,
                case_type=case_type,
                county=county,
                division=division,
                judge=judge,
                paralegal=paralegal,
                current_task=current_task,
                attention=attention,
                opposing_counsel=opposing_counsel,
                opposing_firm=opposing_firm,
                stage=stage,
                sol_date=parse_date(sol_text) if sol_text else None,
                deadlines=self.existing_case.deadlines,
            )
            # Set the status after creating the case
            case.status = status
            # Update next deadline if provided
            if next_deadline_text:
                deadline_date = parse_date(next_deadline_text)
                if deadline_date:
                    case.add_deadline(deadline_date, "Next Deadline")
        else:
            # Create new case
            case = Case.new(
                case_number=case_number,
                case_name=case_name,
                case_type=case_type,
                county=county,
                division=division,
                judge=judge,
                paralegal=paralegal,
                opposing_counsel=opposing_counsel,
                opposing_firm=opposing_firm,
                stage=stage,
                sol_date=sol_text,
                current_task=current_task,
                attention=attention,
                status=status,
            )
            # Set next deadline if provided
            if next_deadline_text:
                deadline_date = parse_date(next_deadline_text)
                if deadline_date:
                    case.add_deadline(deadline_date, "Next Deadline")
        
        self._on_save(case)
        self.app.pop_screen()


class DeadlineScreen(Screen):
    """Screen for managing deadlines for a case."""
    
    BINDINGS = [
        ("escape", "app.pop_screen", "Cancel"),
        ("ctrl+s", "add_deadline", "Add Deadline"),
        ("d", "delete_deadline", "Delete Deadline"),
    ]

    def __init__(self, case: Case, on_save: Callable[[Case], None]) -> None:
        super().__init__()
        self.case = case
        self._on_save = on_save

    def compose(self):
        yield Header(show_clock=False)
        yield Container(
            Vertical(
                Label(f"Deadlines for: {self.case.case_name}", id="deadline-title"),
                
                # Add new deadline form
                Vertical(
                    Label("Add New Deadline:", id="add-deadline-label"),
                    Horizontal(
                        Label("Date:"), 
                        Input(placeholder="YYYY-MM-DD", id="new-deadline-date")
                    ),
                    Horizontal(
                        Label("Description:"), 
                        Input(placeholder="Description of deadline", id="new-deadline-desc")
                    ),
                    Horizontal(
                        Button.success("Add (Ctrl+S)", id="add-deadline"),
                        id="add-deadline-buttons"
                    ),
                    id="add-deadline-form",
                ),
                
                # List existing deadlines
                Label("Existing Deadlines:", id="existing-deadlines-label"),
                Static(id="deadlines-list"),
                
                Horizontal(
                    Button("Close", id="close"),
                    id="buttons",
                ),
                id="deadline-form",
            ),
            id="deadline-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Focus the date input and render deadlines."""
        self.query_one("#new-deadline-date", Input).focus()
        self.render_deadlines()

    def render_deadlines(self) -> None:
        """Render the list of existing deadlines."""
        deadlines_widget = self.query_one("#deadlines-list", Static)
        
        if not self.case.deadlines:
            deadlines_widget.update("[dim]No deadlines set[/]")
            return
        
        lines = []
        today = date.today()
        for i, deadline in enumerate(self.case.deadlines):
            if deadline.resolved:
                continue
                
            days = (deadline.due_date - today).days
            if days < 0:
                color = "red"
                status = f"OVERDUE ({abs(days)} days)"
            elif days == 0:
                color = "orange3"
                status = "DUE TODAY"
            elif days <= 3:
                color = "yellow"
                status = f"Due in {days} days"
            elif days <= 7:
                color = "white"
                status = f"Due in {days} days"
            else:
                color = "dim"
                status = f"Due in {days} days"
            
            lines.append(f"[{color}]{i+1:2d}. {deadline.due_date.strftime('%m/%d/%Y')} - {deadline.description}[/]")
            lines.append(f"     [{color}]{status}[/]\n")
        
        if not lines:
            deadlines_widget.update("[dim]All deadlines resolved[/]")
        else:
            deadlines_widget.update("\n".join(lines))

    @on(Button.Pressed, "#add-deadline")
    def add_deadline_button(self) -> None:
        self.action_add_deadline()

    @on(Button.Pressed, "#close")
    def close(self) -> None:
        self.app.pop_screen()

    def action_add_deadline(self) -> None:
        """Add a new deadline to the case."""
        date_text = self.query_one("#new-deadline-date", Input).value.strip()
        desc_text = self.query_one("#new-deadline-desc", Input).value.strip()
        
        if not date_text or not desc_text:
            self.app.bell()
            return
        
        deadline_date = parse_date(date_text)
        if not deadline_date:
            self.app.bell()
            return
        
        # Add deadline to case
        self.case.add_deadline(deadline_date, desc_text)
        
        # Clear form
        self.query_one("#new-deadline-date", Input).value = ""
        self.query_one("#new-deadline-desc", Input).value = ""
        self.query_one("#new-deadline-date", Input).focus()
        
        # Re-render deadlines
        self.render_deadlines()
        
        # Save the case
        self._on_save(self.case)

    def action_delete_deadline(self) -> None:
        """Delete a deadline (would need selection mechanism)."""
        # For now, just show a message that this feature needs implementation
        pass


class StockManagementScreen(Screen):
    """Screen for managing tracked stocks."""
    
    BINDINGS = [
        ("escape", "app.pop_screen", "Cancel"),
        ("ctrl+s", "add_stock", "Add Stock"),
        ("d", "delete_selected", "Delete Stock"),
    ]

    def __init__(self) -> None:
        super().__init__()
        from .stocks import get_stock_manager
        self.stock_manager = get_stock_manager()

    def compose(self):
        yield Header(show_clock=False)
        yield Container(
            Vertical(
                Label("Stock Management", id="stock-title"),
                
                # Add new stock form
                Vertical(
                    Label("Add New Stock:", id="add-stock-label"),
                    Horizontal(
                        Label("Symbol:"), 
                        Input(placeholder="e.g., AAPL", id="new-stock-symbol")
                    ),
                    Horizontal(
                        Button.success("Add (Ctrl+S)", id="add-stock"),
                        id="add-stock-buttons"
                    ),
                    id="add-stock-form",
                ),
                
                # List current stocks
                Label("Currently Tracked Stocks:", id="current-stocks-label"),
                Static(id="stocks-list"),
                
                Horizontal(
                    Button("Close", id="close"),
                    id="buttons",
                ),
                id="stock-form",
            ),
            id="stock-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Focus the symbol input and render stocks."""
        self.query_one("#new-stock-symbol", Input).focus()
        self.render_stocks()

    def render_stocks(self) -> None:
        """Render the list of current stocks."""
        stocks_widget = self.query_one("#stocks-list", Static)
        
        symbols = self.stock_manager.stock_symbols
        if not symbols:
            stocks_widget.update("[dim]No stocks being tracked[/]")
            return
        
        lines = []
        for i, symbol in enumerate(symbols):
            lines.append(f"[white]{i+1:2d}. {symbol}[/]")
        
        lines.append(f"\n[dim]Total: {len(symbols)} stocks[/]")
        lines.append("[dim]Press 'd' to delete selected stock[/]")
        
        stocks_widget.update("\n".join(lines))

    @on(Button.Pressed, "#add-stock")
    def add_stock_button(self) -> None:
        self.action_add_stock()

    @on(Button.Pressed, "#close")
    def close(self) -> None:
        self.app.pop_screen()

    def action_add_stock(self) -> None:
        """Add a new stock to tracking."""
        symbol_input = self.query_one("#new-stock-symbol", Input)
        symbol = symbol_input.value.strip().upper()
        
        if not symbol:
            self.app.bell()
            return
        
        if self.stock_manager.add_stock(symbol):
            symbol_input.value = ""
            symbol_input.focus()
            self.render_stocks()
        else:
            self.app.bell()  # Symbol already exists or invalid

    def action_delete_selected(self) -> None:
        """Delete a stock (would need selection mechanism)."""
        # For now, just show a message that this feature needs implementation
        # In a full implementation, you'd add a selection mechanism
        pass


class StockManagementScreen(Screen):
    """Screen for managing stock ticker symbols."""
    
    BINDINGS = [
        ("escape", "app.pop_screen", "Cancel"),
        ("ctrl+s", "add_stock", "Add Stock"),
        ("d", "delete_stock", "Delete Stock"),
        ("r", "refresh_stocks", "Refresh"),
    ]

    def __init__(self) -> None:
        super().__init__()
        from .stocks import get_stock_manager
        self.stock_manager = get_stock_manager()

    def compose(self):
        yield Header(show_clock=False)
        yield Container(
            Vertical(
                Label("Stock Ticker Management", id="stock-title"),
                
                # Add new stock form
                Vertical(
                    Label("Add New Stock:", id="add-stock-label"),
                    Horizontal(
                        Label("Symbol:"), 
                        Input(placeholder="e.g., AAPL", id="new-stock-symbol")
                    ),
                    Horizontal(
                        Button.success("Add Stock (Ctrl+S)", id="add-stock"),
                        id="add-stock-buttons"
                    ),
                    id="add-stock-form",
                ),
                
                # List existing stocks
                Label("Current Stocks:", id="current-stocks-label"),
                Static(id="stocks-list"),
                
                Horizontal(
                    Button.success("Refresh Data (r)", id="refresh"),
                    Button("Close", id="close"),
                    id="buttons",
                ),
                id="stock-form",
            ),
            id="stock-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Focus the symbol input and render stocks."""
        self.query_one("#new-stock-symbol", Input).focus()
        self.render_stocks()

    def render_stocks(self) -> None:
        """Render the list of current stocks with their data."""
        stocks_widget = self.query_one("#stocks-list", Static)
        
        try:
            stocks_data = self.stock_manager.get_all_stock_data()
            
            if not stocks_data:
                stocks_widget.update("[dim]No stocks configured[/]")
                return
            
            lines = []
            for i, stock in enumerate(stocks_data):
                # Color coding for changes
                if stock.change >= 0:
                    color = "green"
                    arrow = "▲"
                else:
                    color = "red" 
                    arrow = "▼"
                
                lines.append(f"[white]{i+1:2d}. {stock.symbol:6s}[/] [white]${stock.price:8.2f}[/] [{color}]{arrow}{stock.change_str:8s} ({stock.change_percent_str:7s})[/]")
            
            from datetime import datetime
            lines.append(f"\n[dim]Last updated: {datetime.now().strftime('%I:%M:%S %p')}[/]")
            lines.append(f"[dim]Press 'd' + number to remove a stock[/]")
            
            stocks_widget.update("\n".join(lines))
            
        except Exception as e:
            stocks_widget.update(f"[red]Error loading stocks: {e}[/]")

    @on(Button.Pressed, "#add-stock")
    def add_stock_button(self) -> None:
        self.action_add_stock()

    @on(Button.Pressed, "#refresh")
    def refresh_button(self) -> None:
        self.action_refresh_stocks()

    @on(Button.Pressed, "#close")
    def close(self) -> None:
        self.app.pop_screen()

    def action_add_stock(self) -> None:
        """Add a new stock to the ticker."""
        symbol_text = self.query_one("#new-stock-symbol", Input).value.strip().upper()
        
        if not symbol_text:
            self.app.bell()
            return
        
        if self.stock_manager.add_stock(symbol_text):
            # Clear form
            self.query_one("#new-stock-symbol", Input).value = ""
            self.query_one("#new-stock-symbol", Input).focus()
            
            # Re-render stocks
            self.render_stocks()
        else:
            self.app.bell()  # Stock already exists or invalid

    def action_refresh_stocks(self) -> None:
        """Refresh all stock data."""
        self.stock_manager.refresh_all_data()
        self.render_stocks()

    def action_delete_stock(self) -> None:
        """Delete a stock (simplified - remove first stock for now)."""
        # For a more complete implementation, you'd want to select which stock to delete
        # For now, this is a placeholder
        pass

    def on_key(self, event) -> None:
        """Handle key events for stock deletion."""
        if event.key.isdigit():
            # User pressed a number - delete that stock
            try:
                index = int(event.key) - 1
                if 0 <= index < len(self.stock_manager.stock_symbols):
                    symbol = self.stock_manager.stock_symbols[index]
                    self.stock_manager.remove_stock(symbol)
                    self.render_stocks()
            except (ValueError, IndexError):
                pass