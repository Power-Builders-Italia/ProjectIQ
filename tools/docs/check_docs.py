"""Checks that the user manuals stay complete and their links work.

- every manual in docs/en exists in each language folder (docs/it, docs/fr, docs/de) and vice versa;
- every relative link in README.md and docs/**/*.md points to an existing file, and its #anchor to a heading
  (GitHub heading ids: lower case, punctuation removed, spaces to hyphens);
- README.md links every manual in every language.

Run from the repository root: python3 tools/docs/check_docs.py (exit code 1 on errors). The build workflow runs it.
"""
import os
import re
import sys
from urllib.parse import unquote

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
LANGUAGES = ['en', 'it', 'fr', 'de']
LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+)\)')
HEADING = re.compile(r'^(#{1,6})\s+(.*?)\s*#*\s*$')
FENCE = re.compile(r'^\s*(```|~~~)')


def slug(text):
    text = re.sub(r'`([^`]*)`', r'\1', text)            # inline code keeps its text
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)  # links keep their text
    text = text.strip().lower()
    text = re.sub(r'[^\w\- ]', '', text)                 # unicode letters and digits stay
    return text.replace(' ', '-')


def anchors(path):
    found, counts, fenced = set(), {}, False
    with open(path, encoding='utf-8') as f:
        for line in f:
            if FENCE.match(line):
                fenced = not fenced
                continue
            m = None if fenced else HEADING.match(line)
            if m:
                base = slug(m.group(2))
                n = counts.get(base, 0)
                counts[base] = n + 1
                found.add(base if n == 0 else f'{base}-{n}')
    return found


def links(path):
    fenced = False
    with open(path, encoding='utf-8') as f:
        for number, line in enumerate(f, 1):
            if FENCE.match(line):
                fenced = not fenced
                continue
            if not fenced:
                for target in LINK.findall(line):
                    yield number, target


def main():
    errors = []
    docs = os.path.join(ROOT, 'docs')
    manuals = {lang: sorted(f for f in os.listdir(os.path.join(docs, lang)) if f.endswith('.md'))
               for lang in LANGUAGES if os.path.isdir(os.path.join(docs, lang))}
    reference = manuals.get('en', [])
    if not reference:
        errors.append('docs/en has no manuals')
    for lang in LANGUAGES:
        have = set(manuals.get(lang, []))
        for name in sorted(set(reference) - have):
            errors.append(f'docs/{lang}/{name}: missing (exists in docs/en)')
        for name in sorted(have - set(reference)):
            errors.append(f'docs/{lang}/{name}: not in docs/en')

    files = [os.path.join(ROOT, 'README.md')]
    for base, _, names in os.walk(docs):
        files += [os.path.join(base, n) for n in names if n.endswith('.md')]
    cache = {}
    for path in sorted(files):
        rel = os.path.relpath(path, ROOT)
        for number, target in links(path):
            if re.match(r'^[a-z][a-z0-9+.-]*:', target, re.I):   # http:, https:, mailto:
                continue
            file_part, _, anchor = target.partition('#')
            dest = path if not file_part else os.path.normpath(os.path.join(os.path.dirname(path), unquote(file_part)))
            if not os.path.exists(dest):
                errors.append(f'{rel}:{number}: broken link {target}')
                continue
            if anchor and dest.endswith('.md'):
                if dest not in cache:
                    cache[dest] = anchors(dest)
                if unquote(anchor) not in cache[dest]:
                    errors.append(f'{rel}:{number}: no heading for #{anchor} in {os.path.relpath(dest, ROOT)}')

    with open(os.path.join(ROOT, 'README.md'), encoding='utf-8') as f:
        readme = f.read()
    for lang in LANGUAGES:
        for name in reference:
            if f'docs/{lang}/{name}' not in readme:
                errors.append(f'README.md: no link to docs/{lang}/{name}')

    for e in errors:
        print(e)
    print(f'{len(files)} files checked, {len(errors)} errors')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
