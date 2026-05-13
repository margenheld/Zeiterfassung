# macOS Button-Styling Fix — Design Spec

## Overview

Auf macOS rendern `tk.Button`-Widgets immer als native Aqua-Buttons und ignorieren `bg`, `fg`, `relief=tk.FLAT` sowie `highlightthickness`. Konsequenz im aktuellen Build (siehe Screenshots in der Brainstorm-Session): die Header-Buttons (`‹`, `›`, `⚙`), der `Monat`/`Woche`-Toggle, `Monat senden` im Footer, sowie die Buttons im Update-Banner und in Dialogen erscheinen als weiße System-Buttons. Bei aktiven Toggles und Primary-Buttons (`bg=ACCENT`, `fg="#ffffff"`) ist der Text "weiß auf weiß" — praktisch unsichtbar.

Diese Spec ersetzt alle `tk.Button` in der Anwendung durch Label-basierte Custom-Buttons (`tk.Frame` + inneres `tk.Label`), zentral in `src/theme.py`. Labels und Frames respektieren `bg`/`fg` auch unter Aqua, das gesamte Grid besteht bereits aus diesen Widget-Typen und sieht auf Mac korrekt aus. Außerdem wird die Font-Familie plattformabhängig gesetzt, damit `"Segoe UI"` (existiert auf macOS nicht) nicht auf einen unbekannten Fallback fällt und die pixel-fixierten Zellgrößen kippen.

Out-of-Scope (bewusst): `tk.Checkbutton` im Settings-Dialog (Aqua-Default ist auf dunklem Hintergrund lesbar), Tastatur-Aktivierung der neuen Buttons (Space/Enter/Focus-Ring — die App hat heute keine Tastatur-Navigation außer Pfeile), Linux-Look-Verbesserungen (Tk auf Linux respektiert `tk.Button`-Styling bereits).

## Scope decisions

| # | Decision | Consequence |
|---|----------|-------------|
| 1 | `tk.Label` als Button-Basis statt `ttk.Button`, `tkmacosx` oder `tk.Canvas` | Labels respektieren `bg`/`fg` plattformübergreifend identisch; keine externe Dependency; keine Build-Komplikation; das Grid besteht bereits aus Labels und funktioniert auf Mac einwandfrei |
| 2 | Interner Helper `_label_button(parent, text, command, bg, fg, hover_bg, hover_fg, font, ...) -> tk.Frame` als Single-Source | Vier öffentliche Wrapper (`primary_button`, `secondary_button`, `toggle_button`, `icon_button`) bleiben dünn; ein Punkt für Verhaltensänderung |
| 3 | Outer `tk.Frame` + inneres `tk.Label`, beide mit `<Button-1>` und `<Enter>`/`<Leave>` gebunden | Frame trägt den Hintergrund-Rahmen (Padding), Label den Text; ohne Bindings auf beiden würden Hover/Click bei Cursor-Bewegung über das innere Label nicht zuverlässig auslösen |
| 4 | Drop-in-Signaturen: alle vier öffentlichen Helper behalten ihre aktuelle Aufruf-Signatur | Caller in `ui.py` und Dialogen müssen nicht angefasst werden — kleinerer Diff, kleineres Regression-Risiko |
| 5 | Rückgabe-Typ: `tk.Frame` mit Attribut `_label` (Referenz aufs innere Label) | `set_toggle_active(btn, active)` braucht Zugriff auf Frame *und* Label, um beide bg/fg synchron umzuschalten — Attribut ist die einfachste Variante, ohne eigene Klasse einzuführen |
| 6 | `set_toggle_active` kennt die Frame+Label-Struktur (`btn.config(bg=...)` + `btn._label.config(bg=..., fg=...)`) | Einzige Stelle, die nach Erzeugung re-styled — kapselt die Struktur dort, wo sie ohnehin angefasst wird |
| 7 | Font-Familie plattformabhängig in `theme.py`: `"Helvetica Neue"` auf macOS, `"DejaVu Sans"` auf Linux, `"Segoe UI"` auf Windows | Vermeidet stille Fallbacks mit abweichender Metrik; "Helvetica Neue" ist auf allen unterstützten macOS-Versionen vorinstalliert |
| 8 | Schriftgrößen unverändert lassen | Probe-Label-basierte Pixel-Größen in `_refresh_month`/`_refresh_week` bleiben stabil — keine Layout-Anpassung nötig |
| 9 | Die zwei inline `tk.Button` in `ui.py::_show_update_banner` (Download, Dismiss) werden auf die Helper umgestellt | Kein neuer Helper nötig — `primary_button`-artige Farben für "Download", `icon_button`-artige für "✕"; konsistent zum Rest |
| 10 | `tk.Checkbutton` im Settings-Dialog (Autostart) wird **nicht** ersetzt | Aqua-Default ist laut Screenshot lesbar/bedienbar; Custom-Checkbox wäre eigene Mini-Architektur, die hier YAGNI ist |
| 11 | Versions-Bump auf `1.11.0`, CHANGELOG-Eintrag, `release:minor`-Label | Sichtbare UI-Verbesserung auf einer Plattform; keine breaking changes |

