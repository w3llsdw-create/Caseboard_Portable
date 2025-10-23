from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Tuple
import importlib
import threading

from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static

from .models import Case
from .storage import load_cases
from .widgets import case_type_color, deadline_color
from .constants import normalize_case_type

try:
    yf = importlib.import_module("yfinance")
except ModuleNotFoundError:  # pragma: no cover - optional dependency guard
    yf = None


STOCK_TICKERS: List[str] = [
    "^DJI",
    "^GSPC",
    "^IXIC",
    "^RUT",
    "^VIX",
    "WMT",
    "MUR",
    "MUSA",
    "DDS",
    "JBHT",
    "TSN",
    "ARCB",
    "OZK",
    "HOMB",
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "META",
    "NVDA",
    "TSLA",
    "NFLX",
    "JPM",
    "BAC",
    "GS",
    "CVX",
    "XOM",
    "UNH",
    "JNJ",
    "PFE",
    "PG",
    "KO",
    "PEP",
    "HD",
    "LOW",
    "COST",
    "DIS",
    "NKE",
    "MCD",
    "CAT",
    "BA",
]

STOCK_REFRESH_SECONDS = 90
STOCK_SCROLL_SECONDS = 2.0
STOCK_WINDOW = 7
STOCK_SEPARATOR = "   |   "


