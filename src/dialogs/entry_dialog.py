import tkinter as tk
from tkinter import messagebox, ttk

from src.theme import (
    ACCENT, ACCENT_HOVER, BG, CELL_BG, ENTRY_BG, FONT, FONT_BOLD,
    PAUSE_VALUES, TEXT, TIME_VALUES, apply_combobox_style,
)
from src.time_utils import validate_entry


def open_entry_dialog(parent, date_str, storage, settings, on_change):
    """Modal dialog to edit/delete one day's time entry.

    on_change is invoked after successful save or delete so the caller
    can refresh the calendar view.
    """
    dialog = tk.Toplevel(parent)
    dialog.title(date_str)
    dialog.resizable(False, False)
    dialog.grab_set()
    dialog.configure(bg=BG)

    entry = storage.get(date_str)

    apply_combobox_style(dialog)

    tk.Label(
        dialog, text="Start:", font=FONT, bg=BG, fg=TEXT,
    ).grid(row=0, column=0, padx=10, pady=8, sticky="w")

    start_var = tk.StringVar(value=entry["start"] if entry else settings.get("default_start"))
    ttk.Combobox(
        dialog, textvariable=start_var, values=TIME_VALUES,
        width=8, font=FONT, style="Dark.TCombobox", state="readonly",
    ).grid(row=0, column=1, padx=10, pady=8)

    tk.Label(
        dialog, text="Ende:", font=FONT, bg=BG, fg=TEXT,
    ).grid(row=1, column=0, padx=10, pady=8, sticky="w")

    end_var = tk.StringVar(value=entry["end"] if entry else settings.get("default_end"))
    ttk.Combobox(
        dialog, textvariable=end_var, values=TIME_VALUES,
        width=8, font=FONT, style="Dark.TCombobox", state="readonly",
    ).grid(row=1, column=1, padx=10, pady=8)

    tk.Label(
        dialog, text="Pause (Min):", font=FONT, bg=BG, fg=TEXT,
    ).grid(row=2, column=0, padx=10, pady=8, sticky="w")

    default_pause = settings.get("default_pause")
    if entry and "pause" in entry:
        current_pause = str(entry["pause"])
    else:
        current_pause = str(default_pause) if not entry else "0"
    pause_var = tk.StringVar(value=current_pause)
    ttk.Combobox(
        dialog, textvariable=pause_var, values=PAUSE_VALUES,
        width=8, font=FONT, style="Dark.TCombobox", state="readonly",
    ).grid(row=2, column=1, padx=10, pady=8)

    def save():
        ok, msg = validate_entry(start_var.get(), end_var.get(), pause_minutes=int(pause_var.get()))
        if not ok:
            messagebox.showerror("Fehler", msg, parent=dialog)
            return
        storage.save(date_str, start_var.get(), end_var.get(), pause=int(pause_var.get()))
        dialog.destroy()
        on_change()

    def delete():
        storage.delete(date_str)
        dialog.destroy()
        on_change()

    btn_frame = tk.Frame(dialog, bg=BG)
    btn_frame.grid(row=3, column=0, columnspan=2, pady=12)

    tk.Button(
        btn_frame, text="Speichern", command=save, font=FONT_BOLD,
        bg=ACCENT, fg="#ffffff",
        activebackground=ACCENT_HOVER, activeforeground="#ffffff",
        relief=tk.FLAT, padx=16, pady=4, cursor="hand2",
    ).pack(side=tk.LEFT, padx=5)

    tk.Button(
        btn_frame, text="Löschen", command=delete, font=FONT,
        bg=CELL_BG, fg=TEXT,
        activebackground=ENTRY_BG, activeforeground=TEXT,
        relief=tk.FLAT, padx=16, pady=4, cursor="hand2",
    ).pack(side=tk.LEFT, padx=5)
