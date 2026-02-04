"""Command-line interface for sciencesconf2prog."""

import argparse
import sys
from pathlib import Path

from sciencesconf2prog import __version__
from sciencesconf2prog.builder import build_program


def main():
    parser = argparse.ArgumentParser(
        prog="sciencesconf2prog",
        description="Generate a beautiful conference program from SciencesConf CSV export",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Build command
    build_parser = subparsers.add_parser(
        "build", help="Build the program from a CSV file"
    )
    build_parser.add_argument(
        "csv_file",
        type=Path,
        nargs="?",
        default=Path("planning.csv"),
        help="Path to the CSV file (default: planning.csv)",
    )
    build_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("dist"),
        help="Output directory (default: dist)",
    )
    build_parser.add_argument(
        "--title",
        type=str,
        default="Programme",
        help="Title of the program (default: Programme)",
    )
    build_parser.add_argument(
        "--subtitle",
        type=str,
        default="Conférence 2026",
        help="Subtitle of the program (default: Conférence 2026)",
    )
    build_parser.add_argument(
        "--submissions",
        type=Path,
        default=None,
        help="Path to submissions.json file (default: submissions.json next to CSV)",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "build":
        if not args.csv_file.exists():
            print(f"Error: CSV file not found: {args.csv_file}", file=sys.stderr)
            sys.exit(1)

        try:
            build_program(
                csv_path=args.csv_file,
                output_dir=args.output,
                title=args.title,
                subtitle=args.subtitle,
                submissions_path=args.submissions,
            )
            print(f"Program built successfully in {args.output}/")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
