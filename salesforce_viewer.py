import csv
import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk

try:
    from tkinter.scrolledtext import ScrolledText
except Exception:
    ScrolledText = tk.Text

try:
    import ttkbootstrap as tb
    from ttkbootstrap import ttk as ttk
    from ttkbootstrap.constants import *
    USE_TTKBOOTSTRAP = True
except Exception:
    tb = None
    USE_TTKBOOTSTRAP = False


class SalesforceDataViewer:
    def __init__(self, master, ui_root=None, embedded=False, theme=None):
        self.container = master
        self.root = ui_root or (master.winfo_toplevel() if hasattr(master, "winfo_toplevel") else master)
        self.embedded = embedded
        self.theme = theme or {}

        if not embedded:
            self.root.title("Salesforce Premium Data Viewer v4.0")
            self.root.geometry("1350x920")
            self.root.minsize(1150, 750)
            self.COLOR_BG = "#ffffff"
            self.COLOR_CARD = "#f8f9fa"
            self.COLOR_PRIMARY = "#0066cc"
            self.COLOR_SECONDARY = "#e1e4e8"
            self.COLOR_TEXT = "#24292e"
            self.COLOR_HOVER = "#0052a3"
        else:
            self.COLOR_BG = self.theme.get("app_bg", "#f4f6fb")
            self.COLOR_CARD = self.theme.get("card_bg", "#ffffff")
            self.COLOR_PRIMARY = self.theme.get("primary", "#2563eb")
            self.COLOR_SECONDARY = self.theme.get("secondary", "#d9e2f1")
            self.COLOR_TEXT = self.theme.get("text", "#10203a")
            self.COLOR_HOVER = self.theme.get("hover", "#1d4ed8")

        self.FONT_FAMILY = self.theme.get("font_family", "Segoe UI" if os.name == "nt" else "Helvetica")
        self.OUTER_PADDING = self.theme.get("outer_padding", 15 if not embedded else 18)

        ctk_scaling = 1.0
        if os.name == "nt":
            ctk_scaling = 1.08
        try:
            self.root.tk.call("tk", "scaling", ctk_scaling)
        except Exception:
            pass

        self.setup_advanced_styles()
        
        # Strutture Dati
        self.headers = []
        self.all_rows = []       
        self.filtered_rows = []  
        self.raw_json_data = None
        
        # Paginazione
        self.current_page = 1
        self.page_size = tk.IntVar(value=100)
        self.total_pages = 1
        
        # Elementi UI
        self.tree_table = None
        self.raw_text = None
        self.hierarchical_tree = None
        
        self.build_ui()

    def setup_advanced_styles(self):
        if not self.embedded:
            self.root.configure(background=self.COLOR_BG)
        
        if not USE_TTKBOOTSTRAP:
            self.style = ttk.Style()
            self.style.theme_use("clam")
            
            # Frame e Notebook minimali
            self.style.configure("TFrame", background=self.COLOR_BG)
            self.style.configure("TLabel", background=self.COLOR_BG, foreground=self.COLOR_TEXT, font=(self.FONT_FAMILY, 10))
            self.style.configure("TNotebook", background=self.COLOR_BG, borderwidth=0)
            self.style.configure("TNotebook.Tab", background=self.COLOR_CARD, foreground=self.COLOR_TEXT, padding=[20, 8], font=(self.FONT_FAMILY, 10))
            self.style.map("TNotebook.Tab", background=[("selected", self.COLOR_BG)], font=[("selected", (self.FONT_FAMILY, 10, "bold"))])
            self.style.configure("TLabelframe", background=self.COLOR_BG, foreground=self.COLOR_TEXT)
            self.style.configure("TLabelframe.Label", background=self.COLOR_BG, foreground=self.COLOR_TEXT, font=(self.FONT_FAMILY, 10, "bold"))
            
            # Input Entry Flat
            self.style.configure("TEntry", fieldbackground=self.COLOR_CARD, borderwidth=1, relief="flat", foreground=self.COLOR_TEXT)
            self.style.configure("TButton", font=(self.FONT_FAMILY, 10, "bold"), padding=8)
            
            # Tabella Minimalista (Senza linee verticali)
            self.style.configure(
                "Treeview", 
                background=self.COLOR_BG, 
                foreground=self.COLOR_TEXT, 
                rowheight=32, 
                font=(self.FONT_FAMILY, 10),
                borderwidth=0
            )
            self.style.configure(
                "Treeview.Heading", 
                background=self.COLOR_CARD, 
                foreground=self.COLOR_TEXT, 
                font=(self.FONT_FAMILY, 10, "bold"),
                relief="flat",
                borderwidth=1
            )
            self.style.map("Treeview", background=[("selected", "#dbeafe")], foreground=[("selected", self.COLOR_PRIMARY)])

    def create_flat_button(self, parent, text, command, is_primary=True, width=None):
        """Genera un pulsante moderno con customtkinter."""
        bg_col = self.COLOR_PRIMARY if is_primary else self.COLOR_SECONDARY
        fg_col = "#ffffff" if is_primary else self.COLOR_TEXT
        hov_col = self.COLOR_HOVER if is_primary else "#cbd5e1"

        btn = ctk.CTkButton(
            parent,
            text=text,
            command=command,
            fg_color=bg_col,
            hover_color=hov_col,
            text_color=fg_col,
            font=(self.FONT_FAMILY, 10, "bold" if is_primary else "normal"),
            corner_radius=10,
            height=34,
        )
        if width:
            btn.configure(width=width)
        return btn

    def build_ui(self):
        # Frame Principale
        main_frame = ctk.CTkFrame(self.container, fg_color=self.COLOR_BG)
        main_frame.pack(fill="both", expand=True, padx=self.OUTER_PADDING, pady=self.OUTER_PADDING)

        # ─── HEADER BAR MODERNA (Nessun Bordo Border / LabelFrame) ───
        top_panel = ctk.CTkFrame(main_frame, fg_color=self.COLOR_CARD, corner_radius=16, border_width=1, border_color=self.COLOR_SECONDARY)
        top_panel.pack(fill="x", pady=(0, 20))
        
        # Riga Action & Badge
        file_row = ctk.CTkFrame(top_panel, fg_color="transparent")
        file_row.pack(fill="x", padx=20, pady=(20, 15))
        
        self.load_btn = self.create_flat_button(file_row, "📂  Carica Tracciato Salesforce", self.open_file, is_primary=True)
        self.load_btn.pack(side="left")

        self.file_info_var = tk.StringVar(value="Nessun file importato. Pronto per l'analisi dei dati.")
        info_label = ctk.CTkLabel(file_row, textvariable=self.file_info_var, font=(self.FONT_FAMILY, 11, "normal"), text_color="#516173")
        info_label.pack(side="left", padx=20)

        # Riga Input Ricerca Splittata
        search_row = ctk.CTkFrame(top_panel, fg_color="transparent")
        search_row.pack(fill="x", padx=20, pady=(0, 20))
        
        search_lbl = ctk.CTkLabel(search_row, text="FILTRO GLOBALE", font=(self.FONT_FAMILY, 9, "bold"), text_color="#516173")
        search_lbl.pack(side="left", padx=(0, 15))
        
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.on_search_change)
        
        self.search_entry = ctk.CTkEntry(search_row, textvariable=self.search_var, font=(self.FONT_FAMILY, 11))
        self.search_entry.pack(side="left", fill="x", expand=True, ipady=4)
        self.search_entry.configure(state="disabled")
        
        self.clear_search_btn = self.create_flat_button(search_row, "Reset Filtro", lambda: self.search_var.set(""), is_primary=False)
        self.clear_search_btn.pack(side="right", padx=(15, 0))
        self.clear_search_btn.configure(state="disabled", fg_color=self.COLOR_SECONDARY)

        # ─── CONTENITORE SCHEDE (Notebook) ───
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True)

        # SCHEDA 1: Grid View Piatta
        self.tab_table = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_table, text="Vista Tabellare")
        
        self.table_container = ttk.Frame(self.tab_table)
        self.table_container.pack(fill="both", expand=True, pady=(10, 0))

        # Barra Controllo Paginazione Flat Sotto la Tabella
        self.pagination_frame = ctk.CTkFrame(self.tab_table, fg_color="transparent")
        self.pagination_frame.pack(fill="x", side="bottom")
        
        self.btn_first = self.create_flat_button(self.pagination_frame, "⏮  Prima", self.go_first_page, is_primary=False)
        self.btn_first.pack(side="left", padx=2)
        self.btn_prev = self.create_flat_button(self.pagination_frame, "◀  Prec", self.go_prev_page, is_primary=False)
        self.btn_prev.pack(side="left", padx=2)
        
        self.page_num_label = ctk.CTkLabel(self.pagination_frame, text="Pagina 0 di 0", font=(self.FONT_FAMILY, 10, "bold"), text_color=self.COLOR_TEXT)
        self.page_num_label.pack(side="left", padx=20)
        
        self.btn_next = self.create_flat_button(self.pagination_frame, "Succ  ▶", self.go_next_page, is_primary=False)
        self.btn_next.pack(side="left", padx=2)
        self.btn_last = self.create_flat_button(self.pagination_frame, "Ultima  ⏭", self.go_last_page, is_primary=False)
        self.btn_last.pack(side="left", padx=2)
        
        # Righe per pagina combo custom look
        page_size_lbl = ctk.CTkLabel(self.pagination_frame, text="Righe visibili:", font=(self.FONT_FAMILY, 10), text_color="#516173")
        page_size_lbl.pack(side="right", padx=(15, 8))
        self.page_size_combo = ttk.Combobox(self.pagination_frame, textvariable=self.page_size, values=[50, 100, 200, 500], width=6, state="readonly")
        self.page_size_combo.pack(side="right")
        self.page_size_combo.bind("<<ComboboxSelected>>", lambda e: self.reset_pagination_and_render())
        
        self.set_pagination_state(tk.DISABLED, "#f3f4f6")

        # SCHEDA 2: Esploratore Gerarchico ad Albero Moderno
        self.tab_tree = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_tree, text="Esploratore Struttura")
        
        tree_frame = ttk.Frame(self.tab_tree)
        tree_frame.pack(fill="both", expand=True, pady=10)
        
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient="vertical")
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Treeview ad Albero impostato per nascondere i controlli nativi (+) e usare icone/testo personalizzati
        self.hierarchical_tree = ttk.Treeview(
            tree_frame,
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set,
            columns=("Valore"),
            show="tree headings"
        )
        self.hierarchical_tree.heading("#0", text="  Nodo Oggetto / Campo SF", anchor="w")
        self.hierarchical_tree.heading("Valore", text="  Valore Mappato", anchor="w")
        self.hierarchical_tree.column("Valore", width=550, stretch=True)
        
        tree_scroll_y.config(command=self.hierarchical_tree.yview)
        tree_scroll_x.config(command=self.hierarchical_tree.xview)
        tree_scroll_y.pack(side="right", fill="y")
        tree_scroll_x.pack(side="bottom", fill="x")
        self.hierarchical_tree.pack(side="left", fill="both", expand=True)
        
        # Intercettiamo i click sui nodi dell'albero per gestire i Chevron dinamici di apertura/chiusura
        self.hierarchical_tree.bind("<<TreeviewOpen>>", self.on_tree_node_open)
        self.hierarchical_tree.bind("<<TreeviewClose>>", self.on_tree_node_close)

        # SCHEDA 3: Raw Viewer
        self.tab_raw = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_raw, text="Codice Sorgente")
        self.raw_text = ScrolledText(self.tab_raw, wrap="none", font=("Consolas", 10), bg="#ffffff", fg="#10203a", insertbackground="#10203a", borderwidth=0)
        self.raw_text.pack(fill="both", expand=True, pady=10)

    def set_pagination_state(self, state, bg_color):
        """ Cambia lo stato dei pulsanti nativi tk.Button gestendo i colori per il look disabilitato """
        for child in self.pagination_frame.winfo_children():
            if isinstance(child, ctk.CTkButton):
                child.configure(state=state, fg_color=bg_color)
            elif isinstance(child, ttk.Combobox):
                child.configure(state="readonly" if state == tk.NORMAL else "disabled")

    def open_file(self):
        file_path = filedialog.askopenfilename(
            title="Apri sorgente esportata da Salesforce",
            filetypes=[("Dati Salesforce (*.csv, *.json)", "*.csv *.json"), ("CSV Files", "*.csv"), ("JSON Files", "*.json")]
        )
        if not file_path:
            return

        p = Path(file_path)
        try:
            self.search_var.set("") 
            if p.suffix.lower() == ".csv":
                self.load_csv(p)
            elif p.suffix.lower() == ".json":
                self.load_json(p)
                
            self.search_entry.configure(state="normal")
            self.clear_search_btn.configure(state=tk.NORMAL, fg_color=self.COLOR_SECONDARY)
        except Exception as e:
            messagebox.showerror("Errore di Caricamento", f"Impossibile parsare la struttura dati:\n{str(e)}")

    def load_csv(self, path: Path):
        with open(path, "r", encoding="utf-8-sig") as f:
            sample = f.read(8192)
            f.seek(0)
            raw_content = f.read()
            f.seek(0)
            
            dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
            reader = csv.reader(f, dialect)
            self.headers = next(reader, None)
            if not self.headers:
                raise ValueError("Il file CSV selezionato è privo di intestazioni.")
            self.all_rows = list(reader)

        self.filtered_rows = list(self.all_rows)
        self.file_info_var.set(f"CSV  •  {path.name}  •  {len(self.all_rows)} record")
        
        self.set_raw_text(raw_content)
        self.reset_pagination_and_render()
        self.render_hierarchical_tree_from_flat()
        self.notebook.select(0)

    def flatten_json_record(self, y):
        out = {}
        def flatten(x, name=''):
            if type(x) is dict:
                for a in x:
                    flatten(x[a], name + a + '.')
            elif type(x) is list:
                for i, a in enumerate(x):
                    flatten(a, name + str(i) + '.')
            else:
                out[name[:-1]] = x
        flatten(y)
        return out

    def load_json(self, path: Path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            self.raw_json_data = json.loads(content)
            
        if not isinstance(self.raw_json_data, list):
            raise ValueError("La radice del JSON deve essere un array di record.")
            
        self.set_raw_text(json.dumps(self.raw_json_data, indent=2, ensure_ascii=False))
        
        # ─── FLATTENING COMPLETAMENTE FORZATO PER LA VISTA TABELLARE ───
        flattened_records = [self.flatten_json_record(rec) for rec in self.raw_json_data]
        
        union_headers = set()
        for frec in flattened_records:
            union_headers.update(frec.keys())
        self.headers = sorted(list(union_headers))
        
        self.all_rows = []
        for frec in flattened_records:
            row = [str(frec.get(h, '')) for h in self.headers]
            self.all_rows.append(row)
            
        self.filtered_rows = list(self.all_rows)
        self.file_info_var.set(f"JSON Flat Grid  •  {path.name}  •  {len(self.all_rows)} record")
        
        self.reset_pagination_and_render()
        self.render_true_hierarchical_tree()
        self.notebook.select(0)

    def set_raw_text(self, text: str):
        if self.raw_text is None: return
        self.raw_text.configure(state="normal")
        self.raw_text.delete("1.0", "end")
        if len(text) > 2000000:
            self.raw_text.insert("1.0", "File massivo. Ispezione Raw testuale disattivata per mantenere elevate le prestazioni della UI.")
        else:
            self.raw_text.insert("1.0", text)
        self.raw_text.configure(state="disabled")

    def on_search_change(self, *args):
        query = self.search_var.get().strip().lower()
        if not query:
            self.filtered_rows = list(self.all_rows)
        else:
            self.filtered_rows = [
                row for row in self.all_rows 
                if any(query in str(cell).lower() for cell in row)
            ]
        self.reset_pagination_and_render()

    def reset_pagination_and_render(self):
        self.current_page = 1
        size = self.page_size.get()
        self.total_pages = max(1, (len(self.filtered_rows) + size - 1) // size)
        
        if self.all_rows:
            self.set_pagination_state(tk.NORMAL, self.COLOR_SECONDARY)
        self.render_current_page_table()

    def render_current_page_table(self):
        if not self.headers: return
            
        for child in self.table_container.winfo_children():
            child.destroy()
            
        scroll_y = ttk.Scrollbar(self.table_container, orient="vertical")
        scroll_x = ttk.Scrollbar(self.table_container, orient="horizontal")
        
        self.tree_table = ttk.Treeview(
            self.table_container,
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
            columns=self.headers,
            show="headings"
        )
        
        # Righe alternate molto tenui (Zebra Striping in stile Modern Editor)
        self.tree_table.tag_configure('evenrow', background='#f8fbff')
        self.tree_table.tag_configure('oddrow', background='#ffffff')
        
        scroll_y.config(command=self.tree_table.yview)
        scroll_x.config(command=self.tree_table.xview)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.tree_table.pack(side="left", fill="both", expand=True)
        
        for h in self.headers:
            self.tree_table.heading(h, text=f"  {h}", anchor="w")
            col_width = max(140, len(h) * 9)
            self.tree_table.column(h, width=col_width, minwidth=110, stretch=True)
            
        size = self.page_size.get()
        start_idx = (self.current_page - 1) * size
        end_idx = start_idx + size
        page_items = self.filtered_rows[start_idx:end_idx]
        
        for i, row in enumerate(page_items):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            self.tree_table.insert("", "end", values=row, tags=(tag,))
            
        total_rec = len(self.filtered_rows)
        if total_rec == len(self.all_rows):
            self.page_num_label.configure(text=f"Pagina {self.current_page} di {self.total_pages}   ({total_rec} record totali)")
        else:
            self.page_num_label.configure(text=f"Pagina {self.current_page} di {self.total_pages}   (Trovati {total_rec} di {len(self.all_rows)})")

        self.btn_first.configure(state=tk.NORMAL if self.current_page > 1 else tk.DISABLED, fg_color=self.COLOR_SECONDARY if self.current_page > 1 else "#eef3fa")
        self.btn_prev.configure(state=tk.NORMAL if self.current_page > 1 else tk.DISABLED, fg_color=self.COLOR_SECONDARY if self.current_page > 1 else "#eef3fa")
        self.btn_next.configure(state=tk.NORMAL if self.current_page < self.total_pages else tk.DISABLED, fg_color=self.COLOR_SECONDARY if self.current_page < self.total_pages else "#eef3fa")
        self.btn_last.configure(state=tk.NORMAL if self.current_page < self.total_pages else tk.DISABLED, fg_color=self.COLOR_SECONDARY if self.current_page < self.total_pages else "#eef3fa")

    def go_first_page(self):
        self.current_page = 1
        self.render_current_page_table()

    def go_prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.render_current_page_table()

    def go_next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.render_current_page_table()

    def go_last_page(self):
        self.current_page = self.total_pages
        self.render_current_page_table()

    # ─── GESTIONE CHEVRON CUSTOM PER L'ALBERO GERARCHICO ───
    def on_tree_node_open(self, event):
        """ Al click di espansione cambia il prefisso in Chevron Aperto ▼ """
        item_id = self.hierarchical_tree.focus()
        current_text = self.hierarchical_tree.item(item_id, "text")
        if current_text.startswith("► "):
            self.hierarchical_tree.item(item_id, text="▼ " + current_text[2:])

    def on_tree_node_close(self, event):
        """ Al click di collasso cambia il prefisso in Chevron Chiuso ► """
        item_id = self.hierarchical_tree.focus()
        current_text = self.hierarchical_tree.item(item_id, "text")
        if current_text.startswith("▼ "):
            self.hierarchical_tree.item(item_id, text="► " + current_text[2:])

    def render_hierarchical_tree_from_flat(self):
        if self.hierarchical_tree is None: return
        for item in self.hierarchical_tree.get_children():
            self.hierarchical_tree.delete(item)
            
        for i, row in enumerate(self.all_rows[:100]):
            label = f"Record {i+1}"
            if "Name" in self.headers: label += f" - {row[self.headers.index('Name')]}"
            elif "Id" in self.headers: label += f" ({row[self.headers.index('Id')]})"
                
            parent_node = self.hierarchical_tree.insert("", "end", text="► " + label, open=False)
            
            for h_idx, h in enumerate(self.headers):
                val = row[h_idx]
                if not val: continue
                self.hierarchical_tree.insert(parent_node, "end", text="  " + h, values=(val,))

    def render_true_hierarchical_tree(self):
        if self.hierarchical_tree is None or self.raw_json_data is None: return
        for item in self.hierarchical_tree.get_children():
            self.hierarchical_tree.delete(item)
            
        def insert_json_node(parent, key, value):
            if isinstance(value, dict):
                node = self.hierarchical_tree.insert(parent, "end", text=f"► {key}", open=False)
                for k, v in value.items(): insert_json_node(node, k, v)
            elif isinstance(value, list):
                node = self.hierarchical_tree.insert(parent, "end", text=f"► {key} []", open=False)
                for idx, item in enumerate(value): insert_json_node(node, f"[{idx}]", item)
            else:
                self.hierarchical_tree.insert(parent, "end", text="  " + key, values=(str(value),))

        for idx, record in enumerate(self.raw_json_data[:80]):
            label = f"Record [{idx}]"
            if record.get("Name"): label += f" - {record.get('Name')}"
            elif record.get("Id"): label += f" - {record.get('Id')}"
                
            root_node = self.hierarchical_tree.insert("", "end", text="► " + label, open=False)
            for k, v in record.items():
                insert_json_node(root_node, k, v)


if __name__ == "__main__":
    if USE_TTKBOOTSTRAP:
        root = tb.Window(themename="cosmo")
    else:
        root = tk.Tk()
    app = SalesforceDataViewer(root, ui_root=root, embedded=False)
    root.mainloop()