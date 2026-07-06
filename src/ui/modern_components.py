"""Modern reusable UI components for Salesforce Tools Suite."""

from typing import Callable, Optional, Sequence
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from .modern_theme import ModernTheme, get_theme
from .styles import button_style, card_style as card_tokens, input_style


DEFAULT_THEME = get_theme("dark")
Theme = ModernTheme


class ModernFrame(ctk.CTkFrame):
    """Modern frame with optional elevated/glass styles."""

    def __init__(self, master, theme: Theme = DEFAULT_THEME, card: bool = False, glass: bool = False, **kwargs):
        legacy_card_style = kwargs.pop("card_style", None)
        if legacy_card_style is not None:
            card = legacy_card_style
        if card:
            super().__init__(master, **card_tokens(theme, glass=glass), **kwargs)
        else:
            super().__init__(master, fg_color=theme.app_bg, corner_radius=0, **kwargs)


class ModernCard(ModernFrame):
    """Semantic card container."""

    def __init__(self, master, theme: Theme = DEFAULT_THEME, glass: bool = False, **kwargs):
        super().__init__(master, theme=theme, card=True, glass=glass, **kwargs)


class ModernLabel(ctk.CTkLabel):
    """Modern label."""

    def __init__(self, master, text: str = "", theme: Theme = DEFAULT_THEME, size: int = 11, bold: bool = False, color: Optional[str] = None, **kwargs):
        weight = "bold" if bold else "normal"
        super().__init__(
            master,
            text=text,
            text_color=color or theme.text,
            font=(theme.font_family, size, weight),
            **kwargs,
        )


class ModernButton(ctk.CTkButton):
    """Gradient-inspired button with smooth hover styling."""

    def __init__(
        self,
        master,
        text: str,
        command: Callable,
        theme: Theme = DEFAULT_THEME,
        is_primary: bool = True,
        width: Optional[int] = None,
        **kwargs,
    ):
        style = button_style(theme, is_primary=is_primary)
        super().__init__(
            master,
            text=text,
            command=command,
            font=(theme.font_family, 11, "bold" if is_primary else "normal"),
            width=width,
            **style,
            **kwargs,
        )


class ModernEntry(ctk.CTkEntry):
    """Input with focus border animation behavior."""

    def __init__(self, master, theme: Theme = DEFAULT_THEME, placeholder: str = "", textvariable=None, **kwargs):
        self._theme = theme
        super().__init__(
            master,
            placeholder_text=placeholder,
            textvariable=textvariable,
            font=(theme.font_family, 11),
            **input_style(theme),
            **kwargs,
        )
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)

    def _on_focus_in(self, _event):
        self.configure(border_color=self._theme.primary)

    def _on_focus_out(self, _event):
        self.configure(border_color=self._theme.border)


class ModernComboBox(ctk.CTkComboBox):
    """Styled combobox."""

    def __init__(self, master, theme: Theme = DEFAULT_THEME, values: Optional[Sequence[str]] = None, **kwargs):
        super().__init__(
            master,
            values=list(values or []),
            fg_color=theme.input_bg,
            border_color=theme.border,
            text_color=theme.text,
            button_color=theme.primary,
            button_hover_color=theme.primary_alt,
            dropdown_fg_color=theme.surface_bg,
            dropdown_text_color=theme.text,
            font=(theme.font_family, 10),
            **kwargs,
        )


class FloatingLabelInput(ModernFrame):
    """Input field with static floating label layout."""

    def __init__(self, master, label: str, theme: Theme = DEFAULT_THEME, textvariable=None, **kwargs):
        super().__init__(master, theme=theme, card=False, **kwargs)
        self.label = ModernLabel(self, label, theme=theme, size=9, bold=True, color=theme.muted)
        self.label.pack(anchor="w", pady=(0, 4))
        self.entry = ModernEntry(self, theme=theme, textvariable=textvariable)
        self.entry.pack(fill="x")

    def get(self) -> str:
        return self.entry.get()

    def set(self, value: str) -> None:
        self.entry.delete(0, "end")
        self.entry.insert(0, value)


class ModernToggle(ctk.CTkSwitch):
    """Modern toggle switch."""

    def __init__(self, master, text: str, theme: Theme = DEFAULT_THEME, variable=None, **kwargs):
        super().__init__(
            master,
            text=text,
            variable=variable,
            progress_color=theme.primary,
            button_color=theme.card_bg,
            button_hover_color=theme.primary_alt,
            text_color=theme.text,
            font=(theme.font_family, 10),
            **kwargs,
        )


