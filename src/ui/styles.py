"""Centralized style helpers for modern UI components."""

from typing import Dict, Any
from .modern_theme import ModernTheme

TRANSITION_FAST_MS = 200
TRANSITION_MEDIUM_MS = 280


def button_style(theme: ModernTheme, is_primary: bool = True) -> Dict[str, Any]:
    """Return button style map."""
    fg = theme.primary if is_primary else theme.surface_bg
    hover = theme.primary_alt if is_primary else theme.card_bg
    text = "#ffffff" if is_primary else theme.text
    return {
        "fg_color": fg,
        "hover_color": hover,
        "text_color": text,
        "corner_radius": theme.radius_sm,
        "height": 38,
        "border_width": 1,
        "border_color": theme.border,
    }


def card_style(theme: ModernTheme, glass: bool = False) -> Dict[str, Any]:
    """Return card style map."""
    return {
        "fg_color": theme.glass_tint if glass else theme.card_bg,
        "corner_radius": theme.radius_md,
        "border_width": 1,
        "border_color": theme.border,
    }


def input_style(theme: ModernTheme) -> Dict[str, Any]:
    """Return input style map."""
    return {
        "fg_color": theme.input_bg,
        "border_color": theme.border,
        "text_color": theme.text,
        "corner_radius": theme.radius_sm,
        "height": 36,
    }
