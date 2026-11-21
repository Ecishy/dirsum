"""Command-line interface for dirsum."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .core import NO_EXT, FileStat, by_extension, collect, format_bytes, per_directory, top_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dirsum",
        description="Summarize a directory tree: size by extension, largest files, per-folder rollup.",
    )
    parser.add_argument("path", nargs="?", default=".", help="directory to analyze (default: current directory)")
    parser.add_argument(
        "-e", "--exclude", action="append", metavar="PATTERN",
        help="skip files matching an fnmatch pattern such as '*.tmp' or 'build/*' (repeatable)",
    )
    parser.add_argument(
        "-t", "--top", type=int, default=10, metavar="N",
        help="how many largest files to list (default: 10, 0 disables)",
    )
    parser.add_argument(
        "--dirs", action="store_true",
        help="also show a first-level folder breakdown",
    )
    parser.add_argument(
        "-j", "--json", action="store_true",
        help="print machine-readable JSON instead of the report",
    )
    parser.add_argument(
        "--follow-symlinks", action="store_true",
        help="also descend into symlinked directories (file symlinks are always ignored)",
    )
    parser.add_argument("-V", "--version", action="version", version=f"dirsum {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.path).absolute()

    try:
        files, directories = collect(
            args.path, exclude=tuple(args.exclude or ()), follow_symlinks=args.follow_symlinks,
        )
    except NotADirectoryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(_to_json(root, files, directories, args.top), indent=2))
        return 0

    print_report(root, files, directories, args.top, args.dirs)
    return 0


def print_report(
    root: Path, files: list[FileStat], directories: int, top: int, show_dirs: bool,
) -> None:
    total_bytes = sum(f.size for f in files)
    print(f"Scanned {root}")
    print(f"{len(files):,} files, {directories:,} folders, {format_bytes(total_bytes)} total\n")

    extensions = by_extension(files)
    print("By extension:")
    for ext, (count, size) in sorted(extensions.items(), key=lambda kv: kv[1][1], reverse=True):
        name = f".{ext}" if ext != NO_EXT else ext
        print(f"  {format_bytes(size):>12}  {count:>6,}  {name}")
    print()

    if top > 0 and files:
        print(f"Largest {min(top, len(files))} file(s):")
        for stat in top_files(files, top):
            rel = _display(stat.path, root)
            print(f"  {format_bytes(stat.size):>12}  {rel}")
        print()

    if show_dirs:
        print("First-level folders:")
        for name, (count, size) in per_directory(files, root).items():
            print(f"  {format_bytes(size):>12}  {count:>6,}  {name}")


def _display(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _to_json(root: Path, files: list[FileStat], directories: int, top: int) -> dict:
    return {
        "root": str(root),
        "total_files": len(files),
        "total_dirs": directories,
        "total_bytes": sum(f.size for f in files),
        "by_extension": {
            ext: {"count": count, "bytes": size}
            for ext, (count, size) in by_extension(files).items()
        },
        "largest": [
            {"path": str(f.path), "bytes": f.size}
            for f in top_files(files, top)
        ],
    }


def run() -> int:
    try:
        return main()
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(run())