## 1) Widget-Architektur

### Interner Helper

In `src/theme.py`:

```python
def _label_button(
    parent, text, command, *,
    bg, fg, hover_bg, hover_fg,
    font, padx=0, pady=0,
    label_padx=0, label_pady=0,
    width=None,
):
    """Frame+Label-Konstrukt als Button-Ersatz.

    `tk.Button` ignoriert auf macOS bg/fg (Aqua-Backend zeichnet nativ).
    `tk.Label` respektiert bg/fg auf allen Plattformen — daher Label
    mit Klick-Bindings statt echtem Button.

    Rückgabe: tk.Frame mit Attribut `_label` (Referenz aufs innere Label),
    damit set_toggle_active beide Widgets synchron restylen kann.
    """
    frame = tk.Frame(parent, bg=bg, cursor="hand2")
    label = tk.Label(
        frame, text=text, font=font,
        bg=bg, fg=fg, cursor="hand2",
        width=width,
    )
    label.pack(padx=label_padx, pady=label_pady)
    frame._label = label

    def on_click(_e):
        command()

    def on_enter(_e):
        frame.config(bg=hover_bg)
        label.config(bg=hover_bg, fg=hover_fg)

    def on_leave(_e):
        frame.config(bg=bg)
        label.config(bg=bg, fg=fg)

    for w in (frame, label):
        w.bind("<Button-1>", on_click)
        w.bind("<Enter>", on_enter)
        w.bind("<Leave>", on_leave)

    return frame
```

### Öffentliche Wrapper

Die vier bisherigen Helper bleiben in der Signatur identisch und delegieren an `_label_button`:

```python
def primary_button(parent, text, command, **kw):
    return _label_button(
        parent, text, command,
        bg=ACCENT, fg="#ffffff",
        hover_bg=ACCENT_HOVER, hover_fg="#ffffff",
        font=kw.pop("font", FONT_BOLD),
        label_padx=kw.pop("padx", 16),
        label_pady=kw.pop("pady", 4),
    )

def secondary_button(parent, text, command, **kw):
    return _label_button(
        parent, text, command,
        bg=CELL_BG, fg=TEXT,
        hover_bg=ENTRY_BG, hover_fg=TEXT,
        font=kw.pop("font", FONT),
        label_padx=kw.pop("padx", 16),
        label_pady=kw.pop("pady", 4),
    )

def icon_button(parent, text, command, fg=ACCENT, hover_fg=None, **kw):
    if hover_fg is None:
        hover_fg = fg
    return _label_button(
        parent, text, command,
        bg=CELL_BG, fg=fg,
        hover_bg=ENTRY_BG, hover_fg=hover_fg,
        font=FONT_BOLD,
        width=3,
    )

def toggle_button(parent, text, command, active=False, **kw):
    if active:
        bg, fg, hover_bg, hover_fg = ACCENT, "#ffffff", ACCENT, "#ffffff"
    else:
        bg, fg, hover_bg, hover_fg = CELL_BG, TEXT_MUTED, ENTRY_BG, TEXT
    btn = _label_button(
        parent, text, command,
        bg=bg, fg=fg, hover_bg=hover_bg, hover_fg=hover_fg,
        font=FONT_SMALL, width=6,
    )
    btn._active = active
    return btn
```

### Toggle-Restyling

