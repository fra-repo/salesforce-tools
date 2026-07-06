import tkinter as tk
import customtkinter as ctk

from massive_query_salesforce import ModernMassiveQueryApp
from salesforce_viewer import SalesforceDataViewer
from platform_limit import PlatformLimitsTool

PAGE_INFO = {
    "Home": {
        "title": "Salesforce Operations Suite",
        "subtitle": "Passa tra estrazione massiva e consultazione dati senza aprire finestre separate.",
        "accent": "#2563eb",
    },
    "Massive Query": {
        "title": "Massive Query",
        "subtitle": "Estrai in blocco i record da uno o più oggetti Salesforce.",
        "accent": "#0ea5e9",
    },
    "Data Viewer": {
        "title": "Data Viewer",
        "subtitle": "Esplora e filtra i file CSV o JSON esportati.",
        "accent": "#14b8a6",
    },
    "Limit Monitoring": {
        "title": "Limit Monitoring",
        "subtitle": "Monitora i limiti della piattaforma Salesforce.",
        "accent": "#14b8a6",
    }
}

SUBTOOL_THEME = {
    "app_bg": "#f4f6fb",
    "card_bg": "#ffffff",
    "primary": "#2563eb",
    "secondary": "#d9e2f1",
    "text": "#10203a",
    "subtle": "#516173",
    "hover": "#1d4ed8",
    "outer_padding": 18,
    "shell_border": "#d9e2f1",
    "shell_radius": 22,
    "font_family": "Segoe UI",
}


