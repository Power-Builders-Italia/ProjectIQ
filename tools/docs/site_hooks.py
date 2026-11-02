"""MkDocs hooks for the documentation website (see mkdocs.yml)."""
import html
import re

REPO_URL = 'https://github.com/Power-Builders-Italia/ProjectIQ'


def on_page_context(context, page, config, nav):
    # The home page is the repository README, not a file under docs/
    if page.file.src_uri == 'index.md':
        page.edit_url = f'{REPO_URL}/edit/main/README.md'
    return context


# Search engines show the meta description under the page title: without one every page would repeat site_description
DESCRIPTION_LENGTH = 160
MIN_LENGTH = 60  # shorter paragraphs ("Formerly ...", "Last updated ...") do not describe the page
SKIP_LINE = re.compile(r'^\s*(#|>|\||[-*+] |\d+\. |```|~~~|<|!\[|\[!\[|---|\[[^\]]*\]\([^)]*\)\s*(\||$))')


def page_description(markdown):
    """First prose paragraph of a page, as plain text (headings, lists, tables, the language bar are skipped)."""
    paragraph, fenced = [], False
    for line in markdown.splitlines():
        if re.match(r'^\s*(```|~~~)', line):
            fenced = not fenced
            continue
        if fenced:
            continue
        if not line.strip() or SKIP_LINE.match(line):
            if len(' '.join(paragraph)) >= MIN_LENGTH:
                break
            paragraph = []
            continue
        paragraph.append(line.strip())
    text = ' '.join(paragraph) if len(' '.join(paragraph)) >= MIN_LENGTH else ''
    text = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', text)  # links and images -> their text
    text = re.sub(r'[*_`]', '', text)
    if len(text) > DESCRIPTION_LENGTH:
        text = text[:DESCRIPTION_LENGTH - 1].rsplit(' ', 1)[0] + '…'
    return text


def on_page_markdown(markdown, page, config, files):
    if not page.meta.get('description'):
        description = page_description(markdown)
        if description:
            # The theme writes it into the content attribute as it is
            page.meta['description'] = html.escape(description)
    return markdown
