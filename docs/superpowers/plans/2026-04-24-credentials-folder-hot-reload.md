# Credentials-Status Hot-Reload Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the `credentials.json` ✓/✗ status label in the Settings dialog refresh live (every 500 ms) instead of only at dialog-open time.

**Architecture:** Replace the inline status-label construction in `_open_settings` with a held-reference label plus a `refresh_status` closure that updates the label and reschedules itself via `dialog.after(500, refresh_status)`. The closure self-stops via `status_label.winfo_exists()` when the dialog is destroyed. Single-file change in `src/ui.py`. No new modules, no new imports, no new tests.

**Tech Stack:** Tkinter `dialog.after` for the polling timer; `widget.winfo_exists()` for the lifecycle guard. All stdlib.

**Spec reference:** `docs/superpowers/specs/2026-04-24-credentials-folder-hot-reload-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/ui.py` | Modify | Replace ~10 lines in `_open_settings` (the inline status-label construction + the `if creds_present` precomputation) with a held-reference label + `refresh_status` closure |

No other files. No tests (UI polling, consistent with the "no Tkinter UI tests" stance of the predecessor work).

---

## Chunk 1: Hot-reload polling

### Task 1: Replace inline status label with held-reference + refresh closure

**Files:**
- Modify: `src/ui.py` (`_open_settings`, lines 312-349)

This task has no automated tests. Verification is via `pytest -v` (no regressions) plus a manual smoke test described in Step 4.

- [ ] **Step 1: Apply the edit**

In `src/ui.py`, find this block in `_open_settings` (currently lines 312-349):

```python
        creds_path = os.path.join(self.base_path, "credentials.json")
        creds_present = os.path.exists(creds_path)

        tk.Label(
            dialog, text="Datenordner:", font=FONT, bg=BG, fg=TEXT
        ).grid(row=1, column=0, padx=10, pady=4, sticky="w")

        creds_row = tk.Frame(dialog, bg=BG)
        creds_row.grid(row=1, column=1, padx=10, pady=4, sticky="w")

        def open_data_folder():
            try:
                open_folder(self.base_path)
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
            relief=tk.FLAT, padx=12, pady=2, cursor="hand2"
        ).pack(side=tk.LEFT)

        if creds_present:
            status_text = "✓ credentials.json vorhanden"
            status_fg = STATUS_OK
        else:
            status_text = "✗ credentials.json fehlt"
            status_fg = ACCENT

        tk.Label(
            creds_row, text=status_text, font=FONT_SMALL,
            bg=BG, fg=status_fg
        ).pack(side=tk.LEFT, padx=(10, 0))
```

Replace with:

```python
        creds_path = os.path.join(self.base_path, "credentials.json")

        tk.Label(
            dialog, text="Datenordner:", font=FONT, bg=BG, fg=TEXT
        ).grid(row=1, column=0, padx=10, pady=4, sticky="w")

        creds_row = tk.Frame(dialog, bg=BG)
        creds_row.grid(row=1, column=1, padx=10, pady=4, sticky="w")

        def open_data_folder():
            try:
                open_folder(self.base_path)
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
            relief=tk.FLAT, padx=12, pady=2, cursor="hand2"
        ).pack(side=tk.LEFT)

        status_label = tk.Label(
            creds_row, text="", font=FONT_SMALL, bg=BG
        )
        status_label.pack(side=tk.LEFT, padx=(10, 0))

        def refresh_status():
            if not status_label.winfo_exists():
                return
            if os.path.exists(creds_path):
                status_label.config(
                    text="✓ credentials.json vorhanden", fg=STATUS_OK
                )
            else:
                status_label.config(
                    text="✗ credentials.json fehlt", fg=ACCENT
                )
            dialog.after(500, refresh_status)

        refresh_status()
```

**What changed and why:**
- Removed the `creds_present` line and the `if creds_present: ... else: ...` precomputation block — `refresh_status` handles both initial paint and live refresh.
- The new `tk.Label` has `text=""` and no `fg` at construction; `refresh_status()` populates them on its very first synchronous call (right after `pack`).
- `dialog.after(500, refresh_status)` reschedules at the end, creating the polling loop.
- `status_label.winfo_exists()` at the top of the callback prevents a TclError on the last fire-after-destroy. Tkinter is single-threaded, so no race between the existence check and the `config` call within one iteration.

- [ ] **Step 2: Confirm no leftover variable references**

Run:

```bash
grep -n "creds_present\|status_text\|status_fg" src/ui.py
```

Expected: no matches anywhere in `src/ui.py`. The three local variables only existed inside the replaced block.

- [ ] **Step 3: Run the full test suite**

Run: `python -m pytest -v`
Expected: 86 tests pass, no regressions. (No new tests; the change is UI-polling only.)

- [ ] **Step 4: Manual smoke test**

Run the app from the repo:

```bash
python main.py
```

Click the gear icon (top right) to open Settings.

Test sequence with the dialog kept open the whole time:

1. With `credentials.json` present in the repo root: status label shows `✓ credentials.json vorhanden` (green).
2. Without closing the dialog, in another terminal/Explorer: rename or delete the file (`mv credentials.json credentials.json.bak`).
3. Within ~1 second: the label flips to `✗ credentials.json fehlt` (red).
4. Restore the file (`mv credentials.json.bak credentials.json`).
5. Within ~1 second: the label flips back to `✓ credentials.json vorhanden` (green).
6. Close the Settings dialog. (The polling stops; no Python warnings/errors in the console.)

**Safety:** `credentials.json` is in `.gitignore` (verified) — your local file is not at risk of being committed.

- [ ] **Step 5: Commit**

```bash
git add src/ui.py
git commit -m "feat: settings dialog credentials-status refreshes live every 500ms

Replaces the inline ✓/✗ status label in _open_settings with a held
reference plus a refresh_status closure that polls os.path.exists
every 500 ms via dialog.after. The loop self-stops via
status_label.winfo_exists() when the dialog is destroyed. Reverses
Decision #4 of the original credentials-folder-button spec — the
once-at-open check was friction the user noticed in practice."
```

---

## Verification checklist (post-implementation)

- [ ] `python -m pytest -v` all green (86 tests, unchanged count)
- [ ] Manual smoke test from Step 4 passes — status flips both directions within ~1 second
- [ ] Closing the Settings dialog leaves no errors in the console
- [ ] One commit on the branch with the message above