class ModernTabs(ttk.Notebook):
    """Tabs with modern underline-like style."""

    def __init__(self, master, theme: Theme = DEFAULT_THEME, **kwargs):
        super().__init__(master, **kwargs)
        style = ttk.Style(master)
        style_name = f"ModernNotebook.{id(self)}"
        style.theme_use(style.theme_use())
        style.configure(
            f"{style_name}.TNotebook",
            background=theme.app_bg,
            borderwidth=0,
        )
        style.configure(
            f"{style_name}.TNotebook.Tab",
            background=theme.surface_bg,
            foreground=theme.muted,
            padding=(12, 8),
            borderwidth=0,
        )
        style.map(
            f"{style_name}.TNotebook.Tab",
            background=[("selected", theme.card_bg)],
            foreground=[("selected", theme.primary)],
        )
        self.configure(style=f"{style_name}.TNotebook")


class ModernModal(ctk.CTkToplevel):
    """Simple modal dialog container."""

    def __init__(self, master, title: str, theme: Theme = DEFAULT_THEME):
        super().__init__(master)
        self.title(title)
        self.transient(master)
        self.grab_set()
        self.geometry("420x220")
        self.configure(fg_color=theme.surface_bg)


class ToastManager:
    """Toast notification helper."""

    def __init__(self, root, theme: Theme = DEFAULT_THEME):
        self.root = root
        self.theme = theme

    def show(self, message: str, level: str = "info", duration_ms: int = 2200):
        color_map = {
            "info": self.theme.primary,
            "success": self.theme.success,
            "warning": self.theme.warning,
            "error": self.theme.error,
        }
        toast = ctk.CTkToplevel(self.root)
        toast.overrideredirect(True)
        toast.configure(fg_color=self.theme.surface_bg)

        x = self.root.winfo_rootx() + self.root.winfo_width() - 360
        y = self.root.winfo_rooty() + 32
        toast.geometry(f"320x56+{x}+{y}")

        frame = ModernCard(toast, theme=self.theme)
        frame.pack(fill="both", expand=True, padx=2, pady=2)
        label = ModernLabel(frame, message, theme=self.theme, size=10, bold=True)
        label.pack(side="left", padx=12)
        badge = ctk.CTkFrame(frame, fg_color=color_map.get(level, self.theme.primary), width=8, corner_radius=4)
        badge.pack(side="right", fill="y", padx=8, pady=8)

        toast.after(duration_ms, toast.destroy)


class BadgeChip(ctk.CTkLabel):
    """Badge/chip component."""

    def __init__(self, master, text: str, theme: Theme = DEFAULT_THEME, color: Optional[str] = None, **kwargs):
        super().__init__(
            master,
            text=text,
            fg_color=color or theme.primary,
            text_color="#ffffff",
            corner_radius=999,
            padx=10,
            pady=4,
            font=(theme.font_family, 9, "bold"),
            **kwargs,
        )


class LoadingSpinner(ctk.CTkFrame):
    """Lightweight animated loading indicator."""

    def __init__(self, master, theme: Theme = DEFAULT_THEME, size: int = 16, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._canvas = ctk.CTkCanvas(self, width=size, height=size, bg=theme.app_bg, highlightthickness=0)
        self._canvas.pack()
        self._theme = theme
        self._size = size
        self._angle = 0
        self._running = False

    def start(self):
        self._running = True
        self._tick()

    def stop(self):
        self._running = False

    def _tick(self):
        if not self._running:
            return
        self._canvas.delete("all")
        pad = 2
        self._canvas.create_arc(
            pad,
            pad,
            self._size - pad,
            self._size - pad,
            start=self._angle,
            extent=280,
            width=2,
            outline=self._theme.primary,
            style="arc",
        )
        self._angle = (self._angle + 20) % 360
        self.after(50, self._tick)


class ProgressIndicator(ctk.CTkFrame):
    """Progress bar with gradient-like colors and ETA."""

    def __init__(self, master, theme: Theme = DEFAULT_THEME, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._theme = theme
        self.progress_bar = ctk.CTkProgressBar(
            self,
            progress_color=theme.primary,
            fg_color=theme.border,
            height=10,
            corner_radius=999,
        )
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.progress_bar.set(0)

        self.eta_label = ModernLabel(self, text="ETA: --:--", theme=theme, size=9, color=theme.muted)
        self.eta_label.pack(side="right")

    def set_progress(self, value: float) -> None:
        clamped = max(0.0, min(1.0, float(value)))
        self.progress_bar.set(clamped)
        if clamped >= 0.85:
            self.progress_bar.configure(progress_color=self._theme.success)
        elif clamped >= 0.55:
            self.progress_bar.configure(progress_color=self._theme.accent)
        else:
            self.progress_bar.configure(progress_color=self._theme.primary)

    def set_eta(self, minutes: int, seconds: int) -> None:
        self.eta_label.configure(text=f"ETA: {minutes:02d}:{seconds:02d}")


# Backward-compatible names
ThemedButton = ModernButton
ThemedLabel = ModernLabel
ThemedEntry = ModernEntry
ThemedFrame = ModernFrame
ThemedComboBox = ModernComboBox
