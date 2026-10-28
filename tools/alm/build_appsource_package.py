"""Builds the AppSource package of ProjectIQ from the managed solutions (docs/appsource.md).

Usage:  python tools/alm/build_appsource_package.py SOLUTIONS_DIR --version X.Y.Z.W [--out DIR]
                                                    [--start-date MM/DD/YYYY] [--countries CC,CC,...]
        SOLUTIONS_DIR holds OpenProject365_managed.zip and OpenProject365SupplierPortal_managed.zip.
Exit:   0 ok, 1 invalid input or package.

Steps: checks that both solutions are managed and have the requested version; builds the Package Deployer package
(appsource/ProjectIQ.Package, dotnet publish) and renames it package.zip; adds the files of appsource/assets
([Content_Types].xml, input.xml with start date and countries filled in, logo32.png, TermsOfUse.html) and zips them
flat (no folder) into DIR/PowerBuildersItalia_ProjectIQ_<version>.zip, the file to upload to Azure Blob Storage.
"""
import argparse
import datetime
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "appsource" / "ProjectIQ.Package"
ASSETS = ROOT / "appsource" / "assets"
SOLUTIONS = ("OpenProject365_managed.zip", "OpenProject365SupplierPortal_managed.zip")
ASSET_FILES = ("[Content_Types].xml", "logo32.png", "TermsOfUse.html")
REQUIRED = ("package.zip", "input.xml") + ASSET_FILES
PACKAGE_REQUIRED = ("[Content_Types].xml", "ProjectIQ.Package.dll", "PkgAssets/ImportConfig.xml") + tuple(
    f"PkgAssets/{name}" for name in SOLUTIONS)
VERSION = re.compile(r"^\d+\.\d+\.\d+\.\d+$")
# Countries and regions accepted by AppSource for apps on Dataverse (input.xml SupportedCountries)
ALL_COUNTRIES = (
    "AD,AE,AF,AG,AI,AL,AM,AO,AQ,AR,AS,AT,AU,AW,AX,AZ,BA,BB,BD,BE,BF,BG,BH,BI,BJ,BL,BM,BN,BO,BR,BS,BT,BV,BW,BY,BZ,"
    "CA,CC,CD,CF,CG,CH,CI,CK,CL,CM,CN,CO,CR,CV,CW,CX,CY,CZ,DE,DJ,DK,DM,DO,DZ,EC,EE,EG,ER,ES,ET,FI,FJ,FK,FM,FO,FR,"
    "GA,GB,GD,GE,GF,GG,GH,GI,GL,GM,GN,GP,GQ,GR,GS,GT,GU,GW,GY,HK,HM,HN,HR,HT,HU,ID,IE,IL,IM,IN,IO,IQ,IS,IT,JE,JM,"
    "JO,JP,KE,KG,KH,KI,KM,KN,KR,KW,KY,KZ,LA,LB,LC,LI,LK,LR,LS,LT,LU,LV,LY,MA,MC,MD,ME,MF,MG,MH,MK,ML,MM,MN,MO,MP,"
    "MQ,MR,MS,MT,MU,MV,MW,MX,MY,MZ,NA,NC,NE,NF,NG,NI,NL,NO,NP,NR,NU,NZ,OM,PA,PE,PF,PG,PH,PK,PL,PM,PN,PR,PS,PT,PW,"
    "PY,QA,RE,RO,RS,RU,RW,SA,SB,SC,SE,SG,SH,SI,SJ,SK,SL,SM,SN,SO,SR,ST,SV,SZ,TC,TD,TF,TG,TH,TJ,TK,TL,TM,TN,TO,TR,"
    "TT,TV,TW,TZ,UA,UG,UM,US,UY,UZ,VA,VC,VE,VG,VI,VN,VU,WF,WS,YE,YT,ZA,ZM,ZW")


class PackageError(Exception):
    pass


