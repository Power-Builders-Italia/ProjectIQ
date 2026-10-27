"""Generate the German, French and Italian resx files of the PCF controls.

Reads tools/pcf/strings.txt (Control|Key|de|fr|it), writes
src/pcf/<Control>/strings/<Control>.{1031,1036,1040}.resx with the same keys and order as the
English 1033 file and adds the matching <resx> entries to each manifest.
Fails if a key of the English file has no translation. Run after changing any 1033 resx;
pass control names to limit it to those controls.
"""
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
PCF = ROOT / 'src' / 'pcf'
LCIDS = {'1031': 1, '1036': 2, '1040': 3}  # column in strings.txt

table = {}
for line in (Path(__file__).parent / 'strings.txt').read_text(encoding='utf-8').splitlines():
    if line.strip() and not line.startswith('#'):
        parts = line.split('|')
        table[(parts[0], parts[1])] = parts[2:5]

missing = []
for manifest in sorted(PCF.glob('*/ControlManifest.Input.xml')):
    control = manifest.parent.name
    if sys.argv[1:] and control not in sys.argv[1:]:
        continue
    english = (manifest.parent / 'strings' / f'{control}.1033.resx').read_text(encoding='utf-8')
    header = english[:english.index('<data ')]
    keys = re.findall(r'<data name="([^"]+)"', english)
    for lcid, col in LCIDS.items():
        body = []
        for key in keys:
            row = table.get((control, key))
            if not row:
                missing.append(f'{control}|{key}')
                continue
            body.append(f'  <data name="{key}" xml:space="preserve">\n    <value>{escape(row[col - 1])}</value>\n  </data>\n')
        (manifest.parent / 'strings' / f'{control}.{lcid}.resx').write_text(header + ''.join(body) + '</root>\n', encoding='utf-8')

    xml = manifest.read_text(encoding='utf-8')
    base = f'      <resx path="strings/{control}.1033.resx" version="1.0.0" />\n'
    extra = ''.join(f'      <resx path="strings/{control}.{lcid}.resx" version="1.0.0" />\n'
                    for lcid in LCIDS if f'{control}.{lcid}.resx' not in xml)
    if extra:
        manifest.write_text(xml.replace(base, base + extra), encoding='utf-8')

if missing:
    sys.exit('Missing translations:\n' + '\n'.join(sorted(set(missing))))
print('resx files generated')
