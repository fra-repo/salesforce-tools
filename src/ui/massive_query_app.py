"""Refactored Massive Query Tool with modular architecture."""

import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import threading
import time
from typing import Optional, List, Dict, Any
import logging

from ..core.sf_cli import SalesforceCliManager
from ..core.soql_validator import SOQLValidator
from ..core.exceptions import SalesforceError, ValidationError
from ..operations.data_extractor import SalesforceDataExtractor
from ..operations.data_exporter import DataExporter
from ..ui.theme import get_theme, Theme
from ..ui.components import (
    ThemedButton,
    ThemedLabel,
    ThemedEntry,
    ThemedFrame,
    ThemedComboBox,
    ProgressIndicator,
    FloatingLabelInput,
    BadgeChip,
    LoadingSpinner,
)
import customtkinter as ctk

logger = logging.getLogger(__name__)


class MassiveQueryApp:
    """Refactored Massive Query Tool UI."""

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
            messagebox.showerror(
                "Errore",
                f"Impossibile inizializzare Salesforce CLI: {e}"
            )
            return
        
        self.extractor: Optional[SalesforceDataExtractor] = None
        self.exporter: Optional[DataExporter] = None
        
        # Threading
        self.abort_event = threading.Event()
        self.log_lock = threading.Lock()
        
        # Build UI
        self._build_ui()
        
        # Load orgs async
        threading.Thread(target=self._load_orgs_async, daemon=True).start()
        
        logger.info("MassiveQueryApp initialized")
    
    def _build_ui(self) -> None:
        """Build user interface."""
        main_frame = ThemedFrame(self.container, theme=self.theme, card_style=False)
        main_frame.pack(fill="both", expand=True, padx=self.theme.outer_padding, pady=self.theme.outer_padding)
        
        # TOP BAR
        top_bar = ThemedFrame(main_frame, theme=self.theme, card_style=False)
        top_bar.pack(fill="x", pady=(0, 10))
        
        ThemedLabel(top_bar, "Salesforce Org:", theme=self.theme, size=10, bold=True).pack(side="left", padx=(0, 10))
        BadgeChip(top_bar, text="Massive Query", theme=self.theme).pack(side="left", padx=(0, 10))
        
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
        
        self.open_folder_btn = ThemedButton(
            top_bar,
            "📁 Apri Cartella",
            command=self._open_output_folder,
            theme=self.theme,
            is_primary=False,
        )
        self.open_folder_btn.pack(side="right")
        
        # BODY - Left column
        body = ThemedFrame(main_frame, theme=self.theme, card_style=False)
        body.pack(fill="both", expand=True, pady=(0, 10))
        
        left_col = ThemedFrame(body, theme=self.theme, card_style=False)
        left_col.pack(side="left", fill="both", expand=True)
        
        # Chunk size
        param_card = ThemedFrame(left_col, theme=self.theme, card_style=True)
        param_card.pack(fill="x", pady=(0, 10))
        
        ThemedLabel(
            param_card,
            "Dimensione Chunk",
            theme=self.theme,
            size=12,
            bold=True,
        ).pack(anchor="w", padx=12, pady=(12, 6))
        
        self.chunk_size_var = tk.IntVar(value=200)
        self.chunk_size_entry = FloatingLabelInput(
            param_card,
            theme=self.theme,
            label="Chunk size",
            textvariable=self.chunk_size_var,
        )
        self.chunk_size_entry.pack(fill="x", padx=12, pady=(0, 12))
        
        # Bind values
        values_card = ThemedFrame(left_col, theme=self.theme, card_style=True)
        values_card.pack(fill="both", expand=True)
        
        ThemedLabel(
            values_card,
            "Valori di Bind",
            theme=self.theme,
            size=12,
            bold=True,
        ).pack(anchor="w", padx=12, pady=(12, 6))
        
        self.bind_text = ctk.CTkTextbox(
            values_card,
            wrap="none",
            font=("Consolas", 10),
            border_width=1,
            border_color=self.theme.border,
            fg_color=self.theme.input_bg,
            text_color=self.theme.text,
        )
        self.bind_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        
        # BODY - Right column
        right_col = ThemedFrame(body, theme=self.theme, card_style=False)
        right_col.pack(side="right", fill="both", expand=True)
        
        # Query
        query_card = ThemedFrame(right_col, theme=self.theme, card_style=True)
        query_card.pack(fill="x", pady=(0, 10))
        
        ThemedLabel(
            query_card,
            "Query SOQL",
            theme=self.theme,
            size=12,
            bold=True,
        ).pack(anchor="w", padx=12, pady=(12, 6))
        
        self.query_text = ctk.CTkTextbox(
            query_card,
            height=100,
            wrap="word",
            font=("Consolas", 10),
            border_width=1,
            border_color=self.theme.border,
            fg_color=self.theme.input_bg,
            text_color=self.theme.text,
        )
        self.query_text.pack(fill="x", padx=12, pady=(0, 12))
        self.query_text.insert("1.0", "SELECT Id, Name FROM Account WHERE Id IN :bind_values")
        
        # Output dir
        dest_card = ThemedFrame(right_col, theme=self.theme, card_style=True)
        dest_card.pack(fill="x", pady=(0, 10))
        
        ThemedLabel(
            dest_card,
            "Cartella Output",
            theme=self.theme,
            size=12,
            bold=True,
        ).pack(anchor="w", padx=12, pady=(12, 6))
        
        dest_frame = ThemedFrame(dest_card, theme=self.theme, card_style=False)
        dest_frame.pack(fill="x", padx=12, pady=(0, 12))
        
        self.dest_dir_var = tk.StringVar(value=str(Path("./salesforce_extracts").resolve()))
        self.dest_dir_entry = ThemedEntry(dest_frame, theme=self.theme, textvariable=self.dest_dir_var)
        self.dest_dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        ThemedButton(
            dest_frame,
            "Sfoglia...",
            command=self._browse_folder,
            theme=self.theme,
            is_primary=False,
            width=100,
        ).pack(side="right")
        
        # Export formats - Use pack instead of grid
        options_card = ThemedFrame(right_col, theme=self.theme, card_style=True)
        options_card.pack(fill="x", pady=(0, 15))
        
        ThemedLabel(
            options_card,
            "Formati Export",
            theme=self.theme,
            size=12,
            bold=True,
        ).pack(anchor="w", padx=12, pady=(12, 6))
        
        self.csv_var = tk.BooleanVar(value=True)
        self.json_var = tk.BooleanVar(value=False)
        self.xlsx_var = tk.BooleanVar(value=False)
        
        # Checkbox row 1
        checkbox_row1 = ThemedFrame(options_card, theme=self.theme, card_style=False)
        checkbox_row1.pack(anchor="w", padx=12, pady=(0, 3))
        
        ctk.CTkCheckBox(checkbox_row1, text="CSV", variable=self.csv_var).pack(side="left", padx=(0, 20))
        ctk.CTkCheckBox(checkbox_row1, text="JSON", variable=self.json_var).pack(side="left")
        
        # Checkbox row 2
        checkbox_row2 = ThemedFrame(options_card, theme=self.theme, card_style=False)
        checkbox_row2.pack(anchor="w", padx=12, pady=(0, 12))
        
        ctk.CTkCheckBox(checkbox_row2, text="Excel", variable=self.xlsx_var).pack(side="left")
        
        # Progress & console
        console_card = ThemedFrame(main_frame, theme=self.theme, card_style=True)
        console_card.pack(fill="both", expand=False, side="bottom")
        
        ThemedLabel(
            console_card,
            "Console",
            theme=self.theme,
            size=12,
            bold=True,
        ).pack(anchor="w", padx=12, pady=(12, 6))
        
        self.progress = ProgressIndicator(console_card, theme=self.theme)
        self.progress.pack(fill="x", padx=12, pady=(0, 8))
        self.spinner = LoadingSpinner(console_card, theme=self.theme)
        self.spinner.pack(anchor="e", padx=12, pady=(0, 6))
        
        self.log_text = ctk.CTkTextbox(console_card, wrap="word", font=("Consolas", 9), height=100, border_width=0)
        self.log_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log_text.configure(state="disabled")
        
        # Action buttons
        action_frame = ThemedFrame(console_card, theme=self.theme, card_style=False)
        action_frame.pack(fill="x", padx=12, pady=(0, 12))
        
        self.run_btn = ThemedButton(
            action_frame,
            "🚀 AVVIA",
            command=self._start_extraction,
            theme=self.theme,
            is_primary=True,
        )
        self.run_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))
        
        self.abort_btn = ThemedButton(
            action_frame,
            "🛑 ANNULLA",
            command=self._abort_extraction,
            theme=self.theme,
            is_primary=False,
        )
        self.abort_btn.pack(side="right", fill="x", expand=True, padx=(0, 5))
        self.abort_btn.configure(state="disabled")
    
    def _log(self, msg: str) -> None:
        """Thread-safe logging to UI."""
        with self.log_lock:
            self.root.after(0, self._safe_log, msg)
    
    def _safe_log(self, msg: str) -> None:
        """Write to log text widget."""
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{msg}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
    
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
        self.refresh_btn.configure(state="normal")
    
    def _refresh_orgs(self) -> None:
        """Refresh org list."""
        self.refresh_btn.configure(state="disabled")
        self.sf_cli.clear_cache()
        threading.Thread(target=self._load_orgs_async, daemon=True).start()
    
    def _browse_folder(self) -> None:
        """Browse for output folder."""
        folder = filedialog.askdirectory(initialdir=self.dest_dir_var.get())
        if folder:
            self.dest_dir_var.set(folder)
    
    def _open_output_folder(self) -> None:
        """Open output folder in explorer."""
        import subprocess
        import os
        path = Path(self.dest_dir_var.get())
        path.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(path)
            elif os.name == "posix":
                subprocess.Popen(["open", str(path)])
        except Exception as e:
            self._log(f"Errore apertura cartella: {e}")
    
    def _start_extraction(self) -> None:
        """Start data extraction."""
        try:
            # Validate inputs
            org = self.alias_var.get().strip()
            if not org:
                messagebox.showwarning("Errore", "Seleziona un org")
                return
            
            soql = self.query_text.get("1.0", "end").strip()
            bind_raw = self.bind_text.get("1.0", "end").strip()
            
            SOQLValidator.validate_soql(soql)
            SOQLValidator.check_bind_values_in_query(soql)
            
            # Parse bind values
            bind_values = [v.strip().strip("'\"")
                          for v in bind_raw.replace(",", "\n")
                          .replace(";", "\n")
                          .replace("\t", "\n")
                          .split("\n") if v.strip()]
            
            if not bind_values:
                messagebox.showwarning("Errore", "Nessun valore di bind")
                return
            
            # Start extraction
            self.run_btn.configure(state="disabled")
            self.abort_btn.configure(state="normal")
            self.abort_event.clear()
            self.progress.set_progress(0)
            self.spinner.start()
            
            threading.Thread(
                target=self._run_extraction,
                args=(org, soql, bind_values),
                daemon=True
            ).start()
        except ValidationError as e:
            messagebox.showerror("Errore Validazione", str(e))
        except Exception as e:
            logger.exception(f"Start extraction failed: {e}")
            messagebox.showerror("Errore", str(e))
    
    def _run_extraction(self, org: str, soql: str, bind_values: List[str]) -> None:
        """Execute extraction in worker thread."""
        error_msg = None
        try:
            org_alias = org.split(" ")[0]
            self._log(f"Inizio estrazione da {org_alias}")
            
            # Initialize extractor
            self.extractor = SalesforceDataExtractor(self.sf_cli, org_alias)
            self.exporter = DataExporter(Path(self.dest_dir_var.get()))
            
            # Parse query structure
            structure = self.extractor.parse_soql_structure(soql)
            
            # Chunk values
            chunks = self.extractor.chunk_bind_values(bind_values, self.chunk_size_var.get())
            self._log(f"Suddiviso in {len(chunks)} chunk")
            
            # Extract data
            all_records = []
            total_records = 0
            
            for i, chunk in enumerate(chunks):
                if self.abort_event.is_set():
                    break
                
                progress = (i + 1) / len(chunks)
                self.root.after(0, lambda p=progress: self.progress.set_progress(p))
                
                records = self.extractor.execute_query(soql, chunk)
                all_records.extend(records)
                total_records += len(records)
                
                self._log(f"Chunk {i+1}/{len(chunks)}: {len(records)} record")
            
            if self.abort_event.is_set():
                self._log("Estrazione annullata")
                return
            
            # Process for export
            self._log("Elaborazione dati per export...")
            headers, flat_rows = self.extractor.process_records_for_export(all_records, structure)
            
            # Export
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            base_name = f"extract_{timestamp}"
            
            if self.csv_var.get():
                self.exporter.export_csv(headers, flat_rows, base_name)
                self._log(f"✅ Esportato CSV")
            
            if self.json_var.get():
                self.exporter.export_json(all_records, base_name, flat=False)
                self._log(f"✅ Esportato JSON")
            
            if self.xlsx_var.get():
                self.exporter.export_xlsx(headers, flat_rows, base_name)
                self._log(f"✅ Esportato XLSX")
            
            self._log(f"\n🎉 Completato! {total_records} record estratti")
            self.root.after(0, lambda: messagebox.showinfo("Completato", f"Estrazione completata\n{total_records} record"))
        
        except SalesforceError as e:
            error_msg = str(e)
            logger.error(f"Salesforce error: {e}")
            self._log(f"❌ Errore Salesforce: {e}")
            self.root.after(0, lambda msg=error_msg: messagebox.showerror("Errore", msg))
        except Exception as e:
            error_msg = str(e)
            logger.exception(f"Extraction failed: {e}")
            self._log(f"❌ Errore: {e}")
            self.root.after(0, lambda msg=error_msg: messagebox.showerror("Errore", msg))
        finally:
            self.root.after(0, lambda: [
                self.run_btn.configure(state="normal"),
                self.abort_btn.configure(state="disabled"),
                self.spinner.stop(),
            ])
    
    def _abort_extraction(self) -> None:
        """Abort current extraction."""
        self.abort_event.set()
        self._log("⚠️ Interruzione richiesta...")
