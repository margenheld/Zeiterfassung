# src/ui.py
import tkinter as tk
from tkinter import messagebox, ttk
import calendar
import ctypes
import datetime
import os
import sys
from src.storage import Storage
from src.time_utils import calculate_hours, validate_entry
from src.report import generate_report, generate_pdf
from src.mail import get_gmail_service, send_email
from src.autostart import enable_autostart, disable_autostart

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
    def __init__(self, root, storage, settings, base_path="."):
        self.root = root
        self.storage = storage
        self.settings = settings
        self.base_path = base_path
        self.root.title("Zeiterfassung")
        self.root.configure(bg=BG)

        # Set unique AppUserModelID so Windows shows our icon in taskbar
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("margenheld.zeiterfassung")
        except Exception:
            pass

        # Set window/taskbar icon
        ico_path = os.path.join(base_path, "assets", "margenheld-icon.ico")
        png_path = os.path.join(base_path, "assets", "margenheld-icon.png")
        if os.path.exists(ico_path):
            self.root.iconbitmap(ico_path)
        if os.path.exists(png_path):
            icon = tk.PhotoImage(file=png_path)
            self.root.iconphoto(True, icon)
            self._icon_ref = icon

        self.root.resizable(False, False)

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
        footer_frame = tk.Frame(self.root, bg=BG)
        footer_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.footer_label = tk.Label(
            footer_frame, text="Gesamt: 0.0h", font=FONT_FOOTER,
            bg=BG, fg=ACCENT
        )
        self.footer_label.pack(side=tk.LEFT, expand=True)

        tk.Button(
            footer_frame, text="Monat senden", command=self._send_report,
            font=FONT, bg=CELL_BG, fg=TEXT,
            activebackground=ENTRY_BG, activeforeground=TEXT,
            relief=tk.FLAT, padx=12, pady=4, cursor="hand2"
        ).pack(side=tk.RIGHT)

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

        # Recipient
        tk.Label(
            dialog, text="Empfänger:", font=FONT, bg=BG, fg=TEXT
        ).grid(row=2, column=0, padx=10, pady=8, sticky="w")

        recipient_var = tk.StringVar(value=self.settings.get("recipient"))
        tk.Entry(
            dialog, textvariable=recipient_var, width=25, font=FONT,
            bg=CELL_BG, fg=TEXT, insertbackground=ACCENT,
            relief=tk.FLAT, highlightbackground=TEXT_MUTED,
            highlightcolor=ACCENT, highlightthickness=1
        ).grid(row=2, column=1, padx=10, pady=8)

        # Name
        tk.Label(
            dialog, text="Name:", font=FONT, bg=BG, fg=TEXT
        ).grid(row=3, column=0, padx=10, pady=8, sticky="w")

        name_var = tk.StringVar(value=self.settings.get("name"))
        tk.Entry(
            dialog, textvariable=name_var, width=25, font=FONT,
            bg=CELL_BG, fg=TEXT, insertbackground=ACCENT,
            relief=tk.FLAT, highlightbackground=TEXT_MUTED,
            highlightcolor=ACCENT, highlightthickness=1
        ).grid(row=3, column=1, padx=10, pady=8)

        # Mail-Vorlage
        tk.Label(
            dialog, text="— Mail-Vorlage —", font=FONT_BOLD, bg=BG, fg=TEXT_MUTED
        ).grid(row=4, column=0, columnspan=2, padx=10, pady=(16, 4))

        tk.Label(
            dialog, text="Betreff:", font=FONT, bg=BG, fg=TEXT
        ).grid(row=5, column=0, padx=10, pady=4, sticky="w")
        subject_var = tk.StringVar(value=self.settings.get("mail_subject"))
        tk.Entry(
            dialog, textvariable=subject_var, width=35, font=FONT,
            bg=CELL_BG, fg=TEXT, insertbackground=ACCENT,
            relief=tk.FLAT, highlightbackground=TEXT_MUTED,
            highlightcolor=ACCENT, highlightthickness=1
        ).grid(row=5, column=1, padx=10, pady=4)

        tk.Label(
            dialog, text="Anrede:", font=FONT, bg=BG, fg=TEXT
        ).grid(row=6, column=0, padx=10, pady=4, sticky="w")
        greeting_var = tk.StringVar(value=self.settings.get("mail_greeting"))
        tk.Entry(
            dialog, textvariable=greeting_var, width=35, font=FONT,
            bg=CELL_BG, fg=TEXT, insertbackground=ACCENT,
            relief=tk.FLAT, highlightbackground=TEXT_MUTED,
            highlightcolor=ACCENT, highlightthickness=1
        ).grid(row=6, column=1, padx=10, pady=4)

        tk.Label(
            dialog, text="Inhalt:", font=FONT, bg=BG, fg=TEXT
        ).grid(row=7, column=0, padx=10, pady=4, sticky="nw")
        content_text = tk.Text(
            dialog, width=35, height=3, font=FONT,
            bg=CELL_BG, fg=TEXT, insertbackground=ACCENT,
            relief=tk.FLAT, highlightbackground=TEXT_MUTED,
            highlightcolor=ACCENT, highlightthickness=1, wrap=tk.WORD
        )
        content_text.grid(row=7, column=1, padx=10, pady=4)
        content_text.insert("1.0", self.settings.get("mail_content"))

        tk.Label(
            dialog, text="Gruß:", font=FONT, bg=BG, fg=TEXT
        ).grid(row=8, column=0, padx=10, pady=4, sticky="nw")
        closing_text = tk.Text(
            dialog, width=35, height=2, font=FONT,
            bg=CELL_BG, fg=TEXT, insertbackground=ACCENT,
            relief=tk.FLAT, highlightbackground=TEXT_MUTED,
            highlightcolor=ACCENT, highlightthickness=1, wrap=tk.WORD
        )
        closing_text.grid(row=8, column=1, padx=10, pady=4)
        closing_text.insert("1.0", self.settings.get("mail_closing"))

        tk.Label(
            dialog, text="Platzhalter: {zeitraum}, {gesamt}", font=("Segoe UI", 8),
            bg=BG, fg=TEXT_MUTED
        ).grid(row=9, column=0, columnspan=2, padx=10, pady=(0, 4))

        # Autostart
        autostart_var = tk.BooleanVar(value=self.settings.get("autostart"))
        tk.Checkbutton(
            dialog, text="Autostart (minimiert bei Anmeldung)",
            variable=autostart_var, font=FONT,
            bg=BG, fg=TEXT, selectcolor=CELL_BG,
            activebackground=BG, activeforeground=TEXT,
            cursor="hand2"
        ).grid(row=10, column=0, columnspan=2, padx=10, pady=8, sticky="w")

        def save_settings():
            new_autostart = autostart_var.get()
            old_autostart = self.settings.get("autostart")

            if new_autostart != old_autostart:
                try:
                    if new_autostart:
                        if getattr(sys, "frozen", False):
                            target = sys.executable
                            arguments = "--minimized"
                        else:
                            target = sys.executable
                            main_py = os.path.join(self.base_path, "src", "main.py")
                            arguments = f"{main_py} --minimized"
                        enable_autostart(target, arguments)
                    else:
                        disable_autostart()
                    self.settings.set("autostart", new_autostart)
                except Exception as e:
                    messagebox.showerror(
                        "Autostart-Fehler",
                        f"Autostart konnte nicht geändert werden:\n{e}",
                        parent=dialog
                    )
                    return

            self.settings.set("email", email_var.get())
            self.settings.set("default_pause", int(pause_var.get()))
            self.settings.set("recipient", recipient_var.get())
            self.settings.set("name", name_var.get())
            self.settings.set("mail_subject", subject_var.get())
            self.settings.set("mail_greeting", greeting_var.get())
            self.settings.set("mail_content", content_text.get("1.0", "end-1c"))
            self.settings.set("mail_closing", closing_text.get("1.0", "end-1c"))
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=BG)
        btn_frame.grid(row=11, column=0, columnspan=2, pady=12)

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

    def _send_report(self):
        recipient = self.settings.get("recipient")
        if not recipient:
            messagebox.showwarning(
                "Kein Empfänger",
                "Bitte zuerst einen Empfänger in den Einstellungen angeben.",
                parent=self.root
            )
            return

        credentials_path = os.path.join(self.base_path, "credentials.json")
        token_path = os.path.join(self.base_path, "token.json")

        if not os.path.exists(credentials_path):
            messagebox.showerror(
                "Keine Zugangsdaten",
                "credentials.json nicht gefunden.\n\n"
                "Bitte erstelle ein Google Cloud Projekt mit Gmail API "
                "und lade die OAuth2 Client-ID als credentials.json herunter.",
                parent=self.root
            )
            return

        # Date range dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Zeitraum wählen")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.configure(bg=BG)

        self._apply_combobox_style(dialog)

        today = datetime.date.today()
        # Default: one month ago to today
        if today.month == 1:
            from_default = today.replace(year=today.year - 1, month=12)
        else:
            # Handle months where from-day exceeds target month length
            import calendar as cal_mod
            from_month = today.month - 1
            from_year = today.year
            max_day = cal_mod.monthrange(from_year, from_month)[1]
            from_default = today.replace(month=from_month, day=min(today.day, max_day))

        day_values = [str(d) for d in range(1, 32)]
        month_values = [str(m) for m in range(1, 13)]
        year_values = [str(y) for y in range(2020, today.year + 2)]

        # Von
        tk.Label(
            dialog, text="Von:", font=FONT, bg=BG, fg=TEXT
        ).grid(row=0, column=0, padx=(10, 5), pady=8, sticky="w")

        from_day_var = tk.StringVar(value=str(from_default.day))
        from_day_cb = ttk.Combobox(
            dialog, textvariable=from_day_var, values=day_values,
            width=3, font=FONT, style="Dark.TCombobox", state="readonly"
        )
        from_day_cb.grid(row=0, column=1, padx=2, pady=8)

        tk.Label(dialog, text=".", font=FONT, bg=BG, fg=TEXT).grid(row=0, column=2)

        from_month_var = tk.StringVar(value=str(from_default.month))
        from_month_cb = ttk.Combobox(
            dialog, textvariable=from_month_var, values=month_values,
            width=3, font=FONT, style="Dark.TCombobox", state="readonly"
        )
        from_month_cb.grid(row=0, column=3, padx=2, pady=8)

        tk.Label(dialog, text=".", font=FONT, bg=BG, fg=TEXT).grid(row=0, column=4)

        from_year_var = tk.StringVar(value=str(from_default.year))
        from_year_cb = ttk.Combobox(
            dialog, textvariable=from_year_var, values=year_values,
            width=5, font=FONT, style="Dark.TCombobox", state="readonly"
        )
        from_year_cb.grid(row=0, column=5, padx=(2, 10), pady=8)

        # Bis
        tk.Label(
            dialog, text="Bis:", font=FONT, bg=BG, fg=TEXT
        ).grid(row=1, column=0, padx=(10, 5), pady=8, sticky="w")

        to_day_var = tk.StringVar(value=str(today.day))
        to_day_cb = ttk.Combobox(
            dialog, textvariable=to_day_var, values=day_values,
            width=3, font=FONT, style="Dark.TCombobox", state="readonly"
        )
        to_day_cb.grid(row=1, column=1, padx=2, pady=8)

        tk.Label(dialog, text=".", font=FONT, bg=BG, fg=TEXT).grid(row=1, column=2)

        to_month_var = tk.StringVar(value=str(today.month))
        to_month_cb = ttk.Combobox(
            dialog, textvariable=to_month_var, values=month_values,
            width=3, font=FONT, style="Dark.TCombobox", state="readonly"
        )
        to_month_cb.grid(row=1, column=3, padx=2, pady=8)

        tk.Label(dialog, text=".", font=FONT, bg=BG, fg=TEXT).grid(row=1, column=4)

        to_year_var = tk.StringVar(value=str(today.year))
        to_year_cb = ttk.Combobox(
            dialog, textvariable=to_year_var, values=year_values,
            width=5, font=FONT, style="Dark.TCombobox", state="readonly"
        )
        to_year_cb.grid(row=1, column=5, padx=(2, 10), pady=8)

        def do_send():
            try:
                date_from = datetime.date(
                    int(from_year_var.get()), int(from_month_var.get()), int(from_day_var.get())
                )
                date_to = datetime.date(
                    int(to_year_var.get()), int(to_month_var.get()), int(to_day_var.get())
                )
            except ValueError:
                messagebox.showerror("Ungültiges Datum", "Bitte ein gültiges Datum eingeben.", parent=dialog)
                return

            if date_from > date_to:
                messagebox.showerror("Ungültiger Zeitraum", "Das Von-Datum muss vor dem Bis-Datum liegen.", parent=dialog)
                return

            entries = self.storage.get_all()

            greeting = self.settings.get("mail_greeting")
            content = self.settings.get("mail_content")
            closing = self.settings.get("mail_closing")

            html, total = generate_report(
                date_from, date_to, entries,
                greeting=greeting, content=content, closing=closing
            )

            if html is None:
                messagebox.showinfo(
                    "Keine Einträge",
                    f"Keine Einträge für {date_from.strftime('%d.%m.%Y')} – {date_to.strftime('%d.%m.%Y')} vorhanden.",
                    parent=dialog
                )
                return

            pdf_bytes = generate_pdf(date_from, date_to, entries, name=self.settings.get("name"))
            label = f"{date_from.strftime('%d.%m.%Y')} – {date_to.strftime('%d.%m.%Y')}"

            try:
                service = get_gmail_service(credentials_path, token_path)
                subject_template = self.settings.get("mail_subject")
                subject = subject_template.replace("{zeitraum}", label).replace("{gesamt}", f"{total}h")
                pdf_filename = f"Zeiterfassung_{date_from.strftime('%Y%m%d')}_{date_to.strftime('%Y%m%d')}.pdf"
                send_email(service, recipient, subject, html,
                           pdf_bytes=pdf_bytes, pdf_filename=pdf_filename)
                dialog.destroy()
                messagebox.showinfo(
                    "Gesendet",
                    f"Bericht für {date_from.strftime('%d.%m.%Y')} – {date_to.strftime('%d.%m.%Y')} wurde an {recipient} gesendet.",
                    parent=self.root
                )
            except FileNotFoundError as e:
                messagebox.showerror("Fehler", str(e), parent=dialog)
            except Exception as e:
                messagebox.showerror(
                    "Senden fehlgeschlagen",
                    f"Fehler beim Senden:\n{e}",
                    parent=dialog
                )

        btn_frame = tk.Frame(dialog, bg=BG)
        btn_frame.grid(row=2, column=0, columnspan=6, pady=12)

        tk.Button(
            btn_frame, text="Senden", command=do_send, font=FONT_BOLD,
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
