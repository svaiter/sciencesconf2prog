"""Command-line interface for sciencesconf2prog."""

import argparse
import sys
from pathlib import Path

from sciencesconf2prog import __version__
from sciencesconf2prog.builder import build_program, load_and_process


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
    build_parser.add_argument(
        "--plenaries",
        type=Path,
        default=None,
        help="Path to plenaries.json file (default: plenaries.json next to CSV)",
    )

    # PDF command
    pdf_parser = subparsers.add_parser(
        "pdf", help="Generate a single-page PDF overview of the program"
    )
    pdf_parser.add_argument(
        "csv_file",
        type=Path,
        nargs="?",
        default=Path("planning.csv"),
        help="Path to the CSV file (default: planning.csv)",
    )
    pdf_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("dist/programme.pdf"),
        help="Output PDF file path (default: dist/programme.pdf)",
    )
    pdf_parser.add_argument(
        "--title",
        type=str,
        default="Programme",
        help="Title of the program (default: Programme)",
    )
    pdf_parser.add_argument(
        "--subtitle",
        type=str,
        default="",
        help="Subtitle of the program",
    )
    pdf_parser.add_argument(
        "--page-size",
        type=str,
        default="A3",
        choices=["A3", "A4"],
        help="Page size (default: A3)",
    )
    pdf_parser.add_argument(
        "--submissions",
        type=Path,
        default=None,
        help="Path to submissions.json file (default: submissions.json next to CSV)",
    )
    pdf_parser.add_argument(
        "--plenaries",
        type=Path,
        default=None,
        help="Path to plenaries.json file (default: plenaries.json next to CSV)",
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
                plenaries_path=args.plenaries,
            )
            print(f"Program built successfully in {args.output}/")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


    elif args.command == "pdf":
        if not args.csv_file.exists():
            print(f"Error: CSV file not found: {args.csv_file}", file=sys.stderr)
            sys.exit(1)

        try:
            from sciencesconf2prog.pdf_renderer import render_pdf
        except ImportError:
            print(
                "Error: fpdf2 is required for PDF generation. "
                "Install it with: pip install sciencesconf2prog[pdf]",
                file=sys.stderr,
            )
            sys.exit(1)

        try:
            data = load_and_process(
                csv_path=args.csv_file,
                submissions_path=args.submissions,
                plenaries_path=args.plenaries,
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            render_pdf(
                data=data,
                output_path=args.output,
                title=args.title,
                subtitle=args.subtitle,
                page_size=args.page_size,
            )
            print(f"PDF generated: {args.output}")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