class CaseboardDisplayApp(App):
    """Large format, read-only display board for streaming to a TV."""

    CSS = """
Screen {
    background: #03060f;
    color: #e6f2ff;
}

#display-root {
    padding: 1 3;
}

#display-column {
    height: 100%;
}

#display-header {
    height: 3;
    background: #003051;
    border: solid #0c4a7f;
    color: #8fd4ff;
    text-style: bold;
    content-align: center middle;
    margin: 0 0 1 0;
}

#display-clock {
    height: 1;
    text-align: center;
    color: #9dd1ff;
    margin: 0 0 1 0;
}

#display-overview {
    height: auto;
    margin: 0 0 1 0;
}

.info-panel {
    background: #0a1f38;
    border: solid #134a7c;
    padding: 1 2;
    width: 1fr;
    min-height: 8;
    content-align: left top;
    margin-right: 1;
}

#case-table {
    margin: 1 0 0 0;
    background: #071529;
    border: solid #123456;
    padding: 1 1;
}

#stock-ticker {
    height: 3;
    background: #041129;
    border: solid #23629b;
    padding: 0 2;
    color: #def2ff;
    content-align: left middle;
    margin: 1 0 0 0;
    text-style: bold;
}
"""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.cases: List[Case] = []
        self.clock: Static | None = None
        self.summary_panel: Static | None = None
        self.deadline_panel: Static | None = None
        self.case_table: Static | None = None
        self.stock_ticker: Static | None = None
        self._stock_quotes: Dict[str, Tuple[float, float]] = {}
        self._stock_segments: List[Text] = []
        self._stock_offset: int = 0
        self._stock_fetching: bool = False
        self._focus_animation_active: bool = False
        self._focus_animation_step: int = 0
        self._focus_animation_total: int = 0
        self._focus_animation_source: Dict[str, str] = {}
        self._focus_animation_override: Dict[str, str] | None = None
        self._focus_animation_case_id: str | None = None
        self._focus_animation_pointer: int = -1

    def compose(self) -> ComposeResult:
        self.clock = Static(id="display-clock")
        self.summary_panel = Static(id="display-summary", classes="info-panel")
        self.deadline_panel = Static(id="display-deadlines", classes="info-panel")
        self.case_table = Static(id="case-table")
        self.stock_ticker = Static(id="stock-ticker")

        yield Container(
            Vertical(
                Static("DAVID W. WELLS • CASEBOARD STATUS", id="display-header"),
                self.clock,
                Horizontal(
                    self.summary_panel,
                    self.deadline_panel,
                    id="display-overview",
                ),
                self.case_table,
                self.stock_ticker,
                id="display-column",
            ),
            id="display-root",
        )

    def on_mount(self) -> None:
        self.refresh_display()
        self.update_clock()
        self.set_interval(60.0, self.refresh_display)
        self.set_interval(1.0, self.update_clock)
        self._init_stock_ticker()
        self.set_interval(30.0, self._trigger_focus_animation)
        self.set_interval(0.09, self._advance_focus_animation)

    def action_refresh(self) -> None:
        self.refresh_display()

    def refresh_display(self) -> None:
        self.cases = load_cases()
        self.cases.sort(key=self._case_sort_key)
        self._render_summary()
        self._render_deadlines()
        self._render_case_table()

    def update_clock(self) -> None:
        if not self.clock:
            return
        now = datetime.now()
        self.clock.update(now.strftime("%A • %B %d, %Y • %I:%M:%S %p"))

    def _case_sort_key(self, case: Case):
        attention_priority = 0 if case.attention == "needs_attention" else 1
        status_priority = 0 if case.status in {"open", "filed", "pre-filing"} else 1
        next_deadline = case.next_deadline(date.today())
        if next_deadline:
            deadline_priority = (next_deadline.due_date - date.today()).days
        else:
            deadline_priority = 9999
        return (attention_priority, deadline_priority, status_priority, case.case_name.lower())

    def _render_summary(self) -> None:
        if not self.summary_panel:
            return
        total_cases = len(self.cases)
        attention_cases = len([c for c in self.cases if c.attention == "needs_attention"])
        open_cases = len([c for c in self.cases if c.status in {"open", "filed", "pre-filing"}])

        by_type: dict[str, int] = {}
        for case in self.cases:
            normalized_type = normalize_case_type(case.case_type) if case.case_type else "Other"
            by_type[normalized_type] = by_type.get(normalized_type, 0) + 1

        table = Table.grid(expand=True, pad_edge=False)
        table.add_row(Text("TOTAL CASES", style="bold #b5e0ff"), Text(str(total_cases), style="bold white"))
        table.add_row(Text("ACTIVE", style="#5cffc9"), Text(str(open_cases), style="white"))
        table.add_row(Text("NEEDS ATTENTION", style="#ff9b9b"), Text(str(attention_cases), style="white"))

        # Top three practice areas
        top_types = sorted(by_type.items(), key=lambda item: item[1], reverse=True)[:3]
        if top_types:
            table.add_row(Text("TOP PRACTICE AREAS", style="bold #9bd3ff"), Text("", style="white"))
            for practice, count in top_types:
                table.add_row(Text(f"  {practice}", style="#d0e2ff"), Text(str(count), style="white"))

        self.summary_panel.update(Panel(table, title="FIRM SNAPSHOT", border_style="#23629b", title_align="left"))

    def _render_deadlines(self) -> None:
        if not self.deadline_panel:
            return
        today = date.today()
        upcoming: list[tuple[Case, int, str]] = []
        for case in self.cases:
            next_deadline = case.next_deadline(today)
            if next_deadline:
                days = (next_deadline.due_date - today).days
                upcoming.append((case, days, f"{next_deadline.due_date.strftime('%m/%d/%y')} • {next_deadline.description}"))
        upcoming.sort(key=lambda item: item[1])

        table = Table.grid(expand=True, pad_edge=False)
        table.add_row(Text("NEXT DEADLINES", style="bold #ffd88a"))
        if not upcoming:
            table.add_row(Text("No upcoming deadlines", style="dim"))
        else:
            for case, days, description in upcoming[:6]:
                color = deadline_color(days)
                urgency = "TODAY" if days == 0 else ("OVERDUE" if days < 0 else f"{days} DAYS")
                line = Text.assemble(
                    Text(f"{escape(case.case_name)}", style="white bold"),
                    Text("  •  ", style="dim"),
                    Text(description, style=color),
                    Text(f"  ({urgency})", style=color),
                )
                table.add_row(line)
        self.deadline_panel.update(Panel(table, title="DEADLINE RADAR", border_style="#a8742c", title_align="left"))

    def _render_case_table(self) -> None:
        if not self.case_table:
            return
        if not self.cases:
            self.case_table.update(Panel("No cases on file", border_style="#0d3a66"))
            return

        table = Table(
            box=box.SIMPLE_HEAD,
            expand=True,
            pad_edge=False,
            show_edge=False,
            show_header=True,
            style="#e7f1ff",
            header_style="bold #9bd3ff",
            row_styles=["on #081735", "on #0b2144"],
            border_style="#184b78",
        )
        table.add_column("CASE #", style="bold #c6e5ff", no_wrap=True)
        table.add_column("CASE NAME", style="#f0f8ff", ratio=2, overflow="ellipsis")
        table.add_column("TYPE", style="#8fd4ff", width=16, no_wrap=True)
        table.add_column("STAGE", style="#a8bee2", width=12, overflow="ellipsis")
        table.add_column("ATTN", style="#ff8787", width=10, no_wrap=True)
        table.add_column("STATUS", style="#a4ffd6", width=10, no_wrap=True)
        table.add_column("PARALEGAL", style="#b8ccef", width=16, overflow="ellipsis")
        table.add_column("FOCUS", style="#f5fbff", ratio=2, overflow="ellipsis")
        table.add_column("NEXT DUE", style="#ffd88a", width=28, no_wrap=True, overflow="ellipsis")

        today = date.today()
        for idx, case in enumerate(self.cases):
            raw_type = case.case_type if case.case_type else "Other"
            normalized_type = normalize_case_type(raw_type)
            type_color = case_type_color(raw_type)
            type_name = escape(normalized_type)
            type_label = f"[{type_color}]{type_name}[/]"

            stage_label = escape(case.stage or "-")

            if case.attention == "needs_attention":
                attention_label = "[blink bold #ff6666]⚠ ALERT[/]"
            else:
                attention_label = "[dim]WAIT[/]"

            status_titles = {
                "open": "[green]ACTIVE[/]",
                "filed": "[cyan]FILED[/]",
                "pre-filing": "[yellow]PRE[/]",
                "closed": "[blue]CLOSED[/]",
            }
            status_label = status_titles.get(case.status, f"[white]{escape(case.status.upper())}[/]")

            focus = self._focus_text_for_case(case)
            if focus == "-":
                default_focus_display = "[dim]-[/]"
            else:
                default_focus_display = f"[white]{escape(focus)}[/]"

            if self._focus_animation_override and case.id in self._focus_animation_override:
                anim_text = self._focus_animation_override[case.id]
                if anim_text:
                    focus_display = f"[white]{escape(anim_text)}[/]"
                else:
                    focus_display = "[dim]  [/]"
            else:
                focus_display = default_focus_display

            row_style: str | None = None
            if self._focus_animation_case_id == case.id:
                if self._focus_animation_step <= 2:
                    row_style = "bold on #1f4d7a"
                else:
                    row_style = "on #152b4a"

            next_deadline = case.next_deadline(today)
            if next_deadline:
                days = (next_deadline.due_date - today).days
                color = deadline_color(days)
                desc = next_deadline.description or "-"
                if len(desc) > 30:
                    desc = desc[:29] + "…"
                due_text = (
                    f"[{color}]{next_deadline.due_date.strftime('%m/%d/%y')} ({days:+d})[/]"
                    f" [#a0b8d6]{escape(desc)}[/]"
                )
            else:
                due_text = "[dim]—[/]"

            table.add_row(
                escape(case.case_number or "-"),
                escape(case.case_name or "-"),
                type_label,
                stage_label,
                attention_label,
                status_label,
                escape(case.paralegal or "-"),
                focus_display,
                due_text,
                style=row_style,
            )

        footer = Text.from_markup(
            "[dim]Updated[/] [white]" + datetime.now().strftime("%I:%M:%S %p") + "[/]"
        )
        self.case_table.update(
            Panel(
                table,
                title="LIVE CASE TICKER",
                title_align="left",
                subtitle=footer,
                border_style="#2c6ca3",
            )
        )

    def _trigger_focus_animation(self) -> None:
        if self._focus_animation_active or not self.cases:
            return

        focus_cases = [case for case in self.cases if self._focus_text_for_case(case) not in {"-", ""}]
        if not focus_cases:
            return

        self._focus_animation_pointer = (self._focus_animation_pointer + 1) % len(focus_cases)
        target_case = focus_cases[self._focus_animation_pointer]
        focus_text = self._focus_text_for_case(target_case)

        self._focus_animation_active = True
        self._focus_animation_step = 0
        self._focus_animation_total = len(focus_text)
        self._focus_animation_source = {target_case.id: focus_text}
        self._focus_animation_case_id = target_case.id
        self._apply_focus_animation_step()

    def _advance_focus_animation(self) -> None:
        if not self._focus_animation_active:
            return

        self._focus_animation_step += 1
        if self._focus_animation_step > self._focus_animation_total + 6:
            self._focus_animation_active = False
            self._focus_animation_override = None
            self._focus_animation_source = {}
            self._focus_animation_case_id = None
            self._focus_animation_step = 0
            self._focus_animation_total = 0
            self._render_case_table()
            return

        self._apply_focus_animation_step()

    def _apply_focus_animation_step(self) -> None:
        if not self._focus_animation_active:
            return

        typing_step = max(0, self._focus_animation_step - 3)
        overrides: Dict[str, str] = {}
        if self._focus_animation_source:
            case_id, full_text = next(iter(self._focus_animation_source.items()))
            if typing_step <= 0:
                overrides[case_id] = ""
            elif typing_step >= len(full_text):
                overrides[case_id] = full_text
            else:
                overrides[case_id] = full_text[:typing_step]

        self._focus_animation_override = overrides
        self._render_case_table()

    def _focus_text_for_case(self, case: Case) -> str:
        focus = case.current_task.strip() if case.current_task and case.current_task.strip() else "-"
        if len(focus) > 60:
            focus = focus[:57] + "…"
        return focus

    def _init_stock_ticker(self) -> None:
        if not self.stock_ticker:
            return
        if yf is None:
            self.stock_ticker.update(
                Text(
                    "Install the 'yfinance' package to enable live market data.",
                    style="dim",
                )
            )
            return

        self.stock_ticker.update(Text("Fetching market data…", style="dim"))
        self.set_interval(STOCK_REFRESH_SECONDS, self._refresh_stock_quotes)
        self.set_interval(STOCK_SCROLL_SECONDS, self._advance_stock_ticker)
        self._refresh_stock_quotes()

    def _refresh_stock_quotes(self) -> None:
        if yf is None or self._stock_fetching:
            return

        self._stock_fetching = True

        def worker() -> None:
            quotes = self._fetch_stock_quotes()
            self.call_from_thread(self._apply_stock_quotes, quotes)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _apply_stock_quotes(self, quotes: Dict[str, Tuple[float, float]]) -> None:
        self._stock_fetching = False
        self._stock_quotes = quotes
        self._stock_segments = self._build_stock_segments(quotes)
        self._stock_offset = 0
        self._update_stock_ticker()

    def _advance_stock_ticker(self) -> None:
        if yf is None or not self._stock_segments:
            return
        self._stock_offset = (self._stock_offset + 1) % len(self._stock_segments)
        self._update_stock_ticker()

    def _update_stock_ticker(self) -> None:
        if not self.stock_ticker:
            return
        if yf is None:
            return

        if not self._stock_segments:
            message = "Fetching market data…" if self._stock_fetching else "Market data unavailable."
            self.stock_ticker.update(Text(message, style="dim"))
            return

        window = min(STOCK_WINDOW, len(self._stock_segments))
        pieces: List[Text] = []
        for i in range(window):
            idx = (self._stock_offset + i) % len(self._stock_segments)
            pieces.append(self._stock_segments[idx])
            if i < window - 1:
                pieces.append(Text(STOCK_SEPARATOR, style="#3a5a87"))

        line = Text().join(pieces)
        header = Text("MARKET • ", style="bold #33aaff")
        timestamp = Text(datetime.now().strftime("  %I:%M:%S %p"), style="dim #88aadd")
        self.stock_ticker.update(header + line + timestamp)

    def _build_stock_segments(self, quotes: Dict[str, Tuple[float, float]]) -> List[Text]:
        segments: List[Text] = []
        for symbol in STOCK_TICKERS:
            price, change = quotes.get(symbol, (None, None))
            segments.append(self._format_stock_segment(symbol, price, change))
        return segments

    def _format_stock_segment(
        self, symbol: str, price: float | None, change_pct: float | None
    ) -> Text:
        segment = Text()
        segment.append(f"{symbol:<6}", style="bold white")
        if price is None or change_pct is None:
            segment.append("  N/A", style="dim")
            segment.append("   --", style="dim")
        else:
            arrow = "▲" if change_pct >= 0 else "▼"
            color = "#3bee9d" if change_pct >= 0 else "#ff6464"
            segment.append(f" {price:>8.2f} ", style="white")
            segment.append(f"{arrow}{change_pct:+5.2f}%", style=color)
        return segment

    def _fetch_stock_quotes(self) -> Dict[str, Tuple[float, float]]:
        quotes: Dict[str, Tuple[float, float]] = {}
        if yf is None:
            return quotes

        try:
            tickers = yf.Tickers(" ".join(STOCK_TICKERS))
        except Exception:
            return quotes

        for symbol in STOCK_TICKERS:
            ticker = tickers.tickers.get(symbol)
            if ticker is None:
                continue

            price: float | None = None
            change_pct: float | None = None

            try:
                fast = ticker.fast_info
                price = getattr(fast, "last_price", None)
                change_pct = getattr(fast, "regular_market_change_percent", None)
                if (change_pct is None or change_pct == 0) and price is not None:
                    prev_close = getattr(fast, "previous_close", None)
                    if prev_close:
                        change_pct = ((price - prev_close) / prev_close) * 100
            except Exception:
                pass

            if (price is None or change_pct is None) and hasattr(ticker, "info"):
                try:
                    info = ticker.info
                    price = info.get("regularMarketPrice", price)
                    change_pct = info.get("regularMarketChangePercent", change_pct)
                except Exception:
                    pass

            if isinstance(price, (int, float)) and isinstance(change_pct, (int, float)):
                quotes[symbol] = (float(price), float(change_pct))

        return quotes


def main() -> None:
    CaseboardDisplayApp().run()


if __name__ == "__main__":
    main()
