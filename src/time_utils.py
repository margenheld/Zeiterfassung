def parse_time(time_str):
    """Parse HH:MM string. Returns (hours, minutes) or None if invalid."""
    try:
        parts = time_str.split(":")
        if len(parts) != 2:
            return None
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            return None
        return (h, m)
    except (ValueError, AttributeError):
        return None

def calculate_hours(start_str, end_str, pause_minutes=0):
    """Calculate decimal hours between two HH:MM strings, minus pause."""
    start = parse_time(start_str)
    end = parse_time(end_str)
    if start is None or end is None:
        return 0.0
    start_min = start[0] * 60 + start[1]
    end_min = end[0] * 60 + end[1]
    return round((end_min - start_min - pause_minutes) / 60, 2)

def validate_entry(start_str, end_str):
    """Validate a time entry. Returns (ok, error_message)."""
    start = parse_time(start_str)
    if start is None:
        return False, "Startzeit ungültig (Format: HH:MM)"
    end = parse_time(end_str)
    if end is None:
        return False, "Endzeit ungültig (Format: HH:MM)"
    start_min = start[0] * 60 + start[1]
    end_min = end[0] * 60 + end[1]
    if end_min <= start_min:
        return False, "Endzeit muss nach Startzeit liegen"
    return True, ""