def solution_info(path: Path):
    """(managed, version) read from solution.xml of a solution zip."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("solution.xml").decode("utf-8-sig")
    managed = re.search(r"<Managed>(\d)</Managed>", xml)
    version = re.search(r"<Version>([^<]+)</Version>", xml)
    return (managed is not None and managed.group(1) == "1"), (version.group(1) if version else None)


def check_solutions(folder: Path, version: str):
    errors = []
    for name in SOLUTIONS:
        path = folder / name
        if not path.is_file():
            errors.append(f"{name}: missing in {folder}")
            continue
        managed, found = solution_info(path)
        if not managed:
            errors.append(f"{name}: not a managed solution")
        if found != version:
            errors.append(f"{name}: version {found}, expected {version}")
    if errors:
        raise PackageError("\n".join(errors))


def input_xml(start_date: str, countries: str) -> str:
    if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", start_date):
        raise PackageError(f"start date {start_date}: use MM/DD/YYYY")
    if not re.fullmatch(r"[A-Z]{2}(,[A-Z]{2})*", countries):
        raise PackageError("countries: comma-separated two-letter codes, no spaces")
    text = (ASSETS / "input.xml").read_text(encoding="utf-8")
    return text.replace("{START_DATE}", start_date).replace("{COUNTRIES}", countries)


def build_pd_package(solutions: Path, version: str, work: Path) -> Path:
    """dotnet publish of appsource/ProjectIQ.Package -> path of the .pdpkg.zip."""
    out = work / "pd"
    subprocess.run(["dotnet", "publish", str(PROJECT), "-c", "Release", f"-p:SolutionsDir={solutions.resolve()}/",
                    f"-p:Version={version}", f"-p:BaseOutputPath={out}/", f"-p:BaseIntermediateOutputPath={work / 'obj'}/"],
                   check=True)
    found = sorted(out.rglob("*.pdpkg.zip"))
    if not found:
        raise PackageError("dotnet publish produced no .pdpkg.zip")
    return found[-1]


def assemble(pd_package: Path, xml: str, target: Path):
    """Writes the AppSource zip: package.zip, input.xml and the asset files at the root."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(pd_package, "package.zip")
        z.writestr("input.xml", xml)
        for name in ASSET_FILES:
            z.write(ASSETS / name, name)


def validate(target: Path):
    """Checks the layout that certification requires: flat AppSource zip, package.zip with assembly and solutions."""
    errors = []
    with zipfile.ZipFile(target) as z:
        names = z.namelist()
        errors += [f"{target.name}: {n} missing" for n in REQUIRED if n not in names]
        errors += [f"{target.name}: {n} is in a folder (the zip must be flat)" for n in names if "/" in n]
        if "package.zip" in names:
            with tempfile.TemporaryDirectory() as tmp:
                inner = Path(tmp) / "package.zip"
                inner.write_bytes(z.read("package.zip"))
                with zipfile.ZipFile(inner) as p:
                    have = p.namelist()
                    errors += [f"package.zip: {n} missing" for n in PACKAGE_REQUIRED if n not in have]
    if errors:
        raise PackageError("\n".join(errors))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("solutions", type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "out")
    parser.add_argument("--start-date", default=datetime.date.today().strftime("%m/%d/%Y"))
    parser.add_argument("--countries", default=ALL_COUNTRIES)
    args = parser.parse_args(argv)
    try:
        if not VERSION.match(args.version):
            raise PackageError(f"version {args.version}: use X.Y.Z.W")
        check_solutions(args.solutions, args.version)
        xml = input_xml(args.start_date, args.countries)
        target = args.out / f"PowerBuildersItalia_ProjectIQ_{args.version}.zip"
        with tempfile.TemporaryDirectory() as tmp:
            assemble(build_pd_package(args.solutions, args.version, Path(tmp)), xml, target)
        validate(target)
    except (PackageError, subprocess.CalledProcessError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
