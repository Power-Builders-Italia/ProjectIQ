# Contributing to Open Project 365

## Documentation is part of every change

The user manuals in `docs/<language>/` (English `en`, Italian `it`, French `fr`, German `de`) describe what users see and do. They must always match the application.

Every pull request that changes a functional behaviour — tables, fields, forms, views, buttons and commands, statuses and transitions, validation rules and messages, security roles, notifications, flows, PCF controls, the supplier portal — must:

1. update the affected manual(s) in **English first** (`docs/en/`), then apply the same change to `docs/it/`, `docs/fr/` and `docs/de/`;
2. keep the four versions **structurally identical** (same sections, tables, diagrams and order), so that a reader can switch language at any point;
3. write UI labels, button names and error messages **in English, exactly as they appear on screen**, also in the translated manuals (add a translation in brackets where it helps);
4. add a new manual in all four languages, and a row in the **User manuals** table of [README.md](README.md), when a new functional area is introduced, and add it to the menu of the documentation website in [mkdocs.yml](mkdocs.yml);
5. update [docs/data-model.md](docs/data-model.md) when tables or columns change, and [docs/dev-environment.md](docs/dev-environment.md) when setup or deployment changes;
6. run the documentation check locally:

   ```bash
   python3 tools/docs/check_docs.py
   ```

   It fails when a manual is missing in a language, when a relative link or `#anchor` is broken, or when a manual is not linked from the README. The same check runs in CI on every pull request.

Diagrams are written in [Mermaid](https://mermaid.js.org/) inside the Markdown files, so they are versioned and reviewed with the text.

### Writing style

- Explain the *why* as well as the *how*: start each section with what the feature is for, then the procedure, then the field tables and the rules.
- Prefer numbered steps for procedures, tables for fields and statuses, and a diagram for flows and life cycles.
- Use gender-neutral wording.
- Every manual starts with the language switcher and a link back to the README manual index.

## Bugs

Every bug is tracked as a GitHub issue with the `bug` label; link the fixing pull request to the issue.
