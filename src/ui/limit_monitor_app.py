"""Platform Limits Monitor Tool."""

import tkinter as tk
from pathlib import Path
import threading
import logging
from typing import List
import json
import math

from ..core.sf_cli import SalesforceCliManager
from ..core.exceptions import SalesforceError
from ..ui.theme import get_theme, Theme
from ..ui.components import (
    ThemedButton,
    ThemedLabel,
    ThemedFrame,
    ThemedComboBox,
    BadgeChip,
)
import customtkinter as ctk

logger = logging.getLogger(__name__)


class SemiGaugeWidget(ctk.CTkFrame):
    """Minimal semicircular gauge widget for displaying limit usage."""
    
    def __init__(self, master, name: str, used: int, total: int, theme, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.theme = theme
        self.name = name
        self.used = used
        self.total = total
        self.percentage = (used / total * 100) if total > 0 else 0
        
        # Top section: name + percentage
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 6))
        
        name_label = ctk.CTkLabel(
            header_frame,
            text=name[:30],  # Truncate long names
            text_color=theme.text,
            font=(theme.font_family, 10, "bold"),
        )
        name_label.pack(side="left")
        
        pct_label = ctk.CTkLabel(
            header_frame,
            text=f"{self.percentage:.1f}%",
            text_color=self._get_color_for_percentage(),
            font=(theme.font_family, 10, "bold"),
        )
        pct_label.pack(side="right")
        
        # Canvas for semi-gauge
        self.canvas = ctk.CTkCanvas(
            self,
            width=200,
            height=60,
            bg=theme.card_bg,
            highlightthickness=0,
        )
        self.canvas.pack(pady=(0, 4))
        self._draw_semi_gauge()
        
        # Bottom section: usage info
        footer_label = ctk.CTkLabel(
            self,
            text=f"{used} / {total}",
            text_color=theme.muted,
            font=(theme.font_family, 9),
        )
        footer_label.pack()
    
    def _get_color_for_percentage(self) -> str:
        """Get color based on percentage usage."""
        if self.percentage >= 90:
            return self.theme.error
        elif self.percentage >= 70:
            return self.theme.warning
        elif self.percentage >= 50:
            return self.theme.accent
        else:
            return self.theme.success
    
    def _draw_semi_gauge(self) -> None:
        """Draw minimal semicircular gauge on canvas."""
        w, h = 200, 60
        
        # Background semicircle (light gray)
        self.canvas.create_arc(
            10, 10,
            w - 10, h,
            start=0,
            extent=180,
            fill=self.theme.border,
            outline=self.theme.border,
            width=2,
        )
        
        # Progress semicircle
        if self.percentage > 0:
            extent = (self.percentage / 100) * 180
            self.canvas.create_arc(
                10, 10,
                w - 10, h,
                start=0,
                extent=extent,
                fill=self._get_color_for_percentage(),
                outline=self._get_color_for_percentage(),
                width=2,
            )


