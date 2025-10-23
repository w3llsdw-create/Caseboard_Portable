from __future__ import annotations
from rich.text import Text
from datetime import date
from typing import Optional

from .models import Case
from .constants import CASE_TYPE_COLOR_MAP, normalize_case_type


def deadline_color(days_until: int) -> str:
    """Return color for deadline based on days until due."""
    if days_until < 0:
        return "red"
    elif days_until <= 3:
        return "red"
    elif days_until <= 7:
        return "orange3"
    elif days_until <= 30:
        return "orange3"
    else:
        return "white"


def sol_color(sol_date: Optional[date], today: Optional[date] = None) -> str:
    """Return color for statute of limitations date."""
    if sol_date is None:
        return "dim"
    
    today = today or date.today()
    days = (sol_date - today).days
    
    if days < 0:
        return "red"
    elif days <= 30:
        return "red"
    elif days <= 60:
        return "orange3"
    else:
        return "white"


def case_type_color(case_type: str) -> str:
    """Return the configured color for a case type, accounting for legacy labels."""
    canonical = normalize_case_type(case_type)
    return CASE_TYPE_COLOR_MAP.get(canonical, CASE_TYPE_COLOR_MAP.get("Other", "white"))


class CaseRow:
    """Represents a formatted case row for display in the table."""
    
    def __init__(self, case: Case):
        self.case = case
    
    def __rich__(self) -> Text:
        """Return rich formatted text for the case."""
        today = date.today()
        
        # Build the case info line
        parts = []
        
        # Case number and name
        parts.append(f"[bold cyan]{self.case.case_number}[/] ")
        parts.append(f"[white]{self.case.case_name}[/]")
        
        # Location info
        location_parts = []
        if self.case.county:
            location_parts.append(self.case.county)
        if self.case.division:
            location_parts.append(self.case.division)
        if self.case.judge:
            location_parts.append(f"Hon. {self.case.judge}")
        
        if location_parts:
            parts.append(f"\n[dim]  {' • '.join(location_parts)}[/]")
        
        # Stage
        if self.case.stage:
            parts.append(f" • [blue]{self.case.stage}[/]")
        
        # Next deadline
        next_deadline = self.case.next_deadline(today)
        if next_deadline:
            days = (next_deadline.due_date - today).days
            color = deadline_color(days)
            parts.append(f"\n[{color}]  📅 {next_deadline.due_date} - {next_deadline.description}[/]")
        
        # Statute of limitations
        if self.case.sol_date:
            sol_color_name = sol_color(self.case.sol_date, today)
            days = (self.case.sol_date - today).days
            parts.append(f"\n[{sol_color_name}]  ⚖️  SOL: {self.case.sol_date} ({days} days)[/]")
        
        return Text.from_markup("".join(parts))