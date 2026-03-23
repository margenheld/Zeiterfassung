# src/ui.py
import tkinter as tk
from tkinter import messagebox, ttk
import calendar
import datetime
from src.storage import Storage
from src.time_utils import calculate_hours, validate_entry

DAYS_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONTHS_DE = [
    "", "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]

# Dark Modern color palette
BG = "#1a1a2e"
CELL_BG = "#16213e"
WEEKEND_BG = "#0f3460"
ACCENT = "#e94560"
TEXT = "#e0e0e0"
TEXT_MUTED = "#888888"
ENTRY_BG = "#1a3a5c"
WEEKEND_ENTRY_BG = "#1a3050"
FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_HEADER = ("Segoe UI", 16, "bold")
FONT_FOOTER = ("Segoe UI", 12, "bold")

# Time dropdown values (5-min steps, 00:00 - 23:55)
TIME_VALUES = [f"{h:02d}:{m:02d}" for h in range(24) for m in range(0, 60, 5)]


PAUSE_VALUES = [str(m) for m in range(0, 125, 5)]


class App:
    def __init__(self, root, storage, settings):
        self.root = root
        self.storage = storage
        self.settings = settings
        self.root.title("Zeiterfassung")
        self.root.configure(bg=BG)

        today = datetime.date.today()
        self.year = today.year
        self.month = today.month

        self._build_header()
        self._build_grid()
        self._build_footer()
        self._refresh()

    def _build_header(self):
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill=tk.X, padx=10, pady=(10, 0))

        tk.Button(
            frame, text="\u2039", command=self._prev_month, width=3,
            font=FONT_BOLD, bg=CELL_BG, fg=ACCENT,
            activebackground=ENTRY_BG, activeforeground=ACCENT,
            relief=tk.FLAT, cursor="hand2"
        ).pack(side=tk.LEFT)

        self.header_label = tk.Label(
            frame, text="", font=FONT_HEADER, bg=BG, fg="#ffffff"
        )
        self.header_label.pack(side=tk.LEFT, expand=True)

        tk.Button(
            frame, text="\u2699", command=self._open_settings, width=3,
            font=FONT_BOLD, bg=CELL_BG, fg=TEXT_MUTED,
            activebackground=ENTRY_BG, activeforeground=TEXT,
            relief=tk.FLAT, cursor="hand2"
        ).pack(side=tk.RIGHT)

        tk.Button(
            frame, text="\u203a", command=self._next_month, width=3,
            font=FONT_BOLD, bg=CELL_BG, fg=ACCENT,
            activebackground=ENTRY_BG, activeforeground=ACCENT,
            relief=tk.FLAT, cursor="hand2"
        ).pack(side=tk.RIGHT, padx=(0, 5))

    def _build_grid(self):
        self.grid_frame = tk.Frame(self.root, bg=BG)
        self.grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def _build_footer(self):
        self.footer_label = tk.Label(
            self.root, text="Gesamt: 0.0h", font=FONT_FOOTER,
            bg=BG, fg=ACCENT
        )
        self.footer_label.pack(pady=(0, 10))

    def _prev_month(self):
        if self.month == 1:
            self.month = 12
            self.year -= 1
        else:
            self.month -= 1
        self._refresh()

    def _next_month(self):
        if self.month == 12:
            self.month = 1
            self.year += 1
        else:
            self.month += 1
        self._refresh()

    def _apply_combobox_style(self, dialog):
        style = ttk.Style(dialog)
        style.theme_use("clam")
        style.configure(
            "Dark.TCombobox",
            fieldbackground=CELL_BG, background=CELL_BG,
            foreground=TEXT, arrowcolor=ACCENT,
            bordercolor=TEXT_MUTED, lightcolor=CELL_BG, darkcolor=CELL_BG,
            selectbackground=ENTRY_BG, selectforeground=TEXT
        )
        style.map("Dark.TCombobox",
            fieldbackground=[("readonly", CELL_BG)],
            selectbackground=[("readonly", CELL_BG)],
            selectforeground=[("readonly", TEXT)],
            bordercolor=[("focus", ACCENT)],
        )
        dialog.option_add("*TCombobox*Listbox.background", CELL_BG)
        dialog.option_add("*TCombobox*Listbox.foreground", TEXT)
        dialog.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        dialog.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        dialog.option_add("*TCombobox*Listbox.font", FONT)

    def _open_settings(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Einstellungen")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.configure(bg=BG)

        self._apply_combobox_style(dialog)

        # Email
        tk.Label(
            dialog, text="E-Mail:", font=FONT, bg=BG, fg=TEXT
        ).grid(row=0, column=0, padx=10, pady=8, sticky="w")

        email_var = tk.StringVar(value=self.settings.get("email"))
        tk.Entry(
            dialog, textvariable=email_var, width=25, font=FONT,
            bg=CELL_BG, fg=TEXT, insertbackground=ACCENT,
            relief=tk.FLAT, highlightbackground=TEXT_MUTED,
            highlightcolor=ACCENT, highlightthickness=1
        ).grid(row=0, column=1, padx=10, pady=8)

        # Default pause
        tk.Label(
            dialog, text="Standard-Pause (Min):", font=FONT, bg=BG, fg=TEXT
        ).grid(row=1, column=0, padx=10, pady=8, sticky="w")

        pause_var = tk.StringVar(value=str(self.settings.get("default_pause")))
        ttk.Combobox(
            dialog, textvariable=pause_var, values=PAUSE_VALUES,
            width=8, font=FONT, style="Dark.TCombobox", state="readonly"
        ).grid(row=1, column=1, padx=10, pady=8)

        def save_settings():
            self.settings.set("email", email_var.get())
            self.settings.set("default_pause", int(pause_var.get()))
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=BG)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=12)

        tk.Button(
            btn_frame, text="Speichern", command=save_settings, font=FONT_BOLD,
            bg=ACCENT, fg="#ffffff",
            activebackground="#c73550", activeforeground="#ffffff",
            relief=tk.FLAT, padx=16, pady=4, cursor="hand2"
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame, text="Abbrechen", command=dialog.destroy, font=FONT,
            bg=CELL_BG, fg=TEXT,
            activebackground=ENTRY_BG, activeforeground=TEXT,
            relief=tk.FLAT, padx=16, pady=4, cursor="hand2"
        ).pack(side=tk.LEFT, padx=5)

    def _refresh(self):
        self.header_label.config(text=f"{MONTHS_DE[self.month]} {self.year}")

        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        # Column headers
        for col, day_name in enumerate(DAYS_DE):
            fg = TEXT_MUTED if col < 5 else "#6c6c80"
            lbl = tk.Label(
                self.grid_frame, text=day_name, font=FONT_BOLD,
                bg=BG, fg=fg
            )
            lbl.grid(row=0, column=col, sticky="nsew", padx=2, pady=2)

        # Calendar weeks
        cal = calendar.Calendar(firstweekday=0)
        entries = self.storage.get_all()
        total_hours = 0.0

        for row, week in enumerate(cal.monthdayscalendar(self.year, self.month), start=1):
            for col, day in enumerate(week):
                if day == 0:
                    lbl = tk.Label(
                        self.grid_frame, text="", bg=BG, relief=tk.FLAT
                    )
                    lbl.grid(row=row, column=col, sticky="nsew", padx=2, pady=2)
                    continue

                date_str = f"{self.year}-{self.month:02d}-{day:02d}"
                entry = entries.get(date_str)
                is_weekend = col >= 5

                text = str(day)
                fg = TEXT
                if is_weekend and not entry:
                    fg = "#6c6c80"

                if entry:
                    pause = entry.get("pause", 0)
                    hours = calculate_hours(entry["start"], entry["end"], pause_minutes=pause)
                    text += f"\n{hours}h"
                    total_hours += hours
                    bg = WEEKEND_ENTRY_BG if is_weekend else ENTRY_BG
                    cell = tk.Label(
                        self.grid_frame, text=text, font=FONT,
                        bg=bg, fg=TEXT, relief=tk.SOLID,
                        highlightbackground=ACCENT, highlightthickness=1,
                        width=8, height=3, cursor="hand2"
                    )
                else:
                    bg = WEEKEND_BG if is_weekend else CELL_BG
                    cell = tk.Label(
                        self.grid_frame, text=text, font=FONT,
                        bg=bg, fg=fg, relief=tk.FLAT,
                        width=8, height=3, cursor="hand2"
                    )

                cell.grid(row=row, column=col, sticky="nsew", padx=2, pady=2)
                cell.bind("<Button-1>", lambda e, d=date_str: self._open_dialog(d))

        self.footer_label.config(text=f"Gesamt: {round(total_hours, 2)}h")

        for col in range(7):
            self.grid_frame.columnconfigure(col, weight=1)

    def _open_dialog(self, date_str):
        dialog = tk.Toplevel(self.root)
        dialog.title(date_str)
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.configure(bg=BG)

        entry = self.storage.get(date_str)

        self._apply_combobox_style(dialog)

        tk.Label(
            dialog, text="Start:", font=FONT,
            bg=BG, fg=TEXT
        ).grid(row=0, column=0, padx=10, pady=8, sticky="w")

        start_var = tk.StringVar(value=entry["start"] if entry else "08:00")
        start_cb = ttk.Combobox(
            dialog, textvariable=start_var, values=TIME_VALUES,
            width=8, font=FONT, style="Dark.TCombobox", state="readonly"
        )
        start_cb.grid(row=0, column=1, padx=10, pady=8)

        tk.Label(
            dialog, text="Ende:", font=FONT,
            bg=BG, fg=TEXT
        ).grid(row=1, column=0, padx=10, pady=8, sticky="w")

        end_var = tk.StringVar(value=entry["end"] if entry else "17:00")
        end_cb = ttk.Combobox(
            dialog, textvariable=end_var, values=TIME_VALUES,
            width=8, font=FONT, style="Dark.TCombobox", state="readonly"
        )
        end_cb.grid(row=1, column=1, padx=10, pady=8)

        # Pause dropdown
        tk.Label(
            dialog, text="Pause (Min):", font=FONT,
            bg=BG, fg=TEXT
        ).grid(row=2, column=0, padx=10, pady=8, sticky="w")

        default_pause = self.settings.get("default_pause")
        if entry and "pause" in entry:
            current_pause = str(entry["pause"])
        else:
            current_pause = str(default_pause) if not entry else "0"
        pause_var = tk.StringVar(value=current_pause)

        pause_cb = ttk.Combobox(
            dialog, textvariable=pause_var, values=PAUSE_VALUES,
            width=8, font=FONT, style="Dark.TCombobox", state="readonly"
        )
        pause_cb.grid(row=2, column=1, padx=10, pady=8)

        def save():
            ok, msg = validate_entry(start_var.get(), end_var.get())
            if not ok:
                messagebox.showerror("Fehler", msg, parent=dialog)
                return
            self.storage.save(date_str, start_var.get(), end_var.get(), pause=int(pause_var.get()))
            dialog.destroy()
            self._refresh()

        def delete():
            self.storage.delete(date_str)
            dialog.destroy()
            self._refresh()

        btn_frame = tk.Frame(dialog, bg=BG)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=12)

        tk.Button(
            btn_frame, text="Speichern", command=save, font=FONT_BOLD,
            bg=ACCENT, fg="#ffffff",
            activebackground="#c73550", activeforeground="#ffffff",
            relief=tk.FLAT, padx=16, pady=4, cursor="hand2"
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame, text="Löschen", command=delete, font=FONT,
            bg=CELL_BG, fg=TEXT,
            activebackground=ENTRY_BG, activeforeground=TEXT,
            relief=tk.FLAT, padx=16, pady=4, cursor="hand2"
        ).pack(side=tk.LEFT, padx=5)
