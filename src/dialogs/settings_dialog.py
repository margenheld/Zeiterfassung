import os
import tkinter as tk
import traceback
from tkinter import messagebox, ttk

from src.autostart import disable_autostart, enable_autostart, resolve_autostart_target
from src.platform_open import open_folder
from src.theme import (
    ACCENT, ACCENT_HOVER, BG, CELL_BG, ENTRY_BG, FONT, FONT_BOLD, FONT_SMALL,
    PAUSE_VALUES, STATUS_OK, TEXT, TEXT_MUTED, TIME_VALUES, apply_combobox_style,
)
from src.time_utils import validate_entry


def open_settings_dialog(parent, settings, base_path, on_change):
    """Modal dialog for editing app settings.

    on_change is called after a successful save so the calendar can refresh.
    """
    dialog = tk.Toplevel(parent)
    dialog.title("Einstellungen")
    dialog.resizable(False, False)
    dialog.grab_set()
    dialog.configure(bg=BG)

    apply_combobox_style(dialog)

    creds_path = os.path.join(base_path, "credentials.json")

    tk.Label(
        dialog, text="— Gmail-Zugangsdaten —", font=FONT_BOLD,
        bg=BG, fg=TEXT_MUTED,
    ).grid(row=0, column=0, columnspan=2, padx=10, pady=(8, 4))

    tk.Label(
        dialog, text="Datenordner:", font=FONT, bg=BG, fg=TEXT,
    ).grid(row=1, column=0, padx=10, pady=4, sticky="w")

    creds_row = tk.Frame(dialog, bg=BG)
    creds_row.grid(row=1, column=1, padx=10, pady=4, sticky="w")

    def open_data_folder():
        try:
            open_folder(base_path)
        except Exception as e:
            messagebox.showerror(
                "Ordner konnte nicht geöffnet werden",
                f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}",
                parent=dialog,
            )

    tk.Button(
        creds_row, text="Ordner öffnen", command=open_data_folder,
        font=FONT, bg=CELL_BG, fg=TEXT,
        activebackground=ENTRY_BG, activeforeground=TEXT,
        relief=tk.FLAT, padx=12, pady=2, cursor="hand2",
    ).pack(side=tk.LEFT)

    status_label = tk.Label(creds_row, text="", font=FONT_SMALL, bg=BG)
    status_label.pack(side=tk.LEFT, padx=(10, 0))

    def refresh_status():
        if not status_label.winfo_exists():
            return
        if os.path.exists(creds_path):
            status_label.config(text="✓ credentials.json vorhanden", fg=STATUS_OK)
        else:
            status_label.config(text="✗ credentials.json fehlt", fg=ACCENT)
        dialog.after(500, refresh_status)

    refresh_status()

    def make_entry(textvariable, width):
        return tk.Entry(
            dialog, textvariable=textvariable, width=width, font=FONT,
            bg=CELL_BG, fg=TEXT, insertbackground=ACCENT,
            relief=tk.FLAT, highlightbackground=TEXT_MUTED,
            highlightcolor=ACCENT, highlightthickness=1,
        )

    def make_text(width, height):
        return tk.Text(
            dialog, width=width, height=height, font=FONT,
            bg=CELL_BG, fg=TEXT, insertbackground=ACCENT,
            relief=tk.FLAT, highlightbackground=TEXT_MUTED,
            highlightcolor=ACCENT, highlightthickness=1, wrap=tk.WORD,
        )

    def make_combo(textvariable, values, width):
        return ttk.Combobox(
            dialog, textvariable=textvariable, values=values,
            width=width, font=FONT, style="Dark.TCombobox", state="readonly",
        )

    tk.Label(dialog, text="Absender:", font=FONT, bg=BG, fg=TEXT).grid(
        row=2, column=0, padx=10, pady=8, sticky="w")
    email_var = tk.StringVar(value=settings.get("email"))
    make_entry(email_var, 25).grid(row=2, column=1, padx=10, pady=8)

    tk.Label(dialog, text="Standard-Start:", font=FONT, bg=BG, fg=TEXT).grid(
        row=3, column=0, padx=10, pady=8, sticky="w")
    start_var = tk.StringVar(value=settings.get("default_start"))
    make_combo(start_var, TIME_VALUES, 8).grid(row=3, column=1, padx=10, pady=8)

    tk.Label(dialog, text="Standard-Ende:", font=FONT, bg=BG, fg=TEXT).grid(
        row=4, column=0, padx=10, pady=8, sticky="w")
    end_var = tk.StringVar(value=settings.get("default_end"))
    make_combo(end_var, TIME_VALUES, 8).grid(row=4, column=1, padx=10, pady=8)

    tk.Label(dialog, text="Standard-Pause (Min):", font=FONT, bg=BG, fg=TEXT).grid(
        row=5, column=0, padx=10, pady=8, sticky="w")
    pause_var = tk.StringVar(value=str(settings.get("default_pause")))
    make_combo(pause_var, PAUSE_VALUES, 8).grid(row=5, column=1, padx=10, pady=8)

    tk.Label(dialog, text="Empfänger:", font=FONT, bg=BG, fg=TEXT).grid(
        row=6, column=0, padx=10, pady=8, sticky="w")
    recipient_var = tk.StringVar(value=settings.get("recipient"))
    make_entry(recipient_var, 25).grid(row=6, column=1, padx=10, pady=8)

    tk.Label(dialog, text="Name:", font=FONT, bg=BG, fg=TEXT).grid(
        row=7, column=0, padx=10, pady=8, sticky="w")
    name_var = tk.StringVar(value=settings.get("name"))
    make_entry(name_var, 25).grid(row=7, column=1, padx=10, pady=8)

    tk.Label(dialog, text="Stundenlohn (€):", font=FONT, bg=BG, fg=TEXT).grid(
        row=8, column=0, padx=10, pady=8, sticky="w")
    rate_var = tk.StringVar(value=str(settings.get("hourly_rate") or ""))
    make_entry(rate_var, 10).grid(row=8, column=1, padx=10, pady=8, sticky="w")

    tk.Label(
        dialog, text="(optional – nur für dich sichtbar)", font=FONT_SMALL,
        bg=BG, fg=TEXT_MUTED,
    ).grid(row=8, column=1, padx=(120, 10), pady=8, sticky="w")

    tk.Label(
        dialog, text="— Mail-Vorlage —", font=FONT_BOLD, bg=BG, fg=TEXT_MUTED,
    ).grid(row=9, column=0, columnspan=2, padx=10, pady=(16, 4))

    tk.Label(dialog, text="Betreff:", font=FONT, bg=BG, fg=TEXT).grid(
        row=10, column=0, padx=10, pady=4, sticky="w")
    subject_var = tk.StringVar(value=settings.get("mail_subject"))
    make_entry(subject_var, 35).grid(row=10, column=1, padx=10, pady=4)

    tk.Label(dialog, text="Anrede:", font=FONT, bg=BG, fg=TEXT).grid(
        row=11, column=0, padx=10, pady=4, sticky="w")
    greeting_var = tk.StringVar(value=settings.get("mail_greeting"))
    make_entry(greeting_var, 35).grid(row=11, column=1, padx=10, pady=4)

    tk.Label(dialog, text="Inhalt:", font=FONT, bg=BG, fg=TEXT).grid(
        row=12, column=0, padx=10, pady=4, sticky="nw")
    content_text = make_text(35, 3)
    content_text.grid(row=12, column=1, padx=10, pady=4)
    content_text.insert("1.0", settings.get("mail_content"))

    tk.Label(dialog, text="Gruß:", font=FONT, bg=BG, fg=TEXT).grid(
        row=13, column=0, padx=10, pady=4, sticky="nw")
    closing_text = make_text(35, 2)
    closing_text.grid(row=13, column=1, padx=10, pady=4)
    closing_text.insert("1.0", settings.get("mail_closing"))

    tk.Label(
        dialog, text="Platzhalter: {zeitraum}, {gesamt}", font=("Segoe UI", 8),
        bg=BG, fg=TEXT_MUTED,
    ).grid(row=14, column=0, columnspan=2, padx=10, pady=(0, 4))

    autostart_var = tk.BooleanVar(value=settings.get("autostart"))
    tk.Checkbutton(
        dialog, text="Autostart (minimiert bei Anmeldung)",
        variable=autostart_var, font=FONT,
        bg=BG, fg=TEXT, selectcolor=CELL_BG,
        activebackground=BG, activeforeground=TEXT,
        cursor="hand2",
    ).grid(row=15, column=0, columnspan=2, padx=10, pady=8, sticky="w")

    def save_settings():
        ok, msg = validate_entry(start_var.get(), end_var.get())
        if not ok:
            messagebox.showerror("Standard-Arbeitszeit ungültig", msg, parent=dialog)
            return

        new_autostart = autostart_var.get()
        old_autostart = settings.get("autostart")

        if new_autostart != old_autostart:
            try:
                if new_autostart:
                    target, arguments = resolve_autostart_target(base_path)
                    enable_autostart(target, arguments)
                else:
                    disable_autostart()
                settings.set("autostart", new_autostart)
            except Exception as e:
                messagebox.showerror(
                    "Autostart-Fehler",
                    f"Autostart konnte nicht geändert werden:\n{e}",
                    parent=dialog,
                )
                return

        settings.set("email", email_var.get())
        settings.set("default_start", start_var.get())
        settings.set("default_end", end_var.get())
        settings.set("default_pause", int(pause_var.get()))
        settings.set("recipient", recipient_var.get())
        settings.set("name", name_var.get())
        settings.set("mail_subject", subject_var.get())
        settings.set("mail_greeting", greeting_var.get())
        settings.set("mail_content", content_text.get("1.0", "end-1c"))
        settings.set("mail_closing", closing_text.get("1.0", "end-1c"))
        rate_str = rate_var.get().strip()
        try:
            settings.set("hourly_rate", float(rate_str) if rate_str else 0.0)
        except ValueError:
            settings.set("hourly_rate", 0.0)
        on_change()
        dialog.destroy()

    btn_frame = tk.Frame(dialog, bg=BG)
    btn_frame.grid(row=16, column=0, columnspan=2, pady=12)

    tk.Button(
        btn_frame, text="Speichern", command=save_settings, font=FONT_BOLD,
        bg=ACCENT, fg="#ffffff",
        activebackground=ACCENT_HOVER, activeforeground="#ffffff",
        relief=tk.FLAT, padx=16, pady=4, cursor="hand2",
    ).pack(side=tk.LEFT, padx=5)

    tk.Button(
        btn_frame, text="Abbrechen", command=dialog.destroy, font=FONT,
        bg=CELL_BG, fg=TEXT,
        activebackground=ENTRY_BG, activeforeground=TEXT,
        relief=tk.FLAT, padx=16, pady=4, cursor="hand2",
    ).pack(side=tk.LEFT, padx=5)