class SalesforceSuiteApp:
    def __init__(self):
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title(PAGE_INFO["Home"]["title"])
        self.root.geometry("1500x960")
        self.root.minsize(1280, 840)
        self.root.configure(fg_color="#f4f6fb")

        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.current_page = "Home"
        self.nav_buttons = {}

        self._build_sidebar()
        self._build_content()

        self.show_page("Home")
        

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self.root, width=260, corner_radius=0, fg_color="#ffffff",
            border_width=1, border_color="#d9e2f1",
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(4, weight=1)
        self.sidebar.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=22, pady=(24, 18))

        ctk.CTkLabel(header, text="SF PRO SUITE", font=("Segoe UI", 22, "bold"), text_color="#10203a").pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Estrazione e consultazione dati Salesforce.",
            font=("Segoe UI", 12),
            text_color="#516173",
            wraplength=210,
            justify="left",
        ).pack(anchor="w", pady=(6, 0))

        nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_frame.grid(row=1, column=0, sticky="ew", padx=14)
        nav_frame.grid_columnconfigure(0, weight=1)

        for i, page_name in enumerate(PAGE_INFO):
            self.nav_buttons[page_name] = self._make_nav_button(nav_frame, page_name, row=i)

        footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer.grid(row=5, column=0, sticky="sew", padx=18, pady=18)
        ctk.CTkLabel(
            footer, text="v1.0", font=("Segoe UI", 10), text_color="#94a3b8",
        ).pack(anchor="w")

    def _make_nav_button(self, parent, page_name, row):
        button = ctk.CTkButton(
            parent,
            text=page_name,
            command=lambda: self.show_page(page_name),
            height=46,
            corner_radius=12,
            fg_color="transparent",
            hover_color="#edf4ff",
            text_color="#10203a",
            anchor="w",
            font=("Segoe UI", 13, "bold"),
        )
        button.grid(row=row, column=0, sticky="ew", pady=4)
        return button

    # ------------------------------------------------------------------
    # Main content area
    # ------------------------------------------------------------------
    def _build_content(self):
        self.content = ctk.CTkFrame(self.root, corner_radius=0, fg_color="#f4f6fb")
        self.content.grid(row=0, column=1, sticky="nsew", padx=(0, 18), pady=18)
        self.content.grid_rowconfigure(1, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.hero = ctk.CTkFrame(self.content, corner_radius=24, fg_color="#ffffff", border_width=1, border_color="#d9e2f1")
        self.hero.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 16))
        self.hero.grid_columnconfigure(0, weight=1)

        self.hero_title = ctk.CTkLabel(self.hero, text="", font=("Segoe UI", 26, "bold"), text_color="#10203a")
        self.hero_title.grid(row=0, column=0, sticky="w", padx=24, pady=(20, 2))

        self.hero_subtitle = ctk.CTkLabel(self.hero, text="", font=("Segoe UI", 13), text_color="#516173")
        self.hero_subtitle.grid(row=1, column=0, sticky="w", padx=24, pady=(0, 20))

        self.pages = {
            "Home": ctk.CTkFrame(self.content, corner_radius=22, fg_color="#f4f6fb"),
            "Massive Query": ctk.CTkFrame(self.content, corner_radius=22, fg_color="#f4f6fb"),
            "Data Viewer": ctk.CTkFrame(self.content, corner_radius=22, fg_color="#f4f6fb"),
            "Limit Monitoring": ctk.CTkFrame(self.content, corner_radius=22, fg_color="#f4f6fb"),
        }
        for page in self.pages.values():
            page.grid(row=1, column=0, sticky="nsew")

        self.page_shells = {}
        for page_name in ("Massive Query", "Data Viewer", "Limit Monitoring"):
            self.pages[page_name].grid_rowconfigure(0, weight=1)
            self.pages[page_name].grid_columnconfigure(0, weight=1)
            shell = ctk.CTkFrame(
                self.pages[page_name],
                corner_radius=SUBTOOL_THEME["shell_radius"],
                fg_color=SUBTOOL_THEME["card_bg"],
                border_width=1,
                border_color=SUBTOOL_THEME["shell_border"],
            )
            shell.grid(row=0, column=0, sticky="nsew")
            shell.grid_rowconfigure(0, weight=1)
            shell.grid_columnconfigure(0, weight=1)
            self.page_shells[page_name] = shell

        self._build_home(self.pages["Home"])
        self.query_app = ModernMassiveQueryApp(
            self.page_shells["Massive Query"],
            ui_root=self.root,
            embedded=True,
            theme=SUBTOOL_THEME,
        )
        self.viewer_app = SalesforceDataViewer(
            self.page_shells["Data Viewer"],
            ui_root=self.root,
            embedded=True,
            theme=SUBTOOL_THEME,
        )
        self.limit_monitoring_app = PlatformLimitsTool(
            self.page_shells["Limit Monitoring"],
            sf_connection=None,
        )
        self.limit_monitoring_app.pack(fill="both", expand=True, padx=12, pady=12)

    def _build_home(self, home):
        home.grid_columnconfigure(0, weight=1)
        home.grid_rowconfigure(0, weight=1)

        card = ctk.CTkFrame(home, corner_radius=22, fg_color="#ffffff", border_width=1, border_color="#d9e2f1")
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="Cosa vuoi fare?", font=("Segoe UI", 20, "bold"), text_color="#10203a").grid(
            row=0, column=0, sticky="w", padx=24, pady=(24, 16)
        )

        self._home_action(
            card, row=1,
            title="Massive Query",
            desc="Estrai in blocco i record da uno o più oggetti Salesforce.",
            accent="#0ea5e9",
            target="Massive Query",
        )
        self._home_action(
            card, row=2,
            title="Data Viewer",
            desc="Apri e filtra i file CSV o JSON già esportati.",
            accent="#14b8a6",
            target="Data Viewer",
        )
        self._home_action(
            card, row=3,
            title="Limit Monitoring",
            desc="Monitora i limiti della piattaforma Salesforce.",
            accent="#f59e0b",
            target="Limit Monitoring",
        )

    def _home_action(self, parent, row, title, desc, accent, target):
        item = ctk.CTkFrame(parent, corner_radius=16, fg_color="#f8fbff", border_width=1, border_color="#d9e2f1")
        item.grid(row=row, column=0, sticky="ew", padx=24, pady=(0, 16))
        item.grid_columnconfigure(0, weight=1)

        text_col = ctk.CTkFrame(item, fg_color="transparent")
        text_col.grid(row=0, column=0, sticky="w", padx=18, pady=16)
        ctk.CTkLabel(text_col, text=title, font=("Segoe UI", 15, "bold"), text_color="#10203a").pack(anchor="w")
        ctk.CTkLabel(text_col, text=desc, font=("Segoe UI", 12), text_color="#516173").pack(anchor="w", pady=(2, 0))

        ctk.CTkButton(
            item,
            text="Apri",
            width=110,
            height=38,
            corner_radius=12,
            fg_color=accent,
            hover_color=accent,
            command=lambda: self.show_page(target),
        ).grid(row=0, column=1, padx=18, pady=16)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def show_page(self, page_name):
        self.current_page = page_name
        info = PAGE_INFO[page_name]

        for name, page in self.pages.items():
            page.grid_remove()
        self.pages[page_name].grid()

        for name, button in self.nav_buttons.items():
            if name == page_name:
                button.configure(fg_color="#edf4ff", text_color=PAGE_INFO[name]["accent"])
            else:
                button.configure(fg_color="transparent", text_color="#10203a")

        self.hero_title.configure(text=info["title"])
        self.hero_subtitle.configure(text=info["subtitle"])
        self.root.title(f"Salesforce Operations Suite - {info['title']}" if page_name != "Home" else info["title"])

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    SalesforceSuiteApp().run()