# Arrow-Key Navigation (Monat/Woche) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Im Hauptfenster mit `<Left>` / `<Right>` durch Monate bzw. Wochen navigieren — analog zu den `‹`/`›` Icon-Buttons im Header.

**Architecture:** Zwei `bind`-Aufrufe am Root-Fenster in `App.__init__`. Die View-abhängige Logik (Monat vs. Woche) lebt unverändert in den existierenden `_prev`/`_next`-Methoden. Modal-Dialoge nutzen alle `grab_set()` und fangen Tastenevents automatisch ab — kein expliziter Focus-Tracking-Code nötig.

**Tech Stack:** Tkinter (stdlib). Keine neuen Dependencies.

**Spec reference:** `docs/superpowers/specs/2026-04-27-arrow-key-navigation-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/ui.py` | Modify | Zwei `bind`-Aufrufe in `App.__init__` nach `_build_footer()` ergänzen |

Keine neuen Dateien. Keine Tests (Tk-Mainloop-Bindings unter pytest fummelig; `_prev`/`_next` selbst ändern sich nicht — manuelle Verifikation ist die richtige Wahl).

---

## Chunk 1: Pfeiltasten-Bindings ergänzen

### Task 1: Bindings am Root-Fenster registrieren

**Files:**
- Modify: `src/ui.py` (`App.__init__`, Zeilen 71–75)

Diese Task hat keine automatisierten Tests. Verifikation: `python -m pytest -v` (keine Regressionen). Manueller Smoke-Test ist Sache des Controllers.

- [ ] **Step 1: Edit anwenden**

In `src/ui.py::App.__init__` finde den folgenden Block (aktuell Zeilen 71–75):

```python
        self._build_header()
        self._build_grid()
        self._build_footer()
        self._refresh()
        self._proactive_token_refresh()
```

Ersetze ihn durch:

```python
        self._build_header()
        self._build_grid()
        self._build_footer()
        self.root.bind("<Left>", lambda e: self._prev())
        self.root.bind("<Right>", lambda e: self._next())
        self._refresh()
        self._proactive_token_refresh()
```

**Wichtig:**
- Die Bindings stehen **nach** allen `_build_*`-Aufrufen — vorher würden sie an einem leeren Toplevel hängen, was zwar funktioniert, aber konzeptuell unsauber ist.
- Die Bindings stehen **vor** `_refresh()` und `_proactive_token_refresh()` — beides verändert UI-State bzw. startet Hintergrund-Threads, was für die Bindings irrelevant ist.
- `lambda e: ...` ist nötig, weil Tk dem Handler ein Event-Objekt übergibt, `_prev`/`_next` aber argumentlos sind.

- [ ] **Step 2: Statisch prüfen, dass nur diese Stelle berührt wurde**

Run:

```bash
git diff src/ui.py
```

Expected: Genau zwei `+`-Zeilen mit `self.root.bind(...)`, keine `-`-Zeilen außerhalb des Diff-Kontexts, keine weiteren Änderungen.

- [ ] **Step 3: Volle Test-Suite laufen lassen**

Run: `python -m pytest -v`
Expected: Alle Tests grün, keine Regressionen.

- [ ] **Step 4: SKIP — manueller UI-Smoke-Test (Controller's Aufgabe)**

Der Controller verifiziert manuell:
- App starten, Hauptfenster fokussiert → `<Left>` geht zum vorigen Monat, `<Right>` zum nächsten.
- Auf "Woche" umschalten → `<Left>`/`<Right>` navigieren wochenweise.
- Eintrags-Dialog öffnen, in einem `Entry`-Feld → `<Left>`/`<Right>` bewegen den Cursor im Feld, navigieren **nicht** das Hauptfenster.
- Anderes Programm fokussieren → Pfeiltasten dort beeinflussen die Zeiterfassung nicht.

- [ ] **Step 5: Commit**

```bash
git add src/ui.py
git commit -m "feat(ui): pfeiltasten navigieren monat/woche

<Left>/<Right> am Root-Fenster gebunden — ruft die existierenden
_prev/_next auf, die je nach view_mode Monat oder Woche verschieben.
Modal-Dialoge (grab_set) fangen die Events automatisch ab, kein
expliziter Focus-Check nötig."
```

---

## Verification checklist (post-implementation)

- [ ] `python -m pytest -v` alle grün (keine Regressionen)
- [ ] `git diff master -- src/ui.py` zeigt genau zwei zusätzliche Zeilen
- [ ] Manueller Smoke-Test (Controller, siehe Step 4 oben): Pfeiltasten wirken im Hauptfenster, nicht in Dialogen, nicht im Hintergrund
- [ ] Ein Commit auf dem Branch mit der Message oben