```python
def set_toggle_active(btn, active):
    if active:
        bg, fg = ACCENT, "#ffffff"
        hover_bg, hover_fg = ACCENT, "#ffffff"
    else:
        bg, fg = CELL_BG, TEXT_MUTED
        hover_bg, hover_fg = ENTRY_BG, TEXT
    btn.config(bg=bg)
    btn._label.config(bg=bg, fg=fg)
    btn._active = active
    # Hover-Bindings müssen die neuen Farben kennen — Closures der alten
    # Bindings halten die alten Werte. Re-binden:
    for w in (btn, btn._label):
        w.unbind("<Enter>")
        w.unbind("<Leave>")
    btn.bind("<Enter>", lambda _e: (btn.config(bg=hover_bg), btn._label.config(bg=hover_bg, fg=hover_fg)))
    btn.bind("<Leave>", lambda _e: (btn.config(bg=bg), btn._label.config(bg=bg, fg=fg)))
    btn._label.bind("<Enter>", lambda _e: (btn.config(bg=hover_bg), btn._label.config(bg=hover_bg, fg=hover_fg)))
    btn._label.bind("<Leave>", lambda _e: (btn.config(bg=bg), btn._label.config(bg=bg, fg=fg)))
```

Anmerkung: Re-binden statt zusätzlicher State-Variable ist der einfachere Weg — Toggle-Switch passiert selten (View-Wechsel), Performance-Cost ist null.

## 2) Font-Plattform-Switch

Am Anfang von `src/theme.py`:

```python
import platform

_system = platform.system()
if _system == "Darwin":
    _FONT_FAMILY = "Helvetica Neue"
elif _system == "Linux":
    _FONT_FAMILY = "DejaVu Sans"
else:
    _FONT_FAMILY = "Segoe UI"

FONT = (_FONT_FAMILY, 10)
FONT_SMALL = (_FONT_FAMILY, 8)
FONT_TINY = (_FONT_FAMILY, 7)
FONT_BOLD = (_FONT_FAMILY, 10, "bold")
FONT_HEADER = (_FONT_FAMILY, 16, "bold")
FONT_HEADER_SMALL = (_FONT_FAMILY, 12, "bold")
FONT_FOOTER = (_FONT_FAMILY, 12, "bold")
```

Größen bleiben identisch — Probe-Label-Berechnung in `_refresh_month`/`_refresh_week` bleibt stabil. Familien-Wechsel kann minimal die Pixel-Breite verschieben; falls auf einer Plattform `width=8` für die Standardzelle nicht reicht, ist das ein eigener Fix (nachweisbar nur mit Mac-Test).

## 3) Update-Banner-Buttons in `ui.py`

`_show_update_banner` enthält zwei inline `tk.Button`-Konstruktionen. Diese werden durch Aufrufe der Helper ersetzt:

- **Dismiss-Button (`✕`)**: aktuell `tk.Button(bg=ACCENT, fg="#ffffff", ...)` direkt im Banner-Frame. Da das Banner-Frame `bg=ACCENT` hat (roter Hintergrund), nicht den globalen `CELL_BG`, kann `icon_button` so nicht direkt verwendet werden — es würde einen `CELL_BG`-Hintergrund einführen. Lösung: weiterhin inline mit `_label_button` aufbauen und passende Farben übergeben:

```python
dismiss_btn = _label_button(
    self._update_banner, "✕", lambda: self._dismiss_update_banner(release.version),
    bg=ACCENT, fg="#ffffff",
    hover_bg=ACCENT_HOVER, hover_fg="#ffffff",
    font=FONT_BOLD,
    label_padx=8,
)
```

- **Download-Button**: weiß auf rotem Banner.

```python
download_btn = _label_button(
    self._update_banner, "Download", lambda: self._open_update_download(release),
    bg="#ffffff", fg=ACCENT,
    hover_bg="#f0f0f0", hover_fg=ACCENT_HOVER,
    font=FONT_BOLD,
    label_padx=14, label_pady=2,
)
```

Beides erfordert, dass `_label_button` aus `theme.py` exportiert (= im Modul-Scope verfügbar) ist. Import-Liste in `ui.py` um `_label_button` erweitern. Alternative: wir vermeiden den Unterstrich und nennen den Helper `label_button` (öffentlich). **Entscheidung: ohne Unterstrich, `label_button`** — er wird außerhalb von `theme.py` verwendet, der Unterstrich wäre falsche Signalisierung.

## 4) Datei-Änderungen — Übersicht

