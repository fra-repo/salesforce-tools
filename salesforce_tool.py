"""Main Salesforce Tools Suite Application."""

import tkinter as tk
from tkinter import messagebox
import logging
import sys

import customtkinter as ctk

from src.logging_config import setup_logging
from src.config import AppConfig
from src.ui.theme import get_theme
from src.ui.components import (
    ThemedFrame,
    ThemedLabel,
    ThemedButton,
    ThemedEntry,
    ThemedComboBox,
    ToastManager,
    BadgeChip,
)
from src.ui.massive_query_app import MassiveQueryApp
from src.ui.viewer_app import DataViewerApp
from src.ui.limit_monitor_app import LimitMonitorApp


logger = setup_logging()
logger.info("Starting Salesforce Tools Suite v2.0")


class SalesforceToolsSuite(ctk.CTk):
    """Main application window with embedded tools."""

    def __init__(self):
        super().__init__()

        self.config = AppConfig.load()
        if self.config.theme not in {"dark", "light", "glass", "embedded"}:
            self.config.theme = "dark"
        self.theme = get_theme(self.config.theme)
        self.sidebar_collapsed = False
        self.current_tool = "massive_query"

        self.title("Salesforce Tools Suite v2.0")
        self.geometry(f"{self.config.window_width}x{self.config.window_height}")
        self.minsize(1200, 800)

        ctk.set_appearance_mode("Light" if self.config.theme == "light" else "Dark")
        self.configure(fg_color=self.theme.app_bg)

        self.toast = ToastManager(self, theme=self.theme)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()

        logger.info("Main application initialized")

    def _build_ui(self) -> None:
        main_container = ThemedFrame(self, theme=self.theme, card_style=False)
        main_container.pack(fill="both", expand=True)

        self.sidebar = ThemedFrame(main_container, theme=self.theme, card_style=True, glass=self.config.theme == "glass")
        self.sidebar.pack(side="left", fill="y", padx=(12, 8), pady=12)
        self.sidebar.configure(width=250, fg_color=self.theme.sidebar_bg)
        self.sidebar.pack_propagate(False)

        header_row = ThemedFrame(self.sidebar, theme=self.theme, card_style=False)
        header_row.pack(fill="x", padx=14, pady=(16, 12))
        header_row.configure(fg_color=self.theme.sidebar_bg)

        self.collapse_btn = ThemedButton(
            header_row,
            "☰",
            command=self._toggle_sidebar,
            theme=self.theme,
            is_primary=False,
            width=36,
        )
        self.collapse_btn.pack(side="left")

        self.logo_text = ThemedLabel(header_row, "Salesforce Tools", theme=self.theme, size=14, bold=True)
        self.logo_text.pack(side="left", padx=(10, 0))

        BadgeChip(self.sidebar, text="v2.0", theme=self.theme, color=self.theme.accent).pack(anchor="w", padx=14)

        divider = ctk.CTkFrame(self.sidebar, fg_color=self.theme.border, height=1)
        divider.pack(fill="x", padx=14, pady=(10, 14))

        self.nav_buttons = {}
        self.tools = [
            ("massive_query", "📄", "Massive Query", "Estrai dati in bulk"),
            ("viewer", "👁️", "Visualizzatore", "Visualizza i dati estratti"),
            ("limits", "📊", "Platform Limits", "Monitora limiti Salesforce"),
        ]

        for tool_id, icon, label, tooltip in self.tools:
            self._create_nav_button(tool_id, icon, label, tooltip)

        spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        footer_frame = ThemedFrame(self.sidebar, theme=self.theme, card_style=False)
        footer_frame.pack(fill="x", padx=12, pady=(12, 12))
        footer_frame.configure(fg_color=self.theme.sidebar_bg)

        self.theme_var = tk.StringVar(value=self.config.theme if self.config.theme in {"dark", "light", "glass"} else "dark")
        self.theme_combo = ThemedComboBox(
            footer_frame,
            theme=self.theme,
            values=["dark", "light", "glass"],
            command=self._on_theme_change,
            state="readonly",
        )
        self.theme_combo.set(self.theme_var.get())
        self.theme_combo.pack(fill="x", pady=(0, 8))

        settings_btn = ThemedButton(
            footer_frame,
            "⚙️ Impostazioni",
            command=self._show_settings,
            theme=self.theme,
            is_primary=False,
        )
        settings_btn.pack(fill="x", pady=(0, 6))

        about_btn = ThemedButton(
            footer_frame,
            "ℹ️ Info",
            command=self._show_about,
            theme=self.theme,
            is_primary=False,
        )
        about_btn.pack(fill="x")

        self.content_frame = ThemedFrame(main_container, theme=self.theme, card_style=False)
        self.content_frame.pack(side="right", fill="both", expand=True, padx=(0, 12), pady=12)

        top_nav = ThemedFrame(self.content_frame, theme=self.theme, card_style=True, glass=self.config.theme == "glass")
        top_nav.pack(fill="x", pady=(0, 10))

        self.breadcrumb = ThemedLabel(top_nav, "Home / Massive Query", theme=self.theme, size=11, bold=True)
        self.breadcrumb.pack(side="left", padx=14, pady=12)

        self.search_var = tk.StringVar()
        self.search_entry = ThemedEntry(top_nav, theme=self.theme, placeholder="Search tools...", textvariable=self.search_var, width=240)
        self.search_entry.pack(side="right", padx=12, pady=8)
        self.search_entry.bind("<Return>", lambda _e: self._focus_tool_from_search())

        self.tool_shell = ThemedFrame(self.content_frame, theme=self.theme, card_style=True, glass=self.config.theme == "glass")
        self.tool_shell.pack(fill="both", expand=True)

        self.tool_frames = {}
        for tool_id, _, _, _ in self.tools:
            frame = ThemedFrame(self.tool_shell, theme=self.theme, card_style=False)
            frame.pack(fill="both", expand=True)
            frame.pack_forget()
            self.tool_frames[tool_id] = frame

        try:
            self.tool_apps = {
                "massive_query": MassiveQueryApp(self.tool_frames["massive_query"], ui_root=self, embedded=True, theme_name=self.config.theme),
                "viewer": DataViewerApp(self.tool_frames["viewer"], ui_root=self, embedded=True, theme_name=self.config.theme),
                "limits": LimitMonitorApp(self.tool_frames["limits"], ui_root=self, embedded=True, theme_name=self.config.theme),
            }
        except Exception as e:
            logger.exception(f"Tool initialization failed: {e}")
            messagebox.showerror("Errore", f"Errore inizializzazione tool: {e}")
            self.destroy()
            return

        self._switch_tool("massive_query")

    def _create_nav_button(self, tool_id: str, icon: str, label: str, _tooltip: str) -> None:
        button = ThemedButton(
            self.sidebar,
            f"{icon}  {label}",
            command=lambda: self._switch_tool(tool_id),
            theme=self.theme,
            is_primary=False,
        )
        button.pack(fill="x", padx=12, pady=4)
        self.nav_buttons[tool_id] = {
            "button": button,
            "icon": icon,
            "label": label,
        }

    def _toggle_sidebar(self) -> None:
        self.sidebar_collapsed = not self.sidebar_collapsed
        width = 86 if self.sidebar_collapsed else 250
        self.sidebar.configure(width=width)

        self.logo_text.configure(text="ST" if self.sidebar_collapsed else "Salesforce Tools")
        self.theme_combo.configure(state="disabled" if self.sidebar_collapsed else "readonly")

        for tool in self.nav_buttons.values():
            text = tool["icon"] if self.sidebar_collapsed else f"{tool['icon']}  {tool['label']}"
            tool["button"].configure(text=text)

    def _focus_tool_from_search(self) -> None:
        query = self.search_var.get().strip().lower()
        if not query:
            return
        for tool_id, _, label, _ in self.tools:
            if query in label.lower() or query in tool_id:
                self._switch_tool(tool_id)
                return
        self.toast.show("Nessun tool trovato", level="warning")

    def _switch_tool(self, tool_id: str) -> None:
        for frame in self.tool_frames.values():
            frame.pack_forget()

        for bid, config in self.nav_buttons.items():
            config["button"].configure(
                fg_color=self.theme.primary if bid == tool_id else self.theme.surface_bg,
                text_color="#ffffff" if bid == tool_id else self.theme.text,
            )

        self.current_tool = tool_id
        self.breadcrumb.configure(text=f"Home / {self.nav_buttons[tool_id]['label']}")
        self.after(90, lambda: self.tool_frames[tool_id].pack(fill="both", expand=True))
        logger.info(f"Switched to tool: {tool_id}")

    def _on_theme_change(self, theme_name: str) -> None:
        self.config.theme = theme_name
        self.config.save()
        self.toast.show(f"Tema {theme_name} applicato. Riavvia per applicare a tutti i pannelli.", level="info")

    def _show_settings(self) -> None:
        messagebox.showinfo(
            "Impostazioni",
            f"""Configurazione attuale:

• Chunk size: {self.config.chunk_size}
• Page size: {self.config.page_size}
• Export formats: {', '.join(self.config.export_formats)}
• Theme: {self.config.theme}
• Output dir: {self.config.default_output_dir}

Modifica il file di configurazione per cambiare le impostazioni.""",
        )

    def _show_about(self) -> None:
        messagebox.showinfo(
            "Info",
            """Salesforce Tools Suite v2.0

Strumenti per gestire Salesforce:
• Massive Query - Estrazione bulk di dati
• Visualizzatore - Visualizzazione e filtro dati
• Platform Limits - Monitoraggio limiti org

Repository: https://github.com/fra-repo/salesforce-tools
License: MIT""",
        )

    def _on_close(self) -> None:
        self.config.save()
        logger.info("Application closed")
        self.destroy()


def main():
    """Entry point."""
    try:
        app = SalesforceToolsSuite()
        app.mainloop()
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        print(f"Errore fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
