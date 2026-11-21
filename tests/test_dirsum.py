"""Tests for dirsum's core aggregation and CLI."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from dirsum.cli import main
from dirsum.core import NO_EXT, by_extension, collect, format_bytes, per_directory, top_files


class CoreTestCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def touch(self, rel: str, content: bytes = b"x" * 10) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_collect_finds_nested_files(self) -> None:
        self.touch("a.txt")
        self.touch("sub/b.txt")
        files, dirs = collect(self.root)
        self.assertEqual(len(files), 2)
        self.assertEqual(dirs, 1)

    def test_by_extension_aggregates(self) -> None:
        self.touch("a.jpg", b"x" * 100)
        self.touch("b.jpg", b"x" * 50)
        self.touch("c.txt", b"x" * 10)
        self.touch("noext", b"x" * 5)
        stats = by_extension(collect(self.root)[0])
        self.assertEqual(stats["jpg"], (2, 150))
        self.assertEqual(stats["txt"], (1, 10))
        self.assertEqual(stats[NO_EXT], (1, 5))

    def test_top_files_order_and_limit(self) -> None:
        self.touch("small.txt", b"x" * 10)
        self.touch("big.zip", b"x" * 1000)
        self.touch("mid.jpg", b"x" * 100)
        files = collect(self.root)[0]
        biggest = top_files(files, 2)
        self.assertEqual([s.path.name for s in biggest], ["big.zip", "mid.jpg"])
        self.assertEqual(top_files(files, 0), [])

    def test_per_directory_rolls_up(self) -> None:
        self.touch("src/a.py", b"x" * 100)
        self.touch("src/b.py", b"x" * 50)
        self.touch("docs/c.md", b"x" * 10)
        self.touch("loose.txt", b"x" * 5)
        rollup = per_directory(collect(self.root)[0], self.root)
        self.assertEqual(list(rollup), ["src", "docs", "(root)"])
        self.assertEqual(rollup["src"], (2, 150))
        self.assertEqual(rollup["(root)"], (1, 5))

    def test_exclude_prunes_files_and_dirs(self) -> None:
        self.touch("a.txt")
        self.touch("build/out.txt")
        self.touch("node_modules/x.js")
        files, dirs = collect(self.root, exclude=("build/*", "node_modules"))
        self.assertEqual([f.path.name for f in files], ["a.txt"])
        # "build" itself still exists (its contents were pruned), node_modules is gone
        self.assertEqual(dirs, 1)

    def test_format_bytes(self) -> None:
        self.assertEqual(format_bytes(512), "512 B")
        self.assertEqual(format_bytes(2048), "2.0 KiB")
        self.assertEqual(format_bytes(5 * 1024 * 1024), "5.0 MiB")

    def test_missing_root_raises(self) -> None:
        with self.assertRaises(NotADirectoryError):
            collect(self.root / "nope")


class CliTestCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "src").mkdir()
        (self.root / "a.jpg").write_bytes(b"x" * 500)
        (self.root / "src" / "big.zip").write_bytes(b"x" * 5000)
        (self.root / "note.txt").write_bytes(b"x" * 20)

    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_report_shows_totals_and_tables(self) -> None:
        code, out, _ = self.run_cli(str(self.root))
        self.assertEqual(code, 0)
        self.assertIn("3 files, 1 folder", out)
        self.assertIn(".zip", out)
        self.assertIn("Largest 3 file(s)", out)
        self.assertIn("src/big.zip", out.replace("\\", "/"))

    def test_top_limits_listing(self) -> None:
        code, out, _ = self.run_cli("--top", "1", str(self.root))
        self.assertIn("Largest 1 file(s)", out)
        self.assertNotIn("note.txt", out)

    def test_dirs_breakdown(self) -> None:
        code, out, _ = self.run_cli("--dirs", str(self.root))
        self.assertIn("First-level folders:", out)
        self.assertIn("src", out)

    def test_dirs_hidden_by_default(self) -> None:
        code, out, _ = self.run_cli(str(self.root))
        self.assertNotIn("First-level folders:", out)

    def test_json_output(self) -> None:
        code, out, _ = self.run_cli("--json", str(self.root))
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["total_files"], 3)
        self.assertEqual(data["total_bytes"], 5520)
        self.assertIn("zip", data["by_extension"])
        self.assertEqual(data["largest"][0]["bytes"], 5000)

    def test_exclude_via_cli(self) -> None:
        code, out, _ = self.run_cli("--exclude", "*.jpg", str(self.root))
        self.assertEqual(code, 0)
        self.assertNotIn(".jpg", out)

    def test_missing_dir_exit_two(self) -> None:
        code, _, err = self.run_cli(str(self.root / "nope"))
        self.assertEqual(code, 2)
        self.assertIn("not a directory", err)


if __name__ == "__main__":
    unittest.main()