| Datei | Änderung |
|-------|----------|
| `src/theme.py` | Font-Plattform-Switch am Anfang; neuer Helper `label_button`; vier Wrapper-Funktionen umgebaut; `set_toggle_active` umgebaut |
| `src/ui.py` | Import `label_button` aus `theme`; zwei inline `tk.Button` in `_show_update_banner` durch `label_button`-Aufrufe ersetzt |
| `src/version.py` | `VERSION = "1.11.0"` |
| `CHANGELOG.md` | Eintrag `1.11.0` mit "macOS: alle Buttons im Dark-Theme statt nativ-Aqua; Font-Familie pro Plattform" |

Insgesamt ca. 80–100 geänderte Zeilen, kein Test-Code (UI-Tests existieren nicht, Smoke-Test über Import bleibt grün).

## 5) Verifikations-Plan

**Automatisiert (CI):**
- `pytest` muss komplett grün durchlaufen — `src.theme`-Import wird durch viele Test-Module getriggert (über `src.ui`-Pfad), Import-Fehler würden hier auffallen.

**Manuell auf jeder Plattform (vor Release-Merge):**

1. **Windows** — App starten (`python -m src.main`), alle Buttons prüfen:
   - Header: `‹`, `›`, `⚙` — Hover-Farbe sichtbar
   - Toggle `Monat`/`Woche` — Switch klickbar, aktive Variante mit rotem Hintergrund + weißem Text, inaktive grau
   - Footer: `Monat senden` — Hover dunkler
   - Dialog `Eintrag bearbeiten`: `Speichern`/`Abbrechen` lesbar
   - Update-Banner (falls verfügbar): `Download` weiß auf rot, `✕` weiß auf rot

2. **macOS (primäres Ziel)** — gleiche Checkliste. Vorher-Screenshot vergleichen: kein weißer Aqua-Button mehr; alle Buttons im Dark-Theme; Texte lesbar.

3. **Linux** — gleiche Checkliste, Fokus auf "nichts kaputt gemacht": Font "DejaVu Sans" rendert; Buttons klickbar; Hover funktioniert; Grid-Zellgrößen okay.

Kein UI-Automation-Test — der Wert wäre dem Aufwand nicht entsprechend.

## 6) Risiken & Mitigationen

| Risiko | Mitigation |
|--------|------------|
| Hover-Übergang flackert beim Wechsel Frame↔Label (Mauszeiger triggert beide Bindings) | Beide Bindings setzen exakt die gleichen Farben → idempotent, kein sichtbares Flackern |
| Padding auf Label statt Frame führt zu anderem Klick-Hit-Bereich als vorher | Klick-Binding ist *auf* dem Frame UND dem Label — gesamter sichtbarer Bereich ist klickbar wie bisher |
| Font-Familienwechsel verschiebt Pixel-Metriken auf Mac, Zellen werden zu schmal | Probe-Label-Mechanismus in `_refresh_month`/`_refresh_week` misst zur Laufzeit, passt sich automatisch an; nur falls `width=8` (Char-Einheit) bei einer Familie deutlich schmaler ist, kippt's — laut Screenshot mit aktuellem unbekanntem Fallback ist's okay, mit explizitem "Helvetica Neue" tendenziell stabiler |
| `tk.Frame` ohne explizite `width`/`height` zieht sich auf `0` bei leerem Label-Pad | Label hat immer Text + padx/pady → Frame bekommt natürliche Größe via Pack-Geometry |
| `transient()`/Dialog-Logik erwartet `tk.Button` als Default-Button | Wird nirgendwo getan — Dialoge binden nicht auf Button-Typen, sondern auf `<Return>`-Events am Toplevel |

## 7) Versions-Bump & Release

- `src/version.py`: `VERSION = "1.11.0"`
- `CHANGELOG.md`: neuer Eintrag unter `## 1.11.0`:
  > - macOS: alle Buttons rendern jetzt im Dark-Theme statt als native Aqua-Buttons (Header, Toggle, Footer, Dialog-Buttons, Update-Banner)
  > - Font-Familie wird plattformabhängig gewählt (Windows: Segoe UI, macOS: Helvetica Neue, Linux: DejaVu Sans)
- PR-Label: `release:minor` — sichtbare UI-Verbesserung, keine breaking changes
- Workflow erzeugt automatisch Tag + Release nach Merge
