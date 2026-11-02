"""Regenerates the screenshots of the documentation website home page (docs/assets/screenshots/*.png).

The images are the real PCF controls of src/pcf, rendered in a browser with a stub context and demo data (demo.tsx).
Run from the repository root after `npm ci` in src/pcf; needs Node.js and Playwright with Chromium:

    python3 tools/docs/screenshots/screenshots.py
"""
import glob
import json
import os
import subprocess
import xml.etree.ElementTree as ET

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
PCF = os.path.join(ROOT, 'src', 'pcf')
BUILD = os.path.join(HERE, 'build')
OUT = os.path.join(ROOT, 'docs', 'assets', 'screenshots')
CONTROLS = ['gantt', 'wbs', 'timesheet', 'load', 'cost', 'quotes']
WIDTH = 1600


def strings():
    """English strings of every control, from its .1033.resx file."""
    out = {}
    for f in glob.glob(os.path.join(PCF, '*', 'strings', '*.1033.resx')):
        control = os.path.basename(os.path.dirname(os.path.dirname(f)))
        out[control] = {d.get('name'): d.find('value').text or '' for d in ET.parse(f).getroot().findall('data')}
    return out


def main():
    os.makedirs(BUILD, exist_ok=True)
    with open(os.path.join(BUILD, 'strings.json'), 'w', encoding='utf-8') as f:
        json.dump(strings(), f)
    modules = os.path.join(PCF, 'node_modules')
    subprocess.run(['npx', '--yes', 'esbuild@0.24.0', os.path.join(HERE, 'demo.tsx'), '--bundle', '--log-level=warning',
                    '--outfile=' + os.path.join(BUILD, 'demo.js'), '--alias:PCF=' + PCF,
                    '--alias:react=' + os.path.join(modules, 'react'), '--alias:react-dom=' + os.path.join(modules, 'react-dom'),
                    '--alias:@fluentui/react-components=' + os.path.join(modules, '@fluentui', 'react-components'),
                    '--define:process.env.NODE_ENV="production"'], check=True)
    os.makedirs(OUT, exist_ok=True)
    subprocess.run(['node', os.path.join(HERE, 'shoot.js'), BUILD] + CONTROLS, check=True)
    for c in CONTROLS:
        im = Image.open(os.path.join(BUILD, c + '.raw.png')).convert('RGB')
        im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS).save(os.path.join(OUT, c + '.png'), optimize=True)
        print('saved', os.path.relpath(os.path.join(OUT, c + '.png'), ROOT))


if __name__ == '__main__':
    main()
