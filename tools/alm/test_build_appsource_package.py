"""Tests for build_appsource_package.py: python3 -m unittest discover -s tools/alm -v"""
import tempfile
import unittest
import zipfile
from pathlib import Path

from build_appsource_package import (ALL_COUNTRIES, PACKAGE_REQUIRED, SOLUTIONS, PackageError, assemble,
                                     check_solutions, input_xml, validate)

SOLUTION_XML = "<ImportExportXml><SolutionManifest><Version>{}</Version><Managed>{}</Managed></SolutionManifest></ImportExportXml>"


class AppSourcePackageTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def zip(self, path, files):
        with zipfile.ZipFile(path, "w") as z:
            for name, data in files.items():
                z.writestr(name, data)
        return path

    def solutions(self, version="1.0.5.0", managed=1):
        for name in SOLUTIONS:
            self.zip(self.root / name, {"solution.xml": SOLUTION_XML.format(version, managed)})

    def pd_package(self, skip=None):
        return self.zip(self.root / "pd.pdpkg.zip", {n: "x" for n in PACKAGE_REQUIRED if n != skip})

    def test_managed_solutions_with_the_version_pass(self):
        self.solutions()
        check_solutions(self.root, "1.0.5.0")

    def test_unmanaged_or_other_version_fails(self):
        self.solutions(managed=0)
        with self.assertRaisesRegex(PackageError, "not a managed solution"):
            check_solutions(self.root, "1.0.5.0")
        self.solutions(version="1.0.4.0")
        with self.assertRaisesRegex(PackageError, "version 1.0.4.0, expected 1.0.5.0"):
            check_solutions(self.root, "1.0.5.0")

    def test_missing_solution_fails(self):
        with self.assertRaisesRegex(PackageError, "OpenProject365_managed.zip: missing"):
            check_solutions(self.root, "1.0.5.0")

    def test_input_xml_is_filled(self):
        xml = input_xml("11/01/2026", ALL_COUNTRIES)
        self.assertIn("<StartDate>11/01/2026</StartDate>", xml)
        self.assertIn(",IT,", xml)
        self.assertNotIn("{", xml)

    def test_input_xml_rejects_bad_values(self):
        with self.assertRaises(PackageError):
            input_xml("2026-11-01", "IT")
        with self.assertRaises(PackageError):
            input_xml("11/01/2026", "IT, FR")

    def test_assembled_package_is_flat_and_complete(self):
        target = self.root / "out" / "app.zip"
        assemble(self.pd_package(), input_xml("11/01/2026", "IT"), target)
        validate(target)
        with zipfile.ZipFile(target) as z:
            self.assertEqual(sorted(z.namelist()),
                             sorted(["package.zip", "input.xml", "[Content_Types].xml", "logo32.png", "TermsOfUse.html"]))

    def test_package_without_a_solution_is_rejected(self):
        target = self.root / "app.zip"
        assemble(self.pd_package(skip="PkgAssets/OpenProject365SupplierPortal_managed.zip"), input_xml("11/01/2026", "IT"), target)
        with self.assertRaisesRegex(PackageError, "OpenProject365SupplierPortal_managed.zip missing"):
            validate(target)


if __name__ == "__main__":
    unittest.main()
