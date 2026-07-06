import csv
import json
import os
import re
import shutil
import subprocess
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor
import customtkinter as ctk

try:
    from tkinter.scrolledtext import ScrolledText
except Exception:
    tk.Text

try:
    import openpyxl
    XLSX_AVAILABLE = True
except Exception:
    XLSX_AVAILABLE = False

try:
    import ttkbootstrap as tb
    from ttkbootstrap import ttk as ttk
    from ttkbootstrap.constants import *
    USE_TTKBOOTSTRAP = True
except Exception:
    tb = None
    USE_TTKBOOTSTRAP = False

SAFE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_\.]*$")
SUBQUERY_ITEM_RE = re.compile(
    r"^\(\s*select\s+(?P<fields>.+?)\s+from\s+(?P<relationship>[A-Za-z_][A-Za-z0-9_]*)\b",
    re.IGNORECASE | re.DOTALL
)

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def split_values(raw_text: str):
    tokens = re.split(r"[\n,;\t]+", raw_text)
    res = []
    for t in tokens:
        t_clean = t.strip().strip("'\"")
        if t_clean:
            res.append(t_clean)
    return res

def chunk_list(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def get_sf_command():
    if shutil.which("sf") or shutil.which("sf.cmd"):
        return "sf"
    if shutil.which("sfdx") or shutil.which("sfdx.cmd"):
        return "sfdx"
    return "sf"

def split_top_level_commas(text: str):
    items = []
    current = []
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
            current.append(ch)
            continue
        if ch == ")":
            depth = max(depth - 1, 0)
            current.append(ch)
            continue
        if ch == "," and depth == 0:
            item = "".join(current).strip()
            if item:
                items.append(item)
            current = []
            continue
        current.append(ch)
    tail = "".join(current).strip()
    if tail:
        items.append(tail)
    return items

def clean_sf_metadata(record):
    if isinstance(record, dict):
        new_dict = {}
        for k, v in record.items():
            if k == 'attributes':
                continue
            if isinstance(v, dict) and 'records' in v:
                new_dict[k] = [clean_sf_metadata(r) for r in v['records']]
            else:
                new_dict[k] = clean_sf_metadata(v)
        return new_dict
    elif isinstance(record, list):
        return [clean_sf_metadata(item) for item in record]
    return record

class ModernMassiveQueryApp:
    def __init__(self, master, ui_root=None, embedded=False, theme=None):
        self.container = master
        self.root = ui_root or (master.winfo_toplevel() if hasattr(master, "winfo_toplevel") else master)
        self.embedded = embedded
        self.theme = theme or {}

        if not embedded:
            self.root.title("Salesforce Massive Query Tool v4.4 - UI Refactor")
            self.root.geometry("1200x900")
            self.root.minsize(1050, 800)
            self.color_bg = "#ffffff"
            self.color_card = "#f8f9fa"
            self.color_text = "#24292e"
            self.color_subtle = "#586069"
        else:
            self.color_bg = self.theme.get("app_bg", "#f4f6fb")
            self.color_card = self.theme.get("card_bg", "#ffffff")
            self.color_text = self.theme.get("text", "#10203a")
            self.color_subtle = self.theme.get("subtle", "#516173")

        self.color_primary = self.theme.get("primary", "#2563eb")
        self.color_secondary = self.theme.get("secondary", "#d9e2f1")
        self.color_hover = self.theme.get("hover", "#1d4ed8")
        self.font_family = self.theme.get("font_family", "Segoe UI" if os.name == "nt" else "Helvetica")
        self.outer_padding = self.theme.get("outer_padding", 15 if not embedded else 18)

        try:
            self.root.tk.call("tk", "scaling", 1.08 if os.name == "nt" else 1.0)
        except Exception:
            pass
        
        self.log_lock = threading.Lock()
        self.file_lock = threading.Lock()
        self.data_lock = threading.Lock()
        
        self.abort_event = threading.Event()
        
        self.build_ui()
        threading.Thread(target=self.load_org_aliases_async, daemon=True).start()

    def build_ui(self):
        if not USE_TTKBOOTSTRAP:
            style = ttk.Style()
            style.theme_use("clam")
            style.configure("TFrame", background=self.color_bg)
            style.configure("TLabel", background=self.color_bg, foreground=self.color_text, font=(self.font_family, 10))
            style.configure("TLabelframe", background=self.color_bg, foreground=self.color_text)
            style.configure("TLabelframe.Label", background=self.color_bg, foreground=self.color_text, font=(self.font_family, 10, "bold"))
            style.configure("TEntry", fieldbackground=self.color_card, foreground=self.color_text)
            style.configure("TCombobox", fieldbackground=self.color_card, foreground=self.color_text)
            style.configure("TButton", font=(self.font_family, 10, "bold"), padding=8)
            style.configure("TNotebook", background=self.color_bg, borderwidth=0)
            style.configure("TNotebook.Tab", background=self.color_card, foreground=self.color_text, padding=[18, 8])
            style.map("TNotebook.Tab", background=[("selected", self.color_bg)], foreground=[("selected", self.color_text)])

        main_container = ctk.CTkFrame(self.container, fg_color=self.color_bg)
        main_container.pack(fill="both", expand=True, padx=self.outer_padding, pady=self.outer_padding)

        # ─── TOP BAR (Target Org Selection & Open Folder) ───
        top_bar = ctk.CTkFrame(main_container, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(top_bar, text="Salesforce Org Target:", font=(self.font_family, 10, "bold"), text_color=self.color_text).pack(side="left", padx=(0, 10))
        
        self.alias_var = tk.StringVar()
        self.alias_combo = ctk.CTkComboBox(top_bar, variable=self.alias_var, width=360, font=(self.font_family, 10), values=["Caricamento in corso..."])
        self.alias_combo.pack(side="left", padx=(0, 10))
        self.alias_combo.configure(state="disabled")
        
        self.refresh_btn = ctk.CTkButton(
            top_bar, 
            text="🔄 Aggiorna Lista", 
            command=self.refresh_aliases,
            fg_color=self.color_secondary,
            hover_color="#cbd5e1",
            text_color=self.color_text,
        )
        self.refresh_btn.pack(side="left", padx=(0, 10))

        self.open_folder_btn = ctk.CTkButton(
            top_bar,
            text="📁 Apri Cartella Output",
            command=self.open_output_folder,
            fg_color=self.color_secondary,
            hover_color="#cbd5e1",
            text_color=self.color_text,
        )
        self.open_folder_btn.pack(side="right")

        ctk.CTkFrame(main_container, height=1, fg_color=self.color_secondary).pack(fill="x", pady=(0, 10))

        # ─── BODY FRAME (Split Left / Right) ───
        body_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        body_frame.pack(fill="both", expand=True, pady=(0, 10))

        # COLONNA SINISTRA: Input dati e parametri
        left_col = ctk.CTkFrame(body_frame, fg_color="transparent")
        left_col.pack(side="left", fill="both", expand=True)

        param_card = ctk.CTkFrame(left_col, fg_color=self.color_card, border_width=1, border_color=self.color_secondary, corner_radius=16)
        param_card.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(param_card, text="Impostazioni di Controllo", font=(self.font_family, 12, "bold"), text_color=self.color_text).pack(anchor="w", padx=12, pady=(12, 6))
        
        ctk.CTkLabel(param_card, text="Dimensione dei Chunk (Numero record per query):", font=(self.font_family, 10), text_color=self.color_text).pack(anchor="w", padx=12)
        self.chunk_size_var = tk.IntVar(value=200)
        ctk.CTkEntry(param_card, textvariable=self.chunk_size_var, font=(self.font_family, 10)).pack(fill="x", padx=12, pady=(4, 12))

        values_card = ctk.CTkFrame(left_col, fg_color=self.color_card, border_width=1, border_color=self.color_secondary, corner_radius=16)
        values_card.pack(fill="both", expand=True)
        ctk.CTkLabel(values_card, text="Lista Elementi da Cercare (Bind Values)", font=(self.font_family, 12, "bold"), text_color=self.color_text).pack(anchor="w", padx=12, pady=(12, 6))
        
        ctk.CTkLabel(values_card, text="Incolla qui i valori (separati da virgola, tab o a capo):", font=(self.font_family, 9, "italic"), text_color=self.color_subtle).pack(anchor="w", padx=12, pady=(0, 6))
        self.bind_text = ctk.CTkTextbox(values_card, wrap="none", font=("Consolas", 10), border_width=0)
        self.bind_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # COLONNA DESTRA: Configurazione query ed esportazione
        right_col = ctk.CTkFrame(body_frame, fg_color="transparent")
        right_col.pack(side="right", fill="both", expand=True)

        query_card = ctk.CTkFrame(right_col, fg_color=self.color_card, border_width=1, border_color=self.color_secondary, corner_radius=16)
        query_card.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(query_card, text="Definizione Query SOQL", font=(self.font_family, 12, "bold"), text_color=self.color_text).pack(anchor="w", padx=12, pady=(12, 6))
        
        ctk.CTkLabel(query_card, text="Usa la sintassi ':bind_values' dove inserire i filtri massivi:", font=(self.font_family, 9, "italic"), text_color=self.color_subtle).pack(anchor="w", padx=12, pady=(0, 6))
        self.query_text = ctk.CTkTextbox(query_card, height=120, wrap="word", font=("Consolas", 10), border_width=0)
        self.query_text.pack(fill="x", padx=12)
        self.query_text.insert("1.0", "SELECT Id, Name, Type, (SELECT Id, LastName FROM Contacts), (SELECT Id, Name FROM Opportunities) FROM Account WHERE Id IN :bind_values")

        dest_card = ctk.CTkFrame(right_col, fg_color=self.color_card, border_width=1, border_color=self.color_secondary, corner_radius=16)
        dest_card.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(dest_card, text="Destinazione di Salvataggio", font=(self.font_family, 12, "bold"), text_color=self.color_text).pack(anchor="w", padx=12, pady=(12, 6))
        
        dest_folder_frame = ctk.CTkFrame(dest_card, fg_color="transparent")
        dest_folder_frame.pack(fill="x", padx=12, pady=(0, 12))
        default_path = str(Path("./salesforce_extracts").resolve())
        self.dest_dir_var = tk.StringVar(value=default_path)
        ctk.CTkEntry(dest_folder_frame, textvariable=self.dest_dir_var, font=(self.font_family, 10)).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(dest_folder_frame, text="Sfoglia...", command=self.browse_dest_folder, fg_color=self.color_secondary, hover_color="#cbd5e1", text_color=self.color_text, width=110).pack(side="right")

        options_card = ctk.CTkFrame(right_col, fg_color=self.color_card, border_width=1, border_color=self.color_secondary, corner_radius=16)
        options_card.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(options_card, text="Formati di Esportazione", font=(self.font_family, 12, "bold"), text_color=self.color_text).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 6))
        
        self.out_csv_var = tk.BooleanVar(value=True)
        self.out_json_var = tk.BooleanVar(value=False)
        self.json_flat_var = tk.BooleanVar(value=False)
        self.out_xlsx_var = tk.BooleanVar(value=False)
        
        # Grid layout per i formati di esportazione così da tenerli allineati e puliti
        ctk.CTkCheckBox(options_card, text="CSV", variable=self.out_csv_var).grid(row=1, column=0, sticky="w", padx=12, pady=6)
        
        cb_xlsx = ctk.CTkCheckBox(options_card, text="Excel (.xlsx)", variable=self.out_xlsx_var)
        cb_xlsx.grid(row=2, column=0, sticky="w", padx=12, pady=6)
        if not XLSX_AVAILABLE:
            cb_xlsx.configure(state="disabled")
            self.out_xlsx_var.set(False)
            
        ctk.CTkCheckBox(options_card, text="JSON", variable=self.out_json_var, command=self.toggle_json_options).grid(row=1, column=1, sticky="w", padx=12, pady=6)
        self.cb_json_flat = ctk.CTkCheckBox(options_card, text="Struttura Piatta (Flattened JSON)", variable=self.json_flat_var)
        self.cb_json_flat.grid(row=2, column=1, sticky="w", padx=12, pady=6)
        self.cb_json_flat.configure(state="disabled")

        # Pulsanti di Azione Principali (Avvia / Annulla)
        action_frame = ctk.CTkFrame(right_col, fg_color="transparent")
        action_frame.pack(fill="x", side="bottom")

        self.abort_btn = ctk.CTkButton(
            action_frame,
            text="🛑 ANNULLA",
            command=self.trigger_abort,
            fg_color="#ef4444",
            hover_color="#dc2626",
        )
        self.abort_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))
        self.abort_btn.configure(state="disabled")

        self.run_btn = ctk.CTkButton(
            action_frame, 
            text="🚀 AVVIA ESTRAZIONE", 
            command=self.start_run,
            fg_color=self.color_primary,
            hover_color=self.color_hover,
        )
        self.run_btn.pack(side="right", fill="x", expand=True, padx=(0, 5))

        # ─── BOTTOM CONSOLE (Full Width) ───
        console_card = ctk.CTkFrame(main_container, fg_color=self.color_card, border_width=1, border_color=self.color_secondary, corner_radius=16)
        console_card.pack(fill="both", side="bottom", expand=False)
        ctk.CTkLabel(console_card, text="Console Log & Avanzamento", font=(self.font_family, 12, "bold"), text_color=self.color_text).pack(anchor="w", padx=12, pady=(12, 6))

        progress_frame = ctk.CTkFrame(console_card, fg_color="transparent")
        progress_frame.pack(fill="x", padx=12, pady=(0, 8))

        self.progress_bar = ctk.CTkProgressBar(
            progress_frame, 
            progress_color=self.color_primary,
            fg_color=self.color_secondary,
        )
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.progress_bar.set(0)

        self.eta_label = ctk.CTkLabel(progress_frame, text="ETA: --:--", font=(self.font_family, 9, "bold"), text_color=self.color_text)
        self.eta_label.pack(side="right")

        self.log_text = ctk.CTkTextbox(console_card, wrap="word", font=("Consolas", 9), height=140, border_width=0)
        self.log_text.pack(fill="both", expand=True, padx=12, pady=(0, 5))
        self.log_text.configure(state="disabled")

        log_ops_frame = ctk.CTkFrame(console_card, fg_color="transparent")
        log_ops_frame.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkButton(
            log_ops_frame, 
            text="📋 Copia Log negli Appunti", 
            command=self.copy_logs_to_clipboard,
            fg_color=self.color_secondary,
            hover_color="#cbd5e1",
            text_color=self.color_text,
            height=34,
            width=180,
        ).pack(side="right")

    def toggle_json_options(self):
        if self.out_json_var.get():
            self.cb_json_flat.configure(state="normal")
        else:
            self.cb_json_flat.configure(state="disabled")
            self.json_flat_var.set(False)

    def log_line(self, msg: str):
        with self.log_lock:
            self.root.after(0, self._safe_log, msg)

    def _safe_log(self, msg: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{now_str()}] {msg}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def copy_logs_to_clipboard(self):
        try:
            self.root.clipboard_clear()
            logs = self.log_text.get("1.0", "end-1c")
            self.root.clipboard_append(logs)
            messagebox.showinfo("Copiato", "Tutti i log della console sono stati copiati negli appunti.")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile copiare i log: {str(e)}")

    def refresh_aliases(self):
        self.alias_combo.configure(state="disabled")
        self.alias_combo.configure(values=["Aggiornamento in corso..."])
        self.refresh_btn.configure(state="disabled")
        threading.Thread(target=self.load_org_aliases_async, daemon=True).start()

    def browse_dest_folder(self):
        chosen_dir = filedialog.askdirectory(initialdir=self.dest_dir_var.get())
        if chosen_dir:
            self.dest_dir_var.set(str(Path(chosen_dir).resolve()))

    def open_output_folder(self):
        p = Path(self.dest_dir_var.get())
        p.mkdir(parents=True, exist_ok=True)
        try:
            if hasattr(os, 'startfile'):
                os.startfile(p)
            elif os.name == 'posix':
                subprocess.Popen(['xdg-open', str(p)])
            else:
                subprocess.Popen(['open', str(p)])
        except Exception as e:
            self.log_line(f"Avviso: impossibile aprire la cartella ({str(e)})")

    def load_org_aliases_async(self):
        self.log_line("Recupero alias org in corso (Lettura rapida cache)...")
        aliases = []
        try:
            home = Path.home()
            sf_global_dir = home / ".config" / "sf"
            sfdx_global_dir = home / ".sfdx"
            
            alias_map = {}
            alias_file = sf_global_dir / "alias.json"
            if not alias_file.exists():
                alias_file = sfdx_global_dir / "alias.json"
                
            if alias_file.exists():
                try:
                    with open(alias_file, "r", encoding="utf-8") as f:
                        alias_data = json.load(f)
                        org_aliases = alias_data.get("orgs", alias_data)
                        if isinstance(org_aliases, dict):
                            for alias, username in org_aliases.items():
                                alias_map[username] = alias
                except Exception:
                    pass

            extracted_usernames = set()
            if sf_global_dir.exists():
                for p in sf_global_dir.glob("*.json"):
                    if p.name not in ["alias.json", "config.json", "state.json"]:
                        extracted_usernames.add(p.stem)
                        
            if sfdx_global_dir.exists():
                for p in sfdx_global_dir.glob("*.json"):
                    if p.name not in ["alias.json", "config.json", "state.json", "stash.json"]:
                        if not p.stem.startswith("log-"):
                            extracted_usernames.add(p.stem)

            for username in extracted_usernames:
                if "@" in username:
                    alias = alias_map.get(username)
                    if alias: aliases.append(f"{alias} ({username})")
                    else: aliases.append(username)

            if not aliases:
                self.log_line("Cache locale vuota o non accessibile. Fallback su Salesforce CLI...")
                sf_cmd = get_sf_command()
                cmd = [sf_cmd, "org", "list", "--skip-connection-status", "--json"]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, shell=True)
                raw = proc.stdout.strip()
                if raw:
                    data = json.loads(raw)
                    result_obj = data.get("result", {})
                    for key in ["nonScratchOrgs", "scratchOrgs"]:
                        for org in result_obj.get(key, []):
                            alias = org.get("alias")
                            username = org.get("username")
                            if alias: aliases.append(f"{alias} ({username})")
                            elif username: aliases.append(username)

            aliases = sorted(list(set(aliases)))
            self.log_line(f"Trovate {len(aliases)} org registrate.")
            self.root.after(0, self._update_combo_values, aliases, "readonly")
            
        except Exception as e:
            self.log_line(f"Errore caricamento alias: {str(e)}")
            self.root.after(0, self._update_combo_values, ["Errore caricamento"], "disabled")
        finally:
            self.root.after(0, lambda: self.refresh_btn.configure(state="normal"))

    def _update_combo_values(self, values, state):
        self.alias_combo.configure(values=values)
        self.alias_combo.configure(state=state)
        if values and state == "readonly":
            self.alias_combo.set(values[0])

    def validate_org_alias(self, target: str) -> bool:
        try:
            sf_cmd = get_sf_command()
            cmd = [sf_cmd, "org", "display", "--target-org", target, "--json"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=40, shell=True)
            if proc.returncode != 0: return False
            res = json.loads(proc.stdout)
            return "status" in res and res["status"] == 0
        except Exception: return False

    def trigger_abort(self):
        self.log_line("⚠️ Richiesta di interruzione ricevuta! Arresto in corso...")
        self.abort_event.set()
        self.abort_btn.configure(state="disabled")

    def start_run(self):
        raw_target = self.alias_var.get().strip()
        if not raw_target or raw_target in ["Caricamento in corso...", "CLI Non Trovata", "Errore caricamento"]:
            messagebox.showwarning("Attenzione", "Seleziona un alias Org valido.")
            return
            
        target_org = raw_target.split(" ")[0]
        soql = self.query_text.get("1.0", "end").strip()
        bind_raw = self.bind_text.get("1.0", "end").strip()
        chunk_size = self.chunk_size_var.get()
        dest_dir = self.dest_dir_var.get().strip()
        
        # CONTROLLO CRITICO: Verifica che almeno un formato di output sia selezionato
        if not (self.out_csv_var.get() or self.out_json_var.get() or self.out_xlsx_var.get()):
            messagebox.showwarning("Errore Formato", "Seleziona almeno un formato di esportazione (CSV, JSON o Excel) prima di avviare l'estrazione.")
            return
        
        if not soql or not bind_raw or chunk_size <= 0 or not dest_dir:
            messagebox.showwarning("Attenzione", "Compila tutti i campi obbligatori correttamente.")
            return
            
        values = split_values(bind_raw)
        if not values:
            messagebox.showwarning("Attenzione", "Nessun valore di bind rilevato.")
            return
            
        if ":bind_values" not in soql:
            messagebox.showwarning("Attenzione", "La query SOQL deve contenere il token ':bind_values'.")
            return

        self.run_btn.configure(state="disabled")
        self.abort_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.eta_label.configure(text="ETA: Calcolo...")
        self.abort_event.clear()
        
        threading.Thread(target=self.run_extract, args=(target_org, soql, values, chunk_size, dest_dir), daemon=True).start()

    def parse_fields_and_subqueries(self, soql: str):
        linear = re.sub(r"\s+", " ", soql)
        select_match = re.search(r"\bselect\b(.*)\bfrom\b", linear, re.IGNORECASE)
        if not select_match: raise ValueError("Impossibile isolare la clausola SELECT.")
            
        full_body = select_match.group(1).strip()
        paren_depth = 0
        select_body_chars = []
        for i, char in enumerate(full_body):
            if char == '(': paren_depth += 1
            elif char == ')': paren_depth -= 1
            if paren_depth == 0 and full_body[i:i+5].lower() == " from": break
            select_body_chars.append(char)
            
        select_body = "".join(select_body_chars).strip()
        top_items = split_top_level_commas(select_body)
        
        flat_fields = []
        subqueries = []
        
        for item in top_items:
            item_clean = item.strip()
            if item_clean.startswith("(") and item_clean.endswith(")"):
                sub_match = SUBQUERY_ITEM_RE.match(item_clean)
                if sub_match:
                    rel = sub_match.group("relationship").strip()
                    inner_text = item_clean[1:-1].strip()
                    sub_select = re.search(r"\bselect\b", inner_text, flags=re.IGNORECASE)
                    sub_from = re.search(r"\bfrom\b", inner_text, flags=re.IGNORECASE)
                    
                    if sub_select and sub_from:
                        fields_clause = inner_text[sub_select.end():sub_from.start()].strip()
                        s_fields = [f.strip() for f in split_top_level_commas(fields_clause) if f.strip()]
                    else:
                        s_fields = [f.strip() for f in sub_match.group("fields").strip().split(",") if f.strip()]
                        
                    subqueries.append({"relationship": rel, "fields": s_fields, "raw_item": item_clean})
                else: flat_fields.append(item_clean)
            else: flat_fields.append(item_clean)
        return flat_fields, subqueries

    def run_extract(self, target_org: str, soql: str, values: list, chunk_size: int, dest_dir: str):
        total_records_written = 0
        try:
            if not self.validate_org_alias(target_org):
                messagebox.showerror("Errore Connessione", f"Impossibile comunicare con l'org '{target_org}'.")
                return

            flat_fields, subqueries = self.parse_fields_and_subqueries(soql)
            chunks = list(chunk_list(values, chunk_size))
            
            self.log_line("[Fase 1] Calcolo dinamico delle strutture delle subquery (Pre-flight)...")
            
            max_related_counts = {sq["relationship"]: 0 for sq in subqueries}
            sf_cmd = get_sf_command()
            
            queue = deque([(c, f"C{idx+1}", 0) for idx, c in enumerate(chunks)])
            final_plan = []
            
            while queue and not self.abort_event.is_set():
                c_values, c_id, depth = queue.popleft()
                joined_vals = ",".join([f"'{v.replace(chr(39), chr(92)+chr(39))}'" for v in c_values])
                current_soql = re.sub(r"\(\s*:bind_values\s*\)", f"({joined_vals})", soql)
                current_soql = re.sub(r":bind_values", f"({joined_vals})", current_soql)
                
                if len(current_soql) > 18000 and len(c_values) > 1:
                    half = len(c_values) // 2
                    queue.appendleft((c_values[half:], f"{c_id}b", depth+1))
                    queue.appendleft((c_values[:half], f"{c_id}a", depth+1))
                    continue
                
                final_plan.append((c_values, current_soql, c_id))

            if self.abort_event.is_set():
                self.log_line("🛑 Operazione annullata dall'utente.")
                return

            out_dir = Path(dest_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"extract_{timestamp}"
            
            self.log_line("[Fase 2] Ispezione e strutturazione dei tracciati colonne...")
            
            test_cmd = f'{sf_cmd} data query --query "{final_plan[0][1]}" --target-org {target_org} --json'
            test_proc = subprocess.run(test_cmd, capture_output=True, text=True, shell=True)
            if test_proc.returncode == 0:
                test_res = json.loads(test_proc.stdout).get("result", {}).get("records", [])
                for rec in test_res:
                    for sq in subqueries:
                        rel = sq["relationship"]
                        sub_data = rec.get(rel)
                        if sub_data and isinstance(sub_data, dict):
                            sub_recs = sub_data.get("records", [])
                            if len(sub_recs) > max_related_counts[rel]:
                                max_related_counts[rel] = len(sub_recs)
            
            for sq in subqueries:
                if max_related_counts[sq["relationship"]] == 0:
                    max_related_counts[sq["relationship"]] = 1

            export_fields = [f for f in flat_fields]
            for sq in subqueries:
                rel = sq["relationship"]
                for idx in range(max_related_counts[rel]):
                    for sub_f in sq["fields"]:
                        export_fields.append(f"{rel}_{idx+1}_{sub_f}")

            csv_path = out_dir / f"{base_name}.csv"
            if self.out_csv_var.get():
                with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.DictWriter(f, fieldnames=export_fields)
                    writer.writeheader()

            json_path = out_dir / f"{base_name}.json"
            if self.out_json_var.get():
                with open(json_path, "w", encoding="utf-8") as f:
                    f.write("[\n")

            def extract_flat_value(record_dict, field_path: str):
                parts = field_path.split('.')
                curr = record_dict
                for p in parts:
                    if isinstance(curr, dict):
                        matched_key = next((k for k in curr.keys() if k.lower() == p.lower()), p)
                        curr = curr.get(matched_key)
                    else: return ""
                return "" if curr is None else str(curr)

            self.log_line(f"[Fase 3] Download e Scrittura in Streaming su {out_dir}...")
            
            processed_count = 0
            start_time = time.time()
            
            def process_and_stream_chunk(plan_item):
                nonlocal total_records_written, processed_count
                if self.abort_event.is_set(): return
                
                c_values, current_soql, c_id = plan_item
                cmd = f'{sf_cmd} data query --query "{current_soql}" --target-org {target_org} --json'
                proc = subprocess.run(cmd, capture_output=True, text=True, shell=True)
                
                if proc.returncode != 0:
                    self.log_line(f"❌ Errore su {c_id}: Query fallita.")
                    return
                
                chunk_records = json.loads(proc.stdout).get("result", {}).get("records", [])
                
                local_rows_flat = []
                local_rows_native = []

                if self.out_csv_var.get() or self.out_xlsx_var.get() or (self.out_json_var.get() and self.json_flat_var.get()):
                    for rec in chunk_records:
                        row_data = {}
                        for f in flat_fields:
                            row_data[f] = extract_flat_value(rec, f)
                        for sq in subqueries:
                            rel = sq["relationship"]
                            sub_fields = sq["fields"]
                            m_count = max_related_counts[rel]
                            
                            sub_recs = []
                            rel_key = next((k for k in rec.keys() if k.lower() == rel.lower()), rel)
                            sub_data = rec.get(rel_key)
                            if sub_data and isinstance(sub_data, dict):
                                sub_recs = sub_data.get("records", [])
                                
                            for idx in range(m_count):
                                has_sub_rec = idx < len(sub_recs)
                                sub_rec = sub_recs[idx] if has_sub_rec else {}
                                for sub_f in sub_fields:
                                    col_name = f"{rel}_{idx+1}_{sub_f}"
                                    row_data[col_name] = extract_flat_value(sub_rec, sub_f) if has_sub_rec else ""
                        local_rows_flat.append(row_data)

                if self.out_json_var.get() and not self.json_flat_var.get():
                    for rec in chunk_records:
                        local_rows_native.append(clean_sf_metadata(rec))

                with self.file_lock:
                    if self.abort_event.is_set(): return
                    
                    if self.out_csv_var.get() and local_rows_flat:
                        with open(csv_path, "a", newline="", encoding="utf-8-sig") as f:
                            writer = csv.DictWriter(f, fieldnames=export_fields)
                            for row in local_rows_flat:
                                writer.writerow(row)
                            
                    if self.out_json_var.get():
                        target_rows = local_rows_flat if self.json_flat_var.get() else local_rows_native
                        if target_rows:
                            with open(json_path, "a", encoding="utf-8") as f:
                                for row in target_rows:
                                    prefix = ",\n" if total_records_written > 0 else ""
                                    f.write(prefix + json.dumps(row, ensure_ascii=False, indent=2))
                                    total_records_written += 1

                with self.data_lock:
                    processed_count += 1
                    pct = min(100.0, (processed_count / len(final_plan)) * 100)
                    
                    elapsed = time.time() - start_time
                    avg_time_per_chunk = elapsed / processed_count
                    remaining_chunks = len(final_plan) - processed_count
                    eta_seconds = int(avg_time_per_chunk * remaining_chunks)
                    
                    mins, secs = divmod(eta_seconds, 60)
                    eta_str = f"ETA: {mins:02d}:{secs:02d}" if eta_seconds > 0 else "ETA: 00:00"
                    
                    self.root.after(0, lambda p=pct, e=eta_str: [self.progress_bar.set(p / 100.0), self.eta_label.configure(text=e)])

            with ThreadPoolExecutor(max_workers=4) as executor:
                executor.map(process_and_stream_chunk, final_plan)

            if self.out_json_var.get() and not self.abort_event.is_set():
                with open(json_path, "a", encoding="utf-8") as f: f.write("\n]")

            if self.abort_event.is_set():
                self.log_line("🛑 Estrazione interrotta. I file parziali sono salvati nella cartella destinazione.")
                return

            self.log_line(f"─── Estrazione Completata Con Successo ───")
            self.log_line(f"Record totali scritti: {total_records_written}")
            messagebox.showinfo("Completato", f"Estrazione completata con successo.\nFile salvati in:\n{out_dir}")

        except Exception as e:
            self.log_line(f"ERRORE CRITICO: {str(e)}")
            messagebox.showerror("Errore Estrazione", str(e))
        finally:
            self.root.after(0, lambda: [
                self.run_btn.configure(state="normal"),
                self.abort_btn.configure(state="disabled"),
                self.progress_bar.set(1.0),
                self.eta_label.configure(text="ETA: 00:00")
            ])
    
    def sf_describe_object(self, sobject_name, target_org):
        """Invocazione leggera per popolare l'autocompletamento"""
        sf_cmd = get_sf_command()
        cmd = [sf_cmd, "object", "describe", "--object", sobject_name, "--target-org", target_org, "--json"]
        res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
        if res.returncode == 0:
            return [f.get("name") for f in json.loads(res.stdout).get("result", {}).get("fields", [])]
        return []

if __name__ == "__main__":
    if USE_TTKBOOTSTRAP: root = tb.Window(themename="superhero")
    else: root = tk.Tk()
    app = ModernMassiveQueryApp(root, ui_root=root, embedded=False)
    root.mainloop()
