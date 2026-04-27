# src/ui.py
import tkinter as tk
from tkinter import messagebox
import calendar
import ctypes
import datetime
import os
import platform
import threading
import traceback
from src.time_utils import calculate_hours, get_week_dates, get_week_label, week_spans_months
from src.holidays_de import get_holidays
from src.tooltip import attach_tooltip
from src.mail import refresh_token_if_needed, TokenAuthError, TokenNetworkError
from src.version import VERSION

from src.dialogs.entry_dialog import open_entry_dialog
from src.dialogs.send_dialog import open_send_dialog
from src.dialogs.settings_dialog import open_settings_dialog
from src.theme import (
    BG, CELL_BG, WEEKEND_BG, ACCENT, TEXT, TEXT_MUTED,
    ENTRY_BG, WEEKEND_ENTRY_BG, WEEKEND_FG,
    HOLIDAY_BG, HOLIDAY_BG_HOVER, HOLIDAY_ACCENT,
    FONT, FONT_BOLD, FONT_HEADER, FONT_FOOTER, FONT_SMALL,
    CELL_BG_HOVER, WEEKEND_BG_HOVER, ENTRY_BG_HOVER, WEEKEND_ENTRY_BG_HOVER,
    icon_button, secondary_button, set_toggle_active, toggle_button,
)

