# E-Mail Monatsbericht — Design Spec

## Overview

Send the current month's time report as a formatted HTML email via Gmail OAuth2. Triggered by a "Monat senden" button in the main window footer.

## Google OAuth2 Authentication

- Requires a Google Cloud project with Gmail API enabled
- OAuth2 Client-ID (Desktop App) saved as `credentials.json` in project directory
- First send opens browser for Google login consent
- Token stored locally as `token.json` (auto-refresh on expiry)
- External dependencies: `google-auth-oauthlib`, `google-api-python-client`

## HTML Report

An HTML-formatted table of the currently displayed month. Only days with entries are shown.

**Subject:** `Zeiterfassung — {Month} {Year}` (e.g. "Zeiterfassung — März 2026")

**Table columns:**

| Datum | Wochentag | Start | Ende | Stunden |
|-------|-----------|-------|------|---------|
| 23.03.2026 | Mo | 08:00 | 16:30 | 8.0h |

- **Stunden** = effective work time (end - start - pause). Pause is NOT shown as a separate column.
- Footer row: **Gesamt: X.Xh**
- Date format: DD.MM.YYYY
- Weekday names in German (Mo, Di, Mi, Do, Fr, Sa, So)

## UI Changes

### Footer — "Monat senden" Button

- New button in the footer area of the main window, next to the "Gesamt" label
- Dark-themed, styled like the existing navigation buttons
- On click:
  - If no `credentials.json` found: show error dialog with setup instructions
  - If no recipient configured in settings: show error dialog
  - If no entries in current month: show info dialog
  - Otherwise: attempt send, show success or error message

### Settings Dialog — Recipient Field

- New field "Empfänger:" (text entry) for the recipient email address
- Added to existing settings dialog below "Standard-Pause"
- Stored in `settings.json` as `"recipient"`

## Settings Extension

```json
{"email": "", "default_pause": 30, "recipient": ""}
```

Default for `recipient`: empty string.

## New Files

| File | Responsibility |
|------|---------------|
| `src/report.py` | Generate HTML report string from month data |
| `src/mail.py` | Gmail OAuth2 authentication and email sending |
| `requirements.txt` | External dependencies |
| `tests/test_report.py` | Tests for HTML report generation |

## Files to Modify

| File | Change |
|------|--------|
| `src/ui.py` | "Monat senden" button, recipient field in settings dialog |
| `src/settings.py` | Add `"recipient"` to DEFAULTS |

## Authentication Flow

1. User clicks "Monat senden"
2. `mail.py` checks for `token.json` — if valid, use it
3. If no valid token, check for `credentials.json` — if missing, show error
4. If `credentials.json` exists but no token, open browser for OAuth consent
5. Save token to `token.json` for future use
6. Send email via Gmail API

## Dependencies (requirements.txt)

```
google-auth-oauthlib>=1.0.0
google-api-python-client>=2.0.0
```

## Out of Scope

- Multiple recipients
- Attachments
- Scheduling/automatic sending
- Email validation
- Pause column in report (only effective hours shown)
