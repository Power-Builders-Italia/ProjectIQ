"""Compares two unpacked solution trees (the solutions/ folder) for the deploy-dev drift check (ADR 0002).

Usage:  python tools/alm/compare_solution.py BASELINE CURRENT [--main MAIN] [--summary FILE] [--files FILE]
        python tools/alm/compare_solution.py --check-webresources SRC_DIR WEBRESOURCES_DIR
Exit:   0 same, 1 drift, 2 usage error. With --summary the Markdown report is appended to FILE; with --files
        one line per difference is written to FILE: "A path" (only in CURRENT), "D path" (missing in CURRENT), "M path".
        With --main only the files of CURRENT that differ from both BASELINE and MAIN count (changes MAIN does not
        know about), and A/D/M and the diffs are against MAIN.
        --check-webresources exits 1 when a file of SRC_DIR differs from (or is missing in) the solution copy.

Before comparing, each file is normalized: UTF-8 BOM, CRLF and trailing whitespace dropped; the solution
<Version> and the platform version attributes of the root element ignored; Italian (1040) labels of standard components ignored (the Dev language pack adds them);
built files (plugin assembly, PCF bundles) compared by presence only, since deploy-dev builds them from source.
"""
import argparse
import difflib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

VERSION = re.compile(rb"^\s*<Version>[^<]*</Version>\n?", re.M)
# set by Dataverse at export time, they change with every service update
PLATFORM = re.compile(rb'\s(?:version|OrganizationVersion|CRMServerServiceabilityVersion)="[^"]*"')
ROOT = re.compile(rb"<ImportExportXml\b[^>]*>")
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
    if rel_path.endswith(("/src/Other/Solution.xml", "/src/Other/Customizations.xml")):
        data = ROOT.sub(lambda m: PLATFORM.sub(b"", m.group(0)), data, count=1)
    if STANDARD_ENTITY.match(rel_path):
        data = b"\n".join(line for line in data.split(b"\n") if b'languagecode="1040"' not in line)
    return data


IN_SRC = re.compile(r"^[^/]+/src/")


def _files(root: Path) -> dict:
    # only <Solution>/src is exported; project files beside it (e.g. the .cdsproj) are not
    files = ((p.relative_to(root).as_posix(), p) for p in root.rglob("*") if p.is_file())
    return {rel: p for rel, p in files if IN_SRC.match(rel)}


def _read(files: dict, rel: str):
    return normalize(rel, files[rel].read_bytes()) if rel in files else None


def _compare(baseline: Path, current: Path, main: Path = None):
    """Two-way: every difference between baseline and current. Three-way (main given): only the files where
    current differs from both baseline and main, i.e. changes main does not know about; reported against main."""
    base, cur = _files(baseline), _files(current)
    ref = _files(main) if main is not None else base
    diff, texts = Diff(), {}
    for rel in sorted(base.keys() | cur.keys() | ref.keys()):
        c, r = _read(cur, rel), _read(ref, rel)
        if c == r or (main is not None and c == _read(base, rel)):
            continue
        if r is None:
            diff.added.append(rel)
        elif c is None:
            diff.removed.append(rel)
        else:
            diff.changed.append(rel)
            if _is_text(r) and _is_text(c):
                texts[rel] = "\n".join(difflib.unified_diff(
                    r.decode("utf-8").split("\n"), c.decode("utf-8").split("\n"), "repository", "Dev", lineterm=""))
    return diff, texts


def compare_trees(baseline: Path, current: Path, main: Path = None) -> Diff:
    return _compare(Path(baseline), Path(current), Path(main) if main is not None else None)[0]


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


def check_webresources(src_dir: Path, webresources_dir: Path) -> list:
    """Names of the files of src_dir whose copy under webresources_dir differs or is missing (deploy-dev overlays them)."""
    copies = {p.name: p for p in Path(webresources_dir).rglob("*") if p.is_file() and p.suffix != ".xml"}
    bad = []
    for src in sorted(p for p in Path(src_dir).iterdir() if p.is_file() and not p.name.startswith(".")):
        copy = copies.get(src.name)
        if copy is None or normalize("", src.read_bytes()) != normalize("", copy.read_bytes()):
            bad.append(src.name)
    return bad


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("baseline", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument("--main", type=Path, help="three-way: ignore the changes of CURRENT that MAIN already has")
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--files", type=Path)
    parser.add_argument("--check-webresources", action="store_true")
    args = parser.parse_args(argv)
    for path in (args.baseline, args.current, *([args.main] if args.main else [])):
        if not path.is_dir():
            print(f"Not a directory: {path}", file=sys.stderr)
            return 2
    if args.check_webresources:
        bad = check_webresources(args.baseline, args.current)
        for name in bad:
            print(f"{name}: differs from its copy in {args.current} (or the copy is missing)")
        return 1 if bad else 0
    diff, texts = _compare(args.baseline, args.current, args.main)
    report = format_summary(diff, texts)
    # files first: printing can fail on a console that cannot encode the text (cp1252 on Windows)
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as f:
            f.write(report)
    if args.files:
        lines = [f"A {p}" for p in diff.added] + [f"D {p}" for p in diff.removed] + [f"M {p}" for p in diff.changed]
        # LF on every platform: the list is written on Windows and read by bash on Linux (drift-pr)
        with args.files.open("w", encoding="utf-8", newline="\n") as f:
            f.writelines(line + "\n" for line in lines)
    sys.stdout.write(report.encode(sys.stdout.encoding or "utf-8", "replace").decode(sys.stdout.encoding or "utf-8"))
    return 1 if diff.drift else 0


if __name__ == "__main__":
    sys.exit(main())
