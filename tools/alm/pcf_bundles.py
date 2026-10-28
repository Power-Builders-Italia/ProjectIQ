"""Puts the PCF bundles built from src/pcf into the unpacked solution, so that one import installs them.

    python3 tools/alm/pcf_bundles.py [--check] <pcf out/controls> <solution src/Controls>

Only bundle.js is copied: the comparison of deploy-dev checks its presence, not its bytes. The manifest and the
strings must already match the solution (they are compared by content, so a copy would show up as drift): a control
whose manifest or strings changed is pushed to Dev with tools/pcf/push.sh and exported into the repository as usual.
--check compares only, for the build workflow. Exit code 0 = done, 1 = a control does not match, 2 = usage error.
"""
import argparse
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

PREFIX = "op365_OP365."


def _manifest(path):
    root = ET.fromstring(path.read_bytes())
    for built_by in root.iter("built-by"):  # pac version of the machine that built it
        built_by.attrib.clear()
    return ET.canonicalize(ET.tostring(root), strip_text=True)


def _text(path):
    return path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n").rstrip()


def mismatches(out, controls):
    """Problems that stop the copy: a missing control, a different manifest or different strings."""
    problems = []
    for built in sorted(p for p in out.iterdir() if p.is_dir()):
        target = controls / (PREFIX + built.name)
        if not target.is_dir():
            problems.append(f"{built.name}: not in the solution")
            continue
        if _manifest(built / "ControlManifest.xml") != _manifest(target / "ControlManifest.xml"):
            problems.append(f"{built.name}: ControlManifest.xml differs")
        for resx in sorted((built / "strings").glob("*.resx")):
            copy = target / "strings" / resx.name
            if not copy.is_file() or _text(resx) != _text(copy):
                problems.append(f"{built.name}: strings/{resx.name} differs")
    return problems


def copy_bundles(out, controls):
    for built in sorted(p for p in out.iterdir() if p.is_dir()):
        shutil.copyfile(built / "bundle.js", controls / (PREFIX + built.name) / "bundle.js")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("controls", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if not args.out.is_dir() or not args.controls.is_dir():
        print("both folders must exist", file=sys.stderr)
        return 2
    problems = mismatches(args.out, args.controls)
    for problem in problems:
        print(problem)
    if problems:
        print("Push these controls to Dev with tools/pcf/push.sh and export the solution into the repository.")
        return 1
    if not args.check:
        copy_bundles(args.out, args.controls)
    return 0


if __name__ == "__main__":
    sys.exit(main())
