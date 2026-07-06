"""Platform Limits Monitor Tool."""

import tkinter as tk
from pathlib import Path
import threading
import logging
from typing import List
import json

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
        
        # CONTENT AREA
        content_card = ThemedFrame(main_frame, theme=self.theme, card_style=True)
        content_card.pack(fill="both", expand=True)
        
        ThemedLabel(
            content_card,
            "Limiti Piattaforma",
            theme=self.theme,
            size=12,
            bold=True,
        ).pack(anchor="w", padx=12, pady=(12, 6))
        
        self.limits_text = ctk.CTkTextbox(
            content_card,
            wrap="word",
            font=("Consolas", 10),
            border_width=1,
            border_color=self.theme.border,
            fg_color=self.theme.input_bg,
            text_color=self.theme.text,
        )
        self.limits_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.limits_text.insert("1.0", "Seleziona un org e clicca 'Verifica Limiti' per visualizzare i dati...")
        self.limits_text.configure(state="disabled")
    
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
        """Write to limits text widget."""
        self.limits_text.configure(state="normal")
        self.limits_text.insert("end", f"{msg}\n")
        self.limits_text.see("end")
        self.limits_text.configure(state="disabled")
    
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
        
        self._safe_log(f"\n⏳ Verifica limiti per {org}...")
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
        """Display limits in UI."""
        self.limits_text.configure(state="normal")
        self.limits_text.delete("1.0", "end")
        
        if not limits:
            self.limits_text.insert("1.0", "Nessun limite trovato")
            self.limits_text.configure(state="disabled")
            return
        
        # Handle different limit formats
        if isinstance(limits, dict):
            limits = [limits]
        
        # Display limits
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
                    
                    percentage = (used / total * 100) if total > 0 else 0
                    
                    line = f"{name:35} | {used:8} / {total:8} ({percentage:6.1f}%)\n"
                    self.limits_text.insert("end", line)
            except Exception as e:
                logger.error(f"Error displaying limit: {e}")
                self.limits_text.insert("end", f"Errore: {e}\n")
        
        self.limits_text.configure(state="disabled")
        self._log(f"✅ Limiti caricati")
