"""Build the static program files from CSV data."""

import csv
import json
from pathlib import Path

from sciencesconf2prog.templates import get_html_template, get_css, get_js_template


def parse_csv(csv_path: Path) -> list[dict]:
    """Parse the CSV file and return a list of events."""
    events = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";", quotechar='"')
        for row in reader:
            events.append(dict(row))

    return events


def load_submissions(submissions_path: Path) -> dict[str, dict]:
    """Load submissions.json and return a dict indexed by DOCID."""
    if not submissions_path.exists():
        return {}

    with open(submissions_path, "r", encoding="utf-8") as f:
        submissions = json.load(f)

    return {s["DOCID"]: s for s in submissions if s.get("DOCID")}


def load_plenaries(plenaries_path: Path) -> dict[str, dict]:
    """Load plenaries.json and return a dict indexed by id."""
    if not plenaries_path.exists():
        return {}

    with open(plenaries_path, "r", encoding="utf-8") as f:
        plenaries = json.load(f)

    return {p["id"]: p for p in plenaries if p.get("id")}


def process_events(raw_events: list[dict], submissions: dict[str, dict] = None, plenaries: dict[str, dict] = None) -> dict:
    """Process raw events into structured data for the frontend."""
    if submissions is None:
        submissions = {}
    if plenaries is None:
        plenaries = {}

    events = []
    days = set()
    rooms = set()

    for e in raw_events:
        if not e.get("date"):
            continue

        docid = e.get("docid", "")
        submission = submissions.get(docid, {})

        event = {
            "id": e.get("id", ""),
            "date": e.get("date", ""),
            "start": e.get("start", ""),
            "end": e.get("end", ""),
            "startTime": e.get("start", "")[:5] if e.get("start") else "",
            "endTime": e.get("end", "")[:5] if e.get("end") else "",
            "type": e.get("type", ""),
            "salle": e.get("salle", ""),
            "room": normalize_room(e.get("salle", "")),
            "roomDisplay": e.get("salle", ""),
            "titre": e.get("titre", ""),
            "description": e.get("description", ""),
            "speaker": e.get("speaker", ""),
            "docid": docid,
            "abstract": submission.get("ABSTRACT", ""),
        }

        # Merge plenary data (chair, abstract) by event id
        plenary = plenaries.get(event["id"], {})
        if plenary:
            if plenary.get("chair"):
                event["chair"] = plenary["chair"]
            if plenary.get("abstract") and not event["abstract"]:
                event["abstract"] = plenary["abstract"]

        events.append(event)
        days.add(event["date"])

        if event["salle"]:
            rooms.add(event["salle"])

    return {
        "events": events,
        "days": sorted(days),
        "rooms": sorted(rooms),
    }


def normalize_room(room: str) -> str:
    """Normalize room name for CSS class usage."""
    import unicodedata

    if not room:
        return ""

    normalized = unicodedata.normalize("NFD", room.lower())
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def build_program(
    csv_path: Path,
    output_dir: Path,
    title: str = "Programme",
    subtitle: str = "Conférence 2026",
    submissions_path: Path = None,
    plenaries_path: Path = None,
) -> None:
    """Build the complete program from CSV to static files."""
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load submissions if path provided or look for default location
    if submissions_path is None:
        submissions_path = csv_path.parent / "submissions.json"
    submissions = load_submissions(submissions_path)

    # Load plenaries if path provided or look for default location
    if plenaries_path is None:
        plenaries_path = csv_path.parent / "plenaries.json"
    plenaries = load_plenaries(plenaries_path)

    # Parse and process CSV
    raw_events = parse_csv(csv_path)
    data = process_events(raw_events, submissions, plenaries)

    # Generate files
    html_content = get_html_template(title, subtitle)
    css_content = get_css(data["rooms"])
    js_content = get_js_template(data)

    # Write files
    (output_dir / "index.html").write_text(html_content, encoding="utf-8")
    (output_dir / "styles.css").write_text(css_content, encoding="utf-8")
    (output_dir / "app.js").write_text(js_content, encoding="utf-8")
