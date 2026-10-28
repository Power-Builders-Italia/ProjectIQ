# ProjectIQ — notes for Claude

- Power Apps model-driven app on Dataverse; solution `OpenProject365`, publisher prefix `op365`, choice values from 365000000. Supplier portal is the separate solution `OpenProject365SupplierPortal`.
- Plugins in `src/plugins` (C#), PCF controls in `src/pcf` (React + Fluent UI v9), schema scripts in `tools/dataverse`.

## Documentation rule (mandatory)

Any change to functional behaviour must update the user manuals in `docs/en`, `docs/it`, `docs/fr` and `docs/de` in the same pull request, following [CONTRIBUTING.md](CONTRIBUTING.md):

- English is the reference; the other three languages mirror its structure and keep UI labels/messages in English as on screen.
- Verify statements against the code (plugins, PCF, form scripts, schema scripts) before writing them.
- New functional area → new manual in all four languages + row in the README "User manuals" table.
- Run `python3 tools/docs/check_docs.py` before committing; it must report 0 errors.
- The repository is the only home of the documentation: do not keep copies elsewhere (e.g. SharePoint).
