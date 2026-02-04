# sciencesconf2prog

Generate a responsive conference program from a SciencesConf CSV/JSON export.

## Features

- **Static site** — Generates 3 files (HTML, CSS, JS) deployable anywhere
- **Responsive** — Mobile-first design for all screen sizes
- **Overview mode** — Tab to see the entire program on one page
- **Parallel sessions** — Side-by-side display of simultaneous sessions
- **Abstracts** — Optional integration of abstracts from `submissions.json`
- **Detail modal** — Click any event to see full details

## Installation

```bash
pip install -e .
```

## Usage

### Basic command

```bash
sciencesconf2prog build
```

Reads `planning.csv` and `submissions.json` from the current directory and generates the site in `dist/`.

### Options

```bash
sciencesconf2prog build planning.csv \
  -o public/ \
  --title "SMAI-MODE 2026" \
  --subtitle "Nice, March 18-20" \
  --submissions submissions.json
```

## License

MIT
