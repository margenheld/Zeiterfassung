import datetime
from src.time_utils import calculate_hours

DAYS_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONTHS_DE = [
    "", "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]


def generate_report(year, month, all_entries):
    """Generate an HTML report for the given month. Returns None if no entries."""
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
