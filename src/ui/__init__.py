"""UI Theme configuration and management.

Centralized theme definitions for consistent styling across all UI components.
"""

from dataclasses import dataclass
from typing import Dict, Any
import os


@dataclass
class Theme:
    """Theme configuration dataclass."""

    app_bg: str = "#f4f6fb"
    card_bg: str = "#ffffff"
    primary: str = "#2563eb"
    secondary: str = "#d9e2f1"
    text: str = "#10203a"
    subtle: str = "#516173"
    hover: str = "#1d4ed8"
    success: str = "#10b981"
    warning: str = "#f59e0b"
    danger: str = "#ef4444"
    font_family: str = "Segoe UI" if os.name == "nt" else "Helvetica"
    outer_padding: int = 15
    shell_radius: int = 22
    shell_border: str = "#d9e2f1"

    def to_dict(self) -> Dict[str, Any]:
        """Convert theme to dictionary.

        Returns:
            Dict representation of theme
        """
        return {
            "app_bg": self.app_bg,
            "card_bg": self.card_bg,
            "primary": self.primary,
            "secondary": self.secondary,
            "text": self.text,
            "subtle": self.subtle,
            "hover": self.hover,
            "success": self.success,
            "warning": self.warning,
            "danger": self.danger,
            "font_family": self.font_family,
            "outer_padding": self.outer_padding,
            "shell_radius": self.shell_radius,
            "shell_border": self.shell_border,
        }


# Default light theme
DEFAULT_THEME = Theme()

# Dark theme variant
DARK_THEME = Theme(
    app_bg="#1a1a2e",
    card_bg="#16213e",
    primary="#0f3460",
    secondary="#533483",
    text="#eaeaea",
    subtle="#a8a8a8",
    hover="#16c784",
)

# Theme for embedded subtools (when used within suite)
EMBEDDED_THEME = Theme(
    app_bg="#f4f6fb",
    card_bg="#ffffff",
    primary="#2563eb",
    secondary="#d9e2f1",
    text="#10203a",
    subtle="#516173",
    hover="#1d4ed8",
    outer_padding=18,
    shell_border="#d9e2f1",
    shell_radius=22,
)

THEMES = {
    "light": DEFAULT_THEME,
    "dark": DARK_THEME,
    "embedded": EMBEDDED_THEME,
}


def get_theme(name: str = "light") -> Theme:
    """Get theme by name.

    Args:
        name: Theme name ('light', 'dark', 'embedded')

    Returns:
        Theme instance

    Raises:
        ValueError: If theme name is invalid
    """
    if name not in THEMES:
        raise ValueError(
            f"Theme '{name}' not found. Available: {list(THEMES.keys())}"
        )
    return THEMES[name]