DAYS_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONTHS_DE = [
    "", "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]


class App:
    def __init__(self, root, storage, settings, base_path="."):
        self.root = root
        self.storage = storage
        self.settings = settings
        self.base_path = base_path
        self.root.title(f"Zeiterfassung v{VERSION}")
        self.root.configure(bg=BG)

        # Set unique AppUserModelID so Windows shows our icon in taskbar
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("margenheld.zeiterfassung")
        except Exception:
            pass

        # Set window/taskbar icon
        ico_path = os.path.join(base_path, "assets", "margenheld-icon.ico")
        png_path = os.path.join(base_path, "assets", "margenheld-icon.png")
        if platform.system() == "Windows" and os.path.exists(ico_path):
            self.root.iconbitmap(ico_path)
        if os.path.exists(png_path):
            icon = tk.PhotoImage(file=png_path)
            self.root.iconphoto(True, icon)
            self._icon_ref = icon

        self.root.resizable(False, False)

        today = datetime.date.today()
        self.year = today.year
        self.month = today.month
        self.view_mode = "month"  # "month" or "week"
        iso = today.isocalendar()
        self.iso_year = iso[0]
        self.current_week = iso[1]

        self._build_header()
        self._build_grid()
        self._build_footer()
        self.root.bind("<Left>", lambda e: self._prev())
        self.root.bind("<Right>", lambda e: self._next())
        self._refresh()
        self._proactive_token_refresh()

    def _proactive_token_refresh(self):
        """Erneuert den Gmail-Token beim App-Start im Hintergrund.

        Auth-Fehler werden als Messagebox gezeigt, Netzwerkfehler still
        übergangen, damit ein Offline-Start nicht stört.
        """
        token_path = os.path.join(self.base_path, "token.json")

        def worker():
            try:
                refresh_token_if_needed(token_path)
            except TokenAuthError as e:
                msg = str(e)
                self.root.after(0, lambda: messagebox.showwarning(
                    "Gmail-Anmeldung abgelaufen",
                    "Der Gmail-Token konnte nicht automatisch erneuert werden:\n\n"
                    f"{msg}\n\n"
                    "Beim nächsten Senden wirst du zur erneuten Anmeldung aufgefordert."
                ))
            except TokenNetworkError:
                pass
            except Exception as e:
                err = f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}"
                self.root.after(0, lambda: messagebox.showerror(
                    "Token-Refresh fehlgeschlagen", err
                ))

        threading.Thread(target=worker, daemon=True).start()

    def _build_header(self):
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill=tk.X, padx=10, pady=(10, 0))

        icon_button(frame, "\u2039", self._prev).pack(side=tk.LEFT)

        toggle_frame = tk.Frame(frame, bg=BG)
        toggle_frame.pack(side=tk.LEFT, padx=10)

        self.btn_month = toggle_button(
            toggle_frame, "Monat", lambda: self._set_view("month"), active=True,
        )
        self.btn_month.pack(side=tk.LEFT, padx=(0, 1))

        self.btn_week = toggle_button(
            toggle_frame, "Woche", lambda: self._set_view("week"), active=False,
        )
        self.btn_week.pack(side=tk.LEFT)

        self.header_label = tk.Label(
            frame, text="", font=FONT_HEADER, bg=BG, fg="#ffffff",
        )
        self.header_label.pack(side=tk.LEFT, expand=True)

        icon_button(
            frame, "\u2699", self._open_settings,
            fg=TEXT_MUTED, hover_fg=TEXT,
        ).pack(side=tk.RIGHT)

        icon_button(frame, "\u203a", self._next).pack(side=tk.RIGHT, padx=(0, 5))

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

        secondary_button(
            footer_frame, "Monat senden", self._send, padx=12,
        ).pack(side=tk.RIGHT)

    def _prev(self):
        if self.view_mode == "month":
            if self.month == 1:
                self.month = 12
                self.year -= 1
            else:
                self.month -= 1
        else:
            dates = get_week_dates(self.iso_year, self.current_week)
            prev_monday = dates[0] - datetime.timedelta(days=7)
            iso = prev_monday.isocalendar()
            self.iso_year = iso[0]
            self.current_week = iso[1]
        self._refresh()

    def _next(self):
        if self.view_mode == "month":
            if self.month == 12:
                self.month = 1
                self.year += 1
            else:
                self.month += 1
        else:
            dates = get_week_dates(self.iso_year, self.current_week)
            next_monday = dates[0] + datetime.timedelta(days=7)
            iso = next_monday.isocalendar()
            self.iso_year = iso[0]
            self.current_week = iso[1]
        self._refresh()

    def _set_view(self, mode):
        if mode == self.view_mode:
            return
        today = datetime.date.today()
        if mode == "week":
            iso = today.isocalendar()
            self.iso_year = iso[0]
            self.current_week = iso[1]
        else:
            self.year = today.year
            self.month = today.month
        self.view_mode = mode
        self._update_toggle_style()
        self._refresh()

    def _update_toggle_style(self):
        set_toggle_active(self.btn_month, self.view_mode == "month")
        set_toggle_active(self.btn_week, self.view_mode == "week")

    def _open_settings(self):
        open_settings_dialog(
            self.root, self.settings, self.base_path,
            on_change=self._refresh,
        )

    def _refresh(self):
        if self.view_mode == "month":
            self.header_label.config(text=f"{MONTHS_DE[self.month]} {self.year}")
            self._refresh_month()
        else:
            self.header_label.config(
                text=get_week_label(self.iso_year, self.current_week)
            )
            self._refresh_week()
        # Let tkinter compute the required size, then resize window
        self.root.update_idletasks()
        self.root.geometry("")

    def _refresh_month(self):
        # Build new grid off-screen, then swap to avoid flicker
        new_frame = tk.Frame(self.root, bg=BG)

        # Column headers
        for col, day_name in enumerate(DAYS_DE):
            fg = TEXT_MUTED if col < 5 else WEEKEND_FG
            lbl = tk.Label(
                new_frame, text=day_name, font=FONT_BOLD,
                bg=BG, fg=fg
            )
            lbl.grid(row=0, column=col, sticky="nsew", padx=2, pady=2)

        # Calendar weeks
        cal = calendar.Calendar(firstweekday=0)
        entries = self.storage.get_all()
        total_hours = 0.0

        state = self.settings.get("state")
        holidays_map = get_holidays(state, self.year) if state else {}

        for row, week in enumerate(cal.monthdayscalendar(self.year, self.month), start=1):
            for col, day in enumerate(week):
                if day == 0:
                    lbl = tk.Label(
                        new_frame, text="", bg=BG, relief=tk.FLAT
                    )
                    lbl.grid(row=row, column=col, sticky="nsew", padx=2, pady=2)
                    continue

                date_str = f"{self.year}-{self.month:02d}-{day:02d}"
                entry = entries.get(date_str)
                is_weekend = col >= 5
                day_date = datetime.date(self.year, self.month, day)

                text = str(day)
                fg = TEXT
                if is_weekend and not entry:
                    fg = WEEKEND_FG

                if entry:
                    pause = entry.get("pause", 0)
                    hours = calculate_hours(entry["start"], entry["end"], pause_minutes=pause)
                    total_hours += hours
                    bg = WEEKEND_ENTRY_BG if is_weekend else ENTRY_BG
                    cell = tk.Frame(
                        new_frame, bg=bg, relief=tk.SOLID,
                        highlightbackground=ACCENT, highlightthickness=1,
                        cursor="hand2"
                    )
                    day_lbl = tk.Label(
                        cell, text=str(day), font=FONT,
                        bg=bg, fg=TEXT, cursor="hand2"
                    )
                    day_lbl.pack(pady=(4, 0))
                    time_lbl = tk.Label(
                        cell, text=f"{entry['start']}-{entry['end']}",
                        font=FONT_SMALL, bg=bg, fg=TEXT_MUTED, cursor="hand2"
                    )
                    time_lbl.pack(pady=(0, 4))
                    hover_bg = WEEKEND_ENTRY_BG_HOVER if is_weekend else ENTRY_BG_HOVER
                    for w in (cell, day_lbl, time_lbl):
                        w.bind("<Button-1>", lambda e, d=date_str: self._open_dialog(d))
                        w.bind("<Button-3>", lambda e, d=date_str: self._delete_entry(d))
                        w.bind("<Enter>", lambda e, c=cell, dl=day_lbl, tl=time_lbl, hb=hover_bg: self._cell_hover(c, dl, tl, hb))
                        w.bind("<Leave>", lambda e, c=cell, dl=day_lbl, tl=time_lbl, ob=bg: self._cell_hover(c, dl, tl, ob))
                    if day_date in holidays_map:
                        attach_tooltip(cell, f"Feiertag: {holidays_map[day_date]}")
                elif day_date in holidays_map:
                    cell = self._build_holiday_cell(
                        new_frame,
                        day_text=str(day),
                        name=holidays_map[day_date],
                        max_name_len=12,
                        on_click=lambda d=date_str: self._open_dialog(d),
                    )
                else:
                    bg = WEEKEND_BG if is_weekend else CELL_BG
                    hover_bg = WEEKEND_BG_HOVER if is_weekend else CELL_BG_HOVER
                    cell = tk.Label(
                        new_frame, text=text, font=FONT,
                        bg=bg, fg=fg, relief=tk.FLAT,
                        width=8, height=3, cursor="hand2"
                    )
                    cell.bind("<Button-1>", lambda e, d=date_str: self._open_dialog(d))
                    cell.bind("<Enter>", lambda e, c=cell, hb=hover_bg: c.config(bg=hb))
                    cell.bind("<Leave>", lambda e, c=cell, ob=bg: c.config(bg=ob))

                cell.grid(row=row, column=col, sticky="nsew", padx=2, pady=2)

        for col in range(7):
            new_frame.columnconfigure(col, weight=1)

        # Swap frames: destroy old, place new
        self.grid_frame.destroy()
        self.grid_frame = new_frame
        self.grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5,
                             before=self.footer_label.master)

        rate = self.settings.get("hourly_rate") or 0
        if rate > 0:
            brutto = round(total_hours * rate, 2)
            self.footer_label.config(
                text=f"Gesamt: {round(total_hours, 2)}h  —  {brutto:.2f} € brutto"
            )
        else:
            self.footer_label.config(text=f"Gesamt: {round(total_hours, 2)}h")

    def _refresh_week(self):
        new_frame = tk.Frame(self.root, bg=BG)

        # Column headers
        for col, day_name in enumerate(DAYS_DE):
            fg = TEXT_MUTED if col < 5 else WEEKEND_FG
            lbl = tk.Label(
                new_frame, text=day_name, font=FONT_BOLD,
                bg=BG, fg=fg
            )
            lbl.grid(row=0, column=col, sticky="nsew", padx=2, pady=2)

        dates = get_week_dates(self.iso_year, self.current_week)
        entries = self.storage.get_all()
        total_hours = 0.0
        spans = week_spans_months(self.iso_year, self.current_week)
        state = self.settings.get("state")
        holidays_map: dict[datetime.date, str] = {}
        if state:
            for y in {dates[0].year, dates[-1].year}:
                holidays_map.update(get_holidays(state, y))

        # Probe-Label, um die natürliche Pixel-Größe einer Standard-Wochenzelle
        # zu ermitteln. Holiday-Zellen werden auf diese Größe fixiert, damit
        # längere Feiertagsnamen die Spalte nicht aufweiten.
        probe = tk.Label(new_frame, text="", font=FONT, width=8, height=5)
        probe.update_idletasks()
        cell_size = (probe.winfo_reqwidth(), probe.winfo_reqheight())
        probe.destroy()

        for col, day_date in enumerate(dates):
            date_str = day_date.isoformat()
            entry = entries.get(date_str)
            is_weekend = col >= 5
            day_text = f"{day_date.day}.{day_date.month}." if spans else str(day_date.day)

            fg = TEXT
            if is_weekend and not entry:
                fg = WEEKEND_FG

            if entry:
                pause = entry.get("pause", 0)
                hours = calculate_hours(entry["start"], entry["end"], pause_minutes=pause)
                total_hours += hours
                bg = WEEKEND_ENTRY_BG if is_weekend else ENTRY_BG
                cell = tk.Frame(
                    new_frame, bg=bg, relief=tk.SOLID,
                    highlightbackground=ACCENT, highlightthickness=1,
                    cursor="hand2"
                )
                day_lbl = tk.Label(
                    cell, text=day_text, font=FONT,
                    bg=bg, fg=TEXT, cursor="hand2"
                )
                day_lbl.pack(pady=(8, 0))
                time_lbl = tk.Label(
                    cell, text=f"{entry['start']}-{entry['end']}",
                    font=FONT_SMALL, bg=bg, fg=TEXT_MUTED, cursor="hand2"
                )
                time_lbl.pack(pady=(0, 8))
                hover_bg = WEEKEND_ENTRY_BG_HOVER if is_weekend else ENTRY_BG_HOVER
                for w in (cell, day_lbl, time_lbl):
                    w.bind("<Button-1>", lambda e, d=date_str: self._open_dialog(d))
                    w.bind("<Button-3>", lambda e, d=date_str: self._delete_entry(d))
                    w.bind("<Enter>", lambda e, c=cell, dl=day_lbl, tl=time_lbl, hb=hover_bg: self._cell_hover(c, dl, tl, hb))
                    w.bind("<Leave>", lambda e, c=cell, dl=day_lbl, tl=time_lbl, ob=bg: self._cell_hover(c, dl, tl, ob))
                if day_date in holidays_map:
                    attach_tooltip(cell, f"Feiertag: {holidays_map[day_date]}")
            elif day_date in holidays_map:
                cell = self._build_holiday_cell(
                    new_frame,
                    day_text=day_text,
                    name=holidays_map[day_date],
                    max_name_len=18,
                    on_click=lambda d=date_str: self._open_dialog(d),
                    cell_size=cell_size,
                )
            else:
                bg = WEEKEND_BG if is_weekend else CELL_BG
                hover_bg = WEEKEND_BG_HOVER if is_weekend else CELL_BG_HOVER
                cell = tk.Label(
                    new_frame, text=day_text, font=FONT,
                    bg=bg, fg=fg, relief=tk.FLAT,
                    width=8, height=5, cursor="hand2"
                )
                cell.bind("<Button-1>", lambda e, d=date_str: self._open_dialog(d))
                cell.bind("<Enter>", lambda e, c=cell, hb=hover_bg: c.config(bg=hb))
                cell.bind("<Leave>", lambda e, c=cell, ob=bg: c.config(bg=ob))

            cell.grid(row=1, column=col, sticky="nsew", padx=2, pady=2)

        for col in range(7):
            new_frame.columnconfigure(col, weight=1)

        # Swap frames
        self.grid_frame.destroy()
        self.grid_frame = new_frame
        self.grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5,
                             before=self.footer_label.master)

        # Footer
        rate = self.settings.get("hourly_rate") or 0
        if rate > 0:
            brutto = round(total_hours * rate, 2)
            self.footer_label.config(
                text=f"Gesamt: {round(total_hours, 2)}h  —  {brutto:.2f} € brutto"
            )
        else:
            self.footer_label.config(text=f"Gesamt: {round(total_hours, 2)}h")

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return text[: max_len - 1] + "…"

    def _build_holiday_cell(self, parent, day_text, name, max_name_len, on_click, cell_size=None):
        """Grüne Feiertagszelle. Layout analog zur Eintragszelle.

        cell_size: optional (width_px, height_px). Wenn gesetzt, wird der Frame
        auf diese Pixel-Größe fixiert (verhindert Aufweitung der Spalte durch
        längere Namen — relevant für die Wochenansicht).
        """
        cell = tk.Frame(
            parent, bg=HOLIDAY_BG, relief=tk.SOLID,
            highlightbackground=HOLIDAY_ACCENT, highlightthickness=1,
            cursor="hand2",
        )
        if cell_size is not None:
            cell.config(width=cell_size[0], height=cell_size[1])
            cell.pack_propagate(False)
        day_lbl = tk.Label(
            cell, text=day_text, font=FONT,
            bg=HOLIDAY_BG, fg=TEXT, cursor="hand2",
        )
        day_lbl.pack(pady=(4, 0))
        truncated = self._truncate(name, max_name_len)
        name_lbl = tk.Label(
            cell, text=truncated,
            font=FONT_SMALL, bg=HOLIDAY_BG, fg=TEXT_MUTED, cursor="hand2",
        )
        if cell_size is not None:
            # Pixel-fixierte Zelle: Text bei Bedarf umbrechen, nicht horizontal überstehen.
            name_lbl.config(wraplength=cell_size[0] - 6, justify="center")
        name_lbl.pack(pady=(0, 4))

        for w in (cell, day_lbl, name_lbl):
            w.bind("<Button-1>", lambda e: on_click())
            w.bind("<Enter>", lambda e, c=cell, dl=day_lbl, nl=name_lbl:
                self._cell_hover(c, dl, nl, HOLIDAY_BG_HOVER))
            w.bind("<Leave>", lambda e, c=cell, dl=day_lbl, nl=name_lbl:
                self._cell_hover(c, dl, nl, HOLIDAY_BG))
        if truncated != name:
            # Nur am äußersten Frame binden, sonst gleichzeitige Tooltips, weil
            # Tk Enter-Events an Frame und Child unabhängig schickt.
            attach_tooltip(cell, name)
        return cell

    @staticmethod
    def _cell_hover(frame, day_lbl, time_lbl, bg):
        frame.config(bg=bg)
        day_lbl.config(bg=bg)
        time_lbl.config(bg=bg)

    def _delete_entry(self, date_str):
        if messagebox.askyesno("Eintrag löschen", f"Eintrag für {date_str} löschen?"):
            self.storage.delete(date_str)
            self._refresh()

    def _open_dialog(self, date_str):
        open_entry_dialog(
            self.root, date_str, self.storage, self.settings,
            on_change=self._refresh,
        )

    def _send(self):
        open_send_dialog(self.root, self.storage, self.settings, self.base_path)
