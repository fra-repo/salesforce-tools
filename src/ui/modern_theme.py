"""Modern UI theme system for Salesforce Tools Suite."""

from dataclasses import dataclass
from typing import Dict
import os


@dataclass(frozen=True)
class ModernTheme:
    """Modern theme token set."""

    name: str
    app_bg: str
    surface_bg: str
    card_bg: str
    sidebar_bg: str
    navbar_bg: str
    input_bg: str
    text: str
    muted: str
    border: str
    primary: str
    primary_alt: str
    accent: str
    success: str
    warning: str
    error: str
    shadow: str
    glass_tint: str
    font_family: str = "Segoe UI" if os.name == "nt" else "Inter"
    radius_lg: int = 24
    radius_md: int = 20
    radius_sm: int = 14
    transition_fast_ms: int = 200
    transition_med_ms: int = 280
    blur_hint: int = 14

    @property
    def secondary(self) -> str:
        return self.surface_bg

    @property
    def subtle(self) -> str:
        return self.muted

    @property
    def hover(self) -> str:
        return self.primary_alt

    @property
    def danger(self) -> str:
        return self.error

    @property
    def shell_border(self) -> str:
        return self.border

    @property
    def shell_radius(self) -> int:
        return self.radius_lg

    @property
    def outer_padding(self) -> int:
        return 16


DARK_THEME = ModernTheme(
    name="dark",
    app_bg="#0f172a",
    surface_bg="#1e293b",
    card_bg="#334155",
    sidebar_bg="#111827",
    navbar_bg="#172033",
    input_bg="#1e293b",
    text="#f1f5f9",
    muted="#94a3b8",
    border="#334155",
    primary="#0EA5E9",
    primary_alt="#06b6d4",
    accent="#22d3ee",
    success="#10b981",
    warning="#f59e0b",
    error="#ef4444",
    shadow="#020617",
    glass_tint="#1e293b",
)

LIGHT_THEME = ModernTheme(
    name="light",
    app_bg="#f1f5f9",
    surface_bg="#ffffff",
    card_bg="#f8fafc",
    sidebar_bg="#e2e8f0",
    navbar_bg="#ffffff",
    input_bg="#ffffff",
    text="#0f172a",
    muted="#475569",
    border="#cbd5e1",
    primary="#0284c7",
    primary_alt="#0891b2",
    accent="#06b6d4",
    success="#059669",
    warning="#d97706",
    error="#dc2626",
    shadow="#94a3b8",
    glass_tint="#ffffff",
)

GLASS_THEME = ModernTheme(
    name="glass",
    app_bg="#0b1120",
    surface_bg="#15243a",
    card_bg="#213550",
    sidebar_bg="#0f1b30",
    navbar_bg="#12243a",
    input_bg="#1a2c45",
    text="#e2e8f0",
    muted="#93c5fd",
    border="#2d4e73",
    primary="#22d3ee",
    primary_alt="#0ea5e9",
    accent="#67e8f9",
    success="#34d399",
    warning="#fbbf24",
    error="#f87171",
    shadow="#020617",
    glass_tint="#1d3557",
    blur_hint=18,
)

EMBEDDED_THEME = ModernTheme(
    name="embedded",
    app_bg=DARK_THEME.app_bg,
    surface_bg="#243248",
    card_bg="#2c3e58",
    sidebar_bg=DARK_THEME.sidebar_bg,
    navbar_bg=DARK_THEME.navbar_bg,
    input_bg="#27384f",
    text=DARK_THEME.text,
    muted=DARK_THEME.muted,
    border="#3d536e",
    primary=DARK_THEME.primary,
    primary_alt=DARK_THEME.primary_alt,
    accent=DARK_THEME.accent,
    success=DARK_THEME.success,
    warning=DARK_THEME.warning,
    error=DARK_THEME.error,
    shadow=DARK_THEME.shadow,
    glass_tint=DARK_THEME.glass_tint,
)

THEMES: Dict[str, ModernTheme] = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
    "glass": GLASS_THEME,
    "embedded": EMBEDDED_THEME,
}


def get_theme(name: str = "dark") -> ModernTheme:
    """Return theme by name."""
    key = (name or "dark").strip().lower()
    if key not in THEMES:
        raise ValueError(f"Theme '{name}' not found. Available: {sorted(THEMES.keys())}")
    return THEMES[key]


def get_available_themes() -> Dict[str, ModernTheme]:
    """Return available themes."""
    return dict(THEMES)
