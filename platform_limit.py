import json
import os
import shutil
import subprocess
from pathlib import Path
import customtkinter as ctk
import tkinter as tk


def get_sf_command():
    for candidate in ("sf", "sf.cmd", "sfdx", "sfdx.cmd"):
        if shutil.which(candidate):
            return candidate
    return "sf"


def safe_get(data, *keys, default=None):
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def collect_aliases(alias_data, alias_map, aliases):
    if isinstance(alias_data, dict):
        org_aliases = alias_data.get("orgs", alias_data)
        if isinstance(org_aliases, dict):
            for alias, username in org_aliases.items():
                alias_map[username] = alias
        elif isinstance(org_aliases, list):
            for item in org_aliases:
                if isinstance(item, dict):
                    alias = item.get("alias")
                    username = item.get("username")
                    if alias and username:
                        alias_map[username] = alias
                        aliases.append(f"{alias} ({username})")
                    elif alias:
                        aliases.append(alias)
                    elif username:
                        aliases.append(username)
                elif isinstance(item, str) and item:
                    aliases.append(item)
        return

    if isinstance(alias_data, list):
        for item in alias_data:
            if isinstance(item, dict):
                alias = item.get("alias")
                username = item.get("username")
                if alias and username:
                    alias_map[username] = alias
                    aliases.append(f"{alias} ({username})")
                elif alias:
                    aliases.append(alias)
                elif username:
                    aliases.append(username)
            elif isinstance(item, str) and item:
                aliases.append(item)


