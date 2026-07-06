"""Main Salesforce Tools Suite Application.

Modular dashboard with embedded tools:
- Massive Query Tool
- Data Viewer
- Platform Limits Monitor
"""

import tkinter as tk
from tkinter import messagebox
import logging
import sys

import customtkinter as ctk

from src.logging_config import setup_logging
from src.config import AppConfig
from src.ui.modern_theme import get_theme
from src.ui.modern_components import ModernFrame, ModernLabel, ModernButton

# Setup logging
logger = setup_logging()
logger.info("Starting Salesforce Tools Suite v2.0")


class SalesforceToolsSuite(ctk.CTk):
    """Main application window with embedded tools."""

    def __init__(self):
        """Initialize main application."""
        super().__init__()
        
        # Load config
        self.config = AppConfig.load()
        self.theme = get_theme(self.config.theme)
        
        # Configure window
        self.title("Salesforce Tools Suite v2.0")
        self.geometry(f"{self.config.window_width}x{self.config.window_height}")
        self.minsize(1200, 800)
        
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=self.theme.app_bg)
        
        # Bind window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Initialize tools dictionary
        self.tools = {}
        self.tool_frames = {}
        self.nav_buttons = {}
        
        # Build UI
        self._build_ui()
        
        # Schedule tool initialization after window is fully rendered
        self.after(100, self._initialize_tools)
        
        logger.info("Main application initialized")
    
    def _build_ui(self) -> None:
        """Build main user interface."""
        # Main container with sidebar
        main_container = ModernFrame(self, theme=self.theme, card=False)
        main_container.pack(fill="both", expand=True)
        
        # SIDEBAR
        self.sidebar = ModernFrame(
            main_container,
            theme=self.theme,
            card=False,
        )
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)
        self.sidebar.configure(fg_color=self.theme.surface_bg)
        
        # Logo area
        logo_frame = ModernFrame(self.sidebar, theme=self.theme, card=False)
        logo_frame.pack(fill="x", padx=16, pady=(20, 30))
        logo_frame.configure(fg_color=self.theme.surface_bg)
        
        ModernLabel(
            logo_frame,
            "🚀",
            theme=self.theme,
            size=32,
        ).pack()
        
        ModernLabel(
            logo_frame,
            "Salesforce Tools",
            theme=self.theme,
            size=14,
            bold=True,
        ).pack(pady=(8, 0))
        
        ModernLabel(
            logo_frame,
            "v2.0",
            theme=self.theme,
            size=9,
            color=self.theme.muted,
        ).pack()
        
        # Divider
        divider = ctk.CTkFrame(self.sidebar, fg_color=self.theme.border, height=1)
        divider.pack(fill="x", padx=16, pady=(0, 20))
        
        # Navigation buttons
        tools = [
            ("massive_query", "📄 Massive Query", "Estrai dati in bulk"),
            ("viewer", "👁️ Visualizzatore", "Visualizza i dati estratti"),
            ("limits", "📊 Platform Limits", "Monitora limiti Salesforce"),
        ]
        
        for tool_id, label, tooltip in tools:
            self._create_nav_button(tool_id, label, tooltip)
        
        # Spacer
        spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)
        
        # Footer buttons
        footer_frame = ModernFrame(self.sidebar, theme=self.theme, card=False)
        footer_frame.pack(fill="x", padx=12, pady=(20, 16))
        footer_frame.configure(fg_color=self.theme.surface_bg)
        
        settings_btn = ModernButton(
            footer_frame,
            "⚙️ Impostazioni",
            command=self._show_settings,
            theme=self.theme,
            is_primary=False,
            width=140,
        )
        settings_btn.pack(fill="x", pady=(0, 8))
        
        about_btn = ModernButton(
            footer_frame,
            "ℹ️ Info",
            command=self._show_about,
            theme=self.theme,
            is_primary=False,
            width=140,
        )
        about_btn.pack(fill="x")
        
        # MAIN CONTENT AREA
        self.content_frame = ModernFrame(
            main_container,
            theme=self.theme,
            card=False,
        )
        self.content_frame.pack(side="right", fill="both", expand=True, padx=0, pady=0)
        
        # Container for tool frames
        for tool_id, _, _ in tools:
            frame = ModernFrame(self.content_frame, theme=self.theme, card=False)
            frame.pack(fill="both", expand=True)
            frame.pack_forget()
            self.tool_frames[tool_id] = frame
            
            # Add placeholder label
            placeholder = ModernLabel(
                frame,
                f"Caricamento {tool_id}...",
                theme=self.theme,
                size=14,
            )
            placeholder.pack(expand=True)
    
    def _initialize_tools(self) -> None:
        """Initialize tool apps after window is ready."""
        try:
            from src.ui.massive_query_app import MassiveQueryApp
            from src.ui.viewer_app import DataViewerApp
            from src.ui.limit_monitor_app import LimitMonitorApp
            
            # Clear placeholder labels
            for frame in self.tool_frames.values():
                for widget in frame.winfo_children():
                    widget.destroy()
            
            self.tools = {
                "massive_query": MassiveQueryApp(
                    self.tool_frames["massive_query"],
                    ui_root=self,
                    embedded=True,
                    theme_name=self.config.theme,
                ),
                "viewer": DataViewerApp(
                    self.tool_frames["viewer"],
                    ui_root=self,
                    embedded=True,
                    theme_name=self.config.theme,
                ),
                "limits": LimitMonitorApp(
                    self.tool_frames["limits"],
                    ui_root=self,
                    embedded=True,
                    theme_name=self.config.theme,
                ),
            }
            
            # Show first tool
            self._switch_tool("massive_query")
            logger.info("All tools initialized successfully")
            
        except Exception as e:
            logger.exception(f"Tool initialization failed: {e}")
            messagebox.showerror("Errore", f"Errore inizializzazione tool: {str(e)}")
    
    def _create_nav_button(self, tool_id: str, label: str, tooltip: str) -> None:
        """Create navigation button."""
        btn = ModernButton(
            self.sidebar,
            label,
            command=lambda: self._switch_tool(tool_id),
            theme=self.theme,
            is_primary=False,
            width=140,
        )
        btn.pack(fill="x", padx=12, pady=6)
        self.nav_buttons[tool_id] = btn
    
    def _switch_tool(self, tool_id: str) -> None:
        """Switch active tool."""
        if tool_id not in self.tool_frames:
            return
            
        # Hide all frames
        for fid, frame in self.tool_frames.items():
            frame.pack_forget()
        
        # Reset button styling
        for bid, btn in self.nav_buttons.items():
            btn.configure(
                fg_color=self.theme.surface_bg,
                text_color=self.theme.text,
            )
        
        # Show selected frame and highlight button
        self.tool_frames[tool_id].pack(fill="both", expand=True)
        self.nav_buttons[tool_id].configure(
            fg_color=self.theme.primary,
            text_color="#ffffff",
        )
        
        logger.info(f"Switched to tool: {tool_id}")
    
    def _show_settings(self) -> None:
        """Show settings dialog."""
        messagebox.showinfo(
            "Impostazioni",
            f"""Configurazione attuale:

• Chunk size: {self.config.chunk_size}
• Page size: {self.config.page_size}
• Export formats: {', '.join(self.config.export_formats)}
• Theme: {self.config.theme}
• Output dir: {self.config.default_output_dir}

Modifica il file di configurazione per cambiare le impostazioni."""
        )
    
    def _show_about(self) -> None:
        """Show about dialog."""
        messagebox.showinfo(
            "Info",
            """Salesforce Tools Suite v2.0

Strumenti per gestire Salesforce:
• Massive Query - Estrazione bulk di dati
• Visualizzatore - Visualizzazione e filtro dati
• Platform Limits - Monitoraggio limiti org

Repository: https://github.com/fra-repo/salesforce-tools
License: MIT

Architettura modularizzata con:
✓ Logica separata dall'UI
✓ Error handling strutturato
✓ Configurazione persistente
✓ Logging centralizzato
✓ Design moderno dark theme"""
        )
    
    def _on_close(self) -> None:
        """Handle window close."""
        try:
            self.config.save()
        except Exception as e:
            logger.warning(f"Failed to save config on close: {e}")
        logger.info("Application closed")
        self.destroy()


def main():
    """Entry point."""
    try:
        app = SalesforceToolsSuite()
        # _build_ui may call self.destroy() on tool-init failure and return
        # without raising.  Guard against calling mainloop on a dead Tcl app.
        if app.winfo_exists():
            app.mainloop()
        else:
            logger.error("Application destroyed during initialization; exiting")
            sys.exit(1)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        print(f"Errore fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
