"""Tests for compare_solution.py: python3 -m unittest discover -s tools/alm -v"""
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from compare_solution import Diff, _compare, check_webresources, compare_trees, format_summary, main

ENTITY = "OpenProject365/src/Entities/{}/Entity.xml"
LABEL = '            <displayname description="X" languagecode="1040" />\n'


class CompareTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.base, self.cur, self.main = root / "base", root / "cur", root / "main"
        for tree in (self.base, self.cur, self.main):
            tree.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def put(self, tree, rel, data):
        path = tree / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)

    def both(self, rel, base, cur):
        self.put(self.base, rel, base)
        self.put(self.cur, rel, cur)

    def test_identical_trees_no_drift(self):
        self.both("OpenProject365/src/Other/Customizations.xml", "<a/>\n", "<a/>\n")
        diff = compare_trees(self.base, self.cur)
        self.assertEqual(diff, Diff([], [], []))
        self.assertFalse(diff.drift)

    def test_crlf_and_bom_ignored(self):
        self.both("OpenProject365/src/Other/Customizations.xml", "a\n", "﻿a\r\n")
        self.assertFalse(compare_trees(self.base, self.cur).drift)

    def test_solution_version_ignored(self):
        rel = "OpenProject365/src/Other/Solution.xml"
        self.both(rel, "<x>\n    <Version>1.0.1.0</Version>\n</x>\n", "<x>\n    <Version>1.0.57.0</Version>\n</x>\n")
        self.assertFalse(compare_trees(self.base, self.cur).drift)

    def test_italian_label_on_standard_entity_ignored(self):
        rel = ENTITY.format("Account")
        self.both(rel, "<e>\n</e>\n", "<e>\n" + LABEL + "</e>\n")
        self.assertFalse(compare_trees(self.base, self.cur).drift)

    def test_italian_label_on_op365_entity_is_drift(self):
        rel = ENTITY.format("op365_Project")
        self.both(rel, "<e>\n</e>\n", "<e>\n" + LABEL + "</e>\n")
        self.assertEqual(compare_trees(self.base, self.cur).changed, [rel])

    def test_built_files_compared_by_presence(self):
        dll = "OpenProject365/src/PluginAssemblies/OpenProject365Plugins-X/OpenProject365Plugins.dll"
        bundle = "OpenProject365/src/Controls/op365_OP365.GanttChart/bundle.js"
        self.both(dll, b"MZ\x00\x01", b"MZ\x00\x02")
        self.both(bundle, "var a=1;", "var a=2;")
        self.assertFalse(compare_trees(self.base, self.cur).drift)
        (self.cur / dll).unlink()
        self.assertEqual(compare_trees(self.base, self.cur).removed, [dll])

    def test_binary_file_compared_as_bytes(self):
        rel = "OpenProject365/src/WebResources/op365_/icon.png"
        self.both(rel, b"\x89PNG\xff", b"\x89PNG\xfe")
        self.assertEqual(compare_trees(self.base, self.cur).changed, [rel])

    def test_added_and_removed_files(self):
        self.put(self.cur, "OpenProject365/src/new.xml", "<n/>")
        self.put(self.base, "OpenProject365/src/old.xml", "<o/>")
        diff = compare_trees(self.base, self.cur)
        self.assertEqual(diff.added, ["OpenProject365/src/new.xml"])
        self.assertEqual(diff.removed, ["OpenProject365/src/old.xml"])

    def test_files_outside_src_ignored(self):
        self.put(self.base, "OpenProject365/OpenProject365.cdsproj", "<Project/>")
        self.assertFalse(compare_trees(self.base, self.cur).drift)

    def test_platform_version_attributes_ignored(self):
        root = '<ImportExportXml version="{0}" SolutionPackageVersion="9.2" languagecode="1033" generatedBy="CrmLive" OrganizationVersion="{0}" OrganizationSchemaType="Standard" CRMServerServiceabilityVersion="{0}" xmlns:xsi="x">\n'
        for rel in ("OpenProject365/src/Other/Solution.xml", "OpenProject365/src/Other/Customizations.xml"):
            self.both(rel, root.format("9.2.26102.120") + "</ImportExportXml>\n", root.format("9.2.26103.137") + "</ImportExportXml>\n")
        self.assertFalse(compare_trees(self.base, self.cur).drift)

    def test_non_cp1252_text_on_cp1252_stdout(self):
        rel = "OpenProject365/src/Entities/SystemUser/RibbonDiff.xml"
        self.both(rel, "<a/>\n", "<a>مرحبا</a>\n")
        raw = io.BytesIO()
        summary = self.base.parent / "summary.md"
        with redirect_stdout(io.TextIOWrapper(raw, encoding="cp1252")):
            self.assertEqual(main([str(self.base), str(self.cur), "--summary", str(summary)]), 1)
        self.assertIn("مرحبا", summary.read_text(encoding="utf-8"))

    def test_files_list_written(self):
        self.both("OpenProject365/src/a.xml", "<a/>", "<b/>")
        self.put(self.cur, "OpenProject365/src/new.xml", "<n/>")
        self.put(self.base, "OpenProject365/src/old.xml", "<o/>")
        listing = self.base.parent / "files.txt"
        with redirect_stdout(io.StringIO()):
            main([str(self.base), str(self.cur), "--files", str(listing)])
        self.assertNotIn(b"\r", listing.read_bytes())  # read by bash on Linux after a Windows run
        self.assertEqual(listing.read_text(encoding="utf-8").splitlines(),
                         ["A OpenProject365/src/new.xml", "D OpenProject365/src/old.xml", "M OpenProject365/src/a.xml"])

    def test_check_webresources(self):
        src = self.base.parent / "webresources"
        self.put(src.parent, "webresources/project.form.js", "var a=1;\n")
        self.put(self.base, "OpenProject365/src/WebResources/op365_/scripts/project.form.js", "var a=1;\r\n")
        self.put(src.parent, "webresources/.gitkeep", "")
        self.assertEqual(check_webresources(src, self.base / "OpenProject365/src/WebResources"), [])
        self.put(self.base, "OpenProject365/src/WebResources/op365_/scripts/project.form.js", "var a=2;\n")
        self.assertEqual(check_webresources(src, self.base / "OpenProject365/src/WebResources"), ["project.form.js"])
        self.put(src.parent, "webresources/missing.js", "x")
        self.assertIn("missing.js", check_webresources(src, self.base / "OpenProject365/src/WebResources"))

    def three(self, rel, base, cur, main):
        for tree, data in ((self.base, base), (self.cur, cur), (self.main, main)):
            if data is not None:
                self.put(tree, rel, data)

    def test_three_way_change_already_in_main_is_not_drift(self):
        self.three("OpenProject365/src/a.xml", "<a>1</a>", "<a>2</a>", "<a>2</a>")
        self.assertFalse(compare_trees(self.base, self.cur, self.main).drift)

    def test_three_way_dev_behind_main_is_not_drift(self):
        self.three("OpenProject365/src/a.xml", "<a>1</a>", "<a>1</a>", "<a>2</a>")
        self.three("OpenProject365/src/new.xml", None, None, "<n/>")
        self.assertFalse(compare_trees(self.base, self.cur, self.main).drift)

    def test_three_way_unknown_change_is_drift_against_main(self):
        rel = "OpenProject365/src/a.xml"
        self.three(rel, "<a>1</a>", "<a>3</a>", "<a>2</a>")
        diff, texts = _compare(self.base, self.cur, self.main)
        self.assertEqual(diff, Diff([], [], [rel]))
        self.assertIn("-<a>2</a>", texts[rel])  # the diff is against main

    def test_three_way_added_and_deleted_in_dev(self):
        self.three("OpenProject365/src/dev_only.xml", None, "<d/>", None)
        self.three("OpenProject365/src/deleted_in_dev.xml", "<x/>", None, "<x/>")
        diff = compare_trees(self.base, self.cur, self.main)
        self.assertEqual(diff.added, ["OpenProject365/src/dev_only.xml"])
        self.assertEqual(diff.removed, ["OpenProject365/src/deleted_in_dev.xml"])

    def test_cli_main_option(self):
        self.three("OpenProject365/src/a.xml", "<a>1</a>", "<a>2</a>", "<a>2</a>")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main([str(self.base), str(self.cur), "--main", str(self.main)]), 0)
            self.assertEqual(main([str(self.base), str(self.cur)]), 1)
            self.assertEqual(main([str(self.base), str(self.cur), "--main", str(self.main / "missing")]), 2)

    def test_cli_exit_codes(self):
        rel = "OpenProject365/src/Other/Customizations.xml"
        self.both(rel, "<a/>\n", "<a/>\n")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main([str(self.base), str(self.cur)]), 0)
            self.put(self.cur, rel, "<b/>\n")
            self.assertEqual(main([str(self.base), str(self.cur)]), 1)
            self.assertEqual(main([str(self.base), str(self.cur / "missing")]), 2)

    def test_summary_lists_files_and_caps_diff(self):
        rel = "OpenProject365/src/Other/Customizations.xml"
        diff = Diff(added=["a.xml"], removed=["b.xml"], changed=[rel])
        long_diff = "\n".join(f"+line {i}" for i in range(100))
        text = format_summary(diff, {rel: long_diff}, max_lines=5)
        for path in ("a.xml", "b.xml", rel):
            self.assertIn(path, text)
        self.assertIn("+line 4", text)
        self.assertNotIn("+line 5", text)


if __name__ == "__main__":
    unittest.main()
