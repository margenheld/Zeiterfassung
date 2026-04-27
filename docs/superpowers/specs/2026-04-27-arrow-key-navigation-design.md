# Arrow-Key Navigation (Monat/Woche) — Design Spec

## Overview

Die App soll im Hauptfenster mit den Pfeiltasten **Links** und **Rechts** durch Monate bzw. Wochen navigierbar sein — also genau das, was die `‹`/`›` Icon-Buttons im Header heute tun. Welche Einheit verschoben wird, hängt wie bei den Buttons vom aktuellen `view_mode` ab (Monat oder Woche).

Voraussetzung "Hauptfenster ist fokussiert" wird **implizit** erfüllt: Tk schickt Tastenevents nur an das aktive Fenster, und alle Dialoge der App nutzen `grab_set()` (modal). Wenn ein Dialog offen ist, gehen die Events an den Dialog, nicht ans Root — kein expliziter Focus-Tracking-Code nötig.

## Scope decisions

| # | Decision | Consequence |
|---|----------|-------------|
| 1 | Nur `<Left>` / `<Right>` werden gebunden | Minimaler Eingriff, deckt den User-Wunsch ab. Up/Down/PageUp/PageDown/Home bleiben frei für spätere Erweiterungen |
| 2 | Bindings am Root-Fenster (`self.root.bind`), nicht `bind_all` | Events bubblen via Bindtag-Chain vom fokussierten Child-Widget hoch zum Toplevel — passt zur restlichen App und respektiert die Modal-Grabs der Dialoge |
| 3 | Handler ruft die existierenden `_prev` / `_next` direkt auf | Keine doppelte Logik. View-abhängige Verzweigung (Monat vs. Woche) lebt weiter zentral in `_prev`/`_next` |
| 4 | Kein Debounce / Repeat-Limit | Bei gehaltener Taste feuert Tk wiederholt → schnelles Durchskippen, gewollt. Falls es ruckelt, kann später nachgezogen werden — YAGNI |
| 5 | Keine neuen Tests | Bindings auf das Tk-Mainloop sind unter pytest fummelig zu testen, und `_prev`/`_next` selbst ändern sich nicht. Manuelle Verifikation reicht |
| 6 | Versions-Bump und CHANGELOG nicht Teil dieser Spec | Wird im Release-PR gebündelt |

## Implementation

### `src/ui.py::App.__init__`

Direkt nach dem `_build_footer()`-Aufruf in `__init__` (aktuell Zeile 73) zwei Bindings ergänzen:

```python
self._build_header()
self._build_grid()
self._build_footer()
self.root.bind("<Left>",  lambda e: self._prev())
self.root.bind("<Right>", lambda e: self._next())
self._refresh()
self._proactive_token_refresh()
```

`_prev` und `_next` (Zeilen 155–183) bleiben unverändert — sie verzweigen bereits korrekt nach `view_mode`.

### Verhalten in den Modal-Dialogen

`entry_dialog.py`, `send_dialog.py`, `settings_dialog.py` nutzen alle `grab_set()`. Solange ein Dialog offen ist:

- Tastenevents gehen an das Dialog-Fenster, nicht an Root → unsere Bindings feuern nicht.
- In Dialog-internen `Entry`-Widgets bewegen `<Left>`/`<Right>` weiter den Cursor wie gewohnt (Tk-Default-Bindings auf der Entry-Klasse).

Kein Code in den Dialogen muss angefasst werden.

### Tastatur-Repeat

Tk feuert bei gehaltener Pfeiltaste wiederholt — `_refresh()` baut bei jedem Event das Grid neu auf. Das ist für realistisches Halten (1–2 s) verkraftbar; sollte sich rauskristallisieren, dass es ruckelt, kommt ein Debounce nach. Out of scope für diesen PR.

## Out of scope

- Up/Down, PageUp/PageDown, Home/End, oder Modifier-Kombinationen (z.B. `Shift+Right` für Jahresprung).
- "Heute"-Sprung-Shortcut — der Toggle-Click erfüllt diese Rolle bereits (siehe Spec `2026-04-24-view-toggle-jumps-to-today-design.md`).
- Verhalten ändern, wenn ein Dialog offen ist — der natürliche Modal-Grab reicht.
- Tests für die Bindings.
