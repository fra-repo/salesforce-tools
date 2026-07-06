"""Refactored Platform Limits Monitor App."""

import tkinter as tk
from typing import List, Dict, Any, Optional
import logging

from ..core.sf_cli import SalesforceCliManager
from ..core.exceptions import OrgNotFound
from ..ui.theme import get_theme, Theme
from ..ui.components import (
    ThemedButton,
    ThemedLabel,
    ThemedFrame,
    ThemedComboBox,
)
import customtkinter as ctk

logger = logging.getLogger(__name__)


class LimitMonitorApp(ctk.CTkScrollableFrame):
    """Monitor Salesforce platform limits."""

    def __init__(
        self,
        master,
        ui_root=None,
        embedded: bool = False,
        theme_name: str = "light",
    ):
        """Initialize limit monitor.
        
        Args:
            master: Parent widget
            ui_root: Root window
            embedded: If True, optimize for embedding
            theme_name: Theme name
        """
        self.embedded = embedded
        self.theme = get_theme("embedded" if embedded else theme_name)
        
        super().__init__(master, fg_color="transparent")
        
        self.sf_cli = SalesforceCliManager()
        self.root = ui_root or master
        
        self._build_ui()
        self._load_orgs_async()
        
        logger.info("LimitMonitorApp initialized")
    
    def _build_ui(self) -> None:
        """Build user interface."""
        # Title
        ThemedLabel(
            self,
            "Salesforce Platform Limits",
            theme=self.theme,
            size=20,
            bold=True,
        ).pack(pady=(10, 8))
        
        # Toolbar
        toolbar = ThemedFrame(self, theme=self.theme, card_style=False)
        toolbar.pack(fill="x", padx=12, pady=(0, 10))
        
        ThemedLabel(
            toolbar,
            "Org",
            theme=self.theme,
            size=10,
            bold=True,
            color=self.theme.subtle,
        ).pack(side="left", padx=(0, 8))
        
        self.org_var = tk.StringVar()
        self.org_combo = ThemedComboBox(
            toolbar,
            theme=self.theme,
            values=["Caricamento..."],
        )
        self.org_combo.pack(side="left", padx=(0, 8))
        
        self.refresh_btn = ThemedButton(
            toolbar,
            "Aggiorna",
            command=self._refresh_orgs,
            theme=self.theme,
            is_primary=False,
        )
        self.refresh_btn.pack(side="left", padx=(0, 8))
        
        self.load_btn = ThemedButton(
            toolbar,
            "Carica limiti",
            command=self._load_limits,
            theme=self.theme,
            is_primary=True,
        )
        self.load_btn.pack(side="left")
        
        # Status label
        self.status_label = ThemedLabel(
            self,
            "Seleziona una org...",
            theme=self.theme,
            size=11,
            color=self.theme.subtle,
        )
        self.status_label.pack(anchor="w", padx=12, pady=(0, 10))
        
        # Container for limit cards
        self.container = ThemedFrame(self, theme=self.theme, card_style=False)
        self.container.pack(fill="both", expand=True, padx=4, pady=4)
    
    def _load_orgs_async(self) -> None:
        """Load orgs in background."""
        import threading
        threading.Thread(target=self._discover_orgs, daemon=True).start()
    
    def _discover_orgs(self) -> None:
        """Discover available orgs."""
        try:
            aliases = self.sf_cli.discover_org_aliases()
            if not aliases:
                aliases = ["Nessuna org trovata"]
                self.load_btn.configure(state="disabled")
            else:
                self.load_btn.configure(state="normal")
            
            self.org_combo.configure(values=aliases)
            self.org_var.set(aliases[0])
            self.status_label.configure(
                text=f"Trovate {len(aliases)} org registrate"
            )
        except Exception as e:
            logger.error(f"Org discovery failed: {e}")
            self.status_label.configure(text=f"Errore: {e}")
    
    def _refresh_orgs(self) -> None:
        """Refresh org list."""
        self.refresh_btn.configure(state="disabled")
        self.sf_cli.clear_cache()
        self._load_orgs_async()
        self.refresh_btn.configure(state="normal")
    
    def _load_limits(self) -> None:
        """Load and display limits for selected org."""
        org = self.org_var.get().strip()
        if not org or org == "Nessuna org trovata":
            self.status_label.configure(text="Nessuna org disponibile")
            return
        
        org_alias = org.split(" (")[0].strip()
        self.status_label.configure(text=f"Caricamento limiti per {org_alias}...")
        
        import threading
        threading.Thread(
            target=self._fetch_and_render_limits,
            args=(org_alias,),
            daemon=True
        ).start()
    
    def _fetch_and_render_limits(self, org_alias: str) -> None:
        """Fetch limits from CLI and render."""
        try:
            # Execute CLI command
            result = self.sf_cli._run_command(
                ["org", "list", "limits", "--target-org", org_alias, "--json"]
            )
            
            if not result["success"]:
                raise Exception(result.get("stderr", "Unknown error"))
            
            import json
            payload = json.loads(result["stdout"])
            limits = payload.get("result", {})
            
            # Render limits
            self.root.after(0, lambda: self._render_limits(limits))
            self.root.after(0, lambda: self.status_label.configure(
                text=f"Limiti caricati per {org_alias}"
            ))
        
        except Exception as e:
            logger.error(f"Limits fetch failed: {e}")
            self.root.after(0, lambda: self.status_label.configure(
                text=f"Errore: {e}"
            ))
    
    def _render_limits(self, limits: Dict[str, Any]) -> None:
        """Render limit cards."""
        # Clear container
        for widget in self.container.winfo_children():
            widget.destroy()
        
        if isinstance(limits, dict):
            items = []
            for title, payload in limits.items():
                if not isinstance(payload, dict):
                    continue
                
                remaining = payload.get("Remaining")
                max_val = payload.get("Max")
                
                if remaining is None or max_val is None:
                    continue
                
                items.append((title.replace("_", " "), remaining, max_val))
        else:
            items = []
        
        if not items:
            ThemedLabel(
                self.container,
                "Nessun limite disponibile",
                theme=self.theme,
                size=11,
                color=self.theme.subtle,
            ).pack(pady=20)
            return
        
        # Render cards
        for label, remaining, max_val in items:
            self._create_limit_card(label, remaining, max_val)
    
    def _create_limit_card(
        self, title: str, remaining: int, max_val: int
    ) -> None:
        """Create and render a limit gauge card."""
        max_val = max_val or 1
        remaining = remaining if remaining is not None else 0
        used = max(max_val - remaining, 0)
        ratio = (used / max_val) if max_val else 0
        percent = ratio * 100
        
        # Determine color
        if ratio >= 0.9:
            fill_color = "#dc2626"
        elif ratio >= 0.7:
            fill_color = "#f97316"
        else:
            fill_color = self.theme.primary
        
        # Card frame
        card = ThemedFrame(self.container, theme=self.theme, card_style=True)
        card.pack(fill="x", pady=6, padx=6)
        
        body = ThemedFrame(card, theme=self.theme, card_style=False)
        body.pack(fill="x", padx=14, pady=14)
        
        # Gauge (semicircle arc using Canvas)
        gauge_canvas = ctk.CTkCanvas(
            body,
            width=120,
            height=70,
            bg=self.theme.card_bg,
            highlightthickness=0,
        )
        gauge_canvas.pack(side="left", padx=(0, 16))
        
        # Background arc
        gauge_canvas.create_arc(
            10, 15, 110, 115,
            start=0, extent=180,
            outline=self.theme.secondary,
            width=12,
            style="arc"
        )
        
        # Filled arc
        if ratio > 0:
            extent_angle = -180 * ratio
            gauge_canvas.create_arc(
                10, 15, 110, 115,
                start=180, extent=extent_angle,
                outline=fill_color,
                width=12,
                style="arc"
            )
        
        # Percentage text
        gauge_canvas.create_text(
            60, 55,
            text=f"{percent:.0f}%",
            font=(self.theme.font_family, 13, "bold"),
            fill=fill_color
        )
        
        # Info column
        info_col = ThemedFrame(body, theme=self.theme, card_style=False)
        info_col.pack(side="left", fill="both", expand=True)
        
        ThemedLabel(
            info_col,
            title,
            theme=self.theme,
            size=14,
            bold=True,
        ).pack(anchor="w", pady=(2, 4))
        
        ThemedLabel(
            info_col,
            f"{remaining:,} su {max_val:,}",
            theme=self.theme,
            size=12,
            color=self.theme.subtle,
        ).pack(anchor="w")
