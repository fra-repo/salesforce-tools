"""Platform Limits Monitor Tool."""

import tkinter as tk
from pathlib import Path
import threading
import logging

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

        super().__init__(master, fg_color="transparent")

        try:
            self.sf_cli = SalesforceCliManager()
        except Exception as e:
            logger.error(f"Salesforce CLI not available: {e}")
            self.sf_cli = None

        self.root = ui_root or master

        self._build_ui()

        if self.sf_cli is None:
            # Show a friendly message instead of crashing or silently doing nothing
            self.load_btn.configure(state="disabled")
            self.refresh_btn.configure(state="disabled")
            self.status_label.configure(text="Salesforce CLI non trovato. Installa sf/sfdx e riavvia.")
        else:
            self._load_orgs_async()

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
    
    def _load_orgs_async(self) -> None:
        """Load orgs in background."""
        import threading
        threading.Thread(target=self._discover_orgs, daemon=True).start()

    def _discover_orgs(self) -> None:
        """Discover available orgs (runs in background thread)."""
        try:
            aliases = self.sf_cli.discover_org_aliases()
            has_orgs = bool(aliases)
            if not has_orgs:
                aliases = ["Nessuna org trovata"]
            self.root.after(0, lambda a=aliases, ok=has_orgs: self._update_org_combo(a, ok))
        except Exception as e:
            logger.error(f"Org discovery failed: {e}")
            err = str(e)
            self.root.after(0, lambda: self.status_label.configure(text=f"Errore: {err}"))

    def _update_org_combo(self, aliases: List[str], has_orgs: bool) -> None:
        """Apply org discovery results on the main thread."""
        self.refresh_btn.configure(state="normal")
        self.load_btn.configure(state="normal" if has_orgs else "disabled")
        self.org_combo.configure(values=aliases)
        self.org_var.set(aliases[0])
        count_text = f"Trovate {len(aliases)} org registrate" if has_orgs else "Nessuna org trovata"
        self.status_label.configure(text=count_text)
    
    def _refresh_orgs(self) -> None:
        """Refresh org list."""
        self.refresh_btn.configure(state="disabled")
        self.sf_cli.clear_cache()
        self._load_orgs_async()
        # Button is re-enabled by _update_org_combo once the background thread finishes
    
    def _check_limits(self) -> None:
        """Check platform limits."""
        org = self.alias_var.get().strip()
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
            
            # Run sf org limits command
            result = self.sf_cli._run_command(
                ["org", "list", "limits", "--target-org", org_alias, "--json"]
            )
            
            if result["success"]:
                import json
                data = json.loads(result["stdout"])
                limits = data.get("result", [])
                
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
        else:
            for limit in limits:
                name = limit.get("name", "N/A")
                used = limit.get("used", 0)
                total = limit.get("total", 0)
                percentage = (used / total * 100) if total > 0 else 0
                
                line = f"{name:30} | {used:6} / {total:6} ({percentage:5.1f}%)\n"
                self.limits_text.insert("end", line)
        
        self.limits_text.configure(state="disabled")
        self._log(f"✅ Limiti caricati")
