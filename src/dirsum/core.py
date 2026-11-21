"""Summarize what is inside a directory tree: sizes by extension, largest files."""

from __future__ import annotations

import os
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

#: Label used for files without any extension.
NO_EXT = "(none)"


@dataclass(frozen=True)
class FileStat:
    """One regular file discovered by the walk."""

    path: Path
    size: int


def collect(
    root: str | os.PathLike[str],
    *,
    exclude: tuple[str, ...] = (),
    follow_symlinks: bool = False,
) -> tuple[list[FileStat], int]:
    """Walk *root* and return ``(files, directory_count)``.

    ``exclude`` holds fnmatch patterns matched against file names and
    slash-separated relative paths (case-insensitive on Windows). File
    symlinks are always ignored; with ``follow_symlinks`` the walk also
    descends into symlinked directories.
    """
    root_path = Path(os.path.abspath(root))
    if not root_path.is_dir():
        raise NotADirectoryError(f"not a directory: {root_path}")

    files: list[FileStat] = []
    directories = 0
    for dirpath, dirnames, filenames in os.walk(root_path, followlinks=follow_symlinks):
        current = Path(dirpath)
        dirnames[:] = sorted(
            name
            for name in dirnames
            if not _is_excluded(current / name, root_path, exclude)
            and (follow_symlinks or not _is_link(current / name))
        )
        directories += len(dirnames)
        for name in sorted(filenames):
            path = current / name
            if _is_excluded(path, root_path, exclude) or _is_link(path):
                continue
            try:
                files.append(FileStat(path, path.stat().st_size))
            except OSError:
                continue  # vanished or unreadable; skip quietly
    return files, directories


def by_extension(files: list[FileStat]) -> dict[str, tuple[int, int]]:
    """Aggregate *files* per extension into ``{ext: (count, total_bytes)}``."""
    result: dict[str, tuple[int, int]] = {}
    for stat in files:
        ext = stat.path.suffix.lower().lstrip(".") or NO_EXT
        count, size = result.get(ext, (0, 0))
        result[ext] = (count + 1, size + stat.size)
    return result


def top_files(files: list[FileStat], count: int) -> list[FileStat]:
    """Return the *count* biggest files, biggest first."""
    if count <= 0:
        return []
    return sorted(files, key=lambda s: s.size, reverse=True)[:count]


def per_directory(files: list[FileStat], root: Path) -> dict[str, tuple[int, int]]:
    """Roll *files* up into first-level children of *root*.

    Returns ``{name: (count, total_bytes)}`` sorted by bytes descending;
    files sitting directly in the root are grouped under ``(root)``.
    """
    result: dict[str, tuple[int, int]] = {}
    for stat in files:
        try:
            rel = stat.path.relative_to(root)
        except ValueError:
            rel = stat.path
        name = rel.parts[0] if len(rel.parts) > 1 else "(root)"
        count, size = result.get(name, (0, 0))
        result[name] = (count + 1, size + stat.size)
    return dict(sorted(result.items(), key=lambda kv: kv[1][1], reverse=True))


def format_bytes(size: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:,.0f} {unit}" if unit == "B" else f"{size:,.1f} {unit}"
        size /= 1024
    return f"{size:,.1f} TiB"


def _is_link(path: Path) -> bool:
    if path.is_symlink():
        return True
    if os.name == "nt" and hasattr(path, "is_junction"):
        return path.is_junction()
    return False


def _is_excluded(path: Path, root: Path, patterns: tuple[str, ...]) -> bool:
    if not patterns:
        return False
    rel = path.relative_to(root).as_posix()
    return any(fnmatch(path.name, pat) or fnmatch(rel, pat) for pat in patterns)
