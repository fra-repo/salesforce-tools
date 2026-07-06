"""Refactored Data Viewer App."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import csv
import json
from typing import List, Dict, Any, Optional
import logging

from ..ui.theme import get_theme, Theme
from ..ui.components import (
    ThemedButton,
    ThemedLabel,
    ThemedEntry,
    ThemedFrame,
)
import customtkinter as ctk

logger = logging.getLogger(__name__)


class DataViewerApp:
    """Refactored Data Viewer with pagination and filtering."""

    def __init__(
        self,
        master,
        ui_root=None,
        embedded: bool = False,
        theme_name: str = "light",
    ):
        """Initialize viewer.
        
        Args:
            master: Parent widget
            ui_root: Root window
            embedded: If True, optimize for embedding
            theme_name: Theme name
        """
        self.container = master
        self.root = ui_root or master
        self.embedded = embedded
        self.theme = get_theme("embedded" if embedded else theme_name)
        
        # Data structures
        self.headers: List[str] = []
        self.all_rows: List[List[str]] = []
        self.filtered_rows: List[List[str]] = []
        self.raw_json_data: Optional[List[Dict]] = None
        
        # Pagination
        self.current_page = 1
        self.page_size = tk.IntVar(value=100)
        self.total_pages = 1
        
        # UI elements
        self.tree_table: Optional[ttk.Treeview] = None
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_change)
        
        self._build_ui()
        logger.info("DataViewerApp initialized")
    
    def _build_ui(self) -> None:
        """Build user interface."""
        main_frame = ThemedFrame(self.container, theme=self.theme, card_style=False)
        main_frame.pack(fill="both", expand=True, padx=self.theme.outer_padding, pady=self.theme.outer_padding)
        
        # TOP PANEL - File operations
        top_panel = ThemedFrame(main_frame, theme=self.theme, card_style=True)
        top_panel.pack(fill="x", pady=(0, 20))
        
        file_row = ThemedFrame(top_panel, theme=self.theme, card_style=False)
        file_row.pack(fill="x", padx=20, pady=(20, 15))
        
        self.load_btn = ThemedButton(
            file_row,
            "📂 Carica File",
            command=self._open_file,
            theme=self.theme,
            is_primary=True,
        )
        self.load_btn.pack(side="left")
        
        self.file_info_var = tk.StringVar(value="Nessun file caricato")
        info_label = ThemedLabel(
            file_row,
            textvariable=self.file_info_var,
            theme=self.theme,
            size=11,
        )
        info_label.pack(side="left", padx=20)
        
        # SEARCH ROW
        search_row = ThemedFrame(top_panel, theme=self.theme, card_style=False)
        search_row.pack(fill="x", padx=20, pady=(0, 20))
        
        ThemedLabel(
            search_row,
            "FILTRO GLOBALE",
            theme=self.theme,
            size=9,
            bold=True,
            color=self.theme.subtle,
        ).pack(side="left", padx=(0, 15))
        
        search_entry = ctk.CTkEntry(
            search_row,
            textvariable=self.search_var,
            font=(self.theme.font_family, 11),
        )
        search_entry.pack(side="left", fill="x", expand=True, ipady=4)
        search_entry.configure(state="disabled")
        self.search_entry = search_entry
        
        clear_btn = ThemedButton(
            search_row,
            "Reset",
            command=lambda: self.search_var.set(""),
            theme=self.theme,
            is_primary=False,
        )
        clear_btn.pack(side="right", padx=(15, 0))
        clear_btn.configure(state="disabled")
        self.clear_btn = clear_btn
        
        # TABS
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True)
        
        # Tab 1: Table view
        self.tab_table = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_table, text="Vista Tabellare")
        
        self.table_container = ttk.Frame(self.tab_table)
        self.table_container.pack(fill="both", expand=True, pady=(10, 0))
        
        # Pagination controls
        self.pagination_frame = ThemedFrame(self.tab_table, theme=self.theme, card_style=False)
        self.pagination_frame.pack(fill="x", side="bottom", padx=12, pady=12)
        
        self.btn_first = ThemedButton(
            self.pagination_frame,
            "⏮ Prima",
            command=self._go_first,
            theme=self.theme,
            is_primary=False,
        )
        self.btn_first.pack(side="left", padx=2)
        
        self.btn_prev = ThemedButton(
            self.pagination_frame,
            "◀ Prec",
            command=self._go_prev,
            theme=self.theme,
            is_primary=False,
        )
        self.btn_prev.pack(side="left", padx=2)
        
        self.page_label = ThemedLabel(
            self.pagination_frame,
            "Pagina 0 di 0",
            theme=self.theme,
            size=10,
            bold=True,
        )
        self.page_label.pack(side="left", padx=20)
        
        self.btn_next = ThemedButton(
            self.pagination_frame,
            "Succ ▶",
            command=self._go_next,
            theme=self.theme,
            is_primary=False,
        )
        self.btn_next.pack(side="left", padx=2)
        
        self.btn_last = ThemedButton(
            self.pagination_frame,
            "Ultima ⏭",
            command=self._go_last,
            theme=self.theme,
            is_primary=False,
        )
        self.btn_last.pack(side="left", padx=2)
        
        page_size_label = ThemedLabel(
            self.pagination_frame,
            "Righe:",
            theme=self.theme,
            size=10,
        )
        page_size_label.pack(side="right", padx=(15, 8))
        
        page_size_combo = ttk.Combobox(
            self.pagination_frame,
            textvariable=self.page_size,
            values=[50, 100, 200, 500],
            width=6,
            state="readonly",
        )
        page_size_combo.pack(side="right")
        page_size_combo.bind("<<ComboboxSelected>>", lambda e: self._reset_and_render())
        
        self._set_pagination_state(tk.DISABLED)
        
        # Tab 2: Raw viewer
        self.tab_raw = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_raw, text="Codice Sorgente")
        
        self.raw_text = tk.Text(
            self.tab_raw,
            wrap="none",
            font=("Consolas", 10),
            bg=self.theme.card_bg,
            fg=self.theme.text,
            insertbackground=self.theme.text,
            borderwidth=0,
        )
        self.raw_text.pack(fill="both", expand=True, pady=10)
    
    def _open_file(self) -> None:
        """Open and load CSV or JSON file."""
        path = filedialog.askopenfilename(
            title="Apri file dati",
            filetypes=[("Dati", "*.csv *.json"), ("CSV", "*.csv"), ("JSON", "*.json")],
        )
        if not path:
            return
        
        try:
            p = Path(path)
            self.search_var.set("")
            
            if p.suffix.lower() == ".csv":
                self._load_csv(p)
            elif p.suffix.lower() == ".json":
                self._load_json(p)
            
            self.search_entry.configure(state="normal")
            self.clear_btn.configure(state="normal")
        except Exception as e:
            logger.exception(f"File load failed: {e}")
            messagebox.showerror("Errore", f"Impossibile caricare file: {e}")
    
    def _load_csv(self, path: Path) -> None:
        """Load CSV file."""
        with open(path, "r", encoding="utf-8-sig") as f:
            raw_content = f.read()
            f.seek(0)
            
            sample = f.read(8192)
            f.seek(0)
            
            dialect = csv.Sniffer().sniff(sample)
            reader = csv.reader(f, dialect)
            
            self.headers = next(reader, [])
            if not self.headers:
                raise ValueError("CSV privo di intestazioni")
            
            self.all_rows = list(reader)
        
        self.filtered_rows = list(self.all_rows)
        self.file_info_var.set(
            f"CSV • {path.name} • {len(self.all_rows)} record"
        )
        
        self.raw_text.configure(state="normal")
        self.raw_text.delete("1.0", "end")
        if len(raw_content) > 2000000:
            self.raw_text.insert("1.0", "File massivo. Raw view disattivato.")
        else:
            self.raw_text.insert("1.0", raw_content)
        self.raw_text.configure(state="disabled")
        
        self._reset_and_render()
        self.notebook.select(0)
    
    def _load_json(self, path: Path) -> None:
        """Load JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            self.raw_json_data = json.loads(content)
        
        if not isinstance(self.raw_json_data, list):
            raise ValueError("JSON deve essere array di record")
        
        self.raw_text.configure(state="normal")
        self.raw_text.delete("1.0", "end")
        if len(content) > 2000000:
            self.raw_text.insert("1.0", "File massivo. Raw view disattivato.")
        else:
            self.raw_text.insert("1.0", json.dumps(self.raw_json_data, indent=2, ensure_ascii=False))
        self.raw_text.configure(state="disabled")
        
        # Flatten JSON
        flattened = [self._flatten_json_record(rec) for rec in self.raw_json_data]
        
        # Collect all headers
        all_headers = set()
        for rec in flattened:
            all_headers.update(rec.keys())
        
        self.headers = sorted(list(all_headers))
        self.all_rows = [
            [str(rec.get(h, "")) for h in self.headers]
            for rec in flattened
        ]
        
        self.filtered_rows = list(self.all_rows)
        self.file_info_var.set(
            f"JSON • {path.name} • {len(self.all_rows)} record"
        )
        
        self._reset_and_render()
        self.notebook.select(0)
    
    def _flatten_json_record(self, obj: Any, prefix: str = "") -> Dict[str, Any]:
        """Recursively flatten JSON record."""
        result = {}
        
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_key = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
                result.update(self._flatten_json_record(v, new_key))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                new_key = f"{prefix}[{i}]"
                result.update(self._flatten_json_record(item, new_key))
        else:
            result[prefix] = obj
        
        return result
    
    def _on_search_change(self, *args) -> None:
        """Handle search input changes."""
        query = self.search_var.get().strip().lower()
        
        if not query:
            self.filtered_rows = list(self.all_rows)
        else:
            self.filtered_rows = [
                row for row in self.all_rows
                if any(query in str(cell).lower() for cell in row)
            ]
        
        self._reset_and_render()
    
    def _reset_and_render(self) -> None:
        """Reset pagination and render table."""
        self.current_page = 1
        size = self.page_size.get()
        self.total_pages = max(1, (len(self.filtered_rows) + size - 1) // size)
        
        if self.all_rows:
            self._set_pagination_state(tk.NORMAL)
        
        self._render_table()
    
    def _set_pagination_state(self, state: str) -> None:
        """Set pagination button state."""
        for btn in [self.btn_first, self.btn_prev, self.btn_next, self.btn_last]:
            btn.configure(state=state)
    
    def _render_table(self) -> None:
        """Render current page of table."""
        if not self.headers:
            return
        
        # Clear old table
        for widget in self.table_container.winfo_children():
            widget.destroy()
        
        # Create new tree
        scroll_y = ttk.Scrollbar(self.table_container, orient="vertical")
        scroll_x = ttk.Scrollbar(self.table_container, orient="horizontal")
        
        self.tree_table = ttk.Treeview(
            self.table_container,
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
            columns=self.headers,
            show="headings",
        )
        
        self.tree_table.tag_configure("evenrow", background="#f8fbff")
        self.tree_table.tag_configure("oddrow", background="#ffffff")
        
        scroll_y.config(command=self.tree_table.yview)
        scroll_x.config(command=self.tree_table.xview)
        
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.tree_table.pack(side="left", fill="both", expand=True)
        
        # Add columns
        for h in self.headers:
            self.tree_table.heading(h, text=f"  {h}")
            self.tree_table.column(h, width=max(140, len(h) * 9), minwidth=100)
        
        # Add rows
        size = self.page_size.get()
        start = (self.current_page - 1) * size
        end = start + size
        
        for i, row in enumerate(self.filtered_rows[start:end]):
            tag = "evenrow" if i % 2 == 0 else "oddrow"
            self.tree_table.insert("", "end", values=row, tags=(tag,))
        
        # Update pagination
        total = len(self.filtered_rows)
        if total == len(self.all_rows):
            self.page_label.configure(
                text=f"Pagina {self.current_page} di {self.total_pages} ({total} record)"
            )
        else:
            self.page_label.configure(
                text=f"Pagina {self.current_page} di {self.total_pages} (Trovati {total} di {len(self.all_rows)})"
            )
        
        # Update button states
        can_prev = self.current_page > 1
        can_next = self.current_page < self.total_pages
        
        self.btn_first.configure(state=tk.NORMAL if can_prev else tk.DISABLED)
        self.btn_prev.configure(state=tk.NORMAL if can_prev else tk.DISABLED)
        self.btn_next.configure(state=tk.NORMAL if can_next else tk.DISABLED)
        self.btn_last.configure(state=tk.NORMAL if can_next else tk.DISABLED)
    
    def _go_first(self) -> None:
        self.current_page = 1
        self._render_table()
    
    def _go_prev(self) -> None:
        if self.current_page > 1:
            self.current_page -= 1
            self._render_table()
    
    def _go_next(self) -> None:
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._render_table()
    
    def _go_last(self) -> None:
        self.current_page = self.total_pages
        self._render_table()
