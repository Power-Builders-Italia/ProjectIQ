# Development environment setup

The solution lives unpacked in `solutions/OpenProject365/src`. Publisher and solution are defined in `src/Other/Solution.xml`.

| Item | Value |
|---|---|
| Solution unique name | `OpenProject365` |
| Solution display name | Open Project 365 |
| Publisher unique name | `PowerBuildersItalia` |
| Publisher prefix | `op365` |
| Choice value prefix | `36500` (choice values start at 365000000) |
| Base language | 1033 (English) |

## First import (creates publisher and solution)

Requires the [Power Platform CLI](https://learn.microsoft.com/power-platform/developer/cli/introduction).

```powershell
pac auth create --environment https://<dev-org>.crm4.dynamics.com
pac solution pack --folder solutions/OpenProject365/src --zipfile out/OpenProject365.zip --packagetype Unmanaged
pac solution import --path out/OpenProject365.zip
```

Alternatively download the `OpenProject365-unmanaged` artifact from the `build` workflow run and import it from make.powerapps.com.

## Daily loop

1. Customize in the dev environment, always inside the **Open Project 365** solution.
2. Export and unpack back into the repo:

```powershell
pac solution export --name OpenProject365 --path out/OpenProject365.zip --managed false
pac solution unpack --zipfile out/OpenProject365.zip --folder solutions/OpenProject365/src --packagetype Unmanaged --allowDelete true
```

3. Commit on a feature branch and open a pull request.

## Code

| Folder | Build | Tests |
|---|---|---|
| `src/plugins` | `dotnet build src/plugins/OpenProject365.Plugins -c Release` (.NET Framework 4.6.2, strong-named) | `dotnet test src/plugins/OpenProject365.Plugins.Tests` |
| `src/pcf` | `npm ci && npm run build` (all seven controls, ESLint included) | `npm test` (Jest: WBS tree, critical path, time scale, timesheet, approval, resource load, cost summary, quote comparison) |

Deploy to dev: `python3 tools/dataverse/plugins.py` registers or updates the assembly; `tools/pcf/push.sh` pushes each control into the solution (`pac pcf push` accepts one manifest per project). In the cloud container create the pac profile with `--accept-cleartext-caching` (no keyring).

## Cloud flows

`tools/dataverse/flows.py` creates the connection reference `op365_dataverse` (Microsoft Dataverse) and the **Daily time reminder** flow (Mon–Fri 17:30, W. Europe) that calls `op365_SendTimeReminders`. The flow is created off. A service principal cannot own connections (InvalidUserPlan), so a user creates the Dataverse connection (service principal authentication is fine) and turns the flow on. In Dev link it to the reference in the solution; in Test the `deploy-test` workflow maps the reference through `deployment/test.settings.json`, whose `#{OP365_DATAVERSE_CONNECTION_ID}#` token is replaced with the variable of the same name of the GitHub environment `test`, so the managed layer stays clean and no environment ids are in the repository. Share the target connection with the application user (Can use) so the import can turn the flow on.

After a solution import check that plugin steps are enabled: an interrupted import can leave them disabled.

## Copilot and Work IQ

`tools/dataverse/workiq.py` prepares the read-only exposure of Open Project 365 to Microsoft Copilot and Copilot Cowork (Business Applications in Work IQ, preview). Design and decisions: [ADR 0001](adr/0001-copilot-work-iq-read-only.md). User and admin guide: [Copilot and Cowork](en/copilot.md).

- Writes the descriptions of the custom columns and lookups (the `DESCRIPTIONS` table in the script): the Dataverse semantic model reads them, so keep a description on every new column.
- Sets the app setting `m365copilotmodelappenabled` = 2 (**Microsoft Copilot in model-driven apps** on) on the Open Project 365 app; with it Dataverse indexes the app tables and creates the semantic model of the app (`M365_Primary_model_op365_OpenProject365` in Dev).
- Creates or updates the business skills from `copilot/skills/*.md` (front matter `name` and `description`, body = instructions) as **Organization** skills (`ispersonal` = No) and adds them to the solution (component type 10441). The unique name is the file name.

Run it after the table scripts, then export and unpack the solution. The script is idempotent.

Not in the solution, to configure by hand in every environment (no documented API, no ALM support): Work IQ on the environment, table exclusions and glossary of the semantic model ([copilot/glossary.md](../copilot/glossary.md)), installation of the **Business apps (preview)** plugin. Steps in [Copilot and Cowork](en/copilot.md#set-up-administrators).

When exporting from Dev, drop the Italian (1040) labels the Dev language pack adds to standard components, unless they are part of the change.

## Supplier portal (Power Pages)

The portal is a separate solution, `OpenProject365SupplierPortal`, that depends on `OpenProject365`.
The site uses the enhanced data model. Suppliers sign in, answer RFQs (prices on the lines created by Send) and confirm purchase orders.

- Create the site only in Dev, in make.powerpages.microsoft.com (a user, not the service principal), then run
  `python tools/portal/supplier_portal.py`: Supplier web role, table permissions (Account / Parent scope), Web API site settings, pages and menu.
  The script is idempotent and writes into the portal solution.
- A supplier user is a contact whose parent account is the supplier, with the **Supplier** web role.
- Never use `pac pages upload` with the service principal: it creates empty components that cannot be deleted.
- Table permission roles must be stored in the component JSON (`adx_entitypermission_webrole`) as well as in the
  `powerpagecomponent_powerpagecomponent` relationship: the runtime reads the first, the studio shows the second. The script does both.
- After changes made through the API: Clear cache at `/_services/about` (Administrators role), then sign out and in.
- Export/unpack like the main solution, into `solutions/OpenProject365SupplierPortal/src`. deploy-test imports it after the main solution.
  In a new environment the imported site must be reactivated (Power Pages, Inactive sites) before use.

## CI and Solution Checker

The `build` workflow builds and tests the plugins and the PCF controls and packs the solution on every PR. It also runs the Solution Checker when these repository secrets exist (Settings > Secrets and variables > Actions): `PP_ENVIRONMENT_URL`, `PP_TENANT_ID`, `PP_CLIENT_ID`, `PP_CLIENT_SECRET` (an app registration that is an application user of the dev environment). The step fails if the analysis cannot run; findings are listed in the job log and in the `solution-checker-logs` artifact.

## Environments

| Environment | Status |
|---|---|
| Dev (`<dev-org>.crm4.dynamics.com`, secret `PP_ENVIRONMENT_URL`) | available, unmanaged solution |
| Test (`<test-org>.crm4.dynamics.com`, variable `TEST_ENVIRONMENT_URL`) | managed solution, deployed with the `deploy-test` workflow (Actions > deploy-test > Run workflow); plugin steps are activated on import |
| Build | not needed yet: CI only packs and checks |

## GitHub repository security

The repository is meant to be public: environment URLs, tenant, app and connection ids live only in GitHub secrets and variables.

- **Environment `test`** (Settings > Environments): required reviewer, deployment branches limited to `main`. `deploy-test` runs in it (the environment name is the `settings` input).
  - Variables: `TEST_ENVIRONMENT_URL` (default target URL), `OP365_DATAVERSE_CONNECTION_ID` (Dataverse connection id in Test, Power Apps > Connections > the connection's URL).
  - Optional variables for the company settings ([environment variables](data-model.md#company-settings-environment-variables)): `OP365_TIME_APPROVAL_ENABLED` (`yes`/`no`), `OP365_PURCHASE_REQUEST_THRESHOLD` (number, dot as decimal separator), `OP365_PURCHASING_APPROVER` (User Name in Test). `deploy-test` writes them into `deployment/test.settings.json`; an empty or missing variable is left out, so Test keeps its current value (or the default).
  - Secrets: move `PP_CLIENT_SECRET` (and the other `PP_*`) here when the Solution Checker gets its own app registration; until then they stay repository secrets, used by `build` on pull requests from branches of this repository (pull requests from forks never receive secrets).
- **Actions**: every third-party action is pinned to a commit SHA (tag in a comment); update them together. Workflows run with a read-only `GITHUB_TOKEN` (`permissions: contents: read`). Never use `pull_request_target`.
- **Settings > Actions > General**: "Require approval for all outside collaborators" for fork pull requests.
- **Branch protection on `main`**: pull request required, review from code owners ([CODEOWNERS](../.github/CODEOWNERS)), `build` checks required.
- **Code security**: secret scanning and push protection on; Dependabot alerts on.
- Vulnerability reports: [SECURITY.md](../SECURITY.md).

