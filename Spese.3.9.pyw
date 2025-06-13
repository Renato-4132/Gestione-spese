#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
import json
import os
import sys
import psutil
import uuid
import importlib.util
import subprocess
import shutil
import ctypes
import urllib.request
from tkcalendar import Calendar, DateEntry

# URL del file su GitHub (sostituiscilo con il tuo link reale)
GITHUB_FILE_URL = "https://raw.githubusercontent.com/Renato-4132/Gestione-spese/refs/heads/main/Spese.3.9.pyw"

NOME_FILE = "Spese.py"  # Nome del file da salvare

DB_DIR = "db"
DB_FILE = os.path.join(DB_DIR, "spese_db.json")
FILE_DB = os.path.join(DB_DIR, "letture_db.json")

DAYS_THRESHOLD = 25

class GestioneSpese(tk.Tk):
    CATEGORIA_RIMOSSA = "Categoria Rimossa"

    def __init__(self):
        super().__init__()
        self.title("Gestione Spese pro v.3.9.0")
        self.resizable(True, True)

        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR)

        initial_width = 1750
        initial_height = 750
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self._window_geometry = None
        self.load_window_geometry()
        if self._window_geometry:
            self.geometry(self._window_geometry)
        else:
            x = (screen_width // 2) - (initial_width // 2)
            y = (screen_height // 2) - (initial_height // 2)
            self.geometry(f"{initial_width}x{initial_height}+{x}+{y}")

        self.categorie = ["Generica", self.CATEGORIA_RIMOSSA]
        self.categorie_tipi = {"Generica": "Uscita", self.CATEGORIA_RIMOSSA: "Uscita"}
        self.spese = {}
        self.ricorrenze = {}  
        self.modifica_idx = None
        self.stats_refdate = datetime.date.today()
        self.load_db()
        topbar = ttk.Frame(self)
        topbar.pack(fill=tk.X, pady=4)
        self.btn_save = ttk.Button(topbar, text="Salva", command=self.save_db_and_notify)
        self.btn_save.pack(side=tk.RIGHT, padx=6)
        ttk.Button(topbar, text="Importa Database", command=self.import_db).pack(side=tk.RIGHT, padx=6)
        ttk.Button(topbar, text="Esporta Database", command=self.export_db).pack(side=tk.RIGHT, padx=6)
        ttk.Button(topbar, text="Reset Database", command=self.show_reset_dialog).pack(side=tk.RIGHT, padx=6)
        ttk.Button(topbar, text="Info", command=self.show_info_app).pack(side=tk.LEFT, padx=6)    
        ttk.Button(topbar, text="Saldo Conto", command=self.open_saldo_conto).pack(side=tk.LEFT, padx=6)  
        ttk.Button(topbar, text="Confronta", command=self.open_compare_window).pack(side=tk.LEFT, padx=6) 
        ttk.Button(topbar, text="Utenze", command=self.utenze).pack(side=tk.LEFT, padx=6) 
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        cal_frame = ttk.Frame(main_frame)
        cal_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        today = datetime.date.today()
        
        self.cal = Calendar(
            cal_frame,
            selectmode='day',
            year=today.year,
            month=today.month,
            day=today.day,
            date_pattern="dd-mm-yyyy",
            locale='it_IT'
        )
        
        self.cal.pack(pady=4)
        self.cal.bind("<<CalendarSelected>>", lambda e: self.update_stats())

        btn_today = ttk.Button(cal_frame, text="Reset Calendario - Data odierna", command=self.goto_today)
        btn_today.pack(pady=(6, 0), fill=tk.X)
        btn_estratto = ttk.Button(cal_frame, text="Estratto Dati - Carica Mesi/Anni per statistiche", command=self.apply_estratto)
        btn_estratto.pack(pady=(6, 0), fill=tk.X)
        select_frame = ttk.Frame(cal_frame)
        select_frame.pack(pady=(6, 0), fill=tk.X)
        self.estratto_month_var = tk.StringVar(value=f"{today.month:02d}")
        current_year = today.year
        years = [str(y) for y in range(current_year - 10, current_year + 11)]
        months = [
            "01 - Gennaio", "02 - Febbraio", "03 - Marzo", "04 - Aprile", "05 - Maggio", "06 - Giugno",
            "07 - Luglio", "08 - Agosto", "09 - Settembre", "10 - Ottobre", "11 - Novembre", "12 - Dicembre"
        ]
        ttk.Label(select_frame, text="Mese:", font=("Arial", 9)).grid(row=0, column=0, sticky="e", padx=2, pady=2)
        self.cb_estratto_month = ttk.Combobox(select_frame, values=months, width=14, font=("Arial", 9),
                                              textvariable=self.estratto_month_var, state="readonly")
        self.cb_estratto_month.grid(row=0, column=1, sticky="w", padx=2, pady=2)
        self.cb_estratto_month.current(today.month-1)
        ttk.Label(select_frame, text="Anno:", font=("Arial", 9)).grid(row=1, column=0, sticky="e", padx=2, pady=2)
        self.estratto_year_var = tk.StringVar(value=str(today.year))
        self.cb_estratto_year = ttk.Combobox(select_frame, values=years, width=8, font=("Arial", 9),
                                             textvariable=self.estratto_year_var, state="readonly")
        self.cb_estratto_year.grid(row=1, column=1, sticky="w", padx=2, pady=2)
        self.totalizzatore_frame = ttk.LabelFrame(cal_frame, text="Totalizzatore anno in corso")
        self.totalizzatore_frame.pack(fill=tk.X, pady=(12,2), padx=2)
        self.totalizzatore_entrate_label = ttk.Label(self.totalizzatore_frame, text="Totale Entrate: 0.00 €", foreground="green", font=("Arial", 10, "bold"))
        self.totalizzatore_entrate_label.pack(anchor="w", padx=6, pady=(2,0))
        self.totalizzatore_uscite_label = ttk.Label(self.totalizzatore_frame, text="Totale Uscite: 0.00 €", foreground="red", font=("Arial", 10, "bold"))
        self.totalizzatore_uscite_label.pack(anchor="w", padx=6, pady=(2,0))
        self.totalizzatore_diff_label = ttk.Label(self.totalizzatore_frame, text="Differenza: 0.00 €", foreground="blue", font=("Arial", 10, "bold"))
        self.totalizzatore_diff_label.pack(anchor="w", padx=6, pady=(2,4))
        self.totalizzatore_mese_frame = ttk.LabelFrame(cal_frame, text="Totalizzatore mese corrente")
        self.totalizzatore_mese_frame.pack(fill=tk.X, pady=(3,2), padx=2)
        self.totalizzatore_mese_entrate_label = ttk.Label(self.totalizzatore_mese_frame, text="Totale Entrate mese: 0.00 €", foreground="green", font=("Arial", 10, "bold"))
        self.totalizzatore_mese_entrate_label.pack(anchor="w", padx=6, pady=(2,0))
        self.totalizzatore_mese_uscite_label = ttk.Label(self.totalizzatore_mese_frame, text="Totale Uscite mese: 0.00 €", foreground="red", font=("Arial", 10, "bold"))
        self.totalizzatore_mese_uscite_label.pack(anchor="w", padx=6, pady=(2,0))
        self.totalizzatore_mese_diff_label = ttk.Label(self.totalizzatore_mese_frame, text="Differenza mese: 0.00 €", foreground="blue", font=("Arial", 10, "bold"))
        self.totalizzatore_mese_diff_label.pack(anchor="w", padx=6, pady=(2,4))
        self.spese_mese_frame = ttk.LabelFrame(cal_frame, text="Spese mese corrente per data")
        self.spese_mese_frame.pack(fill=tk.BOTH, expand=False, padx=2, pady=(2,4))
        self.spese_mese_tree = ttk.Treeview(
            self.spese_mese_frame,
            columns=("Data", "Categoria", "Descrizione", "Importo", "Tipo"),
            show="headings",
            height=10  # <-- Modificato qui da 10 a 5
        )
        self.spese_mese_tree.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.spese_mese_tree.heading("Data", text="Data")
        self.spese_mese_tree.heading("Categoria", text="Categoria")
        self.spese_mese_tree.heading("Descrizione", text="Descrizione")
        self.spese_mese_tree.heading("Importo", text="Importo (€)")
        self.spese_mese_tree.heading("Tipo", text="Tipo")
        self.spese_mese_tree.column("Data", width=90, anchor="center")
        self.spese_mese_tree.column("Categoria", width=90, anchor="center")
        self.spese_mese_tree.column("Descrizione", width=120, anchor="w")
        self.spese_mese_tree.column("Importo", width=80, anchor="e")
        self.spese_mese_tree.column("Tipo", width=60, anchor="center")
        self.spese_mese_tree.tag_configure('entrata', foreground='green')
        self.spese_mese_tree.tag_configure('uscita', foreground='red')
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        stat_frame = ttk.LabelFrame(right_frame, text="Statistiche Spese")
        stat_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        mode_frame = ttk.Frame(stat_frame)
        mode_frame.pack(anchor="w", padx=6, pady=(4,0), fill=tk.X)
        self.stats_mode = tk.StringVar(value="giorno")
        ttk.Button(mode_frame, text="Giorno", command=lambda: self.set_stats_mode("giorno"), width=6).pack(side=tk.LEFT, padx=1)
        ttk.Button(mode_frame, text="Mese", command=lambda: self.set_stats_mode("mese"), width=6).pack(side=tk.LEFT, padx=1)
        ttk.Button(mode_frame, text="Anno", command=lambda: self.set_stats_mode("anno"), width=6).pack(side=tk.LEFT, padx=1)
        ttk.Button(mode_frame, text="Totali", command=lambda: self.set_stats_mode("totali"), width=6).pack(side=tk.LEFT, padx=1)
        mode_frame_right = ttk.Frame(mode_frame)
        mode_frame_right.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        ttk.Button(mode_frame_right, text="Esporta giorno da Calendario", command=self.export_giorno_forzato).pack(side=tk.RIGHT, padx=1)
        ttk.Button(mode_frame_right, text="Esporta mese da estratto", command=self.export_month_detail).pack(side=tk.RIGHT, padx=1)
        ttk.Button(mode_frame_right, text="Esporta anno da estratto", command=self.export_anno_dettagliato).pack(side=tk.RIGHT, padx=1)
        ttk.Button(mode_frame, text="Categoria", command=self.open_analisi_categoria, width=10).pack(side=tk.LEFT, padx=2)
        self.stats_label = ttk.Label(stat_frame, text="")
        self.stats_label.pack(anchor="w", padx=6, pady=(2,0))
        self.totali_label = ttk.Label(stat_frame, text="", font=("Arial", 11, "bold"))
        self.totali_label.pack(anchor="w", padx=6, pady=(2,0))
        self.stats_table = ttk.Treeview(stat_frame, columns=("A","B","C","D","E","F"), show="headings")
        self.stats_table.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.stats_table.column("A", width=10, anchor="center")      # Data o Categoria
        self.stats_table.column("B", width=15, anchor="center")      # Categoria o Totale Categoria (€)
        self.stats_table.column("C", width=20, anchor="w")           # Descrizione o Tipo
        self.stats_table.column("D", width=10, anchor="e")           # Importo (€)
        self.stats_table.column("E", width=10, anchor="center")      # Tipo
        self.stats_table.column("F", width=10, anchor="center")      # Modifica
        self.set_stats_mode("giorno")
        self.stats_table.tag_configure("uscita", foreground="red")
        self.stats_table.tag_configure("entrata", foreground="green")
        self.stats_table.bind('<ButtonRelease-1>', self.on_table_click)
        aggiungi_cat_frame = ttk.LabelFrame(right_frame, text="Aggiungi/Modifica Categoria")
        aggiungi_cat_frame.pack(fill=tk.X, padx=2, pady=(8, 2))
        self.nuova_cat = tk.StringVar()
        ttk.Label(aggiungi_cat_frame, text="Nome categoria:").grid(row=0, column=0, sticky="e", padx=4, pady=6)
        self.entry_nuova_cat = ttk.Entry(aggiungi_cat_frame, textvariable=self.nuova_cat, width=20)
        self.entry_nuova_cat.grid(row=0, column=1, sticky="w", padx=2, pady=6)
        ttk.Button(aggiungi_cat_frame, text="Aggiungi Categoria", command=self.add_categoria).grid(row=0, column=2, padx=8, pady=6)
        ttk.Label(aggiungi_cat_frame, text="Seleziona categoria:").grid(row=1, column=0, sticky="e", padx=4, pady=6)
        self.cat_mod_sel = tk.StringVar(value=self.categorie[0])
        self.cat_mod_menu = ttk.Combobox(aggiungi_cat_frame, textvariable=self.cat_mod_sel, values=self.categorie, state="readonly", width=20)
        self.cat_mod_menu.grid(row=1, column=1, sticky="w", padx=2, pady=6)
        self.cat_mod_menu.bind("<<ComboboxSelected>>", lambda e: self.on_categoria_modifica_changed())
        self.btn_modifica_categoria = ttk.Button(aggiungi_cat_frame, text="Modifica Nome", command=self.modifica_categoria)
        self.btn_modifica_categoria.grid(row=1, column=2, padx=4, pady=6)
        self.btn_cancella_categoria = ttk.Button(aggiungi_cat_frame, text="Cancella Categoria", command=self.cancella_categoria)
        self.btn_cancella_categoria.grid(row=1, column=3, padx=8, pady=6)
        form_frame = ttk.LabelFrame(right_frame, text="Inserisci/Modifica Spesa/Entrata")
        form_frame.pack(fill=tk.X, padx=2, pady=(8, 8))
        row = 0
        #ttk.Label(form_frame, text="Data spesa:").grid(row=row, column=0, sticky="e")
        ttk.Label(form_frame, text="Data spesa:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="e")
        self.data_spesa_var = tk.StringVar(value=today.strftime("%d-%m-%Y"))
        self.data_spesa_entry = DateEntry(form_frame, width=10, date_pattern='dd-mm-yyyy',
                                          textvariable=self.data_spesa_var, locale='it_IT')
        self.data_spesa_entry.grid(row=row, column=1, sticky="w")
        self.btn_reset_data_spesa = ttk.Button(form_frame, text="Reset", width=8, command=self.reset_data_spesa)
        self.btn_reset_data_spesa.grid(row=row, column=2, sticky="w", padx=4)
        row += 1
        self.cat_sel = tk.StringVar(value=self.categorie[0])
        ttk.Label(form_frame, text="Seleziona categoria:").grid(row=row, column=0, sticky="e")
        self.cat_menu = ttk.Combobox(form_frame, textvariable=self.cat_sel, values=self.categorie, state="readonly", width=25)
        self.cat_menu.grid(row=row, column=1, sticky="w")
        self.cat_menu.bind("<<ComboboxSelected>>", self.on_categoria_changed)
        row += 1
        ttk.Label(form_frame, text="Descrizione:").grid(row=row, column=0, sticky="e")
        self.desc_entry = ttk.Entry(form_frame, width=40)
        self.desc_entry.grid(row=row, column=1, sticky="w")
        row += 1
        ttk.Label(form_frame, text="Importo (€):").grid(row=row, column=0, sticky="e")
        importo_frame = ttk.Frame(form_frame)
        importo_frame.grid(row=row, column=1, sticky="w")
        self.imp_entry = ttk.Entry(importo_frame, width=12)
        self.imp_entry.pack(side=tk.LEFT)
        style = ttk.Style()
        style.configure('GreenOutline.TButton', foreground='green', borderwidth=2, relief='solid')
        style.map('GreenOutline.TButton',
            bordercolor=[('!disabled', 'green')], foreground=[('!disabled', 'green')]
        )
        style.configure('RedOutline.TButton', foreground='red', borderwidth=2, relief='solid')
        style.map('RedOutline.TButton',
            bordercolor=[('!disabled', 'red')], foreground=[('!disabled', 'red')]
        )
        cat_default_type = self.categorie_tipi.get(self.cat_sel.get(), "Uscita")
        self.tipo_spesa_var = tk.StringVar(value=cat_default_type)
        btn_style = 'GreenOutline.TButton' if self.tipo_spesa_var.get() == "Entrata" else 'RedOutline.TButton'
        self.btn_tipo_spesa = ttk.Button(
            importo_frame,
            text=self.tipo_spesa_var.get(),
            width=10,
            command=self.toggle_tipo_spesa,
            style=btn_style
        )
        self.btn_tipo_spesa.pack(side=tk.LEFT, padx=8)
        row += 1
        ric_frame = ttk.LabelFrame(form_frame, text="Ripeti Spesa/Entrata")
        ric_frame.grid(row=row, column=0, columnspan=4, sticky="w", padx=2, pady=(7, 2))
        self.ricorrenza_tipo = tk.StringVar(value="Nessuna")
        self.ricorrenza_n = tk.IntVar(value=1)
        self.ricorrenza_data_inizio = tk.StringVar(value=self.data_spesa_var.get())
        ttk.Label(ric_frame, text="Tipo ricorrenza:").grid(row=0, column=0, sticky="e", padx=2, pady=2)
        self.ric_combo = ttk.Combobox(ric_frame, values=["Nessuna", "Ogni giorno", "Ogni mese", "Ogni anno"], width=16, state="readonly", textvariable=self.ricorrenza_tipo)
        self.ric_combo.grid(row=0, column=1, sticky="w", padx=2, pady=2)
        ttk.Label(ric_frame, text="Ripeti per n volte:").grid(row=0, column=2, sticky="e", padx=2, pady=2)
        self.ric_n_entry = ttk.Entry(ric_frame, width=4, textvariable=self.ricorrenza_n)
        self.ric_n_entry.grid(row=0, column=3, sticky="w", padx=2, pady=2)
        ttk.Label(ric_frame, text="Data inizio:").grid(row=0, column=4, sticky="e", padx=2, pady=2)
        self.ric_data_inizio = DateEntry(ric_frame, width=12, date_pattern='dd-mm-yyyy', textvariable=self.ricorrenza_data_inizio, locale='it_IT')
        self.ric_data_inizio.grid(row=0, column=5, sticky="w", padx=2, pady=2)
        self.btn_add_ricorrenza = ttk.Button(ric_frame, text="Aggiungi ricorrenza", command=self.add_ricorrenza)
        self.btn_add_ricorrenza.grid(row=0, column=6, padx=10, pady=2)
        self.btn_cancella_ricorrenza = ttk.Button(ric_frame, text="Cancella ricorrenza", command=self.del_ricorrenza)
        self.btn_cancella_ricorrenza.grid(row=0, column=7, padx=5, pady=2)
        self.btn_aggiungi = ttk.Button(form_frame, text="Aggiungi Spesa/Entrata", command=self.add_spesa)
        self.btn_aggiungi.grid(row=row+1, column=1, sticky="w", pady=4)
        self.btn_modifica = ttk.Button(form_frame, text="Salva Modifica", command=self.salva_modifica, state=tk.DISABLED)
        self.btn_modifica.grid(row=row+1, column=2, sticky="w", padx=8)
        self.btn_cancella = ttk.Button(form_frame, text="Cancella", command=self.cancella_voce, state=tk.DISABLED)
        self.btn_cancella.grid(row=row+1, column=3, sticky="w", padx=8)
        self.update_totalizzatore_anno_corrente()
        self.update_totalizzatore_mese_corrente()
        self.update_spese_mese_corrente()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
            
    def load_window_geometry(self):
        if not os.path.exists(DB_FILE):
            return
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._window_geometry = data.get("_window_geometry", None)
        except Exception:
            self._window_geometry = None

    def save_window_geometry(self):
        geometry = self.geometry()
        self._window_geometry = geometry
        try:
            data = {}
            if os.path.exists(DB_FILE):
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data["_window_geometry"] = geometry
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("Errore salvataggio geometria finestra:", e)

    def _on_close(self):
        self.save_window_geometry()
        self.save_db()
        self.destroy()

    def load_db(self):
        if not os.path.exists(DB_FILE):
            return
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.categorie = data.get("categorie", ["Generica"])
            self.categorie_tipi = data.get("categorie_tipi", {"Generica": "Uscita"})
            self.spese = {}
            for obj in data.get("spese", []):
                d = datetime.datetime.strptime(obj["date"], "%d-%m-%Y").date()
                entries = []
                for e in obj.get("entries", []):
                    if "id_ricorrenza" in e:
                        entries.append((e["categoria"], e["descrizione"], float(e["importo"]), e["tipo"], e["id_ricorrenza"]))
                    else:
                        entries.append((e["categoria"], e["descrizione"], float(e["importo"]), e["tipo"]))
                self.spese[d] = entries
            self.ricorrenze = data.get("ricorrenze", {})
            self._window_geometry = data.get("_window_geometry", None)
        except Exception as e:
            print("Errore caricamento DB:", e)
            self.categorie = ["Generica"]
            self.categorie_tipi = {"Generica": "Uscita"}
            self.spese = {}
            self.ricorrenze = {}
            self._window_geometry = None

    def save_db(self):
        data = {
            "categorie": self.categorie,
            "categorie_tipi": self.categorie_tipi,
            "spese": [
                {"date": d.strftime("%d-%m-%Y"), "entries": [
                    {"categoria": c, "descrizione": desc, "importo": imp, "tipo": tipo, **({"id_ricorrenza": rid} if len(entry) == 5 else {})}
                        for entry in sp
                        for c, desc, imp, tipo, *rest in [entry]
                        for rid in [rest[0] if rest else None]
                ]} for d, sp in self.spese.items()
            ],
            "ricorrenze": self.ricorrenze
        }
        if self._window_geometry is not None:
            data["_window_geometry"] = self._window_geometry
        else:
            try:
                data["_window_geometry"] = self.geometry()
            except Exception:
                pass
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def toggle_tipo_spesa(self):
        v = self.tipo_spesa_var.get()
        nuovo = "Entrata" if v == "Uscita" else "Uscita"
        self.tipo_spesa_var.set(nuovo)
        self.btn_tipo_spesa.config(text=nuovo)
        new_style = 'GreenOutline.TButton' if nuovo == "Entrata" else 'RedOutline.TButton'
        self.btn_tipo_spesa.config(style=new_style)

    def on_categoria_changed(self, event=None):
        cat = self.cat_sel.get()
        tipo_cat = self.categorie_tipi.get(cat, "Uscita")
        self.tipo_spesa_var.set(tipo_cat)
        self.btn_tipo_spesa.config(text=tipo_cat)
        new_style = 'GreenOutline.TButton' if tipo_cat == "Entrata" else 'RedOutline.TButton'
        self.btn_tipo_spesa.config(style=new_style)

    def on_categoria_modifica_changed(self, event=None):
        pass

    def add_categoria(self):
        nome = self.nuova_cat.get().strip()
        tipo = "Uscita"
        if not nome or nome in self.categorie or nome == self.CATEGORIA_RIMOSSA:
            self.show_custom_warning("Attenzione", "Nome categoria vuoto, già esistente o riservato.")
            return
        self.categorie.append(nome)
        self.categorie_tipi[nome] = tipo
        self.cat_menu["values"] = self.categorie
        self.cat_mod_menu["values"] = self.categorie
        self.nuova_cat.set("")
        self.cat_sel.set(nome)
        self.cat_mod_sel.set(nome)
        self.on_categoria_changed()

    def modifica_categoria(self):
        old_nome = self.cat_mod_sel.get()
        if old_nome == "Generica":
         self.show_custom_warning("Attenzione", "La categoria 'Generica' non può essere rinominata.")
         return
        new_nome = self.nuova_cat.get().strip()
        if not new_nome:
            self.show_custom_warning("Attenzione", "Inserisci il nuovo nome della categoria.")
            return
        if new_nome == old_nome:
            self.show_custom_info("Info", "Il nuovo nome è uguale a quello attuale.")
            return
        if new_nome in self.categorie:
            self.show_custom_warning("Attenzione", "Esiste già una categoria con questo nome.")
            return
        idx = self.categorie.index(old_nome)
        self.categorie[idx] = new_nome
        self.categorie_tipi[new_nome] = self.categorie_tipi.pop(old_nome)
        for d in self.spese:
            new_entries = []
            for entry in self.spese[d]:
                if entry[0] == old_nome:
                    entry = (new_nome,) + entry[1:]
                new_entries.append(entry)
            self.spese[d] = new_entries
        self.cat_menu["values"] = self.categorie
        self.cat_mod_menu["values"] = self.categorie
        self.cat_sel.set(new_nome)
        self.cat_mod_sel.set(new_nome)
        self.nuova_cat.set("")
        self.save_db()
        self.update_stats()
        self.update_totalizzatore_anno_corrente()
        self.update_totalizzatore_mese_corrente()
        self.update_spese_mese_corrente()
        self.show_custom_info("Attenzione", f"Categoria '{old_nome}' rinominata in '{new_nome}'.")

    def conferma_cancella_categoria(self, cat):
        popup = tk.Toplevel(self)
        popup.title("Conferma eliminazione")
        popup.resizable(False, False)
        width, height = 320, 120
        popup.withdraw()
        popup.update_idletasks()
        parent_x = self.winfo_rootx()
        parent_y = self.winfo_rooty()
        parent_w = self.winfo_width()
        parent_h = self.winfo_height()
        x = parent_x + (parent_w // 2) - (width // 2)
        y = parent_y + (parent_h // 2) - (height // 2)
        popup.geometry(f"{width}x{height}+{x}+{y}")
        popup.deiconify()
        popup.grab_set()
        label = tk.Label(
            popup,
            text=f"Vuoi davvero cancellare la categoria '{cat}'?\nLe spese rimarranno ma saranno\nrinominate come '{self.CATEGORIA_RIMOSSA}'.",
            font=("Arial", 9),
            justify="center",
            wraplength=280
        )
        label.pack(pady=8, padx=10)
        frame = tk.Frame(popup)
        frame.pack(pady=4)
        result = {"ok": False}
        def do_ok():
            result["ok"] = True
            popup.destroy()
        def do_cancel():
            popup.destroy()
        b1 = tk.Button(frame, text="Elimina", font=("Arial", 9), width=8, command=do_ok)
        b2 = tk.Button(frame, text="Annulla", font=("Arial", 9), width=8, command=do_cancel)
        b1.pack(side="left", padx=8)
        b2.pack(side="right", padx=8)
        popup.wait_window()
        return result["ok"]

    def cancella_categoria(self):
        cat = self.cat_mod_sel.get()
        if cat in ("Generica", self.CATEGORIA_RIMOSSA):
            self.show_custom_warning("Attenzione", f"Non puoi cancellare la categoria '{cat}'.")
            return
        if not self.conferma_cancella_categoria(cat):
            return
        if cat in self.categorie:
            self.categorie.remove(cat)
        if cat in self.categorie_tipi:
            del self.categorie_tipi[cat]
        for giorno in self.spese:
            nuove_spese = []
            for voce in self.spese[giorno]:
                voce_cat = voce[0]
                if voce_cat == cat:
                    nuove_spese.append((self.CATEGORIA_RIMOSSA,) + voce[1:])
                else:
                    nuove_spese.append(voce)
            self.spese[giorno] = nuove_spese
        self.cat_menu["values"] = self.categorie
        self.cat_mod_menu["values"] = self.categorie
        self.cat_sel.set(self.categorie[0])
        self.cat_mod_sel.set(self.categorie[0])
        self.save_db()
        self.update_stats()
        self.update_totalizzatore_anno_corrente()
        self.update_totalizzatore_mese_corrente()
        self.update_spese_mese_corrente()
        self.on_categoria_changed()

    def show_custom_warning(self, title, message):
        self._show_custom_message(title, message, "yellow", "black", "warning")

    def show_custom_info(self, title, message):
        self._show_custom_message(title, message, "lightblue", "black", "info")

    def show_custom_askyesno(self, title, message):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.geometry("+%d+%d" % (
            self.winfo_rootx() + 150,
            self.winfo_rooty() + 150
        ))
        label = tk.Label(dialog, text=message, font=("Arial", 9), justify="left", padx=16, pady=12)
        label.pack()
        btns = tk.Frame(dialog)
        btns.pack(pady=(0,10))
        result = {"value": False}
        def yes():
            result["value"] = True
            dialog.destroy()
        def no():
            result["value"] = False
            dialog.destroy()
        b1 = tk.Button(btns, text="Sì", width=8, command=yes)
        b2 = tk.Button(btns, text="No", width=8, command=no)
        b1.grid(row=0, column=0, padx=8)
        b2.grid(row=0, column=1, padx=8)
        dialog.wait_window()
        return result["value"]


    def _show_custom_message(self, title, message, bg, fg, icon=None):
        dialog = tk.Toplevel(self)
        dialog.withdraw()  
        dialog.title(title)
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        frame = tk.Frame(dialog, bg=bg)
        frame.pack(fill="both", expand=True)
        frame.pack_propagate(False) 
        label = tk.Label(frame, text=message, font=("Arial", 10), bg=bg, fg=fg, justify="left", padx=16, pady=12)
        label.pack()
        btn = tk.Button(frame, text="OK", width=10, command=dialog.destroy)
        btn.pack(pady=(0, 10))
        btn.focus_set()
        dialog.bind("<Return>", lambda e: dialog.destroy())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        dialog.update_idletasks()  
        width = label.winfo_reqwidth() + 40  
        height = label.winfo_reqheight() + btn.winfo_reqheight() + 40
        x = (dialog.winfo_screenwidth() - width) // 2
        y = (dialog.winfo_screenheight() - height) // 2
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        dialog.deiconify()  
        dialog.wait_window()  
 
    def reset_data_spesa(self):
        today = datetime.date.today()
        self.data_spesa_var.set(today.strftime("%d-%m-%Y"))

    def add_ricorrenza(self):
        ric_type = self.ricorrenza_tipo.get()
        if ric_type == "Nessuna":
            self.add_spesa()
            return
        try:
            n = int(self.ricorrenza_n.get())
            if n <= 0:
                raise ValueError
        except Exception:
            self.show_custom_warning("Errore", "Numero ripetizioni non valido")
            return
        try:
            data_inizio = datetime.datetime.strptime(self.ricorrenza_data_inizio.get(), "%d-%m-%Y").date()
        except Exception:
            self.show_custom_warning("Errore", "Data inizio ricorrenza non valida")
            return
        cat = self.cat_sel.get()
        desc = self.desc_entry.get().strip()
        try:
            imp = float(self.imp_entry.get().replace(",", "."))
        except Exception:
            self.show_custom_warning("Errore", "Importo non valido")
            return
        tipo = self.tipo_spesa_var.get()
        ric_id = str(uuid.uuid4())
        date_list = []
        for i in range(n):
            if ric_type == "Ogni giorno":
                d = data_inizio + datetime.timedelta(days=i)
            elif ric_type == "Ogni mese":
                month = (data_inizio.month - 1 + i) % 12 + 1
                year = data_inizio.year + (data_inizio.month - 1 + i) // 12
                day = min(data_inizio.day, [31,
                    29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                    31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1])
                try:
                    d = datetime.date(year, month, day)
                except Exception:
                    d = datetime.date(year, month, 1)
            elif ric_type == "Ogni anno":
                year = data_inizio.year + i
                try:
                    d = datetime.date(year, data_inizio.month, data_inizio.day)
                except Exception:
                    d = datetime.date(year, data_inizio.month, 1)
            else:
                break
            date_list.append(d)
        for d in date_list:
            if d not in self.spese:
                self.spese[d] = []
            self.spese[d].append((cat, desc, imp, tipo, ric_id))
        self.ricorrenze[ric_id] = {
            "tipo": ric_type,
            "n": n,
            "data_inizio": data_inizio.strftime("%d-%m-%Y"),
            "cat": cat,
            "desc": desc,
            "imp": imp,
            "tipo_voce": tipo,
            "date_list": [d.strftime("%d-%m-%Y") for d in date_list]
        }
        self.save_db()
        self.update_stats()
        self.update_totalizzatore_anno_corrente()
        self.update_totalizzatore_mese_corrente()
        self.update_spese_mese_corrente()
        self.show_custom_info("Ricorrenza aggiunta", f"Spesa/entrata ricorrente aggiunta per {n} volte.")
        self.ricorrenza_tipo.set("Nessuna")  
        self.reset_modifica_form()

    def del_ricorrenza(self):
        if not self.ricorrenze:
            self.show_custom_warning("Info", "Nessuna ricorrenza trovata.")
            return
        popup = tk.Toplevel(self)
        popup.title("Cancella Ricorrenza")
        popup.grab_set()
        popup.resizable(False, False)
        popup.geometry("+%d+%d" % (
            self.winfo_rootx() + 200,
            self.winfo_rooty() + 120
        ))
        tk.Label(popup, text="Seleziona una ricorrenza da cancellare:", font=("Arial", 10)).pack(padx=12, pady=7)
        frame = tk.Frame(popup)
        frame.pack(padx=8, pady=4)
        ric_list = list(self.ricorrenze.items())
        showlist = []
        for rid, r in ric_list[-10:]:
            tipo = r["tipo"]
            n = r["n"]
            data_inizio = r["data_inizio"]
            desc = r["desc"]
            cat = r["cat"]
            showlist.append(f"{tipo} x{n} da {data_inizio} - {cat} - {desc} ({rid[:8]})")
        ric_sel = tk.StringVar(value=showlist[0] if showlist else "")
        ric_combo = ttk.Combobox(frame, values=showlist, state="readonly", width=60, textvariable=ric_sel)
        ric_combo.grid(row=0, column=0, padx=4, pady=4)
        def get_selected_id():
            idx = showlist.index(ric_sel.get())
            return ric_list[-10:][idx][0]
        def do_ok():
            rid = get_selected_id()
            self._delete_ricorrenza_by_id(rid)
            popup.destroy()
        def do_cancel():
            popup.destroy()
        frame_btn = tk.Frame(popup)
        frame_btn.pack(pady=5)
        tk.Button(frame_btn, text="Cancella", command=do_ok, width=10).grid(row=0, column=0, padx=8)
        tk.Button(frame_btn, text="Annulla", command=do_cancel, width=10).grid(row=0, column=1, padx=8)

    def _delete_ricorrenza_by_id(self, ric_id):
        if ric_id not in self.ricorrenze:
            self.show_custom_warning("Errore", "Ricorrenza non trovata.")
            return
        for d in list(self.spese.keys()):
            nuove = []
            for voce in self.spese[d]:
                if len(voce) == 5 and voce[4] == ric_id:
                    continue
                nuove.append(voce if len(voce) == 4 else voce[:4])
            if nuove:
                self.spese[d] = nuove
            else:
                del self.spese[d]
        del self.ricorrenze[ric_id]
        self.save_db()
        self.update_stats()
        self.update_totalizzatore_anno_corrente()
        self.update_totalizzatore_mese_corrente()
        self.update_spese_mese_corrente()

    def add_spesa(self):
        if self.ricorrenza_tipo.get() != "Nessuna":
            self.add_ricorrenza()
            return
        data = self.data_spesa_var.get()
        cat = self.cat_sel.get()
        desc = self.desc_entry.get().strip()
        try:
            imp = float(self.imp_entry.get().replace(",", "."))
        except Exception:
            self.show_custom_warning("Errore", "Importo non valido")
            return
        tipo = self.tipo_spesa_var.get()
        d = datetime.datetime.strptime(data, "%d-%m-%Y").date()
        if d not in self.spese:
            self.spese[d] = []
        self.spese[d].append((cat, desc, imp, tipo))
        self.desc_entry.delete(0, tk.END)
        self.imp_entry.delete(0, tk.END)
        self.on_categoria_changed()
        self.save_db()
        self.update_stats()
        self.update_totalizzatore_anno_corrente()
        self.update_totalizzatore_mese_corrente()
        self.update_spese_mese_corrente()
        self.reset_modifica_form()

    def set_tipo_spesa_editable(self, editable=True):
        if editable:
            self.btn_tipo_spesa.state(["!disabled"])
        else:
            self.btn_tipo_spesa.state(["disabled"])

    def on_table_click(self, event):
        mode = self.stats_mode.get()
        if mode != "giorno":
            return
        region = self.stats_table.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.stats_table.identify_column(event.x)
        if col != "#6":
            return
        rowid = self.stats_table.identify_row(event.y)
        if not rowid:
            return
        vals = self.stats_table.item(rowid, "values")
        giorno_str, cat, desc, imp, tipo, _ = vals
        giorno = datetime.datetime.strptime(giorno_str, "%d-%m-%Y").date()
        idx = self.stats_table.index(rowid)
        voce = self.spese[giorno][idx]
        self.modifica_idx = (giorno, idx)
        self.cat_sel.set(cat)
        self.desc_entry.delete(0, tk.END)
        self.desc_entry.insert(0, desc)
        self.imp_entry.delete(0, tk.END)
        self.imp_entry.insert(0, imp)
        self.tipo_spesa_var.set(tipo)
        self.btn_tipo_spesa.config(text=tipo)
        self.btn_modifica["state"] = tk.NORMAL
        self.btn_aggiungi["state"] = tk.DISABLED
        self.btn_cancella["state"] = tk.NORMAL
        self.data_spesa_var.set(giorno.strftime("%d-%m-%Y"))
        self.set_tipo_spesa_editable(False)
        new_style = 'GreenOutline.TButton' if tipo == "Entrata" else 'RedOutline.TButton'
        self.btn_tipo_spesa.config(style=new_style)
        if len(voce) == 5:
            ric_id = voce[4]
            if ric_id in self.ricorrenze:
                ric = self.ricorrenze[ric_id]
                self.show_custom_info("Voce ricorrente", f"Questa voce è parte di una ricorrenza: {ric['tipo']} x{ric['n']} da {ric['data_inizio']}.\nPuoi cancellare tutta la ricorrenza dal pannello sotto.")

    def reset_modifica_form(self):
        self.modifica_idx = None
        self.btn_modifica["state"] = tk.DISABLED
        self.btn_aggiungi["state"] = tk.NORMAL
        self.btn_cancella["state"] = tk.DISABLED
        self.desc_entry.delete(0, tk.END)
        self.imp_entry.delete(0, tk.END)
        self.on_categoria_changed()
        self.data_spesa_var.set(datetime.date.today().strftime("%d-%m-%Y"))
        self.set_tipo_spesa_editable(True)

    def salva_modifica(self):
        if not self.modifica_idx:
            return
        old_dt, idx = self.modifica_idx
        new_data = self.data_spesa_var.get()
        new_dt = datetime.datetime.strptime(new_data, "%d-%m-%Y").date()
        cat = self.cat_sel.get()
        desc = self.desc_entry.get().strip()
        try:
            imp = float(self.imp_entry.get().replace(",", "."))
        except Exception:
            self.show_custom_warning("Errore", "Importo non valido")
            return
        tipo = self.tipo_spesa_var.get()

        if old_dt not in self.spese or idx >= len(self.spese[old_dt]):
            self.show_custom_warning("Errore", "La voce selezionata non esiste più.")
            self.reset_modifica_form()
            return
        voce_old = self.spese[old_dt][idx]
        id_ric = voce_old[4] if len(voce_old) == 5 else None

        del self.spese[old_dt][idx]
        if not self.spese[old_dt]:
            del self.spese[old_dt]
        if new_dt not in self.spese:
            self.spese[new_dt] = []
        voce_new = (cat, desc, imp, tipo)
        if id_ric is not None:
            voce_new += (id_ric,)
        self.spese[new_dt].append(voce_new)
        self.save_db()
        self.update_stats()
        self.update_totalizzatore_anno_corrente()
        self.update_totalizzatore_mese_corrente()
        self.update_spese_mese_corrente()
        self.reset_modifica_form()

    def cancella_voce(self):
        if not self.modifica_idx:
            return
        dt, idx = self.modifica_idx
        if dt in self.spese and 0 <= idx < len(self.spese[dt]):
            del self.spese[dt][idx]
            if not self.spese[dt]:
                del self.spese[dt]
            self.save_db()
            self.update_stats()
            self.update_totalizzatore_anno_corrente()
            self.update_totalizzatore_mese_corrente()
            self.update_spese_mese_corrente()
        self.reset_modifica_form()

    def update_spese_mese_corrente(self):
        for i in self.spese_mese_tree.get_children():
            self.spese_mese_tree.delete(i)
        now = datetime.date.today()
        year, month = now.year, now.month
        spese_mese = []
        for d in sorted(self.spese.keys()):
            if d.year == year and d.month == month:
                for entry in self.spese[d]:
                    cat, desc, imp, tipo = entry[:4]
                    spese_mese.append((d, cat, desc, imp, tipo))
        for d, cat, desc, imp, tipo in spese_mese:
            tag = 'entrata' if tipo == 'Entrata' else 'uscita'
            self.spese_mese_tree.insert("", "end", values=(
                d.strftime("%d-%m-%Y"), cat, desc, f"{imp:.2f}", tipo
            ), tags=(tag,))

    def apply_estratto(self):
        try:
            m = int(self.cb_estratto_month.get().split(" - ")[0])
            y = int(self.cb_estratto_year.get())
            d = datetime.date(y, m, 1)
            self.stats_refdate = d
            self.cal.selection_set(d)
            self.set_stats_mode("mese")
            self.update_totalizzatore_anno_corrente()
            self.update_totalizzatore_mese_corrente()
            self.update_spese_mese_corrente()
        except Exception:
            self.show_custom_warning("Errore", "Mese o anno non validi")

    def set_stats_mode(self, mode):
        self.stats_mode.set(mode)
        if mode == "giorno":
            self.stats_label.config(text="Statistiche giornaliere")
            self.stats_table["displaycolumns"] = ("A","B","C","D","E","F")
            self.stats_table.heading("A", text="Data")
            self.stats_table.heading("B", text="Categoria")
            self.stats_table.heading("C", text="Descrizione")
            self.stats_table.heading("D", text="Importo (€)")
            self.stats_table.heading("E", text="Tipo")
            self.stats_table.heading("F", text="Modifica")
        elif mode == "mese":
            ref = self.stats_refdate
            monthname = self.get_month_name(ref.month)
            self.stats_label.config(text=f"Statistiche mensili per {monthname} {ref.year}")
            self.stats_table["displaycolumns"] = ("A","B","C")
            self.stats_table.heading("A", text="Categoria")
            self.stats_table.heading("B", text="Totale Categoria (€)")
            self.stats_table.heading("C", text="Tipo")
        elif mode == "anno":
            ref = self.stats_refdate
            self.stats_label.config(text=f"Statistiche annuali per {ref.year}")
            self.stats_table["displaycolumns"] = ("A","B","C")
            self.stats_table.heading("A", text="Categoria")
            self.stats_table.heading("B", text="Totale Categoria (€)")
            self.stats_table.heading("C", text="Tipo")
        else:
            self.stats_label.config(text="Totali per categoria")
            self.stats_table["displaycolumns"] = ("A","B","C")
            self.stats_table.heading("A", text="Categoria")
            self.stats_table.heading("B", text="Totale Categoria (€)")
            self.stats_table.heading("C", text="Tipo")
        self.update_stats()
        self.update_totalizzatore_anno_corrente()
        self.update_totalizzatore_mese_corrente()
        self.update_spese_mese_corrente()

    def get_month_name(self, month):
        mesi = [
            "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
            "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
        ]
        return mesi[month-1] if 1 <= month <= 12 else str(month)

    def update_stats(self):
        for i in self.stats_table.get_children():
            self.stats_table.delete(i)
        mode = self.stats_mode.get()
        tot_entrate, tot_uscite = 0.0, 0.0
        if mode == "giorno":
            try:
                giorno = datetime.datetime.strptime(self.cal.get_date(), "%d-%m-%Y").date()
            except Exception:
                giorno = datetime.date.today()
            spese = self.spese.get(giorno, [])
            for idx, entry in enumerate(spese):
                cat, desc, imp, tipo = entry[:4]
                tag = "entrata" if tipo == "Entrata" else "uscita"
                self.stats_table.insert(
                    "", "end",
                    values=(giorno.strftime("%d-%m-%Y"), cat, desc, f"{imp:.2f}", tipo, "Modifica"),
                    tags=(f"{giorno.strftime('%d-%m-%Y')}|{idx}", tag)
                )
                if tipo == "Entrata":
                    tot_entrate += imp
                else:
                    tot_uscite += imp
        else:
            totali = {}
            ref = self.stats_refdate
            for d, sp in self.spese.items():
                if mode == "mese":
                    if not (d.year == ref.year and d.month == ref.month):
                        continue
                elif mode == "anno":
                    if d.year != ref.year:
                        continue
                for entry in sp:
                    cat, desc, imp, tipo = entry[:4]
                    if cat not in totali:
                        totali[cat] = {"Entrata": 0.0, "Uscita": 0.0}
                    totali[cat][tipo] += imp
            for cat in sorted(totali.keys()):
                for tipo in ("Entrata", "Uscita"):
                    if totali[cat][tipo] > 0:
                        tag = "entrata" if tipo == "Entrata" else "uscita"
                        self.stats_table.insert(
                            "", "end",
                            values=(cat, f"{totali[cat][tipo]:.2f}", tipo),
                            tags=(tag,)
                        )
                        if tipo == "Entrata":
                            tot_entrate += totali[cat][tipo]
                        else:
                            tot_uscite += totali[cat][tipo]
        txt_tot = f"Totale Entrate: {tot_entrate:.2f}    Totale Uscite: {tot_uscite:.2f}    Differenza: {(tot_entrate-tot_uscite):.2f}"
        self.totali_label.config(text=txt_tot)

    def update_totalizzatore_anno_corrente(self):
        anno = datetime.date.today().year
        totale_entrate = 0.0
        totale_uscite = 0.0
        for d, sp in self.spese.items():
            if d.year == anno:
                for entry in sp:
                    tipo = entry[3]
                    imp = entry[2]
                    if tipo == "Entrata":
                        totale_entrate += imp
                    else:
                        totale_uscite += imp
        differenza = totale_entrate - totale_uscite
        self.totalizzatore_entrate_label.config(text=f"Totale Entrate: {totale_entrate:.2f} €")
        self.totalizzatore_uscite_label.config(text=f"Totale Uscite:  {totale_uscite:.2f} €")
        self.totalizzatore_diff_label.config(
            text=f"Differenza:      {differenza:.2f} €",
            foreground="blue" if differenza >= 0 else "red"
        )

    def update_totalizzatore_mese_corrente(self):
        now = datetime.date.today()
        year, month = now.year, now.month
        totale_entrate = 0.0
        totale_uscite = 0.0
        for d, sp in self.spese.items():
            if d.year == year and d.month == month:
                for entry in sp:
                    tipo = entry[3]
                    imp = entry[2]
                    if tipo == "Entrata":
                        totale_entrate += imp
                    else:
                        totale_uscite += imp
        differenza = totale_entrate - totale_uscite
        self.totalizzatore_mese_entrate_label.config(text=f"Totale Entrate mese: {totale_entrate:.2f} €")
        self.totalizzatore_mese_uscite_label.config(text=f"Totale Uscite mese:  {totale_uscite:.2f} €")
        self.totalizzatore_mese_diff_label.config(
            text=f"Differenza mese:     {differenza:.2f} €",
            foreground="blue" if differenza >= 0 else "red"
        )

    def show_reset_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("Reset Database")
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.geometry("+%d+%d" % (
            self.winfo_rootx() + 120,
            self.winfo_rooty() + 120
        ))
        label = tk.Label(dialog, text=(
            "Vuoi cancellare tutte le spese e/o le categorie?\n\n"
            "Scegli 'Sì' per cancellare tutto (spese + categorie, resterà solo la categoria di default)\n\n"
            "'No' per cancellare solo le spese.\n\n"
            "'Solo Letture' per cancellare le letture delle utenze\n"
        ), font=("Arial", 10), justify="left", padx=12, pady=10)
        label.pack()
        btns = tk.Frame(dialog)
        btns.pack(pady=(0,10))

        def do_yes():
            dialog.destroy()
            self.spese = {}
            self.categorie = ["Generica"]
            self.categorie_tipi = {"Generica": "Uscita"}
            self.ricorrenze = {}
            self.cat_menu["values"] = self.categorie
            self.cat_mod_menu["values"] = self.categorie
            self.cat_sel.set(self.categorie[0])
            self.cat_mod_sel.set(self.categorie[0])
            self.save_db()
            self.update_stats()
            self.update_totalizzatore_anno_corrente()
            self.update_totalizzatore_mese_corrente()
            self.update_spese_mese_corrente()
            self.show_custom_warning("Spese", "Spese e categorie azzerate")
        def do_no():
            dialog.destroy()
            self.spese = {}
            self.ricorrenze = {}
            self.save_db()
            self.update_stats()
            self.update_totalizzatore_anno_corrente()
            self.update_totalizzatore_mese_corrente()
            self.update_spese_mese_corrente()
            self.show_custom_warning("Spese", "Spese azzerate")
        def do_letture():
            dialog.destroy()
            if os.path.exists(FILE_DB):
             os.remove(FILE_DB)
            self.show_custom_warning("Letture", "Letture utenze azzerate")
        def do_cancel():
            dialog.destroy()
        tk.Button(btns, text="Sì", command=do_yes, width=3).grid(row=0, column=0, padx=5)
        tk.Button(btns, text="No", command=do_no, width=3).grid(row=0, column=1, padx=5)
        tk.Button(btns, text="Solo letture", command=do_letture, width=8).grid(row=0, column=2, padx=5)
        tk.Button(btns, text="Annulla", command=do_cancel, width=8).grid(row=0, column=3, padx=5)
        btns.focus_set()
        dialog.bind("<Escape>", lambda e: do_cancel())
        dialog.bind("<Return>", lambda e: do_yes())

    def export_giorno_forzato(self):
        old_mode = self.stats_mode.get()
        self.stats_mode.set("giorno")
        self.export_stats()
        self.stats_mode.set(old_mode)

    def export_stats(self):
        mode = self.stats_mode.get()
        lines = []
        tot_entrate, tot_uscite = 0.0, 0.0
        if mode == "giorno":
            try:
                giorno = datetime.datetime.strptime(self.cal.get_date(), "%d-%m-%Y").date()
            except Exception:
                giorno = datetime.date.today()
            spese = self.spese.get(giorno, [])
            if not spese:
                spese = self.spese.get(giorno.strftime("%d-%m-%Y"), [])
            lines.append(f"Statistiche per giorno: {giorno.strftime('%d-%m-%Y')}\n")
            lines.append(f"{'Data':<12} {'Categoria':<20} {'Descrizione':<30} {'Importo':>10} {'Tipo':<8}")
            for entry in spese:
                cat, desc, imp, tipo = entry[:4]
                lines.append(f"{giorno.strftime('%d-%m-%Y'):<12} {cat:<20} {desc:<30} {imp:>10.2f} {tipo:<8}")
                if tipo == "Entrata":
                    tot_entrate += imp
                else:
                    tot_uscite += imp
            if not spese:
                lines.append("Nessuna spesa trovata per il giorno selezionato.")
        else:
            totali = {}
            tipo_cat = {}
            ref = self.stats_refdate
            if mode == "mese":
                year, month = ref.year, ref.month
                monthname = self.get_month_name(month)
                lines.append(f"Statistiche per mese: {monthname} {year}\n")
                for d, sp in self.spese.items():
                    if isinstance(d, str):
                        try:
                            d2 = datetime.datetime.strptime(d, "%d-%m-%Y").date()
                        except Exception:
                            continue
                    else:
                        d2 = d
                    if d2.year == year and d2.month == month:
                        for entry in sp:
                            cat, desc, imp, tipo = entry[:4]
                            totali[cat] = totali.get(cat, 0.0) + imp
                            tipo_cat[cat] = self.categorie_tipi.get(cat, tipo)
            elif mode == "anno":
                year = ref.year
                lines.append(f"Statistiche per anno: {year}\n")
                for d, sp in self.spese.items():
                    if isinstance(d, str):
                        try:
                            d2 = datetime.datetime.strptime(d, "%d-%m-%Y").date()
                        except Exception:
                            continue
                    else:
                        d2 = d
                    if d2.year == year:
                        for entry in sp:
                            cat, desc, imp, tipo = entry[:4]
                            totali[cat] = totali.get(cat, 0.0) + imp
                            tipo_cat[cat] = self.categorie_tipi.get(cat, tipo)
            elif mode == "totali":
                lines.append(f"Statistiche totali per categoria\n")
                for d, sp in self.spese.items():
                    for entry in sp:
                        cat, desc, imp, tipo = entry[:4]
                        totali[cat] = totali.get(cat, 0.0) + imp
                        tipo_cat[cat] = self.categorie_tipi.get(cat, tipo)
            lines.append(f"{'Categoria':<20} {'Totale Categoria (€)':>20} {'Tipo':<8}")
            for cat in sorted(totali.keys()):
                tipo = tipo_cat.get(cat, "Uscita")
                lines.append(f"{cat:<20} {totali[cat]:>20.2f} {tipo:<8}")
                if tipo == "Entrata":
                    tot_entrate += totali[cat]
                else:
                    tot_uscite += totali[cat]
        lines.append("-" * 48)
        lines.append(f"Totale Entrate: {tot_entrate:.2f}    Totale Uscite: {tot_uscite:.2f}    Differenza: {(tot_entrate-tot_uscite):.2f}")
        self.show_export_preview("\n".join(lines))

    def export_month_detail(self):
        ref = self.stats_refdate
        month = ref.month
        year = ref.year
        monthname = self.get_month_name(month)
        lines = []
        tot_entrate, tot_uscite = 0.0, 0.0
        lines.append(f"Spese dettagliate per il mese: {monthname} {year}\n")
        days_in_month = [
            d for d in sorted(self.spese.keys())
            if d.year == year and d.month == month
        ]
        giorni_settimana = [
            "Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"
        ]
        if not days_in_month:
            lines.append("Nessuna spesa registrata in questo mese.\n")
        else:
            for d in days_in_month:
                giorno_it = giorni_settimana[d.weekday()]
                lines.append(f"{giorno_it} {d.strftime('%d-%m-%Y')}:")
                lines.append(f"  {'Categoria':<18} {'Descrizione':<30} {'Importo (€)':>12} {'Tipo':<8}")
                for entry in self.spese.get(d, []):
                    cat, desc, imp, tipo = entry[:4]
                    lines.append(f"  {cat:<18} {desc:<30} {imp:>12.2f} {tipo:<8}")
                    if tipo == "Entrata":
                        tot_entrate += imp
                    else:
                        tot_uscite += imp
                lines.append("")
        lines.append("-" * 60)
        lines.append(f"Totale Entrate mese: {tot_entrate:.2f}    Totale Uscite mese: {tot_uscite:.2f}    Differenza: {(tot_entrate-tot_uscite):.2f}")
        self.show_export_preview("\n".join(lines))

    def show_export_preview(self, content):
        """ Mostra la finestra di anteprima dell'esportazione con posizione fissa. """
        preview = tk.Toplevel(self)
        preview.withdraw()  # 🔹 Nasconde temporaneamente la finestra per evitare movimenti
        preview.title("Anteprima Esportazione Statistiche")
        preview.geometry("1400x700")

        # 🔹 Calcola la posizione centrale SENZA far muovere la finestra
        screen_width = preview.winfo_screenwidth()
        screen_height = preview.winfo_screenheight()
        x = (screen_width - 1400) // 2
        y = (screen_height - 700) // 2
        preview.geometry(f"1400x700+{x}+{y}")

        preview.deiconify()  # 🔹 Ora la finestra appare direttamente nella posizione corretta
        preview.grab_set()
        preview.lift()

        # 🔹 Creazione del widget di testo
        text = tk.Text(preview, wrap="none", font=("Arial", 10))
        text.insert("1.0", content)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        preview.update()  # 🔹 Forza il rendering della finestra


        def save_file():
            """ Salva il contenuto dell'anteprima su file e chiude la finestra. """
            file = filedialog.asksaveasfilename(
                parent=preview,  
                title="Salva Statistiche",
                defaultextension=".txt",
                filetypes=[("File di testo", "*.txt"), ("Tutti i file", "*.*")]
            )
            if file:
                with open(file, "w", encoding="utf-8") as f:
                    f.write(content)
                preview.destroy()
                self.show_custom_warning("Esportazione completata", f"Statistiche esportate in {file}")

        btn_frame = ttk.Frame(preview)
        btn_frame.pack(fill=tk.X, pady=8)

        btn_salva = ttk.Button(btn_frame, text="Salva", command=save_file)
        btn_salva.pack(side=tk.LEFT, padx=10)

        btn_chiudi = ttk.Button(btn_frame, text="Chiudi", command=preview.destroy)
        btn_chiudi.pack(side=tk.RIGHT, padx=10)

        preview.update() 

        
    def import_db(self):
        file = filedialog.askopenfilename(
            title="Importa Database",
            defaultextension=".json",
            initialdir=DB_DIR,
            filetypes=[("File JSON", "*.json"), ("Tutti i file", "*.*")]
        )
        if file:
            try:
                with open(file, "r", encoding="utf-8") as fsrc:
                    dbdata = fsrc.read()
                with open(DB_FILE, "w", encoding="utf-8") as fdst:
                    fdst.write(dbdata)
                self.load_db()
                self.cat_menu["values"] = self.categorie
                self.cat_mod_menu["values"] = self.categorie
                if self.categorie:
                    self.cat_sel.set(self.categorie[0])
                    self.cat_mod_sel.set(self.categorie[0])
                self.update_stats()
                self.update_totalizzatore_anno_corrente()
                self.update_totalizzatore_mese_corrente()
                self.update_spese_mese_corrente()
                self.show_custom_warning("Importazione completata", f"Database importato da {file}")
            except Exception as e:
                self.show_custom_warning("Errore", "Errore durante l'esportazione:", f"{e}")

    def export_db(self):
        now = datetime.date.today()
        default_dir = DB_DIR
        default_filename = f"Export_{now.day:02d}-{now.month:02d}-{now.year}.json"
        file = filedialog.asksaveasfilename(
            title="Esporta Database",
            defaultextension=".json",
            initialdir=default_dir,
            initialfile=default_filename,
            filetypes=[("File JSON", "*.json"), ("Tutti i file", "*.*")]
        )
        if file:
            try:
                with open(DB_FILE, "r", encoding="utf-8") as fsrc:
                    dbdata = fsrc.read()
                with open(file, "w", encoding="utf-8") as fdst:
                    fdst.write(dbdata)
                self.show_custom_warning("Esportazione completata", f"Database esportato in {file}")
            except Exception as e:
                self.show_custom_warning("Errore", "Errore durante l'esportazione:", f"{e}")

    def export_anno_dettagliato(self):
        try:
            year = int(self.estratto_year_var.get())
        except Exception:
            year = datetime.date.today().year
        mesi = [
            "Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
            "Lug", "Ago", "Set", "Ott", "Nov", "Dic"
        ]

        categorie = sorted(
            set(
                entry[0]
                for sp in self.spese.values()
                for entry in sp
                if isinstance(entry, (list, tuple)) and len(entry) >= 4
            ).union(self.categorie)
        )
        totali_entrate_mese = [0.0 for _ in range(12)]
        totali_uscite_mese = [0.0 for _ in range(12)]
        cat_mese = {cat: [0.0 for _ in range(12)] for cat in categorie}
        cat_anno = {cat: 0.0 for cat in categorie}
        cat_entrata_mese = {cat: [0.0 for _ in range(12)] for cat in categorie}
        cat_entrata_anno = {cat: 0.0 for cat in categorie}
        totale_entrate_anno = 0.0
        totale_uscite_anno = 0.0

        def date_from_key(d):
            if isinstance(d, datetime.date):
                return d
            try:
                return datetime.datetime.strptime(d, "%d-%m-%Y").date()
            except Exception:
                return None

        for d, sp in self.spese.items():
            d2 = date_from_key(d)
            if d2 and d2.year == year:
                m = d2.month - 1
                for entry in sp:
                    if isinstance(entry, (list, tuple)) and len(entry) >= 4:
                        cat, desc, imp, tipo = entry[:4]
                        if tipo == "Entrata":
                            totali_entrate_mese[m] += imp
                            totale_entrate_anno += imp
                            cat_entrata_mese[cat][m] += imp
                            cat_entrata_anno[cat] += imp
                        else:
                            totali_uscite_mese[m] += imp
                            totale_uscite_anno += imp
                            cat_mese[cat][m] += imp
                            cat_anno[cat] += imp

        lines = []
        
        lines.append(f"Entrate anno {year}:")
        header_ent = "{:<14}".format("") + "".join(f"{m:>8}" for m in mesi) + f"{'Totale':>10}"
        lines.append(header_ent)
        ent_row = "{:<14}".format("Entrate") + "".join(f"{totali_entrate_mese[m]:8.2f}" for m in range(12)) + f"{totale_entrate_anno:10.2f}"
        lines.append(ent_row)
        lines.append("")

        lines.append("Entrate per categoria:")
        cat_ent_header = "{:<14}".format("Categoria") + "".join(f"{m:>8}" for m in mesi) + f"{'Totale':>10}"
        lines.append(cat_ent_header)
        for cat in categorie:
            if sum(cat_entrata_mese[cat]) > 0:  # Mostra solo le categorie con almeno un importo in entrata
                row = "{:<14}".format(cat[:14]) + "".join(f"{cat_entrata_mese[cat][m]:8.2f}" for m in range(12)) + f"{cat_entrata_anno[cat]:10.2f}"
                lines.append(row)
        lines.append("")
    
        lines.append("Uscite per categoria:")
        cat_header = "{:<14}".format("Categoria") + "".join(f"{m:>8}" for m in mesi) + f"{'Totale':>10}"
        lines.append(cat_header)
        for cat in categorie:
            if sum(cat_mese[cat]) > 0:  # Mostra solo le categorie con almeno un importo in uscita
                row = "{:<14}".format(cat[:14]) + "".join(f"{cat_mese[cat][m]:8.2f}" for m in range(12)) + f"{cat_anno[cat]:10.2f}"
                lines.append(row)
        lines.append("")

        lines.append("Uscite totali mese:")
        tot_mese_str = "{:<14}".format("") + "".join(f"{totali_uscite_mese[m]:8.2f}" for m in range(12)) + f"{totale_uscite_anno:10.2f}"
        lines.append(tot_mese_str)
        lines.append("")

        lines.append(f"Totale Entrate anno: {totale_entrate_anno:.2f} €   Totale Uscite anno: {totale_uscite_anno:.2f} €    Differenza anno: {(totale_entrate_anno - totale_uscite_anno):.2f} €")
        #lines.append(f"Totale Uscite anno: {totale_uscite_anno:.2f} €")
        #lines.append(f"Differenza anno: {(totale_entrate_anno - totale_uscite_anno):.2f} €")

        self.show_export_preview("\n".join(lines))

    def open_analisi_categoria(self):
        import calendar
        popup = tk.Toplevel(self)
        popup.title("Analisi Categoria")
        popup.geometry("700x600")
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()
    
        self.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 350
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 300
        popup.geometry(f"+{x}+{y}")
  
        frame_top = ttk.Frame(popup)
        frame_top.pack(padx=18, pady=10, fill=tk.X)
        ttk.Label(frame_top, text="Seleziona modalità:").pack(side=tk.LEFT)
        mode_var = tk.StringVar(value="Giorno")
        mode_combo = ttk.Combobox(frame_top, values=["Giorno", "Mese", "Anno", "Totale"], textvariable=mode_var, state="readonly", width=10)
        mode_combo.pack(side=tk.LEFT, padx=10)
    
        frame_period = ttk.Frame(popup)
        frame_period.pack(padx=18, pady=2, fill=tk.X)
    
        months = [
            "01 - Gennaio", "02 - Febbraio", "03 - Marzo", "04 - Aprile", "05 - Maggio", "06 - Giugno",
            "07 - Luglio", "08 - Agosto", "09 - Settembre", "10 - Ottobre", "11 - Novembre", "12 - Dicembre"
        ]
        today = datetime.date.today()
        current_year = today.year
    
        day_var = tk.StringVar(value=str(today.day))
        month_var = tk.StringVar(value=months[today.month - 1])
        year_var = tk.StringVar(value=str(today.year))
    
        def get_years(center=None):
            if center is None:
                center = datetime.date.today().year
            return [str(y) for y in range(center-10, center+11)]
    
        year_combo = ttk.Combobox(frame_period, values=get_years(current_year), textvariable=year_var, state="readonly", width=8)
        month_combo = ttk.Combobox(frame_period, values=months, textvariable=month_var, state="readonly", width=16)
        day_combo = ttk.Combobox(frame_period, values=[str(d) for d in range(1, 32)], textvariable=day_var, state="readonly", width=4)
        year_combo_only = ttk.Combobox(frame_period, values=get_years(current_year), textvariable=year_var, state="readonly", width=8)

        def update_days(*_):
            try:
                m = months.index(month_var.get()) + 1
                y = int(year_var.get())
            except Exception:
                m = today.month
                y = today.year
            n_days = calendar.monthrange(y, m)[1]
            days = [str(d) for d in range(1, n_days+1)]
            day_combo['values'] = days
            if day_var.get() not in days:
                day_var.set(days[-1])
        month_var.trace_add("write", update_days)
        year_var.trace_add("write", update_days)
     
        def reset_period():
            oggi = datetime.date.today()
            day_var.set(str(oggi.day))
            month_var.set(months[oggi.month - 1])
            year_var.set(str(oggi.year))
    
        def update_period_inputs(*_):
            for widget in frame_period.winfo_children():
                widget.pack_forget()
            mode = mode_var.get()
            if mode == "Giorno":
                day_combo.pack(side=tk.LEFT)
                month_combo.pack(side=tk.LEFT, padx=(4,8))
                year_combo.pack(side=tk.LEFT)
                reset_btn = ttk.Button(frame_period, text="Reset", width=8, command=reset_period)
                reset_btn.pack(side=tk.LEFT, padx=(10, 0))
                update_days()
            elif mode == "Mese":
                month_combo.pack(side=tk.LEFT, padx=(0,8))
                year_combo.pack(side=tk.LEFT)
                reset_btn = ttk.Button(frame_period, text="Reset", width=8, command=reset_period)
                reset_btn.pack(side=tk.LEFT, padx=(10, 0))
            elif mode == "Anno":
                year_combo_only.pack(side=tk.LEFT)
                reset_btn = ttk.Button(frame_period, text="Reset", width=8, command=reset_period)
                reset_btn.pack(side=tk.LEFT, padx=(10, 0))
        mode_combo.bind("<<ComboboxSelected>>", update_period_inputs)
        update_period_inputs()

        def update_years(*_):
            try:
                y = int(year_var.get())
            except Exception:
                y = datetime.date.today().year
            year_combo['values'] = get_years(y)
            year_combo_only['values'] = get_years(y)
            update_days()
        year_var.trace_add("write", update_years)
    
        frame_cat = ttk.Frame(popup)
        frame_cat.pack(padx=18, pady=12, fill=tk.X)
        ttk.Label(frame_cat, text="Categoria:").pack(side=tk.LEFT)
        def get_catlist():
            return ["Tutte le categorie"] + sorted(self.categorie)
        cat_var = tk.StringVar(value="Tutte le categorie")
        cat_combo = ttk.Combobox(frame_cat, values=get_catlist(), textvariable=cat_var, state="readonly", width=25)
        cat_combo.pack(side=tk.LEFT, padx=10)
 
        main_result_frame = ttk.Frame(popup)
        main_result_frame.pack(padx=18, fill=tk.BOTH, expand=True)
        text_result = tk.Text(main_result_frame, height=22, width=90, font=("Arial", 10), wrap='none')
        text_result.pack(fill=tk.BOTH, expand=True)
        frame_buttons = ttk.Frame(main_result_frame)
        frame_buttons.pack(fill=tk.X, pady=8)
        export_btn = ttk.Button(frame_buttons, text="Esporta", width=15)
        export_btn.pack(side=tk.LEFT, padx=4)
    
        def aggiorna_cat_combo():
            cat_combo['values'] = get_catlist()
            if cat_var.get() not in cat_combo['values']:
                cat_var.set("Tutte le categorie")
        aggiorna_cat_combo()
    
        def mostra_dettagli(*_):
            cat = cat_var.get()
            mode = mode_var.get()
            result_lines = []
    
            ENTRATA_CAT = "Entrata"  
    
            def calcola_totale(entries):
                totale = 0.0
                for e in entries:
                    if e[0] == ENTRATA_CAT:
                        totale += e[2]
                    else:
                        totale -= e[2]
                return totale
    
            if mode == "Giorno":
                try:
                    m = months.index(month_var.get()) + 1
                    d = int(day_var.get())
                    y = int(year_var.get())
                    giorno = datetime.date(y, m, d)
                except Exception:
                    giorno = today
                spese_giorno = self.spese.get(giorno, [])
                if cat == "Tutte le categorie":
                    filtered = spese_giorno
                    if not filtered:
                        result_lines.append(f"Nessuna spesa per '{cat}' il {giorno.strftime('%d-%m-%Y')}.")
                    else:
                        result_lines.append(f"Entrate/Uscite per il giorno {giorno.strftime('%d-%m-%Y')}:")
                        for e in filtered:
                            segno = "+" if e[0] == ENTRATA_CAT else "-"
                            result_lines.append(f"- {e[0]} | {e[1]}: {segno}{e[2]:.2f} € ({e[3]})")
                else:
                    filtered = [e for e in spese_giorno if e[0] == cat]
                    if not filtered:
                        result_lines.append(f"Nessuna spesa per '{cat}' il {giorno.strftime('%d-%m-%Y')}.")
                    else:
                        result_lines.append(f"Spese '{cat}' per il giorno {giorno.strftime('%d-%m-%Y')}:")
                        for e in filtered:
                            result_lines.append(f"- {e[0]} | {e[1]}: {e[2]:.2f} € ({e[3]})")
                        tot = sum(e[2] for e in filtered)
                        result_lines.append(f"Totale: {tot:.2f} €")
    
            elif mode == "Mese":
                try:
                    m = months.index(month_var.get()) + 1
                    y = int(year_var.get())
                except Exception:
                    m = today.month
                    y = today.year
                found = []
                for d, sp in self.spese.items():
                    if d.year == y and d.month == m:
                        if cat == "Tutte le categorie":
                            for e in sp:
                                found.append((d, e))
                        else:
                            for e in sp:
                                if e[0] == cat:
                                    found.append((d, e))
                if cat == "Tutte le categorie":
                    if not found:
                        result_lines.append(f"Nessuna spesa per '{cat}' in {self.get_month_name(m)} {y}.")
                    else:
                        result_lines.append(f"Entrate/Uscite per {self.get_month_name(m)} {y}:")
                        for d, e in found:
                            segno = "+" if e[0] == ENTRATA_CAT else "-"
                            result_lines.append(f"- {d.strftime('%d-%m-%Y')} | {e[0]} | {e[1]}: {segno}{e[2]:.2f} € ({e[3]})")
                else:
                    if not found:
                        result_lines.append(f"Nessuna spesa per '{cat}' in {self.get_month_name(m)} {y}.")
                    else:
                        result_lines.append(f"Spese '{cat}' per {self.get_month_name(m)} {y}:")
                        for d, e in found:
                            result_lines.append(f"- {d.strftime('%d-%m-%Y')} | {e[0]} | {e[1]}: {e[2]:.2f} € ({e[3]})")
                        tot = sum(e[2] for _, e in found)
                        result_lines.append(f"Totale: {tot:.2f} €")
    
            elif mode == "Anno":
                try:
                    y = int(year_var.get())
                except Exception:
                    y = today.year
                found = []
                for d, sp in self.spese.items():
                    if d.year == y:
                        if cat == "Tutte le categorie":
                            for e in sp:
                                found.append((d, e))
                        else:
                            for e in sp:
                                if e[0] == cat:
                                    found.append((d, e))
                if cat == "Tutte le categorie":
                    if not found:
                        result_lines.append(f"Nessuna spesa per '{cat}' nel {y}.")
                    else:
                        result_lines.append(f"Entrate/Uscite per l'anno {y}:")
                        for d, e in found:
                            segno = "+" if e[0] == ENTRATA_CAT else "-"
                            result_lines.append(f"- {d.strftime('%d-%m-%Y')} | {e[0]} | {e[1]}: {segno}{e[2]:.2f} € ({e[3]})")
                else:
                    if not found:
                        result_lines.append(f"Nessuna spesa per '{cat}' nel {y}.")
                    else:
                        result_lines.append(f"Spese '{cat}' per l'anno {y}:")
                        for d, e in found:
                            result_lines.append(f"- {d.strftime('%d-%m-%Y')} | {e[0]} | {e[1]}: {e[2]:.2f} € ({e[3]})")
                        tot = sum(e[2] for _, e in found)
                        result_lines.append(f"Totale: {tot:.2f} €")
    
            elif mode == "Totale":
                found = []
                for d, sp in self.spese.items():
                    if cat == "Tutte le categorie":
                        for e in sp:
                            found.append((d, e))
                    else:
                        for e in sp:
                            if e[0] == cat:
                                found.append((d, e))
                if cat == "Tutte le categorie":
                    if not found:
                        result_lines.append(f"Nessuna spesa per '{cat}'.")
                    else:
                        result_lines.append(f"Entrate/Uscite totali:")
                        for d, e in found:
                            segno = "+" if e[0] == ENTRATA_CAT else "-"
                            result_lines.append(f"- {d.strftime('%d-%m-%Y')} | {e[0]} | {e[1]}: {segno}{e[2]:.2f} € ({e[3]})")
                else:
                    if not found:
                        result_lines.append(f"Nessuna spesa per '{cat}'.")
                    else:
                        result_lines.append(f"Spese '{cat}' totali:")
                        for d, e in found:
                            result_lines.append(f"- {d.strftime('%d-%m-%Y')} | {e[0]} | {e[1]}: {e[2]:.2f} € ({e[3]})")
                        tot = sum(e[2] for _, e in found)
                        result_lines.append(f"Totale: {tot:.2f} €")
    
            text_result.delete("1.0", tk.END)
            text_result.insert(tk.END, "\n".join("    " + l for l in result_lines))
    
        def esporta_analisi():
            contenuto = text_result.get("1.0", tk.END).strip()
            if not contenuto:
                from tkinter import messagebox
                self.show_custom_warning("Esporta", "Nulla da esportare.")
                return
            preview = tk.Toplevel(popup)
            preview.title("Preview esportazione")
            preview.geometry("800x500")
            preview.transient(popup)
            preview.grab_set()
            preview.focus_set()
            tx = tk.Text(preview, font=("Arial", 10), wrap="none")
            tx.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            contenuto_preview = "\n".join("    "+l.lstrip() for l in contenuto.splitlines())
            tx.insert(tk.END, contenuto_preview)
            tx.config(state="disabled")
            frm = ttk.Frame(preview)
            frm.pack(fill=tk.X, padx=10, pady=8)
            def do_save():
                from tkinter import filedialog, messagebox
                file = filedialog.asksaveasfilename(
                    parent=preview,
                    title="Esporta Analisi Categoria",
                    defaultextension=".txt",
                    filetypes=[("File di testo", "*.txt"), ("Tutti i file", "*.*")]
                )
                if file:
                    with open(file, "w", encoding="utf-8") as f:
                        f.write(contenuto_preview)
                        self.show_custom_warning("Esporta", f"Analisi esportata in {file}")
                    preview.destroy()
            ttk.Button(frm, text="Salva...", command=do_save, width=15).pack(side=tk.LEFT, padx=6)
            ttk.Button(frm, text="Chiudi", command=preview.destroy, width=12).pack(side=tk.RIGHT, padx=6)
            preview.lift()
            preview.attributes('-topmost', True)
            preview.after(100, lambda: preview.attributes('-topmost', False))
    
        export_btn.config(command=esporta_analisi)
 
        mode_var.trace_add("write", mostra_dettagli)
        month_var.trace_add("write", mostra_dettagli)
        year_var.trace_add("write", mostra_dettagli)
        day_var.trace_add("write", mostra_dettagli)
        cat_var.trace_add("write", mostra_dettagli)
    
        mostra_dettagli()
        
    def open_saldo_conto(self):
        popup = tk.Toplevel(self)
        popup.title("Saldo Conto Corrente")
        popup.geometry("480x440")
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()
    
        # Leggi saldo da spese_db.json
        saldo_data = {"saldo": 0.0, "data": datetime.date.today().strftime("%d-%m-%Y")}
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    dbdata = json.load(f)
                saldo_data["saldo"] = dbdata.get("saldo", 0.0)
                saldo_data["data"] = dbdata.get("saldo_data", datetime.date.today().strftime("%d-%m-%Y"))
            except Exception:
                pass
    
        frame = ttk.Frame(popup)
        frame.pack(padx=28, pady=18, fill=tk.BOTH, expand=True)
    
        lastframe = ttk.LabelFrame(frame, text="Ultimo saldo inserito", padding=10)
        lastframe.pack(fill=tk.X, padx=0, pady=(0, 18))
    
        ttk.Label(lastframe, text="Ultimo saldo:", font=("Arial", 11)).grid(row=0, column=0, sticky="e", padx=(0,8), pady=2)
        last_saldo_var = tk.StringVar(value=f"{saldo_data['saldo']:.2f}")
        ttk.Entry(lastframe, textvariable=last_saldo_var, width=15, font=("Arial", 11), state="readonly").grid(row=0, column=1, padx=(0,8), pady=2)
        ttk.Label(lastframe, text="€", font=("Arial", 11)).grid(row=0, column=2, sticky="w", pady=2)
    
        ttk.Label(lastframe, text="Data inserimento:", font=("Arial", 11)).grid(row=1, column=0, sticky="e", padx=(0,8), pady=2)
        last_data_var = tk.StringVar(value=saldo_data["data"])
        ttk.Entry(lastframe, textvariable=last_data_var, width=12, font=("Arial", 11), state="readonly").grid(row=1, column=1, pady=2, sticky="w")
    
        btmframe = ttk.LabelFrame(frame, text="Aggiorna saldo bancario", padding=10)
        btmframe.pack(fill=tk.X, padx=0, pady=(18, 0))
    
        try:
            default_dt = datetime.datetime.strptime(saldo_data["data"], "%d-%m-%Y").date()
        except Exception:
            default_dt = datetime.date.today()
        anni = list(range(default_dt.year - 5, default_dt.year + 11))
        mesi = list(range(1, 13))
        giorni = list(range(1, 32))
    
        ttk.Label(btmframe, text="Data saldo:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="e", padx=(0,8), pady=2)
        day_var = tk.StringVar(value=f"{default_dt.day:02d}")
        month_var = tk.StringVar(value=f"{default_dt.month:02d}")
        year_var = tk.StringVar(value=str(default_dt.year))
    
        cb_day = ttk.Combobox(btmframe, textvariable=day_var, values=[f"{g:02d}" for g in giorni], width=4, state="readonly", font=("Arial", 10))
        cb_month = ttk.Combobox(btmframe, textvariable=month_var, values=[f"{m:02d}" for m in mesi], width=4, state="readonly", font=("Arial", 10))
        cb_year = ttk.Combobox(btmframe, textvariable=year_var, values=[str(a) for a in anni], width=6, state="readonly", font=("Arial", 10))
        cb_day.grid(row=0, column=1, sticky="w", padx=(0,2))
        cb_month.grid(row=0, column=2, sticky="w", padx=(0,2))
        cb_year.grid(row=0, column=3, sticky="w", padx=(0,6))
    
        def reset_data_today():
            oggi = datetime.date.today()
            day_var.set(f"{oggi.day:02d}")
            month_var.set(f"{oggi.month:02d}")
            year_var.set(str(oggi.year))
        ttk.Button(btmframe, text="Reset", command=reset_data_today, width=5).grid(row=0, column=4, padx=(0,0))
    
        ttk.Label(btmframe, text="Inserire saldo bancario:", font=("Arial", 11)).grid(row=1, column=0, sticky="e", pady=(18,2))
        saldo_var = tk.StringVar()
        saldo_entry = ttk.Entry(btmframe, textvariable=saldo_var, width=15, font=("Arial", 11))
        saldo_entry.grid(row=1, column=1, padx=8, pady=(18,2), columnspan=2, sticky="w")
        ttk.Label(btmframe, text="€", font=("Arial", 11)).grid(row=1, column=3, sticky="w", pady=(18,2))
    
        data_var = tk.StringVar(value=saldo_data["data"])
        def aggiorna_data_var(*_):
            val = f"{day_var.get()}-{month_var.get()}-{year_var.get()}"
            data_var.set(val)
        day_var.trace_add("write", aggiorna_data_var)
        month_var.trace_add("write", aggiorna_data_var)
        year_var.trace_add("write", aggiorna_data_var)
        aggiorna_data_var()
    
        lbl_saldo_mese = ttk.Label(frame, text="", font=("Arial", 11))
        lbl_saldo_mese.pack(anchor="w", pady=(24,0))
        lbl_saldo_anno = ttk.Label(frame, text="", font=("Arial", 11))
        lbl_saldo_anno.pack(anchor="w")
        lbl_saldo_tot = ttk.Label(frame, text="", font=("Arial", 11, "bold"))
        lbl_saldo_tot.pack(anchor="w", pady=(0,16))
    
        today = datetime.date.today()
        mese = today.month
        anno = today.year
    
        def get_selected_date():
            try:
                return datetime.datetime.strptime(data_var.get(), "%d-%m-%Y").date()
            except Exception:
                return today
    
        def calcola_saldo(filtro):
            try:
                saldo = float(last_saldo_var.get())
            except Exception:
                saldo = 0.0
            data_saldo = get_selected_date()
            saldo_mese = saldo
            saldo_anno = saldo
            saldo_totale = saldo
            for d in sorted(self.spese.keys()):
                if d < data_saldo:
                    continue
                for entry in self.spese[d]:
                    imp = entry[2]
                    tipo = entry[3]
                    if tipo == "Entrata":
                        saldo_totale += imp
                        if d.year == anno:
                            saldo_anno += imp
                            if d.month == mese:
                                saldo_mese += imp
                    else:
                        saldo_totale -= imp
                        if d.year == anno:
                            saldo_anno -= imp
                            if d.month == mese:
                                saldo_mese -= imp
            if filtro == "mese":
                return saldo_mese
            elif filtro == "anno":
                return saldo_anno
            else:
                return saldo_totale
    
        def aggiorna_saldi(*_):
            sm = calcola_saldo("mese")
            sa = calcola_saldo("anno")
            st = calcola_saldo("totale")
            lbl_saldo_mese.config(text=f"Saldo nel mese: {sm:.2f} €")
            lbl_saldo_anno.config(text=f"Saldo nell'anno: {sa:.2f} €")
            lbl_saldo_tot.config(text=f"Saldo totale    : {st:.2f} €")
    
        data_var.trace_add("write", aggiorna_saldi)
        aggiorna_saldi()
    
        def custom_warning(msg, parent):
            warn = tk.Toplevel(parent)
            warn.transient(parent)
            warn.title("Attenzione")
            warn.configure(bg="#ffff99")
            warn.resizable(False, False)
            warn.lift()
            warn.grab_set()
            width = 420
            height = 160
            warn.geometry(f"{width}x{height}")
            label = tk.Label(warn, text=msg, font=("Arial", 10), bg="#ffff99", fg="black", wraplength=390)
            label.pack(padx=18, pady=30)
            btn = ttk.Button(warn, text="OK", command=warn.destroy)
            btn.pack(pady=(0,18))
            warn.update_idletasks()
            parent_x = parent.winfo_rootx()
            parent_y = parent.winfo_rooty()
            parent_w = parent.winfo_width()
            parent_h = parent.winfo_height()
            x = parent_x + (parent_w // 2) - (width // 2)
            y = parent_y + (parent_h // 2) - (height // 2)
            warn.geometry(f"{width}x{height}+{x}+{y}")
            warn.focus_force()
            warn.attributes('-topmost', True)
            warn.after(100, lambda: warn.attributes('-topmost', False))
    
        def salva_saldo():
            try:
                saldo = float(saldo_var.get())
                data = data_var.get()
                last_saldo_var.set(f"{saldo:.2f}")
                last_data_var.set(data)
                db = {}
                if os.path.exists(DB_FILE):
                    with open(DB_FILE, "r", encoding="utf-8") as f:
                        db = json.load(f)
                db["saldo"] = saldo
                db["saldo_data"] = data
                with open(DB_FILE, "w", encoding="utf-8") as f:
                    json.dump(db, f, indent=2, ensure_ascii=False)
                custom_warning("Saldo aggiornato!", popup)
                saldo_var.set("") 
                aggiorna_saldi()
            except Exception:
                custom_warning("Saldo non valido!", popup)
    
        def esporta():
            sm = calcola_saldo("mese")
            sa = calcola_saldo("anno")
            st = calcola_saldo("totale")
            lines = [
                f"Saldo inserito il {last_data_var.get()}: {last_saldo_var.get()} €",
                f"Saldo nel mese: {sm:.2f} €",
                f"Saldo nell'anno: {sa:.2f} €",
                f"Saldo totale: {st:.2f} €",
            ]
            preview = tk.Toplevel(popup)
            preview.title("Preview esportazione saldo conto")
            preview.geometry("400x180")
            preview.transient(popup)
            preview.resizable(False, False)
            preview.grab_set()
            preview.update_idletasks()
            parent_x = popup.winfo_rootx()
            parent_y = popup.winfo_rooty()
            parent_w = popup.winfo_width()
            parent_h = popup.winfo_height()
            win_w = preview.winfo_width()
            win_h = preview.winfo_height()
            x = parent_x + (parent_w // 2) - (win_w // 2)
            y = parent_y + (parent_h // 2) - (win_h // 2)
            preview.geometry(f"+{x}+{y}")
    
            t = tk.Text(preview, font=("Arial", 10), height=6, wrap="word")
            t.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            t.insert(tk.END, "\n".join(lines))
            t.config(state="disabled")
    
            def do_save():
                file = filedialog.asksaveasfilename(
                    parent=preview,
                    title="Esporta Saldo Conto",
                    defaultextension=".txt",
                    filetypes=[("File di testo", "*.txt"), ("Tutti i file", "*.*")]
                )
                if file:
                    with open(file, "w", encoding="utf-8") as f:
                        f.write("\n".join(lines))
                    custom_warning("Saldo esportato", preview)
       
            frm = ttk.Frame(preview)
            frm.pack(fill=tk.X, padx=10, pady=8)
            ttk.Button(frm, text="Salva...", command=do_save, width=15).pack(side=tk.LEFT, padx=6)
            ttk.Button(frm, text="Chiudi", command=preview.destroy, width=12).pack(side=tk.RIGHT, padx=6)
    
            preview.lift()
            preview.focus_force()
            preview.attributes('-topmost', True)
            preview.after(100, lambda: preview.attributes('-topmost', False))
    
        frame_btn = ttk.Frame(frame)
        frame_btn.pack(pady=(24,0))
        ttk.Button(frame_btn, text="Salva saldo", command=salva_saldo).pack(side=tk.LEFT, padx=6)
        ttk.Button(frame_btn, text="Preview/Esporta", command=esporta).pack(side=tk.LEFT, padx=6)
        ttk.Button(frame_btn, text="Chiudi", command=popup.destroy).pack(side=tk.RIGHT, padx=6)
        
    def goto_today(self):
        today = datetime.date.today()
        self.cal.selection_set(today)
        self.stats_refdate = today
        self.update_stats()
        self.update_totalizzatore_anno_corrente()
        self.update_totalizzatore_mese_corrente()
        self.update_spese_mese_corrente()

    def open_compare_window(self):
        today = datetime.date.today()
        mese_oggi = f"{today.month:02d}"
        anno_oggi = str(today.year)
    
        compare_by_year = tk.BooleanVar(value=False)
    
        def get_rows(mese, anno, per_anno=False):
            rows = []
            for d in sorted(self.spese):
                if (per_anno and d.year == anno) or (not per_anno and d.month == mese and d.year == anno):
                    for voce in self.spese[d]:
                        cat = voce[0]
                        imp = voce[2]
                        tipo = voce[3]
                        data_pagamento = d.strftime("%d-%m-%Y")
                        entrata = imp if tipo == "Entrata" else 0
                        uscita = imp if tipo == "Uscita" else 0
                        rows.append((cat, data_pagamento, entrata, uscita))
            return rows
    
        win = tk.Toplevel(self)
        win.title("Confronta mesi/anni per categoria")
        win.geometry("1035x510")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
    
        frame = ttk.Frame(win)
        frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)
    
        anni_spese = set(d.year for d in self.spese.keys())
        anno_corrente = today.year
        anni = sorted(list(set(list(range(anno_corrente-10, anno_corrente+11))).union(anni_spese)))
        mesi = [f"{i:02d}" for i in range(1, 13)]
  
        mode_frame = ttk.Frame(frame)
        mode_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0,8))
        tk.Label(mode_frame, text="Modalità confronto:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0,10))
        ttk.Radiobutton(mode_frame, text="Mese", variable=compare_by_year, value=False, command=lambda: update_tables()).pack(side=tk.LEFT)
        ttk.Radiobutton(mode_frame, text="Anno", variable=compare_by_year, value=True, command=lambda: update_tables()).pack(side=tk.LEFT)
   
        left = ttk.Frame(frame)
        left.grid(row=2, column=0, sticky="nswe", padx=(0,16))
        left_select_frame = ttk.Frame(frame)
        left_select_frame.grid(row=1, column=0, sticky="ew", padx=(0,16), pady=(0,6))
        tk.Label(left_select_frame, text="Mese/Anno 1", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0,8))
        left_mese = tk.StringVar(value=mese_oggi)
        left_anno = tk.StringVar(value=anno_oggi)
        cb_lm = ttk.Combobox(left_select_frame, textvariable=left_mese, values=mesi, width=4, state="readonly", font=("Arial", 10))
        cb_la = ttk.Combobox(left_select_frame, textvariable=left_anno, values=[str(a) for a in anni], width=7, state="readonly", font=("Arial", 10))
        cb_lm.pack(side="left", padx=(0,3))
        cb_la.pack(side="left")
        def reset_left():
            left_mese.set(mese_oggi)
            left_anno.set(anno_oggi)
        ttk.Button(left_select_frame, text="Reset", command=reset_left, width=6).pack(side=tk.LEFT, padx=7)
        left_tree = ttk.Treeview(left, columns=("Categoria","Data","Entrata","Uscita"), show="headings", height=12)
        style = ttk.Style()
        style.configure("Big.Treeview.Heading", font=("Arial", 10, "bold"))
        style.configure("Big.Treeview", font=("Arial", 10))
        left_tree.configure(style="Big.Treeview")
        for col, w, anchor in [("Categoria",180,"w"),("Data",110,"center"),("Entrata",100,"e"),("Uscita",100,"e")]:
            left_tree.heading(col, text=col, anchor=anchor)
            left_tree.column(col, width=w, anchor=anchor, stretch=True)
        left_tree.pack(fill=tk.BOTH, expand=True)
        left_diff_lbl = tk.Label(left, text="", font=("Arial", 10, "bold"))
        left_diff_lbl.pack(pady=(4,0))
   
        right = ttk.Frame(frame)
        right.grid(row=2, column=1, sticky="nswe")
        right_select_frame = ttk.Frame(frame)
        right_select_frame.grid(row=1, column=1, sticky="ew", pady=(0,6))
        tk.Label(right_select_frame, text="Mese/Anno 2", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0,8))
        right_mese = tk.StringVar(value=mese_oggi)
        right_anno = tk.StringVar(value=anno_oggi)
        cb_rm = ttk.Combobox(right_select_frame, textvariable=right_mese, values=mesi, width=4, state="readonly", font=("Arial", 10))
        cb_ra = ttk.Combobox(right_select_frame, textvariable=right_anno, values=[str(a) for a in anni], width=7, state="readonly", font=("Arial", 10))
        cb_rm.pack(side="left", padx=(0,3))
        cb_ra.pack(side="left")
        def reset_right():
            right_mese.set(mese_oggi)
            right_anno.set(anno_oggi)
        ttk.Button(right_select_frame, text="Reset", command=reset_right, width=6).pack(side=tk.LEFT, padx=7)
        right_tree = ttk.Treeview(right, columns=("Categoria","Data","Entrata","Uscita"), show="headings", height=12)
        right_tree.configure(style="Big.Treeview")
        for col, w, anchor in [("Categoria",180,"w"),("Data",110,"center"),("Entrata",100,"e"),("Uscita",100,"e")]:
            right_tree.heading(col, text=col, anchor=anchor)
            right_tree.column(col, width=w, anchor=anchor, stretch=True)
        right_tree.pack(fill=tk.BOTH, expand=True)
        right_diff_lbl = tk.Label(right, text="", font=("Arial", 10, "bold"))
        right_diff_lbl.pack(pady=(4,0))
    
        def update_month_visibility():
            if compare_by_year.get():
                cb_lm.pack_forget()
                cb_rm.pack_forget()
            else:
                if not cb_lm.winfo_ismapped():
                    cb_lm.pack(side="left", padx=(0,3))
                if not cb_rm.winfo_ismapped():
                    cb_rm.pack(side="left", padx=(0,3))
    
        def update_tables():
            update_month_visibility()
            per_anno = compare_by_year.get()
            a1 = int(left_anno.get())
            a2 = int(right_anno.get())
            m1 = int(left_mese.get()) if not per_anno else 1
            m2 = int(right_mese.get()) if not per_anno else 1
            rows1 = get_rows(m1, a1, per_anno=per_anno)
            rows2 = get_rows(m2, a2, per_anno=per_anno)
            left_tree.delete(*left_tree.get_children())
            right_tree.delete(*right_tree.get_children())
            tot_ent1 = tot_usc1 = 0
            for cat, data, ent, usc in rows1:
                left_tree.insert("", "end", values=(cat, data, f"{ent:.2f}", f"{usc:.2f}"))
                tot_ent1 += ent
                tot_usc1 += usc
            diff1 = tot_ent1 - tot_usc1
            left_diff_lbl.config(text=f"Totale entrate: {tot_ent1:.2f}   Totale uscite: {tot_usc1:.2f}   Differenza: {diff1:.2f} €", fg="blue" if diff1>=0 else "red")
            tot_ent2 = tot_usc2 = 0
            for cat, data, ent, usc in rows2:
                right_tree.insert("", "end", values=(cat, data, f"{ent:.2f}", f"{usc:.2f}"))
                tot_ent2 += ent
                tot_usc2 += usc
            diff2 = tot_ent2 - tot_usc2
            right_diff_lbl.config(text=f"Totale entrate: {tot_ent2:.2f}   Totale uscite: {tot_usc2:.2f}   Differenza: {diff2:.2f} €", fg="blue" if diff2>=0 else "red")
    
        for var in [left_mese, left_anno, right_mese, right_anno, compare_by_year]:
            var.trace_add("write", lambda *a: update_tables())
        update_tables()
    
        def do_preview_export():
            per_anno = compare_by_year.get()
            a1 = int(left_anno.get())
            a2 = int(right_anno.get())
            m1 = int(left_mese.get()) if not per_anno else 1
            m2 = int(right_mese.get()) if not per_anno else 1
            rows1 = get_rows(m1, a1, per_anno=per_anno)
            rows2 = get_rows(m2, a2, per_anno=per_anno)
            lines = []
            if per_anno:
                lines.append(f"Confronto Anno {a1} vs {a2}\n")
            else:
                lines.append(f"Confronto {m1:02d}/{a1} vs {m2:02d}/{a2}\n")
            lines.append("Periodo 1:")
            lines.append(f"{'Categoria':18} {'Data':12} {'Entrata':>10} {'Uscita':>10}")
            for cat, data, ent, usc in rows1:
                lines.append(f"{cat:18.18} {data:12} {ent:10.2f} {usc:10.2f}")
            tot_ent1 = sum(ent for _,_,ent,_ in rows1)
            tot_usc1 = sum(usc for _,_,_,usc in rows1)
            diff1 = tot_ent1 - tot_usc1
            lines.append(f"Totale entrate: {tot_ent1:.2f}   Totale uscite: {tot_usc1:.2f}   Differenza: {diff1:.2f} €\n")
            lines.append("Periodo 2:")
            lines.append(f"{'Categoria':18} {'Data':12} {'Entrata':>10} {'Uscita':>10}")
            for cat, data, ent, usc in rows2:
                lines.append(f"{cat:18.18} {data:12} {ent:10.2f} {usc:10.2f}")
            tot_ent2 = sum(ent for _,_,ent,_ in rows2)
            tot_usc2 = sum(usc for _,_,_,usc in rows2)
            diff2 = tot_ent2 - tot_usc2
            lines.append(f"Totale entrate: {tot_ent2:.2f}   Totale uscite: {tot_usc2:.2f}   Differenza: {diff2:.2f} €")
            text = "\n".join(lines)
            prev = tk.Toplevel(win)
            prev.title("Preview/Esporta confronto")
            prev.geometry("1100x500")
            prev.transient(win)
            prev.resizable(False, False)
            prev.grab_set()
            t = tk.Text(prev, font=("Arial", 10), height=24, width=120, wrap="none")
            t.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            t.insert(tk.END, text)
            t.config(state="disabled")
            def do_save():
                file = filedialog.asksaveasfilename(
                    parent=prev,
                    title="Esporta confronto",
                    defaultextension=".txt",
                    filetypes=[("File di testo", "*.txt"), ("Tutti i file", "*.*")]
                )
                if file:
                    with open(file, "w", encoding="utf-8") as f:
                        f.write(text)
            frm = ttk.Frame(prev)
            frm.pack(fill=tk.X, padx=10, pady=8)
            ttk.Button(frm, text="Salva...", command=do_save, width=15).pack(side=tk.LEFT, padx=6)
            ttk.Button(frm, text="Chiudi", command=prev.destroy, width=12).pack(side=tk.RIGHT, padx=6)
            prev.lift()
            prev.focus_force()
            prev.attributes('-topmost', True)
            prev.after(100, lambda: prev.attributes('-topmost', False))
    
        btnframe = ttk.Frame(win)
        btnframe.pack(side=tk.BOTTOM, fill=tk.X, pady=(10,7))
        ttk.Button(btnframe, text="Preview/Esporta", command=do_preview_export, width=18).pack(side=tk.LEFT, padx=8)
        ttk.Button(btnframe, text="Chiudi", command=win.destroy, width=14).pack(side=tk.RIGHT, padx=8)




    def aggiorna(self, url, nome_file):
        """Scarica un file da GitHub e lo salva nella cartella corrente, sovrascrivendo l'esistente."""
        try:
          urllib.request.urlretrieve(url, nome_file)
          print(f"Download completato! {nome_file} è stato aggiornato.")
          self.show_custom_warning("Attenzione", "Aggiornamento completato con successo \n\n 🚀 🔄 Riavviare il programma per applicare le modifiche !")
          return
        except Exception as e:
          print(f"Errore durante il download: {str(e)}")
          self.show_custom_warning("Attenzione", "❌ Aggiornamento NON completato ! \n\n Sembra ci sia stato un problema. 😕")
          return



    def show_info_app(self):
            import tkinter as tk
            from tkinter import ttk
    
            info = (
                "Gestione Spese Pro\n"
                "Versione v.3.9.0\n\n"
                "Funzionalità principali:\n"
                "• Inserimento, modifica e cancellazione di spese ed entrate\n"
                "• Gestione categorie personalizzate\n"
                "• Ricorrenze (spese/entrate ripetute)\n"
                "• Esportazione dettagliata mese/anno\n"
                "• Statistiche giornaliere, mensili, annuali e totali\n"
                "• Backup, import/export database\n"
                "\n"
                "Sviluppo Python/Tkinter, 2023-2025\n"
                "\n"
                "© 2025 Tutti i diritti riservati\n\n"
                "• Usa i pulsanti qui sopra per scegliere la modalità di visualizzazione delle statistiche (Giorno, Mese, Anno, Totali).\n"
                "• Per esportare le statistiche del giorno selezionato, usa 'Esporta giorno da Calendario'.\n"
                "• Per esportare i dati di un mese o di un anno specifico, seleziona mese e anno dal riquadro sinistro e poi usa i pulsanti 'Esporta mese da estratto' o 'Esporta anno da estratto'.\n\n"
                 "• Questo programma si basa su Python. Puoi scaricare Python dal sito ufficiale: https://www.python.org/downloads/\n"
                 "• Inoltre, è necessario installare il pacchetto aggiuntivo tkcalendar..\n"
                 
                 "Su Linux:\n"
                 "  Apri il terminale e digita:\n"
                 "  sudo apt install tkcalendar\n"
                 "Su Windows:\n"
                 "  Apri il terminale (Prompt dei comandi) e digita:\n"
                 "  py -m pip install tkcalendar\n"
                 "\n"
                 "Assicurati di installare Python e tkcalendar prima di avviare il programma.\n"
            )
            info_win = tk.Toplevel(self)
            info_win.withdraw()
            info_win.title("Informazioni sulla applicazione")
            info_win.resizable(False, False)
            label = tk.Label(info_win, text=info, font=("Arial", 11), justify="left", padx=18, pady=18)
            label.pack()
            
            btn_aggiorna = ttk.Button(info_win, text="Aggiorna", command=lambda: self.aggiorna(GITHUB_FILE_URL, NOME_FILE))
            btn_aggiorna.pack(side=tk.LEFT, padx=100, pady=10)  # 🔹 Align left with spacing

            btn_chiudi = ttk.Button(info_win, text="Chiudi", command=info_win.destroy)
            btn_chiudi.pack(side=tk.RIGHT, padx=100, pady=10)  # 🔹 Align right with spacing

            info_win.update_idletasks()
    
            min_w, min_h = 1160, 640
            win_width = max(info_win.winfo_width(), min_w)
            win_height = max(info_win.winfo_height(), min_h)
            parent_x = self.winfo_rootx()
            parent_y = self.winfo_rooty()
            parent_width = self.winfo_width()
            parent_height = self.winfo_height()
    
            x = parent_x + (parent_width // 2) - (win_width // 2)
            y = parent_y + (parent_height // 2) - (win_height // 2)
            info_win.geometry(f"{win_width}x{win_height}+{x}+{y}")
    
            info_win.deiconify()
            info_win.grab_set()
            info_win.transient(self)
            info_win.focus_set()

    def save_db_and_notify(self):
            """Salva il database e mostra una finestra che conferma il salvataggio."""
            self.save_db()
            self.show_custom_warning("Attenzione", "Dati Salvati correttamente !")

    def check_file_db(self):
         if not os.path.exists(FILE_DB):
            with open(FILE_DB, "w") as file:
                file.write("")  # Crea un file vuoto
                self.utenze()
         else:
            now = datetime.datetime.now()
            threshold = now - datetime.timedelta(days=DAYS_THRESHOLD)
            file_mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(FILE_DB))
          
         if file_mod_time < threshold:
            self.show_custom_warning("Attenzione", "Ricordati di aggiornare i dati !")
            self.update_file_date()

    def update_file_date(self):
            now_timestamp = datetime.datetime.now().timestamp()
            os.utime(FILE_DB, (now_timestamp, now_timestamp))  # Aggiorna la data del file




    def utenze(self):
        self.check_file_db()  
        def get_consumi_per_anno(anno):
            return {
                "Acqua": [(f"{m:02d}/{anno}", 0.0, 0.0, 0.0) for m in range(1, 13)],
                "Luce":  [(f"{m:02d}/{anno}", 0.0, 0.0, 0.0) for m in range(1, 13)],
                "Gas":   [(f"{m:02d}/{anno}", 0.0, 0.0, 0.0) for m in range(1, 13)],
            }

        utenze = ["Acqua", "Luce", "Gas"]

        def carica_db():
            if os.path.exists(FILE_DB):
                try:
                    with open(FILE_DB, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    letture = data.get("letture_salvate", {u: {} for u in utenze})
                    for utenza in letture:
                        for anno in letture[utenza]:
                            norm = []
                            for r in letture[utenza][anno]:
                                if len(r) == 3:
                                    mese, prec, att = r
                                    consumo = float(att) - float(prec)
                                    norm.append((mese, float(prec), float(att), float(consumo)))
                                else:
                                    norm.append(tuple(r))
                            letture[utenza][anno] = norm
                    anagrafiche = data.get("anagrafiche", {u: {
                        "Ragione sociale": "",
                        "Telefono": "",
                        "Email": "",
                        "Numero contratto": "",
                        "POD": "",
                        "Note": ""
                    } for u in utenze})
                    for utenza in utenze:
                        if utenza not in anagrafiche:
                            anagrafiche[utenza] = {
                                "Ragione sociale": "",
                                "Telefono": "",
                                "Email": "",
                                "Numero contratto": "",
                                "POD": "",
                                "Note": ""
                            }
                        else:
                            for campo in ["Ragione sociale", "Telefono", "Email", "Numero contratto", "POD", "Note"]:
                                if campo not in anagrafiche[utenza]:
                                    anagrafiche[utenza][campo] = ""
                    return letture, anagrafiche
                except Exception as e:
                    #####self.show_custom_warning("Errore", "Errore lettura dati") ###se non vengono inseriti i dati darebbe un errore sempre
                    return {u: {} for u in utenze}, {u: {
                        "Ragione sociale": "",
                        "Telefono": "",
                        "Email": "",
                        "Numero contratto": "",
                        "POD": "",
                        "Note": ""
                    } for u in utenze}
            else:
                return {u: {} for u in utenze}, {u: {
                    "Ragione sociale": "",
                    "Telefono": "",
                    "Email": "",
                    "Numero contratto": "",
                    "POD": "",
                    "Note": ""
                } for u in utenze}

        def scrivi_db():
            try:
                data = {
                    "letture_salvate": {
                        u: {a: [list(r) for r in anni] for a, anni in letture_salvate[u].items()}
                        for u in utenze
                    },
                    "anagrafiche": anagrafiche
                }
                with open(FILE_DB, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=1, ensure_ascii=False)
            except Exception as e:
                 self.show_custom_warning("Errore", "Errore scrittura dati")
 
        letture_salvate, anagrafiche = carica_db()
        self.letture_salvate_utenze = letture_salvate
        self.anagrafiche_salvate_utenze = anagrafiche

        anno_corrente = str(datetime.datetime.now().year)
        year_current = int(anno_corrente)
        anni = [str(a) for a in range(year_current-10, year_current+10)]
        consumi = get_consumi_per_anno(anno_corrente)

        win = tk.Toplevel(self)
        win.title("Gestione Consumi Utenze")
        win.geometry("1300x700")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        top_controls = ttk.Frame(win)
        top_controls.pack(pady=(0, 6))
        ttk.Label(top_controls, text="Gestione Consumi Utenze", font=("Arial", 14, "bold")).pack(side=tk.LEFT, padx=(0, 25))
        ttk.Label(top_controls, text="Anno: ").pack(side=tk.LEFT)
        anno_var = tk.StringVar(value=anno_corrente)
        

        def salva_letture_preview(txt, preview_win):
            """ Salva il contenuto della preview in un file e forza la finestra di salvataggio in primo piano """

            preview_win.wm_attributes('-topmost', 1)  # Forza la preview a rimanere sopra tutto

            file = filedialog.asksaveasfilename(
                parent=preview_win,  # Associa il dialogo direttamente alla finestra di preview
                title="Salva Preview",
                defaultextension=".txt",
                filetypes=[("File di testo", "*.txt"), ("Tutti i file", "*.*")]
            )

            preview_win.wm_attributes('-topmost', 0)  # Rimuove la proprietà topmost dopo il salvataggio

            if file:
                with open(file, "w", encoding="utf-8") as f:
                    f.write(txt.get("1.0", tk.END))  # Esporta tutto il contenuto della Textbox
                    preview_win.destroy()
                    self.show_custom_warning("Esportazione completata", f"Statistiche esportate in {file}")

        def esporta_preview():
            """ Crea la finestra di anteprima e aggiunge pulsanti per il salvataggio """
            preview_win = tk.Toplevel(win)
            preview_win.title("Preview Esportazione")
            preview_win.geometry("700x500")
            preview_win.after(10, lambda: preview_win.focus_set()) 
            screen_width = preview_win.winfo_screenwidth()
            screen_height = preview_win.winfo_screenheight()
            x = (screen_width - 700) // 2
            y = (screen_height - 500) // 2
            preview_win.geometry(f"700x500+{x}+{y}")
            txt = tk.Text(preview_win, font=("Arial", 10), wrap="none")
            txt.pack(fill=tk.BOTH, expand=True)
            anno_x = anno_var.get()  
            txt.insert(tk.END, f"Estratto letture per anno {anno_x}\n\n")
            for utenza in utenze:
                txt.insert(tk.END, f"{utenza}\n")
                txt.insert(tk.END, f"{'Mese':10s} {'Prec':>10s} {'Att':>10s} {'Consumo':>10s}\n")
                txt.insert(tk.END, "-" * 45 + "\n")
                for iid in self.trees[utenza].get_children():
                    mese, prec, att, cons = self.trees[utenza].item(iid)['values']
                    txt.insert(tk.END, f"{mese:10s} {float(prec):10.2f} {float(att):10.2f} {float(cons):10.2f}\n")
                txt.insert(tk.END, "\n")
            txt.config(state="disabled") 
            btn_frame = ttk.Frame(preview_win)
            btn_frame.pack(fill=tk.X, pady=12)
            ttk.Button(btn_frame, text="Salva", command=lambda: salva_letture_preview(txt, preview_win)).grid(row=0, column=0, padx=10)
            ttk.Button(btn_frame, text="Chiudi", command=preview_win.destroy).grid(row=0, column=1, padx=10)
            preview_win.focus_set()
            preview_win.lift()
            preview_win.attributes('-topmost', True)
            preview_win.after(100, lambda: preview_win.attributes('-topmost', False))

        def chiudi():
            win.destroy()

        def cambia_anno(*args):
            nonlocal consumi
            for utenza in utenze:
                if self.trees[utenza].get_children():
                    anno_attuale = self.trees[utenza].item(self.trees[utenza].get_children()[0])['values'][0].split("/")[1]
                    letture_salvate[utenza][anno_attuale] = [
                        tuple(self.trees[utenza].item(iid)['values']) for iid in self.trees[utenza].get_children()
                    ]
            scrivi_db()
            for utenza in utenze:
                self.trees[utenza].delete(*self.trees[utenza].get_children())
            anno_sel = anno_var.get()
            consumi = get_consumi_per_anno(anno_sel)
            for utenza in utenze:
                if (anno_sel not in letture_salvate[utenza]) or (not letture_salvate[utenza][anno_sel]):
                    letture_salvate[utenza][anno_sel] = [
                        (f"{m:02d}/{anno_sel}", 0.0, 0.0, 0.0) for m in range(1, 13)
                    ]
                righe = letture_salvate[utenza][anno_sel]
                righe_norm = []
                for r in righe:
                    if len(r) == 3:
                        mese, prec, att = r
                        consumo = float(att) - float(prec)
                        righe_norm.append((mese, float(prec), float(att), float(consumo)))
                    else:
                        righe_norm.append(tuple(r))
                letture_salvate[utenza][anno_sel] = righe_norm
                for mese, prec, att, consumo in righe_norm:
                    self.trees[utenza].insert("", "end", values=(mese, float(prec), float(att), float(consumo)))

        anno_cb = ttk.Combobox(top_controls, values=anni, textvariable=anno_var, state="readonly", width=8)
        anno_cb.pack(side=tk.LEFT)
        def reset_anno():
            anno_var.set(anno_corrente)
       
        ttk.Button(top_controls, text="Reset anno", command=reset_anno).pack(side=tk.LEFT, padx=7)
        ttk.Button(top_controls, text="Esporta", command=esporta_preview).pack(side=tk.LEFT, padx=7)
        ttk.Button(top_controls, text="Analizza", command=lambda: crea_tabella_consumi(FILE_DB)).pack(side=tk.LEFT, padx=7)
        ttk.Button(top_controls, text="Chiudi", command=chiudi).pack(side=tk.LEFT, padx=7)

        anno_var.trace_add("write", cambia_anno)

        main_frame = ttk.Frame(win)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=6)
        for c in range(len(utenze)):
            main_frame.grid_columnconfigure(c, weight=1)

        colori = {"Acqua": "#ccefff", "Luce": "#fff9cc", "Gas": "#ffe0cc"}
        self.trees = {}
        anag_entries = {}

        def crea_tabella_consumi(FILE_DB):
            """Mostra i consumi di Luce, Acqua e Gas in una finestra con scrolling verticale e orizzontale."""

            try:
                with open(FILE_DB, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    letture_salvate = data.get("letture_salvate", {})
            except Exception as e:
                print(f"❌ Errore lettura file: {e}")
                return
            utenze = ["Acqua", "Luce", "Gas"]
            win = tk.Tk()
            win.title("Consumi Utenze - Anteprima")
            win.geometry("1200x600")
            screen_width = win.winfo_screenwidth()
            screen_height = win.winfo_screenheight()
            x_coordinate = (screen_width - 1200) // 2
            y_coordinate = (screen_height - 600) // 2
            win.geometry(f"1200x600+{x_coordinate}+{y_coordinate}")
            frame_principale = ttk.Frame(win)
            frame_principale.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            canvas = tk.Canvas(frame_principale)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scroll_y = ttk.Scrollbar(frame_principale, orient=tk.VERTICAL, command=canvas.yview)
            scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
            canvas.configure(yscrollcommand=scroll_y.set)
            scroll_x = ttk.Scrollbar(frame_principale, orient=tk.HORIZONTAL, command=canvas.xview)
            scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
            canvas.configure(xscrollcommand=scroll_x.set)
            frame_interno = ttk.Frame(canvas)
            canvas.create_window((0, 0), window=frame_interno, anchor="nw")

            for utenza in utenze:
                frame_tabella = ttk.Frame(frame_interno)
                frame_tabella.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
                ttk.Label(frame_tabella, text=f"Consumi {utenza}", font=("Arial", 12, "bold")).pack(pady=5)
                colonne = ["Anno"] + ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic", "Totale"]
                tree = ttk.Treeview(frame_tabella, columns=colonne, show="headings")
                for col in colonne:
                    tree.heading(col, text=col)
                    tree.column(col, width=80, anchor="center") 
                tree.pack(fill=tk.BOTH, expand=True)
                for anno in sorted(letture_salvate.get(utenza, {}).keys(), reverse=True):
                    row = [anno]
                    tot_consumi = 0.0
                    for mese in range(1, 13):
                        mese_str = f"{mese:02d}/{anno}"
                        consumo = sum(float(r[3]) for r in letture_salvate.get(utenza, {}).get(anno, []) if r[0] == mese_str)
                        row.append(consumo)
                        tot_consumi += consumo
                    row.append(tot_consumi) 
                    tree.insert("", tk.END, values=row)
                tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
                tree.yview_moveto(0)
            frame_bottoni = ttk.Frame(win)
            frame_bottoni.pack(fill=tk.X, padx=10, pady=10)
            ttk.Button(frame_bottoni, text="Salva", command=lambda: salva_dati_letture(letture_salvate)).pack(side=tk.LEFT, padx=10)
            ttk.Button(frame_bottoni, text="Chiudi", command=win.destroy).pack(side=tk.RIGHT, padx=10)
            frame_interno.update_idletasks()
            canvas.config(scrollregion=canvas.bbox("all"))
            canvas.yview_moveto(0)
            win.mainloop()

        def salva_dati_letture(letture_salvate):
            """Salva i dati in un file scelto dall'utente in formato testo."""
            win.focus_force()  # Porta la finestra in primo piano
    
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("File di testo", "*.txt"), ("Tutti i file", "*.*")],
                title="Salva i dati dei consumi"
            )
            if not file_path:
                print("❌ Salvataggio annullato dall'utente.")
                return
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    for utenza, anni in letture_salvate.items():
                        f.write(f"Consumi {utenza}:\n")
                        for anno, dati in sorted(anni.items(), reverse=True):
                            f.write(f"  {anno}:\n")
                            for r in dati:
                                f.write(f"    {r[0]} - {r[3]} {utenza}\n")
                        f.write("\n")       
                self.show_custom_warning("Esportazione", f"Statistiche esportate in {file_path}")
            except Exception as e:
                self.show_custom_warning("Esportazione", f"Errore durante il salvataggio {e}")

        def centra_su_padre(finestra, padre):
            padre.update_idletasks()
            larghezza = finestra.winfo_reqwidth()
            altezza = finestra.winfo_reqheight()
            px = padre.winfo_rootx() + (padre.winfo_width() // 2) - (larghezza // 2)
            py = padre.winfo_rooty() + (padre.winfo_height() // 2) - (altezza // 2)
            finestra.geometry(f"+{px}+{py}")

        def salva_letture_utenza(utenza):
            anno_sel = anno_var.get()
            letture_salvate[utenza][anno_sel] = [
                tuple(self.trees[utenza].item(iid)['values']) for iid in self.trees[utenza].get_children()
            ]
            scrivi_db()

        def salva_anagrafica_utenza(utenza):
            for field, ent in anag_entries[utenza].items():
                if field == "Note":
                    anagrafiche[utenza][field] = ent.get("1.0", "end-1c")
                else:
                    anagrafiche[utenza][field] = ent.get()
            scrivi_db()

        def apri_modale(utenza):
            selected = self.trees[utenza].focus()
            if not selected:
                  self.show_custom_warning("Errore", "Seleziona un mese dalla tabella")
                  return
            item = self.trees[utenza].item(selected)
            mese, prec, att, _ = item['values']

            items = self.trees[utenza].get_children()
            idx = items.index(selected)

            if idx > 0:
                prev_item = self.trees[utenza].item(items[idx - 1])
                prev_att = float(prev_item['values'][2])
                prec = prev_att

            modal = tk.Toplevel(win)
            modal.title(f"Modifica letture {utenza} - {mese}")
            modal.geometry("520x220")
            modal.resizable(False, False)
            modal.transient(win)
            modal.grab_set()
            centra_su_padre(modal, win)

            tk.Label(modal, text=f"{utenza} - {mese}", font=("Arial", 12, "bold")).pack(pady=10)
            tk.Label(modal, text="Lettura precedente:").pack()
            prec_var = tk.DoubleVar(value=prec)
            e_prec = tk.Entry(modal, textvariable=prec_var, font=("Arial", 10), width=22)
            e_prec.pack()
            tk.Label(modal, text="Lettura attuale:").pack()
            att_var = tk.DoubleVar(value=att)
            tk.Entry(modal, textvariable=att_var, font=("Arial", 10), width=22).pack()
            
            def salva():
                try:
                    p = float(prec_var.get())
                    a = float(att_var.get())
                    if a < p:
                        conferma = tk.Toplevel(modal)
                        conferma.title("Conferma Forzatura")
                        conferma.geometry("350x120")
                        conferma.resizable(False, False)
                        conferma.transient(modal)
                        conferma.grab_set()
                        centra_su_padre(conferma, modal)
                        fnt = ("Arial", 9, "bold")
                        msg = tk.Label(conferma,
                                       text="La lettura attuale è minore della precedente.\nVuoi forzare l'inserimento?",
                                       font=fnt, fg="red")
                        msg.pack(pady=15)
                        btn_frame = ttk.Frame(conferma)
                        btn_frame.pack()
                        def ok():
                            consumo = round(a - p, 2)
                            self.trees[utenza].item(selected, values=(mese, p, a, consumo))
                            if idx + 1 < len(items):
                                next_item = self.trees[utenza].item(items[idx + 1])
                                next_mese, _, next_att, _ = next_item['values']
                                next_att_f = float(next_att)
                                next_cons = round(next_att_f - a, 2)
                                self.trees[utenza].item(items[idx + 1], values=(next_mese, a, next_att_f, next_cons))
                            conferma.destroy()
                            modal.destroy()
                            salva_letture_utenza(utenza)
                        def annulla():
                            conferma.destroy()
                        ttk.Button(btn_frame, text="Forza", command=ok).pack(side=tk.LEFT, padx=12)
                        ttk.Button(btn_frame, text="Annulla", command=annulla).pack(side=tk.LEFT, padx=12)
                        return
                    consumo = round(a - p, 2)
                    self.trees[utenza].item(selected, values=(mese, p, a, consumo))
                    if idx + 1 < len(items):
                        next_item = self.trees[utenza].item(items[idx + 1])
                        next_mese, _, next_att, _ = next_item['values']
                        next_att_f = float(next_att)
                        next_cons = round(next_att_f - a, 2)
                        self.trees[utenza].item(items[idx + 1], values=(next_mese, a, next_att_f, next_cons))
                    modal.destroy()
                    salva_letture_utenza(utenza)
                except ValueError:
                    self.show_custom_warning("Errore", "Valori non validi")

            ttk.Button(modal, text="Salva", command=salva).pack(pady=10)

        for idx, utenza in enumerate(utenze):
            frame = tk.Frame(main_frame, bg=colori[utenza], bd=2, relief="groove")
            frame.grid(row=0, column=idx, padx=8, pady=6, sticky="nswe")

            top_btn_fr = tk.Frame(frame, bg=colori[utenza])
            top_btn_fr.pack(fill="x", padx=4, pady=(2,0))
            btn_mod_letture = tk.Button(
                top_btn_fr,
                text="Modifica Letture",
                bg="red",
                fg="white",
                activebackground="#c00",
                font=("Arial", 11, "bold"),
                command=lambda u=utenza: apri_modale(u)
            )
            btn_mod_letture.pack(side=tk.LEFT, anchor="nw", padx=2, pady=2)

            tk.Label(frame, text=utenza, font=("Arial", 12, "bold"), bg=colori[utenza]).pack(pady=(2,2))

            tree = ttk.Treeview(frame, columns=("Mese", "Prec", "Att", "Consumo"), show="headings", height=13)
            tree.heading("Mese", text="Mese")
            tree.heading("Prec", text="Precedente")
            tree.heading("Att", text="Attuale")
            tree.heading("Consumo", text="Consumo")
            tree.column("Mese", width=68, anchor="center")
            tree.column("Prec", width=70, anchor="e")
            tree.column("Att", width=70, anchor="e")
            tree.column("Consumo", width=85, anchor="e")
            tree.pack(padx=8, pady=6, fill="both", expand=True)

            anno_sel = anno_var.get()
            if (anno_sel not in letture_salvate[utenza]) or (not letture_salvate[utenza][anno_sel]):
                letture_salvate[utenza][anno_sel] = [
                    (f"{m:02d}/{anno_sel}", 0.0, 0.0, 0.0) for m in range(1, 13)
                ]
            righe = letture_salvate[utenza][anno_sel]
            righe_norm = []
            for r in righe:
                if len(r) == 3:
                    mese, prec, att = r
                    consumo = float(att) - float(prec)
                    righe_norm.append((mese, float(prec), float(att), float(consumo)))
                else:
                    righe_norm.append(tuple(r))
            letture_salvate[utenza][anno_sel] = righe_norm
            for mese, prec, att, consumo in righe_norm:
                tree.insert("", "end", values=(mese, float(prec), float(att), float(consumo)))

            self.trees[utenza] = tree

            def salva_letture_local(u=utenza):
                salva_letture_utenza(u)
                self.show_custom_warning("Attenzione", f"Dati {u} Salvati Corretamente !")
                
            ttk.Button(frame, text="Salva Letture", width=16, command=salva_letture_local).pack(pady=(0,6))

            anag_frame = tk.Frame(frame, bg=colori[utenza], bd=1, relief="ridge")
            anag_frame.pack(fill="both", padx=4, pady=(0,8))

            anag_entries[utenza] = {}
            campi = [
                ("Ragione sociale", 32),
                ("Telefono", 18),
                ("Email", 32),
                ("Numero contratto", 18),
                ("POD", 18)
            ]
            for row, (label, width) in enumerate(campi):
                tk.Label(anag_frame, text=label+":", font=("Arial", 10, "bold"), bg=colori[utenza]).grid(row=row, column=0, sticky="e", padx=3, pady=1)
                ent = tk.Entry(anag_frame, width=width)
                ent.grid(row=row, column=1, sticky="w", padx=3, pady=1)
                ent.insert(0, anagrafiche[utenza][label])
                ent.config(state="readonly")
                anag_entries[utenza][label] = ent

            tk.Label(anag_frame, text="Note:", font=("Arial", 10, "bold"), bg=colori[utenza]).grid(row=5, column=0, sticky="ne", padx=3, pady=(5,1))
            note_txt = tk.Text(anag_frame, width=40, height=3, wrap="word")
            note_txt.grid(row=5, column=1, sticky="w", padx=3, pady=(5,1))
            note_txt.insert("1.0", anagrafiche[utenza]["Note"])
            note_txt.config(state="disabled")
            anag_entries[utenza]["Note"] = note_txt

            btns = ttk.Frame(anag_frame)
            btns.grid(row=6, column=0, columnspan=2, pady=(5,5))

            def set_editable(editable, u=utenza):
                for k, ent in anag_entries[u].items():
                    if k == "Note":
                        ent.config(state="normal" if editable else "disabled")
                    else:
                        ent.config(state="normal" if editable else "readonly")

            def salva_dati(u=utenza):
                for field, ent in anag_entries[u].items():
                    if field == "Note":
                        anagrafiche[u][field] = ent.get("1.0", "end-1c")
                    else:
                        anagrafiche[u][field] = ent.get()
                set_editable(False, u)
                scrivi_db()
                #self.show_db_saved_popup()
                self.show_custom_warning("Attenzione", f"Dati {u} Salvati correttamente !")

            def modifica_dati(u=utenza):
                set_editable(True, u)

 
def check_and_install_python():
    """ Verifica se Python è installato e lo installa se mancante """

    # Controlla se l'eseguibile Python è disponibile
    python_path = shutil.which("python") or shutil.which("python3")
    
    if python_path:
        print(f"Python è già installato: {python_path}")
    else:
        print("Python non è installato. Tentativo di installazione...")

        if sys.platform.startswith("win"):
            subprocess.run(["winget", "install", "Python.Python"], check=True)  # Installa Python su Windows
        elif sys.platform.startswith("linux"):
            subprocess.run(["sudo", "apt", "install", "-y", "python3"], check=True)  # Installa Python su Linux (Debian-based)
        elif sys.platform.startswith("darwin"):
            subprocess.run(["brew", "install", "python"], check=True)  # Installa Python su macOS
        else:
            print("Sistema operativo non supportato per l'installazione automatica.")
        
        print("Installazione completata. Riavvia il terminale per aggiornare i percorsi.")

def install_tkcalendar():
    """ Controlla se tkcalendar è installato e, se mancante, lo installa automaticamente """
    package_name = "tkcalendar"
    # Verifica se il pacchetto è installato
    if importlib.util.find_spec(package_name) is None:
        print(f"{package_name} non è installato. Installazione in corso...")
        # Esegue il comando di installazione
        subprocess.run([sys.executable, "-m", "pip", "install", package_name], check=True)
        print(f"{package_name} installato con successo!")
    else:
        print(f"{package_name} è già installato.")

def install_psutil():
    """ Controlla se psutil è installato e, se mancante, lo installa automaticamente """
    package_name = "psutil"
    # Verifica se il pacchetto è installato
    if importlib.util.find_spec(package_name) is None:
        print(f"{package_name} non è installato. Installazione in corso...")
        # Esegue il comando di installazione
        subprocess.run([sys.executable, "-m", "pip", "install", package_name], check=True)
        print(f"{package_name} installato con successo!")
    else:
        print(f"{package_name} è già installato.")

def check_single_instance():
    """ Impedisce avvio multiplo su Windows Linux Osx"""
    if sys.platform.startswith("win"):
        # 🔒 Controllo su Windows con Mutex
        mutex_name = "Global\\AppMutex"
        mutex = ctypes.windll.kernel32.CreateMutexW(None, True, mutex_name)
        if ctypes.windll.kernel32.GetLastError() == 183:  # Il mutex esiste già
            print("Un'altra istanza è già in esecuzione!")
            show_warning_popup()
            sys.exit(1)
        return  # Evita il controllo successivo
    else:
         current_pid = os.getpid()
         current_script = os.path.abspath(sys.argv[0])
         for proc in psutil.process_iter(attrs=["pid", "cmdline"]):  # Usa 'cmdline' su Linux/macOS
          try:
            cmd = proc.info["cmdline"]
            if cmd and current_script in cmd and proc.info["pid"] != current_pid:
                print("Un'altra istanza è già in esecuzione!")
                show_warning_popup()
                sys.exit(1)
          except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
         return  # Evita il controllo successivo

def show_warning_popup():
    """ Mostra un messaggio di avviso con tkinter """
    root = tk.Tk()
    root.withdraw()  # Nasconde la finestra principale
    messagebox.showwarning("Attenzione", "Oops! \n\nSembra che il programma sia già aperto. \n\nChiudilo e riprova! \n\n Gestione Spese Pro \n© 2025 Tutti i diritti riservati \n")
    sys.exit(1)







# Test della funzione
if __name__ == "__main__":
    check_single_instance()
    print("Programma avviato correttamente.")

if __name__ == "__main__":
    check_and_install_python()
    install_tkcalendar()
    install_psutil()
    print("Programma avviato.")
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)
app = GestioneSpese()
app.mainloop()
    
    
