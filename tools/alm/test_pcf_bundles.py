"""Tests for pcf_bundles.py: python3 -m unittest discover -s tools/alm -v"""
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from pcf_bundles import main, mismatches

BUILT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<manifest>\n'
         '  <control namespace="OP365" constructor="Cost" version="{0}">\n'
         '    <resources><code path="bundle.js" order="1"/></resources>\n'
         '    <built-by name="pac" version="1.51.1"/>\n  </control>\n</manifest>')
SOLUTION = ('<manifest><control constructor="Cost" namespace="OP365" version="{0}">'
            '<resources><code path="bundle.js" order="1" /></resources>'
            '<built-by name="pac" version="1.40.0" /></control></manifest>')


class PcfBundlesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.out, self.controls = root / "out", root / "Controls"
        self.put(self.out / "Cost/ControlManifest.xml", BUILT.format("1.0.2"))
        self.put(self.out / "Cost/bundle.js", "new")
        self.put(self.out / "Cost/strings/Cost.1033.resx", "<root>a</root>\n")
        self.put(self.controls / "op365_OP365.Cost/ControlManifest.xml", SOLUTION.format("1.0.2"))
        self.put(self.controls / "op365_OP365.Cost/bundle.js", "old")
        self.put(self.controls / "op365_OP365.Cost/strings/Cost.1033.resx", "﻿<root>a</root>\r\n")

    def tearDown(self):
        self._tmp.cleanup()

    def put(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run_main(self, *extra):
        with redirect_stdout(io.StringIO()):
            return main([*extra, str(self.out), str(self.controls)])

    def test_matching_control_gets_the_new_bundle(self):
        self.assertEqual(mismatches(self.out, self.controls), [])
        self.assertEqual(self.run_main(), 0)
        self.assertEqual((self.controls / "op365_OP365.Cost/bundle.js").read_text(), "new")

    def test_check_copies_nothing(self):
        self.assertEqual(self.run_main("--check"), 0)
        self.assertEqual((self.controls / "op365_OP365.Cost/bundle.js").read_text(), "old")

    def test_changed_manifest_stops(self):
        self.put(self.out / "Cost/ControlManifest.xml", BUILT.format("1.0.3"))
        self.assertEqual(mismatches(self.out, self.controls), ["Cost: ControlManifest.xml differs"])
        self.assertEqual(self.run_main(), 1)
        self.assertEqual((self.controls / "op365_OP365.Cost/bundle.js").read_text(), "old")

    def test_changed_or_new_strings_stop(self):
        self.put(self.out / "Cost/strings/Cost.1033.resx", "<root>b</root>\n")
        self.put(self.out / "Cost/strings/Cost.1040.resx", "<root>c</root>\n")
        self.assertEqual(mismatches(self.out, self.controls),
                         ["Cost: strings/Cost.1033.resx differs", "Cost: strings/Cost.1040.resx differs"])

    def test_control_missing_from_solution_stops(self):
        self.put(self.out / "New/ControlManifest.xml", BUILT.format("1.0.0"))
        self.assertEqual(mismatches(self.out, self.controls), ["New: not in the solution"])

    def test_missing_folder_is_usage_error(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main([str(self.out / "missing"), str(self.controls)]), 2)


if __name__ == "__main__":
    unittest.main()