class LimitMonitorApp:
    """Platform Limits Monitor."""

    def __init__(
        self,
        master,
        ui_root=None,
        embedded: bool = False,
        theme_name: str = "light",
    ):
        """Initialize app.
        
        Args:
            master: Parent widget
            ui_root: Root window (for tk.after)
            embedded: If True, optimize for embedding
            theme_name: Theme name ('light', 'dark', 'embedded')
        """
        self.container = master
        self.root = ui_root or master
        self.embedded = embedded
        self.theme = get_theme("embedded" if embedded else theme_name)
        
        # Initialize managers
        try:
            self.sf_cli = SalesforceCliManager()
        except Exception as e:
            logger.error(f"CLI initialization failed: {e}")
            self._build_error_ui(str(e))
            return
        
        # Threading
        self.log_lock = threading.Lock()
        
        # Build UI
        self._build_ui()
        
        # Load orgs async
        threading.Thread(target=self._load_orgs_async, daemon=True).start()
        
        logger.info("LimitMonitorApp initialized")
    
    def _build_error_ui(self, error_msg: str) -> None:
        """Build error UI when initialization fails."""
        frame = ThemedFrame(self.container, theme=self.theme, card_style=False)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ThemedLabel(
            frame,
            "❌ Errore Inizializzazione",
            theme=self.theme,
            size=14,
            bold=True,
            color=self.theme.error,
        ).pack(pady=20)
        
        ThemedLabel(
            frame,
            error_msg,
            theme=self.theme,
            size=10,
            color=self.theme.muted,
        ).pack(pady=10)
    
    def _build_ui(self) -> None:
        """Build user interface."""
        main_frame = ThemedFrame(self.container, theme=self.theme, card_style=False)
        main_frame.pack(fill="both", expand=True, padx=self.theme.outer_padding, pady=self.theme.outer_padding)
        
        # TOP BAR
        top_bar = ThemedFrame(main_frame, theme=self.theme, card_style=False)
        top_bar.pack(fill="x", pady=(0, 10))
        
        ThemedLabel(top_bar, "Salesforce Org:", theme=self.theme, size=10, bold=True).pack(side="left", padx=(0, 10))
        BadgeChip(top_bar, text="Platform Limits", theme=self.theme).pack(side="left", padx=(0, 10))
        
        self.alias_var = tk.StringVar()
        self.alias_combo = ThemedComboBox(
            top_bar,
            theme=self.theme,
            values=["Caricamento..."],
        )
        self.alias_combo.pack(side="left", padx=(0, 10))
        self.alias_combo.configure(state="disabled")
        # Bind to the combobox value changes
        self.alias_combo.bind("<FocusOut>", self._on_org_selected)
        
        self.refresh_btn = ThemedButton(
            top_bar,
            "🔄 Aggiorna",
            command=self._refresh_orgs,
            theme=self.theme,
            is_primary=False,
        )
        self.refresh_btn.pack(side="left", padx=(0, 10))
        
        self.check_limits_btn = ThemedButton(
            top_bar,
            "📊 Verifica Limiti",
            command=self._check_limits,
            theme=self.theme,
            is_primary=True,
        )
        self.check_limits_btn.pack(side="right")
        
        # CONTENT AREA with scrollable frame
        content_card = ThemedFrame(main_frame, theme=self.theme, card_style=True)
        content_card.pack(fill="both", expand=True)
        
        # Scrollable container
        self.scrollable_frame = ctk.CTkScrollableFrame(
            content_card,
            fg_color=self.theme.card_bg,
        )
        self.scrollable_frame.pack(fill="both", expand=True, padx=12, pady=12)
        
        # Initial message
        self.init_label = ThemedLabel(
            self.scrollable_frame,
            "Seleziona un org e clicca 'Verifica Limiti' per visualizzare i dati...",
            theme=self.theme,
            size=10,
            color=self.theme.muted,
        )
        self.init_label.pack(pady=20)
    
    def _on_org_selected(self, event=None) -> None:
        """Handle org selection from combobox."""
        selected = self.alias_combo.get()
        self.alias_var.set(selected)
        logger.debug(f"Org selected: {selected}")
    
    def _log(self, msg: str) -> None:
        """Thread-safe logging to UI."""
        with self.log_lock:
            self.root.after(0, self._safe_log, msg)
    
    def _safe_log(self, msg: str) -> None:
        """Write to scrollable frame."""
        label = ThemedLabel(
            self.scrollable_frame,
            msg,
            theme=self.theme,
            size=9,
            color=self.theme.muted,
        )
        label.pack(anchor="w", pady=2)
    
    def _load_orgs_async(self) -> None:
        """Load orgs in background thread."""
        try:
            aliases = self.sf_cli.discover_org_aliases()
            if aliases:
                self._log(f"Trovate {len(aliases)} org")
            else:
                self._log("Nessuna org trovata")
            self.root.after(0, self._update_org_combo, aliases)
        except Exception as e:
            logger.error(f"Org loading failed: {e}")
            self._log(f"Errore caricamento org: {e}")
    
    def _update_org_combo(self, aliases: List[str]) -> None:
        """Update org combobox."""
        self.alias_combo.configure(values=aliases, state="readonly")
        if aliases:
            self.alias_combo.set(aliases[0])
            self.alias_var.set(aliases[0])
        self.refresh_btn.configure(state="normal")
    
    def _refresh_orgs(self) -> None:
        """Refresh org list."""
        self.refresh_btn.configure(state="disabled")
        self.sf_cli.clear_cache()
        threading.Thread(target=self._load_orgs_async, daemon=True).start()
    
    def _check_limits(self) -> None:
        """Check platform limits."""
        # Read current value from combobox directly
        org = self.alias_combo.get().strip()
        if not org:
            self._safe_log("❌ Seleziona un org")
            return
        
        # Clear previous content
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self._log(f"\n⏳ Verifica limiti per {org}...")
        threading.Thread(
            target=self._fetch_limits,
            args=(org,),
            daemon=True
        ).start()
    
    def _fetch_limits(self, org: str) -> None:
        """Fetch limits from Salesforce."""
        try:
            org_alias = org.split(" ")[0]
            logger.info(f"Fetching limits for org: {org_alias}")
            
            # Run sf org list limits command
            result = self.sf_cli._run_command(
                ["org", "list", "limits", "--target-org", org_alias, "--json"]
            )
            
            if result["success"]:
                data = json.loads(result["stdout"])
                logger.debug(f"Raw limits response: {json.dumps(data, indent=2)}")
                
                # Parse limits data - handle different response formats
                limits = []
                if isinstance(data, dict):
                    if "result" in data:
                        limits = data["result"]
                    else:
                        # Assume the dict itself contains limits
                        limits = data
                elif isinstance(data, list):
                    limits = data
                
                # Clear and show limits
                self.root.after(0, self._display_limits, limits)
            else:
                self._log(f"❌ Errore: {result.get('stderr', 'Unknown error')}")
        
        except Exception as e:
            logger.exception(f"Limits fetch failed: {e}")
            self._log(f"❌ Errore: {e}")
    
    def _display_limits(self, limits) -> None:
        """Display limits with minimal semi-gauges in UI."""
        # Clear previous content
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        if not limits:
            label = ThemedLabel(
                self.scrollable_frame,
                "Nessun limite trovato",
                theme=self.theme,
                size=10,
                color=self.theme.muted,
            )
            label.pack(pady=20)
            return
        
        # Handle different limit formats
        if isinstance(limits, dict):
            limits = [limits]
        
        # Display limits as semi-gauges
        gauge_count = 0
        for limit in limits:
            try:
                if isinstance(limit, dict):
                    # Try different key formats
                    name = limit.get("name") or limit.get("Name") or limit.get("LIMIT_NAME", "N/A")
                    used = limit.get("used") or limit.get("Used") or limit.get("value", 0)
                    total = limit.get("total") or limit.get("Total") or limit.get("max", 0)
                    
                    # Convert to int if string
                    try:
                        used = int(used) if used else 0
                        total = int(total) if total else 0
                    except (ValueError, TypeError):
                        used = 0
                        total = 0
                    
                    # Create gauge widget
                    gauge = SemiGaugeWidget(
                        self.scrollable_frame,
                        name=name,
                        used=used,
                        total=total,
                        theme=self.theme,
                    )
                    gauge.pack(fill="x", pady=12)
                    gauge_count += 1
            except Exception as e:
                logger.error(f"Error displaying limit: {e}")
        
        self._log(f"✅ Limiti caricati ({gauge_count} limiti visualizzati)")
