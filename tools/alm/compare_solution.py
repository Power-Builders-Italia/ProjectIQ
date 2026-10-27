"""Compares two unpacked solution trees (the solutions/ folder) for the deploy-dev drift check (ADR 0002).

Usage:  python tools/alm/compare_solution.py BASELINE CURRENT [--summary FILE]
Exit:   0 same, 1 drift, 2 usage error. With --summary the Markdown report is appended to FILE.

Before comparing, each file is normalized: UTF-8 BOM, CRLF and trailing whitespace dropped; the solution
<Version> ignored; Italian (1040) labels of standard components ignored (the Dev language pack adds them);
built files (plugin assembly, PCF bundles) compared by presence only, since deploy-dev builds them from source.
"""
import argparse
import difflib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

VERSION = re.compile(rb"^\s*<Version>[^<]*</Version>\n?", re.M)
STANDARD_ENTITY = re.compile(r"^[^/]+/src/Entities/(?!op365_)[^/]+/")
BUILT = (re.compile(r"^[^/]+/src/PluginAssemblies/.+\.dll$"), re.compile(r"^[^/]+/src/Controls/.+/bundle\.js$"))


@dataclass
class Diff:
    added: list = field(default_factory=list)
    removed: list = field(default_factory=list)
    changed: list = field(default_factory=list)

    @property
    def drift(self) -> bool:
        return bool(self.added or self.removed or self.changed)


def _is_text(data: bytes) -> bool:
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def normalize(rel_path: str, data: bytes) -> bytes:
    if any(p.match(rel_path) for p in BUILT):
        return b""
    if not _is_text(data):
        return data
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    data = b"\n".join(line.rstrip() for line in data.replace(b"\r\n", b"\n").split(b"\n"))
    if rel_path.endswith("/src/Other/Solution.xml"):
        data = VERSION.sub(b"", data)
    if STANDARD_ENTITY.match(rel_path):
        data = b"\n".join(line for line in data.split(b"\n") if b'languagecode="1040"' not in line)
    return data


def _files(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p for p in root.rglob("*") if p.is_file()}


def _compare(baseline: Path, current: Path):
    base, cur = _files(baseline), _files(current)
    diff, texts = Diff(), {}
    diff.added = sorted(cur.keys() - base.keys())
    diff.removed = sorted(base.keys() - cur.keys())
    for rel in sorted(base.keys() & cur.keys()):
        a, b = normalize(rel, base[rel].read_bytes()), normalize(rel, cur[rel].read_bytes())
        if a != b:
            diff.changed.append(rel)
            if _is_text(a) and _is_text(b):
                texts[rel] = "\n".join(difflib.unified_diff(
                    a.decode("utf-8").split("\n"), b.decode("utf-8").split("\n"), "repository", "Dev", lineterm=""))
    return diff, texts


def compare_trees(baseline: Path, current: Path) -> Diff:
    return _compare(Path(baseline), Path(current))[0]


def format_summary(diff: Diff, diffs: dict, max_lines: int = 40) -> str:
    if not diff.drift:
        return "### Solution comparison\n\nNo differences.\n"
    out = ["### Solution comparison", ""]
    for title, paths in (("Only in Dev", diff.added), ("Only in the repository", diff.removed), ("Changed", diff.changed)):
        if paths:
            out += [f"**{title}** ({len(paths)})", ""] + [f"- `{p}`" for p in paths] + [""]
    for rel in diff.changed:
        if rel in diffs:
            lines = diffs[rel].split("\n")
            out += [f"<details><summary><code>{rel}</code></summary>", "", "```diff"] + lines[:max_lines]
            if len(lines) > max_lines:
                out.append(f"... {len(lines) - max_lines} more lines")
            out += ["```", "", "</details>", ""]
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("baseline", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args(argv)
    for path in (args.baseline, args.current):
        if not path.is_dir():
            print(f"Not a directory: {path}", file=sys.stderr)
            return 2
    diff, texts = _compare(args.baseline, args.current)
    report = format_summary(diff, texts)
    print(report)
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as f:
            f.write(report)
    return 1 if diff.drift else 0


if __name__ == "__main__":
    sys.exit(main())
