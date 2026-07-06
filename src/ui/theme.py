"""Compatibility theme module backed by the modern theme system."""

from .modern_theme import (
    ModernTheme as Theme,
    DARK_THEME,
    LIGHT_THEME,
    GLASS_THEME,
    EMBEDDED_THEME,
    get_theme,
)

DEFAULT_THEME = LIGHT_THEME
THEMES = {
    "light": LIGHT_THEME,
    "dark": DARK_THEME,
    "glass": GLASS_THEME,
    "embedded": EMBEDDED_THEME,
}
