# E-Mail Monatsbericht Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Send the current month's time report as a formatted HTML email via Gmail OAuth2.

**Architecture:** Three new modules — `report.py` generates the HTML report from month data, `mail.py` handles Gmail OAuth2 auth and sending, `requirements.txt` declares dependencies. Settings and UI are extended for recipient field and send button.

**Tech Stack:** Python 3, google-auth-oauthlib, google-api-python-client, tkinter

---

## File Structure

| File | Change | Responsibility |
|------|--------|---------------|
| `src/report.py` | **New** | Generate HTML report string from month entries |
| `src/mail.py` | **New** | Gmail OAuth2 authentication and email sending |
| `requirements.txt` | **New** | External dependencies |
| `tests/test_report.py` | **New** | Tests for HTML report generation |
| `src/settings.py` | **Modify** | Add `"recipient"` to DEFAULTS |
| `src/ui.py` | **Modify** | "Monat senden" button, recipient field in settings |

---

## Chunk 1: Report Generation

### Task 1: HTML report generator

**Files:**
- Create: `src/report.py`
- Create: `tests/test_report.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_report.py
import pytest
from src.report import generate_report

def test_empty_entries():
    html = generate_report(2026, 3, {})
    assert html is None

def test_single_entry():
    entries = {
        "2026-03-23": {"start": "08:00", "end": "16:30", "pause": 30}
    }
    html = generate_report(2026, 3, entries)
    assert "Zeiterfassung für März 2026:" in html
    assert "23.03.2026" in html
    assert "Mo" in html
    assert "08:00" in html
    assert "16:30" in html
    assert "8.0h" in html
    assert "<table" in html

def test_multiple_entries_sorted():
    entries = {
        "2026-03-25": {"start": "09:00", "end": "17:00", "pause": 30},
        "2026-03-23": {"start": "08:00", "end": "16:30", "pause": 30},
    }
    html = generate_report(2026, 3, entries)
    pos_23 = html.index("23.03.2026")
    pos_25 = html.index("25.03.2026")
    assert pos_23 < pos_25  # sorted by date

def test_total_hours():
    entries = {
        "2026-03-23": {"start": "08:00", "end": "16:30", "pause": 30},
        "2026-03-24": {"start": "09:00", "end": "17:00", "pause": 60},
    }
    html = generate_report(2026, 3, entries)
    # 8.0 + 7.0 = 15.0
    assert "15.0h" in html

def test_filters_other_months():
    entries = {
        "2026-03-23": {"start": "08:00", "end": "16:30", "pause": 0},
        "2026-04-01": {"start": "09:00", "end": "17:00", "pause": 0},
    }
    html = generate_report(2026, 3, entries)
    assert "23.03.2026" in html
    assert "01.04.2026" not in html

def test_legacy_entry_no_pause():
    entries = {
        "2026-03-23": {"start": "08:00", "end": "16:30"}
    }
    html = generate_report(2026, 3, entries)
    assert "8.5h" in html  # no pause field = pause 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_report.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement report generator**

```python
# src/report.py
import datetime
from src.time_utils import calculate_hours

