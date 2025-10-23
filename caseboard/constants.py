"""Shared configuration values for Caseboard."""

from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

# Canonical list of case types available in the UI (label, value)
CASE_TYPE_OPTIONS: List[Tuple[str, str]] = [
    ("Personal Injury", "Personal Injury"),
    ("MVA", "MVA"),
    ("Wrongful Death", "Wrongful Death"),
    ("Catastrophic Injury", "Catastrophic Injury"),
    ("Medical Malpractice", "Medical Malpractice"),
    ("Divorce", "Divorce"),
    ("Environmental", "Environmental"),
    ("Other", "Other"),
]

CASE_TYPE_VALUES = {value for _, value in CASE_TYPE_OPTIONS}

# Color palette for case types, using high-contrast hex values tuned for the dashboards.
CASE_TYPE_COLOR_MAP: Dict[str, str] = {
    "Personal Injury": "#8fd4ff",      # light blue
    "MVA": "#b49cff",                  # purple
    "Wrongful Death": "#ff6666",       # red
    "Catastrophic Injury": "#ff9c4d",  # orange
    "Medical Malpractice": "#ff3030",  # brightest red
    "Divorce": "#ffe066",              # yellow
    "Environmental": "#66f7b2",        # green
    "Other": "#a0a8b8",               # gray
}

# Legacy case type labels mapped to the new palette so older data still renders well.
CASE_TYPE_ALIASES: Dict[str, str] = {
    "Family Law": "Divorce",
    "Probate": "Other",
    "Estate Planning": "Other",
    "Business Law": "Other",
    "Real Estate": "Other",
    "Workers Comp": "Personal Injury",
    "Intentional Tort": "Other",
    "Criminal": "Other",
}


def normalize_case_type(case_type: str) -> str:
    """Return the canonical case type label for a stored value."""
    return CASE_TYPE_ALIASES.get(case_type, case_type)


def ensure_case_type_options(existing: Iterable[str]) -> List[Tuple[str, str]]:
    """Return UI options including the canonical list plus any legacy values in use."""
    options = list(CASE_TYPE_OPTIONS)
    seen = {value for _, value in options}
    for value in existing:
        if value and value not in seen:
            options.append((value, value))
            seen.add(value)
    return options
