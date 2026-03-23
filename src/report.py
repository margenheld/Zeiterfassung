import datetime
from src.time_utils import calculate_hours

DAYS_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONTHS_DE = [
    "", "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]


def generate_report(date_from, date_to, all_entries):
    """Generate an HTML report for the given date range (inclusive). Returns None if no entries."""
    from_str = date_from.isoformat()
    to_str = date_to.isoformat()
    range_entries = {
        k: v for k, v in all_entries.items() if from_str <= k <= to_str
    }

    if not range_entries:
        return None

    label = f"{date_from.strftime('%d.%m.%Y')} – {date_to.strftime('%d.%m.%Y')}"
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

    html = f"""<html><body style="margin:0;padding:0;background:#0f172a;font-family:'Segoe UI',Arial,sans-serif;">
<div style="max-width:640px;margin:0 auto;padding:32px 24px;">
<h2 style="color:#ffffff;font-size:20px;font-weight:700;margin:0 0 4px 0;">Zeiterfassung</h2>
<p style="color:#94a3b8;font-size:14px;margin:0 0 24px 0;">{label}</p>
<table style="border-collapse:collapse;width:100%;border-radius:8px;overflow:hidden;">
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
</table>
</div>
</body></html>"""

    return html
