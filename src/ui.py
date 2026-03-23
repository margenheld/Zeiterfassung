# src/ui.py
import tkinter as tk
from tkinter import messagebox
import calendar
import datetime
from src.storage import Storage
from src.time_utils import calculate_hours, validate_entry

DAYS_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONTHS_DE = [
    "", "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]

class App:
    def __init__(self, root, storage):
        self.root = root
        self.storage = storage
        self.root.title("Zeiterfassung")

        today = datetime.date.today()
        self.year = today.year
        self.month = today.month

        self._build_header()
        self._build_grid()
        self._build_footer()
        self._refresh()

    def _build_header(self):
        frame = tk.Frame(self.root)
        frame.pack(fill=tk.X, padx=10, pady=(10, 0))

        tk.Button(frame, text="<", command=self._prev_month, width=3).pack(side=tk.LEFT)
        self.header_label = tk.Label(frame, text="", font=("Arial", 14, "bold"))
        self.header_label.pack(side=tk.LEFT, expand=True)
        tk.Button(frame, text=">", command=self._next_month, width=3).pack(side=tk.RIGHT)

    def _build_grid(self):
        self.grid_frame = tk.Frame(self.root)
        self.grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def _build_footer(self):
        self.footer_label = tk.Label(self.root, text="Gesamt: 0.0h", font=("Arial", 12))
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

    def _refresh(self):
        self.header_label.config(text=f"{MONTHS_DE[self.month]} {self.year}")

        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        # Column headers
        for col, day_name in enumerate(DAYS_DE):
            lbl = tk.Label(self.grid_frame, text=day_name, font=("Arial", 10, "bold"))
            lbl.grid(row=0, column=col, sticky="nsew", padx=1, pady=1)

        # Calendar weeks
        cal = calendar.Calendar(firstweekday=0)  # Monday first
        entries = self.storage.get_all()
        total_hours = 0.0

        for row, week in enumerate(cal.monthdayscalendar(self.year, self.month), start=1):
            for col, day in enumerate(week):
                if day == 0:
                    # Day outside current month
                    lbl = tk.Label(self.grid_frame, text="", relief=tk.FLAT)
                    lbl.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)
                    continue

                date_str = f"{self.year}-{self.month:02d}-{day:02d}"
                entry = entries.get(date_str)

                text = str(day)
                if entry:
                    hours = calculate_hours(entry["start"], entry["end"])
                    text += f"\n{hours}h"
                    total_hours += hours

                is_weekend = col >= 5
                bg = "#e0e0e0" if is_weekend else "#ffffff"
                if entry:
                    bg = "#d4edda" if not is_weekend else "#c8d6c0"

                cell = tk.Label(
                    self.grid_frame, text=text, relief=tk.RIDGE,
                    bg=bg, width=8, height=3, cursor="hand2"
                )
                cell.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)
                cell.bind("<Button-1>", lambda e, d=date_str: self._open_dialog(d))

        self.footer_label.config(text=f"Gesamt: {round(total_hours, 2)}h")

        # Make grid columns expand evenly
        for col in range(7):
            self.grid_frame.columnconfigure(col, weight=1)

    def _open_dialog(self, date_str):
        dialog = tk.Toplevel(self.root)
        dialog.title(date_str)
        dialog.resizable(False, False)
        dialog.grab_set()

        entry = self.storage.get(date_str)

        tk.Label(dialog, text="Start (HH:MM):").grid(row=0, column=0, padx=10, pady=5)
        start_var = tk.StringVar(value=entry["start"] if entry else "")
        tk.Entry(dialog, textvariable=start_var, width=10).grid(row=0, column=1, padx=10, pady=5)

        tk.Label(dialog, text="Ende (HH:MM):").grid(row=1, column=0, padx=10, pady=5)
        end_var = tk.StringVar(value=entry["end"] if entry else "")
        tk.Entry(dialog, textvariable=end_var, width=10).grid(row=1, column=1, padx=10, pady=5)

        def save():
            ok, msg = validate_entry(start_var.get(), end_var.get())
            if not ok:
                messagebox.showerror("Fehler", msg, parent=dialog)
                return
            self.storage.save(date_str, start_var.get(), end_var.get())
            dialog.destroy()
            self._refresh()

        def delete():
            self.storage.delete(date_str)
            dialog.destroy()
            self._refresh()

        btn_frame = tk.Frame(dialog)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="Speichern", command=save).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Löschen", command=delete).pack(side=tk.LEFT, padx=5)
