import datetime
import io
from src.time_utils import calculate_hours

DAYS_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONTHS_DE = [
    "", "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]


def _build_table_rows(range_entries):
    """Build HTML table rows and calculate total hours. Returns (rows_html, total)."""
    rows = []
    total = 0.0

    for date_str in sorted(range_entries.keys()):
        entry = range_entries[date_str]
        dt = datetime.date.fromisoformat(date_str)
        weekday = DAYS_DE[dt.weekday()]
        day_fmt = dt.strftime("%d.%m.%Y")
        pause = entry.get("pause", 0)
        hours = round(calculate_hours(entry["start"], entry["end"], pause_minutes=pause), 2)
        total += hours

        row_bg = "#1e293b" if len(rows) % 2 == 0 else "#243347"
        rows.append(
            f"<tr style='background:{row_bg};'>"
            f"<td style='padding:10px 14px;border-bottom:1px solid rgba(255,255,255,0.08);color:#cbd5e1;'>{day_fmt}</td>"
            f"<td style='padding:10px 14px;border-bottom:1px solid rgba(255,255,255,0.08);color:#94a3b8;'>{weekday}</td>"
            f"<td style='padding:10px 14px;border-bottom:1px solid rgba(255,255,255,0.08);color:#cbd5e1;'>{entry['start']}</td>"
            f"<td style='padding:10px 14px;border-bottom:1px solid rgba(255,255,255,0.08);color:#cbd5e1;'>{entry['end']}</td>"
            f"<td style='padding:10px 14px;border-bottom:1px solid rgba(255,255,255,0.08);color:#00D8A7;font-weight:600;'>{hours}h</td>"
            f"</tr>"
        )

    total = round(total, 2)
    rows_html = "\n".join(rows)
    return rows_html, total


def _table_html(rows_html, total):
    """Wrap rows in the styled table with header and total row."""
    return f"""<table style="border-collapse:collapse;width:100%;border-radius:8px;overflow:hidden;">
<tr style="background:#334155;">
<th style="padding:10px 14px;text-align:left;color:#94a3b8;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">Datum</th>
<th style="padding:10px 14px;text-align:left;color:#94a3b8;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">Tag</th>
<th style="padding:10px 14px;text-align:left;color:#94a3b8;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">Start</th>
<th style="padding:10px 14px;text-align:left;color:#94a3b8;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">Ende</th>
<th style="padding:10px 14px;text-align:left;color:#94a3b8;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">Stunden</th>
</tr>
{rows_html}
<tr style="background:#334155;">
<td colspan="4" style="padding:12px 14px;color:#ffffff;font-weight:700;">Gesamt</td>
<td style="padding:12px 14px;color:#00D8A7;font-weight:700;font-size:15px;">{total}h</td>
</tr>
</table>"""


def _filter_entries(date_from, date_to, all_entries):
    """Filter entries to the given date range (inclusive). Returns dict or None."""
    from_str = date_from.isoformat()
    to_str = date_to.isoformat()
    range_entries = {
        k: v for k, v in all_entries.items() if from_str <= k <= to_str
    }
    return range_entries if range_entries else None


def _apply_placeholders(text, label, total):
    """Replace {zeitraum} and {gesamt} placeholders in text."""
    return text.replace("{zeitraum}", label).replace("{gesamt}", f"{total}h")


def generate_report(date_from, date_to, all_entries, greeting="", content="", closing=""):
    """Generate an HTML email report with greeting, content, table, and closing.

    Returns (html, total) tuple, or (None, 0) if no entries.
    """
    range_entries = _filter_entries(date_from, date_to, all_entries)
    if not range_entries:
        return None, 0

    label = f"{date_from.strftime('%d.%m.%Y')} – {date_to.strftime('%d.%m.%Y')}"
    rows_html, total = _build_table_rows(range_entries)
    table = _table_html(rows_html, total)

    greeting_filled = _apply_placeholders(greeting, label, total)
    content_filled = _apply_placeholders(content, label, total)
    closing_filled = _apply_placeholders(closing, label, total)

    # Build text sections as styled paragraphs
    text_style = "color:#cbd5e1;font-size:14px;line-height:1.6;margin:0 0 16px 0;"
    greeting_html = f'<p style="{text_style}">{greeting_filled}</p>' if greeting_filled else ""
    content_html = f'<p style="{text_style}">{content_filled}</p>' if content_filled else ""
    closing_html = f'<p style="{text_style}margin-top:24px;white-space:pre-line;">{closing_filled}</p>' if closing_filled else ""

    html = f"""<html><body style="margin:0;padding:0;background:#0f172a;font-family:'Segoe UI',Arial,sans-serif;">
<div style="max-width:640px;margin:0 auto;padding:32px 24px;">
{greeting_html}
{content_html}
{table}
{closing_html}
</div>
</body></html>"""

    return html, total


def generate_pdf(date_from, date_to, all_entries, name=""):
    """Generate a PDF of the time tracking table. Returns PDF bytes, or None if no entries."""
    from xhtml2pdf import pisa

    range_entries = _filter_entries(date_from, date_to, all_entries)
    if not range_entries:
        return None

    label = f"{date_from.strftime('%d.%m.%Y')} – {date_to.strftime('%d.%m.%Y')}"
    rows_html, total = _build_table_rows(range_entries)

    # PDF uses a print-friendly light theme
    pdf_rows = []
    for date_str in sorted(range_entries.keys()):
        entry = range_entries[date_str]
        dt = datetime.date.fromisoformat(date_str)
        weekday = DAYS_DE[dt.weekday()]
        day_fmt = dt.strftime("%d.%m.%Y")
        pause = entry.get("pause", 0)
        hours = round(calculate_hours(entry["start"], entry["end"], pause_minutes=pause), 2)

        row_bg = "#ffffff" if len(pdf_rows) % 2 == 0 else "#f1f5f9"
        pdf_rows.append(
            f"<tr style='background:{row_bg};'>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #d1d5db;color:#111827;'>{day_fmt}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #d1d5db;color:#4b5563;'>{weekday}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #d1d5db;color:#111827;'>{entry['start']}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #d1d5db;color:#111827;'>{entry['end']}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #d1d5db;color:#111827;font-weight:600;'>{hours}h</td>"
            f"</tr>"
        )

    pdf_rows_html = "\n".join(pdf_rows)

    pdf_html = f"""<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:20px;font-family:Arial,sans-serif;font-size:12px;color:#111827;">
<h2 style="font-size:18px;margin:0 0 4px 0;color:#111827;">Zeiterfassung</h2>
{"<p style='color:#111827;font-size:13px;margin:0 0 2px 0;font-weight:600;'>" + name + "</p>" if name else ""}
<p style="color:#4b5563;font-size:12px;margin:0 0 16px 0;">{label}</p>
<table style="border-collapse:collapse;width:100%;">
<tr style="background:#1e293b;">
<th style="padding:8px 12px;text-align:left;color:#ffffff;font-size:11px;font-weight:600;text-transform:uppercase;">Datum</th>
<th style="padding:8px 12px;text-align:left;color:#ffffff;font-size:11px;font-weight:600;text-transform:uppercase;">Tag</th>
<th style="padding:8px 12px;text-align:left;color:#ffffff;font-size:11px;font-weight:600;text-transform:uppercase;">Start</th>
<th style="padding:8px 12px;text-align:left;color:#ffffff;font-size:11px;font-weight:600;text-transform:uppercase;">Ende</th>
<th style="padding:8px 12px;text-align:left;color:#ffffff;font-size:11px;font-weight:600;text-transform:uppercase;">Stunden</th>
</tr>
{pdf_rows_html}
<tr style="background:#1e293b;">
<td colspan="4" style="padding:10px 12px;color:#ffffff;font-weight:700;">Gesamt</td>
<td style="padding:10px 12px;color:#ffffff;font-weight:700;">{total}h</td>
</tr>
</table>
</body></html>"""

    buffer = io.BytesIO()
    pisa.CreatePDF(pdf_html, dest=buffer)
    return buffer.getvalue()
