import datetime
import html
import io
from collections import OrderedDict

from src.time_utils import DAYS_DE, calculate_hours, get_week_label


def _esc(text):
    return html.escape(text or "", quote=True)


def _esc_multiline(text):
    return _esc(text).replace("\n", "<br>")


COLUMN_LABELS = ["Datum", "Tag", "Start", "Ende", "Stunden"]

# Style-Dict pro Render-Ziel. Felder werden direkt als CSS-Strings in die
# Inline-Styles der Zellen geschrieben — `_week_block` und `_build_table`
# sind dadurch struktur-, nicht stylegetrieben.
HTML_STYLE = {
    "table_extra": "border-radius:8px;overflow:hidden;",
    "th_row":      "background:#1e293b;",
    "th_cell":     "padding:10px 14px;text-align:left;color:#94a3b8;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;",
    "kw_row":      "background:#334155;",
    "kw_cell":     "padding:10px 14px;color:#ffffff;font-weight:600;font-size:13px;letter-spacing:0.03em;",
    "row_a":       "background:#1e293b;",
    "row_b":       "background:#243347;",
    "td_base":     "padding:10px 14px;border-bottom:1px solid rgba(255,255,255,0.08);",
    "c_date":      "color:#cbd5e1;",
    "c_day":       "color:#94a3b8;",
    "c_time":      "color:#cbd5e1;",
    "c_hours":     "color:#00D8A7;font-weight:600;",
    "sum_row":     "background:#263244;",
    "sum_lbl":     "padding:10px 14px;color:#cbd5e1;font-weight:600;",
    "sum_hrs":     "padding:10px 14px;color:#00D8A7;font-weight:700;",
    "total_row":   "background:#334155;",
    "total_lbl":   "padding:12px 14px;color:#ffffff;font-weight:700;",
    "total_hrs":   "padding:12px 14px;color:#00D8A7;font-weight:700;font-size:15px;",
}

PDF_STYLE = {
    "table_extra": "",
    "th_row":      "background:#1e293b;",
    "th_cell":     "padding:8px 12px;text-align:left;color:#ffffff;font-size:11px;font-weight:600;text-transform:uppercase;",
    "kw_row":      "background:#e2e8f0;",
    "kw_cell":     "padding:8px 12px;color:#111827;font-weight:700;font-size:12px;",
    "row_a":       "background:#ffffff;",
    "row_b":       "background:#f1f5f9;",
    "td_base":     "padding:8px 12px;border-bottom:1px solid #d1d5db;",
    "c_date":      "color:#111827;",
    "c_day":       "color:#4b5563;",
    "c_time":      "color:#111827;",
    "c_hours":     "color:#111827;font-weight:600;",
    "sum_row":     "background:#cbd5e1;",
    "sum_lbl":     "padding:8px 12px;color:#111827;font-weight:700;",
    "sum_hrs":     "padding:8px 12px;color:#111827;font-weight:700;",
    "total_row":   "background:#1e293b;",
    "total_lbl":   "padding:10px 12px;color:#ffffff;font-weight:700;",
    "total_hrs":   "padding:10px 12px;color:#ffffff;font-weight:700;",
}


def _entry_hours(entry):
    pause = entry.get("pause", 0)
    return round(calculate_hours(entry["start"], entry["end"], pause_minutes=pause), 2)


def _group_by_week(range_entries):
    """Group entries by ISO week, chronologically.

    Returns OrderedDict keyed by (iso_year, iso_week), value is list of
    (date_str, entry) tuples sorted by date.
    """
    groups = OrderedDict()
    for date_str in sorted(range_entries.keys()):
        entry = range_entries[date_str]
        dt = datetime.date.fromisoformat(date_str)
        iso = dt.isocalendar()
        key = (iso.year, iso.week)
        groups.setdefault(key, []).append((date_str, entry))
    return groups


def _filter_entries(date_from, date_to, all_entries):
    from_str = date_from.isoformat()
    to_str = date_to.isoformat()
    range_entries = {
        k: v for k, v in all_entries.items() if from_str <= k <= to_str
    }
    return range_entries if range_entries else None


def _apply_placeholders(text, label, total):
    # text ist bereits escaped; label und total sind strukturell sicher
    # (Datum + Float), werden aber für Konsistenz ebenfalls escaped.
    return text.replace("{zeitraum}", _esc(label)).replace("{gesamt}", _esc(f"{total}h"))