DAYS_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONTHS_DE = [
    "", "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]


def generate_report(year, month, all_entries):
    """Generate an HTML report for the given month. Returns None if no entries."""
    # Filter entries for this month
    prefix = f"{year}-{month:02d}-"
    month_entries = {
        k: v for k, v in all_entries.items() if k.startswith(prefix)
    }

    if not month_entries:
        return None

    month_name = MONTHS_DE[month]
    rows = []
    total = 0.0

    for date_str in sorted(month_entries.keys()):
        entry = month_entries[date_str]
        dt = datetime.date.fromisoformat(date_str)
        weekday = DAYS_DE[dt.weekday()]
        day_fmt = dt.strftime("%d.%m.%Y")
        pause = entry.get("pause", 0)
        hours = round(calculate_hours(entry["start"], entry["end"], pause_minutes=pause), 2)
        total += hours

        rows.append(
            f"<tr>"
            f"<td style='padding:8px;border:1px solid #ddd;'>{day_fmt}</td>"
            f"<td style='padding:8px;border:1px solid #ddd;'>{weekday}</td>"
            f"<td style='padding:8px;border:1px solid #ddd;'>{entry['start']}</td>"
            f"<td style='padding:8px;border:1px solid #ddd;'>{entry['end']}</td>"
            f"<td style='padding:8px;border:1px solid #ddd;'>{hours}h</td>"
            f"</tr>"
        )

    total = round(total, 2)
    rows_html = "\n".join(rows)

    html = f"""<html><body style="font-family:Arial,sans-serif;color:#333;">
<p style="font-size:16px;"><strong>Zeiterfassung für {month_name} {year}:</strong></p>
<table style="border-collapse:collapse;width:100%;max-width:600px;">
<tr style="background:#f0f0f0;">
<th style="padding:8px;border:1px solid #ddd;text-align:left;">Datum</th>
<th style="padding:8px;border:1px solid #ddd;text-align:left;">Wochentag</th>
<th style="padding:8px;border:1px solid #ddd;text-align:left;">Start</th>
<th style="padding:8px;border:1px solid #ddd;text-align:left;">Ende</th>
<th style="padding:8px;border:1px solid #ddd;text-align:left;">Stunden</th>
</tr>
{rows_html}
<tr style="background:#f0f0f0;font-weight:bold;">
<td colspan="4" style="padding:8px;border:1px solid #ddd;">Gesamt</td>
<td style="padding:8px;border:1px solid #ddd;">{total}h</td>
</tr>
</table>
</body></html>"""

    return html
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_report.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/report.py tests/test_report.py
git commit -m "feat: add HTML report generator for monthly time entries"
```

---

## Chunk 2: Gmail OAuth2 Mail Sending

### Task 2: Gmail OAuth2 authentication and sending

**Files:**
- Create: `src/mail.py`
- Create: `requirements.txt`

- [ ] **Step 1: Create requirements.txt**

```
google-auth-oauthlib>=1.0.0
google-api-python-client>=2.0.0
```

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements.txt`

- [ ] **Step 3: Implement mail module**

```python
# src/mail.py
import os
import base64
from email.mime.text import MIMEText

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def get_gmail_service(credentials_path="credentials.json", token_path="token.json"):
    """Authenticate with Gmail API and return a service object.

    Returns the service object, or raises an exception on failure.
    """
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(
                "credentials.json nicht gefunden. "
                "Bitte erstelle ein Google Cloud Projekt mit Gmail API "
                "und lade die OAuth2 Client-ID herunter."
            )
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        creds = flow.run_local_server(port=0)

    with open(token_path, "w") as f:
        f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def send_email(service, to, subject, html_body):
    """Send an HTML email via Gmail API.

    Returns the sent message id, or raises an exception on failure.
    """
    message = MIMEText(html_body, "html")
    message["to"] = to
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {"raw": raw}

    sent = service.users().messages().send(userId="me", body=body).execute()
    return sent["id"]
```

- [ ] **Step 4: Commit**

```bash
git add src/mail.py requirements.txt
git commit -m "feat: add Gmail OAuth2 authentication and email sending"
```

---

## Chunk 3: Settings Extension & UI Integration

### Task 3: Add recipient to settings

**Files:**
- Modify: `src/settings.py`
- Modify: `tests/test_settings.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_settings.py`:

```python
def test_recipient_default(tmp_settings):
    assert tmp_settings.get("recipient") == ""
```

- [ ] **Step 2: Run test — should FAIL**

Run: `python -m pytest tests/test_settings.py::test_recipient_default -v`
Expected: FAIL — returns `None` instead of `""`

- [ ] **Step 3: Add recipient to DEFAULTS in `src/settings.py`**

Change `DEFAULTS` dict:

```python
DEFAULTS = {
    "email": "",
    "default_pause": 30,
    "recipient": "",
}
```

- [ ] **Step 4: Run all settings tests**

Run: `python -m pytest tests/test_settings.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/settings.py tests/test_settings.py
git commit -m "feat: add recipient field to settings defaults"
```

### Task 4: UI — recipient field and send button

**Files:**
- Modify: `src/ui.py`

- [ ] **Step 1: Add recipient field to settings dialog**

In `_open_settings`, after the default pause combobox, add:

```python
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
```

Move the button frame from `row=2` to `row=3`:

```python
btn_frame.grid(row=3, column=0, columnspan=2, pady=12)
```

Update `save_settings` to also save recipient:

```python
def save_settings():
    self.settings.set("email", email_var.get())
    self.settings.set("default_pause", int(pause_var.get()))
    self.settings.set("recipient", recipient_var.get())
    dialog.destroy()
```

- [ ] **Step 2: Add "Monat senden" button to footer**

In `_build_footer`, replace the single label with a frame containing both the label and button:

```python
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
```

- [ ] **Step 3: Add `_send_report` method**

Add import at top of `src/ui.py`:

```python
from src.report import generate_report
from src.mail import get_gmail_service, send_email
```

Add method to App class:

```python
def _send_report(self):
    import os

    recipient = self.settings.get("recipient")
    if not recipient:
        messagebox.showwarning(
            "Kein Empfänger",
            "Bitte zuerst einen Empfänger in den Einstellungen angeben.",
            parent=self.root
        )
        return

    if not os.path.exists("credentials.json"):
        messagebox.showerror(
            "Keine Zugangsdaten",
            "credentials.json nicht gefunden.\n\n"
            "Bitte erstelle ein Google Cloud Projekt mit Gmail API "
            "und lade die OAuth2 Client-ID als credentials.json herunter.",
            parent=self.root
        )
        return

    entries = self.storage.get_all()
    html = generate_report(self.year, self.month, entries)

    if html is None:
        messagebox.showinfo(
            "Keine Einträge",
            f"Keine Einträge für {MONTHS_DE[self.month]} {self.year} vorhanden.",
            parent=self.root
        )
        return

    try:
        service = get_gmail_service()
        month_name = MONTHS_DE[self.month]
        subject = f"Zeiterfassung — {month_name} {self.year}"
        send_email(service, recipient, subject, html)
        messagebox.showinfo(
            "Gesendet",
            f"Bericht für {month_name} {self.year} wurde an {recipient} gesendet.",
            parent=self.root
        )
    except FileNotFoundError as e:
        messagebox.showerror("Fehler", str(e), parent=self.root)
    except Exception as e:
        messagebox.showerror(
            "Senden fehlgeschlagen",
            f"Fehler beim Senden:\n{e}",
            parent=self.root
        )
```

- [ ] **Step 4: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 5: Manual test**

Run: `python -m src.main`
Verify:
- Settings dialog now has "Empfänger" field
- Footer has "Monat senden" button
- Without credentials.json: shows error about missing credentials
- Without recipient: shows warning to configure settings
- Without entries: shows info about no entries

- [ ] **Step 6: Commit**

```bash
git add src/ui.py
git commit -m "feat: add recipient setting and send report button"
```

---

## Chunk 4: Final Verification

### Task 5: Run all tests and add .gitignore entries

- [ ] **Step 1: Update .gitignore**

Add to `.gitignore`:

```
credentials.json
token.json
settings.json
```

These contain secrets/user data and should not be committed.

- [ ] **Step 2: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: add OAuth credentials and token to gitignore"
```
