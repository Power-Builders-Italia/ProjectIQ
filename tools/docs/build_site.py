"""Stages the documentation website sources for MkDocs (see mkdocs.yml).

The Markdown files stay where they are on GitHub; this script copies them into build/site-src:
- README.md becomes the home page (index.md);
- docs/** keeps its layout (docs/en/... -> en/...); docs/README.md is left out, the home page replaces it;
- relative links are rewritten for the site: to README.md -> home page, to other files under docs/ -> unchanged,
  to files outside docs/ (CONTRIBUTING.md, copilot/, LICENSE...) -> the file on GitHub.

Run from the repository root: python3 tools/docs/build_site.py && mkdocs build --strict
"""
import os
import posixpath
import re
import shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'build', 'site-src')
REPO_URL = 'https://github.com/Power-Builders-Italia/open-project-365'
LINK = re.compile(r'\]\(([^)\s]+)\)')
FENCE = re.compile(r'^\s*(```|~~~)')


def site_path(repo_path):
    """Repository path of a Markdown file -> path inside the site, or None when it is not published."""
    if repo_path == 'README.md':
        return 'index.md'
    if repo_path.startswith('docs/') and repo_path != 'docs/README.md':
        return repo_path[len('docs/'):]
    return None


def rewrite(target, source):
    """Rewrites one link target found in the repository file `source`."""
    if re.match(r'^[a-z]+:', target) or target.startswith('#'):
        return target
    path, _, anchor = target.partition('#')
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(source), path))
    published = site_path(resolved)
    if published is None:
        kind = 'tree' if os.path.isdir(os.path.join(ROOT, resolved)) else 'blob'
        return f'{REPO_URL}/{kind}/main/{resolved}' + (f'#{anchor}' if anchor else '')
    relative = posixpath.relpath(published, posixpath.dirname(site_path(source)) or '.')
    return relative + (f'#{anchor}' if anchor else '')


def convert(source):
    lines, fenced = [], False
    with open(os.path.join(ROOT, source), encoding='utf-8') as f:
        for line in f:
            if FENCE.match(line):
                fenced = not fenced
            elif not fenced:
                line = LINK.sub(lambda m: '](' + rewrite(m.group(1), source) + ')', line)
            lines.append(line)
    target = os.path.join(OUT, site_path(source))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    sources = ['README.md']
    for folder, _, files in os.walk(os.path.join(ROOT, 'docs')):
        for name in files:
            sources.append(os.path.relpath(os.path.join(folder, name), ROOT).replace(os.sep, '/'))
    for source in sorted(sources):
        if source.endswith('.md'):
            if site_path(source):
                convert(source)
        else:  # images and other assets keep their place
            target = os.path.join(OUT, source[len('docs/'):])
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copyfile(os.path.join(ROOT, source), target)
    print(f'Site sources staged in {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
