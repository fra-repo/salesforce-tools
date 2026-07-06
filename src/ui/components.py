"""Reusable UI components built with customtkinter."""

import customtkinter as ctk
from typing import Callable, Optional
from .theme import Theme, DEFAULT_THEME


class ThemedButton(ctk.CTkButton):
    """Themed button with consistent styling."""

    def __init__(
        self,
        master,
        text: str,
        command: Callable,
        theme: Theme = DEFAULT_THEME,
        is_primary: bool = True,
        width: Optional[int] = None,
        **kwargs
    ):
        """Initialize themed button.

        Args:
            master: Parent widget
            text: Button text
            command: Button click callback
            theme: Theme instance
            is_primary: If True, use primary color; else secondary
            width: Optional fixed width
        """
        bg_color = theme.primary if is_primary else theme.secondary
        text_color = "#ffffff" if is_primary else theme.text
        hover_color = theme.hover if is_primary else "#cbd5e1"

        super().__init__(
            master,
            text=text,
            command=command,
            fg_color=bg_color,
            hover_color=hover_color,
            text_color=text_color,
            font=(theme.font_family, 10, "bold" if is_primary else "normal"),
            corner_radius=10,
            height=34,
            width=width,
            **kwargs
        )


class ThemedLabel(ctk.CTkLabel):
    """Themed label with consistent styling."""

    def __init__(
        self,
        master,
        text: str,
        theme: Theme = DEFAULT_THEME,
        size: int = 10,
        bold: bool = False,
        color: Optional[str] = None,
        **kwargs
    ):
        """Initialize themed label.

        Args:
            master: Parent widget
            text: Label text
            theme: Theme instance
            size: Font size
            bold: If True, use bold font
            color: Optional text color (defaults to theme.text)
        """
        text_color = color or theme.text
        font_weight = "bold" if bold else "normal"

        super().__init__(
            master,
            text=text,
            font=(theme.font_family, size, font_weight),
            text_color=text_color,
            **kwargs
        )


class ThemedEntry(ctk.CTkEntry):
    """Themed entry field with consistent styling."""

    def __init__(
        self,
        master,
        theme: Theme = DEFAULT_THEME,
        placeholder: str = "",
        **kwargs
    ):
        """Initialize themed entry.

        Args:
            master: Parent widget
            theme: Theme instance
            placeholder: Placeholder text
        """
        super().__init__(
            master,
            placeholder_text=placeholder,
            fg_color=theme.card_bg,
            border_color=theme.secondary,
            text_color=theme.text,
            font=(theme.font_family, 10),
            **kwargs
        )


class ThemedFrame(ctk.CTkFrame):
    """Themed frame with consistent styling."""

    def __init__(
        self,
        master,
        theme: Theme = DEFAULT_THEME,
        card_style: bool = False,
        **kwargs
    ):
        """Initialize themed frame.

        Args:
            master: Parent widget
            theme: Theme instance
            card_style: If True, use card styling (border, corner radius)
        """
        if card_style:
            super().__init__(
                master,
                fg_color=theme.card_bg,
                border_width=1,
                border_color=theme.secondary,
                corner_radius=16,
                **kwargs
            )
        else:
            super().__init__(
                master,
                fg_color=theme.app_bg,
                **kwargs
            )


class ThemedComboBox(ctk.CTkComboBox):
    """Themed combobox with consistent styling."""

    def __init__(
        self,
        master,
        theme: Theme = DEFAULT_THEME,
        values: list = None,
        **kwargs
    ):
        """Initialize themed combobox.

        Args:
            master: Parent widget
            theme: Theme instance
            values: List of values
        """
        super().__init__(
            master,
            values=values or [],
            fg_color=theme.card_bg,
            border_color=theme.secondary,
            text_color=theme.text,
            font=(theme.font_family, 10),
            button_color=theme.primary,
            dropdown_fg_color=theme.card_bg,
            dropdown_text_color=theme.text,
            **kwargs
        )


class ProgressIndicator(ctk.CTkFrame):
    """Progress bar with ETA indicator."""

    def __init__(
        self,
        master,
        theme: Theme = DEFAULT_THEME,
        **kwargs
    ):
        """Initialize progress indicator.

        Args:
            master: Parent widget
            theme: Theme instance
        """
        super().__init__(master, fg_color="transparent", **kwargs)

        self.progress_bar = ctk.CTkProgressBar(
            self,
            progress_color=theme.primary,
            fg_color=theme.secondary,
            height=8,
        )
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.progress_bar.set(0)

        self.eta_label = ThemedLabel(
            self,
            text="ETA: --:--",
            theme=theme,
            size=9,
        )
        self.eta_label.pack(side="right")

    def set_progress(self, value: float) -> None:
        """Set progress value.

        Args:
            value: Progress value 0.0-1.0
        """
        self.progress_bar.set(value)

    def set_eta(self, minutes: int, seconds: int) -> None:
        """Set ETA display.

        Args:
            minutes: Minutes remaining
            seconds: Seconds remaining
        """
        self.eta_label.configure(text=f"ETA: {minutes:02d}:{seconds:02d}")