# _week_block und _build_table rendern Werte aus dem Storage (entry["start"],
# entry["end"], weekday, day_fmt, iso_week). Diese sind durch validate_entry
# bzw. datetime-Formatter strukturell auf [0-9:.-] beschränkt — kein Escape
# nötig. Wenn diese Quelle sich mal ändert (z.B. freie Eingabe), Escape ergänzen.
def _week_block(iso_year, iso_week, week_entries, style):
    """Render einen Wochen-Block (KW-Header, Tageszeilen, Wochensumme).
    Returns (rows_html, week_total)."""
    s = style
    rows = [
        f"<tr style='{s['kw_row']}'>"
        f"<td colspan='5' style='{s['kw_cell']}'>{get_week_label(iso_year, iso_week)}</td>"
        f"</tr>"
    ]

    week_total = 0.0
    for idx, (date_str, entry) in enumerate(week_entries):
        dt = datetime.date.fromisoformat(date_str)
        weekday = DAYS_DE[dt.weekday()]
        day_fmt = dt.strftime("%d.%m.%Y")
        hours = _entry_hours(entry)
        week_total += hours
        row_bg = s["row_a"] if idx % 2 == 0 else s["row_b"]
        td = s["td_base"]
        rows.append(
            f"<tr style='{row_bg}'>"
            f"<td style='{td}{s['c_date']}'>{day_fmt}</td>"
            f"<td style='{td}{s['c_day']}'>{weekday}</td>"
            f"<td style='{td}{s['c_time']}'>{entry['start']}</td>"
            f"<td style='{td}{s['c_time']}'>{entry['end']}</td>"
            f"<td style='{td}{s['c_hours']}'>{hours}h</td>"
            f"</tr>"
        )

    week_total = round(week_total, 2)
    rows.append(
        f"<tr style='{s['sum_row']}'>"
        f"<td colspan='4' style='{s['sum_lbl']}'>Summe KW {iso_week}</td>"
        f"<td style='{s['sum_hrs']}'>{week_total}h</td>"
        f"</tr>"
    )
    return "\n".join(rows), week_total


def _build_table(groups, style):
    """Bauen die komplette Stundentabelle (Header, alle Wochen-Blöcke,
    Gesamt-Footer). Returns (table_html, total)."""
    s = style
    week_blocks = []
    total = 0.0
    for (iso_year, iso_week), week_entries in groups.items():
        block_html, week_total = _week_block(iso_year, iso_week, week_entries, s)
        week_blocks.append(block_html)
        total += week_total
    total = round(total, 2)

    th_cells = "".join(
        f'<th style="{s["th_cell"]}">{label}</th>' for label in COLUMN_LABELS
    )

    table = (
        f'<table style="border-collapse:collapse;width:100%;{s["table_extra"]}">'
        f'<tr style="{s["th_row"]}">{th_cells}</tr>'
        f'{"".join(week_blocks)}'
        f'<tr style="{s["total_row"]}">'
        f'<td colspan="4" style="{s["total_lbl"]}">Gesamt</td>'
        f'<td style="{s["total_hrs"]}">{total}h</td>'
        f'</tr>'
        f'</table>'
    )
    return table, total


def generate_report(date_from, date_to, all_entries, greeting="", content="", closing=""):
    """Generate an HTML email report with greeting, content, table, and closing.

    Returns (html, total) tuple, or (None, 0) if no entries.
    """
    range_entries = _filter_entries(date_from, date_to, all_entries)
    if not range_entries:
        return None, 0

    label = f"{date_from.strftime('%d.%m.%Y')} – {date_to.strftime('%d.%m.%Y')}"
    groups = _group_by_week(range_entries)
    table, total = _build_table(groups, HTML_STYLE)

    greeting_filled = _apply_placeholders(_esc_multiline(greeting), label, total)
    content_filled = _apply_placeholders(_esc_multiline(content), label, total)
    closing_filled = _apply_placeholders(_esc_multiline(closing), label, total)

    text_style = "color:#cbd5e1;font-size:14px;line-height:1.6;margin:0 0 16px 0;"
    greeting_html = f'<p style="{text_style}">{greeting_filled}</p>' if greeting_filled else ""
    content_html = f'<p style="{text_style}">{content_filled}</p>' if content_filled else ""
    closing_html = f'<p style="{text_style}margin-top:24px;white-space:pre-line;">{closing_filled}</p>' if closing_filled else ""

    html_out = f"""<html><head><meta charset="utf-8"><meta http-equiv="Content-Type" content="text/html; charset=utf-8"></head>
<body style="margin:0;padding:0;background:#0f172a;font-family:'Segoe UI',Arial,sans-serif;">
<div style="max-width:640px;margin:0 auto;padding:32px 24px;">
{greeting_html}
{content_html}
{table}
{closing_html}
</div>
</body></html>"""

    return html_out, total


def generate_pdf(date_from, date_to, all_entries, name=""):
    """Generate a PDF of the time tracking table. Returns PDF bytes, or None if no entries."""
    from xhtml2pdf import pisa

    range_entries = _filter_entries(date_from, date_to, all_entries)
    if not range_entries:
        return None

    label = f"{date_from.strftime('%d.%m.%Y')} – {date_to.strftime('%d.%m.%Y')}"
    groups = _group_by_week(range_entries)
    table, _ = _build_table(groups, PDF_STYLE)

    name_html = (
        f"<p style='color:#111827;font-size:13px;margin:0 0 2px 0;font-weight:600;'>{_esc(name)}</p>"
        if name else ""
    )

    pdf_html = f"""<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:20px;font-family:Arial,sans-serif;font-size:12px;color:#111827;">
<h2 style="font-size:18px;margin:0 0 4px 0;color:#111827;">Zeiterfassung</h2>
{name_html}
<p style="color:#4b5563;font-size:12px;margin:0 0 16px 0;">{_esc(label)}</p>
{table}
</body></html>"""

    buffer = io.BytesIO()
    pisa.CreatePDF(pdf_html, dest=buffer)
    return buffer.getvalue()
