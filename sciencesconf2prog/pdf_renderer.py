"""Render a single-page landscape PDF overview of the conference program."""

import unicodedata
from datetime import datetime, timedelta

EVENT_COLORS = {
    "discours": (255, 235, 156),
    "session": (198, 239, 206),
    "pause": (255, 224, 178),
    "logistique": (220, 220, 240),
}

BORDER_COLORS = {
    "discours": (200, 180, 80),
    "session": (120, 180, 130),
    "pause": (200, 160, 100),
    "logistique": (160, 160, 180),
}

MAX_HOUR = 20  # Trim the grid at 20:00


def _sanitize(text):
    """Replace characters unsupported by latin-1 Helvetica with closest ASCII."""
    text = unicodedata.normalize("NFC", text)
    replacements = {
        "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u2026": "...", "\u00a0": " ",
        "\u0301": "", "\u0300": "",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def render_pdf(data, output_path, title="Programme", subtitle="", page_size="A3"):
    """Render the conference program as a single-page landscape PDF."""
    from fpdf import FPDF

    events = data["events"]
    days = data["days"]

    # Build comm talks per session id
    session_talks = _collect_session_talks(events)

    # Filter out comm events for rendering
    non_comm = [e for e in events if e["type"] != "comm"]

    # Compute time grid (snapped to 30min, capped at MAX_HOUR)
    time_min, time_max = _compute_time_range(non_comm)

    # Compute day layouts (sub-columns for parallel sessions)
    day_layouts = _compute_day_layouts(non_comm, days)

    # Find overlapping pause+logistique pairs per (day, start, end)
    overlap_map = _find_pause_logistique_overlaps(non_comm)

    # Page setup
    if page_size == "A3":
        page_w, page_h = 420, 297
    else:
        page_w, page_h = 297, 210

    pdf = FPDF(orientation="L", unit="mm", format=(page_h, page_w))
    pdf.add_page()
    pdf.set_auto_page_break(auto=False)

    # Layout constants
    margin_left = 10
    margin_right = 5
    margin_top = 8
    margin_bottom = 5
    time_col_w = 12
    header_h = 14
    title_h = 10 if title else 0

    grid_x = margin_left + time_col_w
    grid_y = margin_top + title_h + header_h
    grid_w = page_w - grid_x - margin_right
    grid_h = page_h - grid_y - margin_bottom

    # Title
    if title:
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_xy(0, margin_top)
        full_title = title
        if subtitle:
            full_title += f" - {subtitle}"
        pdf.cell(page_w, 6, _sanitize(full_title), align="C")

    # Day column widths (proportional to sub-column count)
    day_gap = 1
    total_gaps = (len(days) - 1) * day_gap if len(days) > 1 else 0
    usable_w = grid_w - total_gaps

    total_subcols = sum(max(1, len(day_layouts.get(d, {}))) for d in days)
    day_widths = {}
    day_x_starts = {}
    x_cursor = grid_x
    for d in days:
        n = max(1, len(day_layouts.get(d, {})))
        w = usable_w * n / total_subcols
        day_widths[d] = w
        day_x_starts[d] = x_cursor
        x_cursor += w + day_gap

    # Day headers
    pdf.set_font("Helvetica", "B", 8)
    for d in days:
        x = day_x_starts[d]
        w = day_widths[d]
        pdf.set_fill_color(70, 70, 100)
        pdf.set_text_color(255, 255, 255)
        pdf.rect(x, margin_top + title_h, w, header_h, "F")
        pdf.set_xy(x, margin_top + title_h)
        try:
            dt = datetime.strptime(d, "%Y-%m-%d")
            label = dt.strftime("%A %d %B")
        except ValueError:
            label = d
        pdf.cell(w, header_h, _sanitize(label), align="C")

    pdf.set_text_color(0, 0, 0)

    # Time grid helpers
    total_minutes = _minutes_between(time_min, time_max)
    if total_minutes <= 0:
        total_minutes = 1

    def y_for_time(t):
        t_clamped = max(time_min, min(time_max, t))
        m = _minutes_between(time_min, t_clamped)
        return grid_y + (m / total_minutes) * grid_h

    # Draw time labels every 30 min (on the hour and half-hour)
    pdf.set_font("Helvetica", "", 5)
    t = time_min
    while t <= time_max:
        y = y_for_time(t)
        label = t.strftime("%H:%M")
        pdf.set_xy(margin_left, y - 1.5)
        pdf.cell(time_col_w - 1, 3, label, align="R")
        pdf.set_draw_color(210, 210, 210)
        pdf.set_line_width(0.1)
        pdf.line(grid_x, y, grid_x + grid_w, y)
        t += timedelta(minutes=30)

    # Track which events we already drew (for overlap handling)
    drawn_ids = set()

    # Draw events
    for e in non_comm:
        d = e["date"]
        if d not in day_x_starts:
            continue

        etype = e["type"]
        event_key = (e.get("id", ""), d, e["startTime"], e["endTime"], etype)
        if event_key in drawn_ids:
            continue

        start_t = _parse_time(e["startTime"])
        end_t = _parse_time(e["endTime"])
        if not start_t or not end_t:
            continue

        # Clamp to grid range
        start_t = max(start_t, time_min)
        end_t = min(end_t, time_max)

        y1 = y_for_time(start_t)
        y2 = y_for_time(end_t)
        h = y2 - y1
        if h < 0.5:
            continue

        day_x = day_x_starts[d]
        day_w = day_widths[d]
        rooms_in_day = day_layouts.get(d, {})

        # Check for pause/logistique overlap
        overlap_key = (d, e["startTime"], e["endTime"])
        if overlap_key in overlap_map and etype in ("pause", "logistique"):
            pair = overlap_map[overlap_key]
            if pair["pause"] and pair["logistique"]:
                # Draw split cell: top = pause, bottom = logistique
                _draw_split_pause_logistique(
                    pdf, pair["pause"], pair["logistique"],
                    day_x, y1, day_w, h,
                )
                drawn_ids.add((pair["pause"].get("id", ""), d, e["startTime"], e["endTime"], "pause"))
                drawn_ids.add((pair["logistique"].get("id", ""), d, e["startTime"], e["endTime"], "logistique"))
                continue

        drawn_ids.add(event_key)

        color = EVENT_COLORS.get(etype, (230, 230, 230))
        border_color = BORDER_COLORS.get(etype, (180, 180, 180))

        if etype in ("pause", "logistique"):
            x, w = day_x, day_w
        elif etype == "discours":
            x, w = day_x, day_w
        elif etype == "session":
            room = e.get("salle", "")
            if room in rooms_in_day:
                idx = rooms_in_day[room]
                n = len(rooms_in_day)
                sub_w = day_w / n
                x = day_x + idx * sub_w
                w = sub_w
            else:
                x, w = day_x, day_w
        else:
            continue

        talks = session_talks.get(e.get("id", ""), []) if etype == "session" else []
        _draw_event(pdf, e, x, y1, w, h, color, border_color, talks)

    # Day column separators
    pdf.set_draw_color(150, 150, 150)
    pdf.set_line_width(0.3)
    for d in days:
        x = day_x_starts[d]
        pdf.line(x, grid_y, x, grid_y + grid_h)
    if days:
        last_d = days[-1]
        x_end = day_x_starts[last_d] + day_widths[last_d]
        pdf.line(x_end, grid_y, x_end, grid_y + grid_h)

    pdf.line(grid_x, grid_y, grid_x + grid_w, grid_y)
    pdf.line(grid_x, grid_y + grid_h, grid_x + grid_w, grid_y + grid_h)

    pdf.output(str(output_path))


def _compute_time_range(events):
    """Find earliest start and latest end, snapped to 30-min boundaries, capped at MAX_HOUR."""
    starts = []
    ends = []
    for e in events:
        s = _parse_time(e.get("startTime", ""))
        t = _parse_time(e.get("endTime", ""))
        if s:
            starts.append(s)
        if t:
            ends.append(t)

    time_min = min(starts) if starts else datetime(2000, 1, 1, 8, 0)
    time_max = max(ends) if ends else datetime(2000, 1, 1, 18, 0)

    # Snap min down to nearest 30 min
    time_min = time_min.replace(minute=(time_min.minute // 30) * 30, second=0)

    # Snap max up to nearest 30 min, then cap at MAX_HOUR
    if time_max.minute % 30 != 0:
        time_max = time_max.replace(minute=((time_max.minute // 30) + 1) * 30 % 60, second=0)
        if time_max.minute == 0:
            time_max += timedelta(hours=0)  # already rolled over
            time_max = time_max.replace(hour=time_max.hour + 1 if time_max.minute == 0 and time_max.second == 0 else time_max.hour)

    cap = datetime(2000, 1, 1, MAX_HOUR, 0)
    if time_max > cap:
        time_max = cap

    return time_min, time_max


def _compute_day_layouts(events, days):
    """For each day, compute room -> sub-column index for sessions."""
    day_rooms = {d: [] for d in days}
    for e in events:
        if e["type"] == "session" and e.get("salle") and e["date"] in day_rooms:
            room = e["salle"]
            if room not in day_rooms[e["date"]]:
                day_rooms[e["date"]].append(room)
    return {
        d: {room: i for i, room in enumerate(sorted(rooms))}
        for d, rooms in day_rooms.items()
    }


def _collect_session_talks(events):
    """Build a dict: session_id -> list of {speaker_short, title} from comm events."""
    session_ids = {e["id"] for e in events if e["type"] == "session" and e.get("id")}
    talks = {sid: [] for sid in session_ids}

    for e in events:
        if e["type"] == "comm" and e.get("id") in talks:
            speaker = e.get("speaker", "").strip()
            short_name = ""
            if speaker:
                name = speaker.split(",")[0].strip()
                parts = name.split()
                if parts:
                    short_name = parts[-1]
            talks[e["id"]].append({
                "speaker": short_name,
                "title": e.get("titre", "").strip(),
            })

    return talks


def _find_pause_logistique_overlaps(events):
    """Find (day, start, end) slots where both a pause and logistique exist."""
    by_slot = {}
    for e in events:
        if e["type"] in ("pause", "logistique"):
            key = (e["date"], e["startTime"], e["endTime"])
            if key not in by_slot:
                by_slot[key] = {"pause": None, "logistique": None}
            by_slot[key][e["type"]] = e

    return {k: v for k, v in by_slot.items() if v["pause"] and v["logistique"]}


def _draw_split_pause_logistique(pdf, pause_event, logi_event, x, y, w, h):
    """Draw a split cell: left = pause title, right = logistique title (no names)."""
    w_left = w / 2
    w_right = w - w_left
    pad = 0.5

    font_size = min(5, max(3.5, h / 2.5))

    # Left: pause
    r, g, b = EVENT_COLORS["pause"]
    br, bg, bb = BORDER_COLORS["pause"]
    pdf.set_fill_color(r, g, b)
    pdf.set_draw_color(br, bg, bb)
    pdf.set_line_width(0.2)
    pdf.rect(x, y, w_left, h, "DF")

    pdf.set_text_color(30, 30, 30)
    pdf.set_font("Helvetica", "B", font_size)
    title = _sanitize(pause_event.get("titre", ""))
    _draw_clipped_text(pdf, title, x + pad, y + pad, w_left - 2 * pad, h - 2 * pad, font_size)

    # Right: logistique (title only, no description/names)
    r, g, b = EVENT_COLORS["logistique"]
    br, bg, bb = BORDER_COLORS["logistique"]
    pdf.set_fill_color(r, g, b)
    pdf.set_draw_color(br, bg, bb)
    pdf.rect(x + w_left, y, w_right, h, "DF")

    pdf.set_font("Helvetica", "B", font_size)
    title = _sanitize(logi_event.get("titre", ""))
    _draw_clipped_text(pdf, title, x + w_left + pad, y + pad, w_right - 2 * pad, h - 2 * pad, font_size)


def _parse_time(time_str):
    """Parse HH:MM time string into a datetime (date part is arbitrary)."""
    if not time_str:
        return None
    try:
        parts = time_str.split(":")
        return datetime(2000, 1, 1, int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        return None


def _minutes_between(t1, t2):
    return (t2 - t1).total_seconds() / 60


def _draw_event(pdf, event, x, y, w, h, color, border_color, session_talks=None):
    """Draw a colored rectangle with event text."""
    r, g, b = color
    pdf.set_fill_color(r, g, b)
    br, bg, bb = border_color
    pdf.set_draw_color(br, bg, bb)
    pdf.set_line_width(0.2)
    pdf.rect(x, y, w, h, "DF")

    pad = 0.5
    text_x = x + pad
    text_y = y + pad
    text_w = w - 2 * pad
    text_h = h - 2 * pad
    bottom_y = y + h - pad

    if text_w < 2 or text_h < 2:
        return

    pdf.set_text_color(30, 30, 30)

    etype = event["type"]
    title = _sanitize(event.get("titre", ""))
    speaker = _sanitize(event.get("speaker", ""))
    room = _sanitize(event.get("salle", ""))

    chair = ""
    if etype == "session":
        chair = speaker
        speaker = ""

    cursor_y = text_y

    # Adaptive font sizes based on cell height
    if h > 20:
        title_size = 6
        info_size = 5
        talk_size = 4.5
    elif h > 10:
        title_size = 5.5
        info_size = 4.5
        talk_size = 4
    else:
        title_size = min(5, max(3.5, h / 2.5))
        info_size = max(3.5, title_size - 0.5)
        talk_size = max(3, title_size - 1)

    # Title (bold)
    pdf.set_font("Helvetica", "B", title_size)
    if title:
        cursor_y = _draw_clipped_text(pdf, title, text_x, cursor_y, text_w, bottom_y - cursor_y, title_size)

    # Speaker (for plenaries)
    if speaker and etype == "discours" and cursor_y < bottom_y - 1:
        pdf.set_font("Helvetica", "", info_size)
        cursor_y = _draw_clipped_text(pdf, speaker, text_x, cursor_y, text_w, bottom_y - cursor_y, info_size)

    # Room (for plenaries and sessions)
    if room and etype in ("discours", "session") and cursor_y < bottom_y - 1:
        pdf.set_font("Helvetica", "", info_size)
        pdf.set_text_color(100, 100, 100)
        cursor_y = _draw_clipped_text(pdf, room, text_x, cursor_y, text_w, bottom_y - cursor_y, info_size)
        pdf.set_text_color(30, 30, 30)

    # Chair info
    plenary_chair = event.get("chair", "")
    if etype == "discours" and plenary_chair:
        chair = _sanitize(plenary_chair)
    if chair and cursor_y < bottom_y - 1:
        pdf.set_font("Helvetica", "I", info_size)
        cursor_y = _draw_clipped_text(pdf, f"Chair: {chair}", text_x, cursor_y, text_w, bottom_y - cursor_y, info_size)

    # Session speakers (comma-separated last names)
    if etype == "session" and session_talks and cursor_y < bottom_y - 1:
        speakers_text = ", ".join(
            _sanitize(t["speaker"]) for t in session_talks if t["speaker"]
        )
        if speakers_text:
            cursor_y += talk_size * 0.2
            pdf.set_font("Helvetica", "", talk_size)
            pdf.set_text_color(50, 50, 50)
            cursor_y = _draw_clipped_text(
                pdf, speakers_text, text_x, cursor_y, text_w, bottom_y - cursor_y, talk_size
            )
            pdf.set_text_color(30, 30, 30)


def _draw_clipped_text(pdf, text, x, y, max_w, max_h, font_size):
    """Draw text clipped to a bounding box. Returns new y position."""
    if max_h < font_size * 0.35:
        return y

    line_h = font_size * 0.4
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test = f"{current_line} {word}".strip() if current_line else word
        if pdf.get_string_width(test) <= max_w:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    max_lines = max(1, int(max_h / line_h))
    lines = lines[:max_lines]

    for line in lines:
        if y + line_h > y + max_h + font_size * 0.35:
            break
        while pdf.get_string_width(line) > max_w and len(line) > 1:
            line = line[:-1]
        pdf.set_xy(x, y)
        pdf.cell(max_w, line_h, line)
        y += line_h

    return y
