# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

sciencesconf2prog is a static site generator that transforms SciencesConf CSV exports into a beautiful, responsive conference program website. It produces three static files (HTML, CSS, JS) with embedded data—no server-side processing required.

## Commands

```bash
# Install in development mode
pip install -e .

# Build the program (reads planning.csv, outputs to dist/)
sciencesconf2prog build

# Build with custom options
sciencesconf2prog build planning.csv -o public/ --title "SMAI-MODE 2026" --subtitle "Nice, 18-20 Mars"

# Preview the output
cd dist && python3 -m http.server 8000
```

## Architecture

### Data Flow

1. **Input**: `planning.csv` (SciencesConf export, semicolon-delimited) + optional `submissions.json` (abstracts)
2. **Processing**: `builder.py` parses CSV, merges abstracts by DOCID, structures data
3. **Output**: Static HTML/CSS/JS with event data embedded as JSON in `app.js`

### Module Structure (`sciencesconf2prog/`)

- `cli.py` - argparse-based CLI, entry point via `sciencesconf2prog` command
- `builder.py` - CSV parsing, submissions loading, data processing, file generation
- `templates.py` - HTML template, CSS stylesheet, and JS code as Python strings with f-string interpolation for embedding data

### Event Types

The CSV contains these event types that map to different visual styles:
- `discours` - Plenary sessions (purple)
- `session` - Parallel sessions containing multiple `comm` events (teal)
- `comm` - Individual communications/talks within sessions (green)
- `pause` - Breaks (orange)
- `logistique` - Logistics/info items (gray)

### Key Design Decisions

- All data is embedded in `app.js` at build time—no runtime fetching
- Sessions and their nested talks are linked by matching room + time range
- Room names are normalized (lowercase, diacritics removed) for CSS class generation
- The UI has two modes: daily view (detailed with talks) and overview (compact, all days)
