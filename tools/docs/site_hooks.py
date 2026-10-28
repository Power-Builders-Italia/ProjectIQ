"""MkDocs hooks for the documentation website (see mkdocs.yml)."""

REPO_URL = 'https://github.com/Power-Builders-Italia/projectiq'


def on_page_context(context, page, config, nav):
    # The home page is the repository README, not a file under docs/
    if page.file.src_uri == 'index.md':
        page.edit_url = f'{REPO_URL}/edit/main/README.md'
    return context