class PlatformLimitsTool(ctk.CTkScrollableFrame):
    def __init__(self, master, sf_connection=None, ui_root=None, embedded=False, theme=None):
        super().__init__(master, fg_color="transparent")
        self.sf = sf_connection
        self.theme = theme or {}
        self.root = ui_root or (master.winfo_toplevel() if hasattr(master, "winfo_toplevel") else master)

        self.color_bg = self.theme.get("app_bg", "#f4f6fb")
        self.color_card = self.theme.get("card_bg", "#ffffff")
        self.color_primary = self.theme.get("primary", "#2563eb")
        self.color_secondary = self.theme.get("secondary", "#d9e2f1")
        self.color_text = self.theme.get("text", "#10203a")
        self.color_subtle = self.theme.get("subtle", "#516173")
        self.color_hover = self.theme.get("hover", "#1d4ed8")
        self.font_family = self.theme.get("font_family", "Segoe UI" if os.name == "nt" else "Helvetica")
        
        ctk.CTkLabel(self, text="Salesforce Platform Limits", font=(self.font_family, 20, "bold"), text_color=self.color_text).pack(pady=(10, 8))

        self.toolbar = ctk.CTkFrame(self, fg_color="transparent")
        self.toolbar.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(self.toolbar, text="Org", font=(self.font_family, 10, "bold"), text_color=self.color_subtle).pack(side="left", padx=(0, 8))

        self.org_var = tk.StringVar()
        self.org_combo = ctk.CTkComboBox(self.toolbar, variable=self.org_var, width=320, values=["Caricamento in corso..."])
        self.org_combo.pack(side="left", padx=(0, 8))

        self.refresh_btn = ctk.CTkButton(
            self.toolbar,
            text="Aggiorna",
            command=self.refresh_orgs,
            fg_color=self.color_secondary,
            hover_color="#cbd5e1",
            text_color=self.color_text,
            height=32,
        )
        self.refresh_btn.pack(side="left", padx=(0, 8))

        self.load_btn = ctk.CTkButton(
            self.toolbar,
            text="Carica limiti",
            command=self.load_limits,
            fg_color=self.color_primary,
            hover_color=self.color_hover,
            height=32,
        )
        self.load_btn.pack(side="left")

        self.status_label = ctk.CTkLabel(self, text="Seleziona una org per recuperare i limiti.", font=(self.font_family, 11), text_color=self.color_subtle)
        self.status_label.pack(anchor="w", padx=12, pady=(0, 10))

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=4, pady=4)

        self.refresh_orgs()

        if self.sf is not None:
            self.load_limits()

    def clear_container(self):
        for child in self.container.winfo_children():
            child.destroy()

    def set_status(self, text):
        self.status_label.configure(text=text)

    def refresh_orgs(self):
        self.set_status("Recupero org disponibili...")
        aliases = self._discover_org_aliases()
        if not aliases:
            aliases = ["Nessuna org trovata"]
            self.load_btn.configure(state="disabled")
        else:
            self.load_btn.configure(state="normal")
        self.org_combo.configure(values=aliases)
        self.org_var.set(aliases[0])
        self.set_status(f"Trovate {len(aliases)} org registrate. Seleziona quella da cui leggere i limiti.")

    def _discover_org_aliases(self):
        aliases = []
        alias_map = {}
        for alias_file in (
            Path.home() / ".config" / "sf" / "alias.json",
            Path.home() / ".sfdx" / "alias.json",
        ):
            if alias_file.exists():
                try:
                    with open(alias_file, "r", encoding="utf-8") as handle:
                        alias_data = json.load(handle)
                    collect_aliases(alias_data, alias_map, aliases)
                except Exception:
                    pass

        for folder in (Path.home() / ".config" / "sf", Path.home() / ".sfdx"):
            if folder.exists():
                for entry in folder.glob("*.json"):
                    if entry.name in {"alias.json", "config.json", "state.json", "stash.json"}:
                        continue
                    if entry.stem.startswith("log-"):
                        continue
                    if "@" in entry.stem:
                        alias = alias_map.get(entry.stem)
                        aliases.append(f"{alias} ({entry.stem})" if alias else entry.stem)

        if aliases:
            return sorted(list(set(aliases)))

        try:
            sf_cmd = get_sf_command()
            cmd = f"{sf_cmd} org list --skip-connection-status --json"
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                shell=True,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout)
                result_obj = data.get("result", {})
                for key in ("nonScratchOrgs", "scratchOrgs"):
                    for org in result_obj.get(key, []):
                        alias = org.get("alias")
                        username = org.get("username")
                        if alias and username:
                            aliases.append(f"{alias} ({username})")
                        elif alias:
                            aliases.append(alias)
                        elif username:
                            aliases.append(username)
        except Exception:
            pass

        return sorted(list(set(aliases)))

    def fetch_limits(self):
        try:
            limits = self.sf.limits()
            self.render_limits(limits)
        except Exception as e:
            ctk.CTkLabel(self.container, text=f"Errore: {e}", text_color="#dc2626", font=(self.font_family, 11)).pack()

    def load_limits(self):
        self.clear_container()
        selected = self.org_var.get().strip()
        if not selected or selected == "Nessuna org trovata":
            self.set_status("Nessuna org disponibile da interrogare.")
            return

        org_alias = selected.split(" (")[0].strip()
        self.set_status(f"Recupero limiti per {org_alias}...")

        if self.sf is not None:
            self.fetch_limits()
            self.set_status(f"Limiti caricati da connessione diretta per {org_alias}.")
            return

        try:
            limits = self._fetch_limits_from_cli(org_alias)
            self.render_limits(limits)
            self.set_status(f"Limiti caricati per {org_alias}.")
        except Exception as exc:
            self.clear_container()
            ctk.CTkLabel(self.container, text=f"Impossibile caricare i limiti per {org_alias}: {exc}", text_color="#dc2626", font=(self.font_family, 11), wraplength=700).pack(pady=20)
            self.set_status("Errore nel recupero dei limiti.")

    def _fetch_limits_from_cli(self, org_alias):
        sf_cmd = get_sf_command()
        cmd = f'{sf_cmd} org list limits --target-org "{org_alias}" --json'
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=40,
            shell=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or f"Impossibile leggere l'org {org_alias}")

        payload = json.loads(proc.stdout)
        if not isinstance(payload, dict):
            raise RuntimeError(f"Risposta CLI inattesa: {type(payload).__name__}")

        result = payload.get("result", payload)
        return result

    def render_limits(self, limits):
        self.clear_container()

        if isinstance(limits, list):
            items = []
            for payload in limits:
                if not isinstance(payload, dict):
                    continue

                title = payload.get("name") or payload.get("Name") or payload.get("label") or payload.get("Label")
                remaining = payload.get("remaining") or payload.get("Remaining")
                max_val = payload.get("max") or payload.get("Max")

                if title is None or (remaining is None and max_val is None):
                    continue

                items.append((str(title).replace("_", " "), remaining, max_val))

        elif isinstance(limits, dict):
            items = []
            for title, payload in limits.items():
                if not isinstance(payload, dict):
                    continue

                remaining = payload.get("Remaining")
                max_val = payload.get("Max")
                if remaining is None and max_val is None:
                    continue

                label = title.replace("_", " ")
                items.append((label, remaining, max_val))
        else:
            ctk.CTkLabel(
                self.container,
                text=f"Risposta limiti inattesa: {type(limits).__name__}",
                text_color="#dc2626",
                font=(self.font_family, 11),
            ).pack(pady=20)
            return

        if not items:
            ctk.CTkLabel(
                self.container,
                text="Nessun limite numerico restituito dal comando.",
                text_color=self.color_subtle,
                font=(self.font_family, 11),
            ).pack(pady=20)
            return

        # Renderizza tutte le card in un colpo solo (istantaneo grazie a CTkCanvas)
        for label, remaining, max_val in items:
            self.create_limit_card(label, remaining, max_val)

    def create_limit_card(self, title, remaining, max_val):
        max_val = max_val or 0
        remaining = remaining if remaining is not None else 0
        used = max(max_val - remaining, 0)
        ratio = (used / max_val) if max_val else 0
        percent_val = ratio * 100

        # Card container
        card = ctk.CTkFrame(self.container, fg_color=self.color_card, border_width=1, border_color=self.color_secondary, corner_radius=14)
        card.pack(fill="x", pady=6, padx=6)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=14, pady=14)

        # --- GAUGE GRAFICO NATIVO (Semicerchio) ---
        # Sfrutta il background nativo della card per nascondere la base del cerchio
        gauge_canvas = ctk.CTkCanvas(body, width=120, height=70, bg=self.color_card, highlightthickness=0)
        gauge_canvas.pack(side="left", padx=(0, 16))

        # Colore dinamico basato sulle soglie di utilizzo critiche
        if ratio >= 0.9:
            fill_color = "#dc2626"  # Rosso
        elif ratio >= 0.7:
            fill_color = "#f97316"  # Arancione
        else:
            fill_color = self.color_primary

        # 1. Sfondo grigio dell'arco (scala completa da 0 a 180 gradi)
        gauge_canvas.create_arc(10, 15, 110, 115, start=0, extent=180, outline=self.color_secondary, width=12, style="arc")
        
        # 2. Arco di riempimento effettivo (proporzionale all'uso di Salesforce)
        if ratio > 0:
            extent_angle = -180 * ratio
            gauge_canvas.create_arc(10, 15, 110, 115, start=180, extent=extent_angle, outline=fill_color, width=12, style="arc")

        # 3. Testo con percentuale ricavata al centro del gauge
        gauge_canvas.create_text(60, 55, text=f"{percent_val:.0f}%", font=(self.font_family, 13, "bold"), fill=fill_color)

        # --- BLOCCO INFORMAZIONI TESTUALI ---
        text_col = ctk.CTkFrame(body, fg_color="transparent")
        text_col.pack(side="left", fill="both", expand=True)

        title_label = ctk.CTkLabel(
            text_col,
            text=title,
            font=(self.font_family, 14, "bold"),
            text_color=self.color_text,
            anchor="w",
        )
        title_label.pack(anchor="w", pady=(2, 4))

        remaining_label = ctk.CTkLabel(
            text_col,
            text=f"{remaining:,} rimanenti su {max_val:,}",
            font=(self.font_family, 12),
            text_color=self.color_subtle,
            anchor="w",
        )
        remaining_label.pack(anchor="w")


# Se eseguito direttamente, permette di testare la UI in modalità standalone
if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    root = ctk.CTk()
    root.title("Test Sandbox")
    root.geometry("800x600")
    
    tool = PlatformLimitsTool(root)
    tool.pack(fill="both", expand=True, padx=10, pady=10)
    
    root.mainloop()