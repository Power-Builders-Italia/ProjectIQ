# deploy-dev Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `deploy-dev` workflow that imports the solutions built from `main` into Dev after a drift check against the tag `dev-deployed`, opening a draft pull request when Dev holds unexported changes.

**Architecture:** A pure-Python comparer (`tools/alm/compare_solution.py`, stdlib only, unit-tested in CI) decides drift between two `solutions/` trees. The workflow has three jobs: `deploy` (environment `dev`: export, compare, import, plugins, PCF, portal, verify), `drift-pr` (no secrets: branch + draft PR) and `tag` (moves `dev-deployed`).

**Tech Stack:** Python 3 stdlib (`unittest`, `pathlib`, `difflib`, `re`), GitHub Actions, `microsoft/powerplatform-actions`, Power Platform CLI, `gh`.

**Spec:** [docs/adr/0002-deploy-dev.md](../../adr/0002-deploy-dev.md)

## Global Constraints

- Every action pinned to a commit SHA with the tag in a comment, using the SHAs already in `build.yml` / `pages.yml` / `deploy-test.yml` (e.g. `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`, `microsoft/powerplatform-actions/*@6e91314a9c6e694ea5c894fe8c40e09d73aa892b # v1`).
- Workflow default `permissions: contents: read`; `contents: write` + `pull-requests: write` only on `drift-pr`; `contents: write` only on `tag`. Never `pull_request_target`.
- Secrets only from the GitHub environment `dev`: `PP_ENVIRONMENT_URL`, `PP_TENANT_ID`, `PP_CLIENT_ID`, `PP_CLIENT_SECRET`. No repository-level secrets, no secret values in `run:` echo.
- Triggers: `push` to `main` with `paths` `solutions/**`, `src/plugins/**`, `src/pcf/**`, `src/webresources/**`; `workflow_dispatch` with boolean inputs `check-only`, `skip-drift-check` and string input `baseline`.
- `concurrency: { group: deploy-dev, cancel-in-progress: false }`.
- Tag name `dev-deployed`; drift branch `drift/YYYYMMDD-hhmm` (UTC) created from the baseline commit.
- Comparer exit codes: `0` same, `1` drift, `2` usage error.
- Documentation in English in `docs/dev-environment.md`; `python3 tools/docs/check_docs.py` reports 0 errors.

## Review Focus

- **CRLF vs LF and a UTF-8 BOM** between a Windows export and the repository: must compare equal (test in Task 1).
- **Built files** (`PluginAssemblies/**/*.dll`, `Controls/**/bundle.js`) with different bytes: equal; the same file missing on one side: drift (Task 1).
- **Binary or non-UTF-8 files** (`.png` web resources): compared as bytes, never crash on decode (Task 1).
- **Italian labels on `op365_` components** that differ: drift, while the same difference on `Account` is ignored (Task 1).
- **First run without tag and without `baseline`**: the run stops before touching Dev with a message naming the `baseline` input (Task 2, manual check in Task 4).

---

### Task 1: Solution comparer

**Files:**
- Create: `tools/alm/compare_solution.py`
- Create: `tools/alm/test_compare_solution.py`
- Modify: `.github/workflows/build.yml` (job `code`: new step before "Plugins build and tests")

**Interfaces:**
- Produces:
  - `normalize(rel_path: str, data: bytes) -> bytes` — rules below; `rel_path` uses `/`, relative to the `solutions/` root (e.g. `OpenProject365/src/Entities/Account/Entity.xml`).
  - `Diff` dataclass: `added: list[str]`, `removed: list[str]`, `changed: list[str]` (sorted, relative paths; `added` = only in current); property `drift: bool`.
  - `compare_trees(baseline: Path, current: Path) -> Diff`
  - `format_summary(diff: Diff, diffs: dict[str, str], max_lines: int = 40) -> str` — Markdown for `$GITHUB_STEP_SUMMARY`.
  - CLI: `python tools/alm/compare_solution.py BASELINE CURRENT [--summary FILE]` → exit 0/1/2; with `--summary` appends the Markdown to FILE.

Normalization rules (in order):
1. Strip a UTF-8 BOM; convert CRLF to LF; strip trailing whitespace on each line.
2. `*/src/Other/Solution.xml`: remove the `<Version>…</Version>` element.
3. Files under `*/src/Entities/<name>/` where `<name>` does not start with `op365_`: drop every line containing `languagecode="1040"`.
4. Built files (`*/src/PluginAssemblies/**/*.dll`, `*/src/Controls/**/bundle.js`): content replaced by `b""` (presence only).
5. Rules 1–3 apply only to files that decode as UTF-8; other files are compared as raw bytes.

- [ ] **Step 1: Write the failing tests** in `tools/alm/test_compare_solution.py` (`unittest`, temp dirs built per test):
  - `test_identical_trees_no_drift` → `Diff([], [], [])`, `drift is False`.
  - `test_crlf_and_bom_ignored` → baseline `a\n`, current `﻿a\r\n` → no drift.
  - `test_solution_version_ignored` → `<Version>1.0.1.0</Version>` vs `<Version>1.0.57.0</Version>` in `OpenProject365/src/Other/Solution.xml` → no drift.
  - `test_italian_label_on_standard_entity_ignored` → extra `<displayname description="X" languagecode="1040" />` line in `OpenProject365/src/Entities/Account/Entity.xml` → no drift.
  - `test_italian_label_on_op365_entity_is_drift` → same line in `Entities/op365_Project/Entity.xml` → `changed == ["OpenProject365/src/Entities/op365_Project/Entity.xml"]`.
  - `test_built_files_compared_by_presence` → different bytes in `PluginAssemblies/X/OpenProject365Plugins.dll` and `Controls/op365_OP365.GanttChart/bundle.js` → no drift; dll missing in current → `removed == [".../OpenProject365Plugins.dll"]`.
  - `test_binary_file_compared_as_bytes` → `WebResources/op365_/icon.png` with bytes `b"\x89PNG\xff"` vs `b"\x89PNG\xfe"` → `changed` lists it, no exception.
  - `test_added_and_removed_files` → file only in current → `added`; only in baseline → `removed`.
  - `test_cli_exit_codes` → `main([base, cur])` returns 0 / 1; missing directory returns 2.
  - `test_summary_lists_files_and_caps_diff` → `format_summary` contains each path and at most `max_lines` diff lines per file.

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest discover -s tools/alm -v`
Expected: errors `ModuleNotFoundError: No module named 'compare_solution'` (or import failures).

- [ ] **Step 3: Implement `tools/alm/compare_solution.py`** with the interfaces above. `compare_trees` walks both trees with `Path.rglob("*")` (files only), keys by POSIX relative path; unified diffs via `difflib.unified_diff` on decoded normalized text, only for text files. `main(argv: list[str] | None = None) -> int` uses `argparse`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tools/alm -v`
Expected: 10 tests, `OK`.

- [ ] **Step 5: Run against the real tree**

Run: `python3 tools/alm/compare_solution.py solutions solutions; echo $?`
Expected: `0`.

- [ ] **Step 6: Add to CI** — in `build.yml` job `code`, step `ALM tools tests` running `python3 -m unittest discover -s tools/alm -v` (ubuntu has Python 3).

- [ ] **Step 7: Commit**

```bash
git add tools/alm .github/workflows/build.yml
git commit -m "ALM: solution comparer for the deploy-dev drift check"
```

### Task 2: Workflow `deploy-dev` — job `deploy`

**Files:**
- Create: `.github/workflows/deploy-dev.yml`

**Interfaces:**
- Consumes: CLI of Task 1 (`compare_solution.py BASELINE CURRENT --summary FILE`, exit 0/1/2).
- Produces: job `deploy` outputs `drift` (`'true'`/`'false'`) and `baseline` (full SHA); artifact `dev-export` (folder `solutions/` with the unpacked Dev export, both solutions) when `drift == 'true'`; artifact `drift-summary` (`summary.md`).

Steps of job `deploy` (`runs-on: windows-latest`, `environment: dev`, `defaults.run.shell: pwsh` unless stated):

- [ ] **Step 1: Header** — name, triggers, inputs, top-level `permissions: contents: read`, `concurrency` (Global Constraints). Comment block at the top in the style of `deploy-test.yml` explaining the flow and pointing to ADR 0002.
- [ ] **Step 2: Checkout and baseline** — `actions/checkout` with `fetch-depth: 0`; step `Resolve baseline` (bash): `git rev-parse dev-deployed^{commit}` if the tag exists, else `inputs.baseline` if set, else `echo "::error::No tag dev-deployed: run the workflow with the baseline input (the commit that matches Dev)"; exit 1`. Writes `baseline` to `$GITHUB_OUTPUT`. Skipped entirely when `inputs.skip-drift-check`.
- [ ] **Step 3: Tools** — `powerplatform-actions/actions-install`; `setup-python` (3.13) with `pip install requests`; `setup-dotnet` (`10.0.x`); `setup-node` (22, npm cache on `src/pcf/package-lock.json`).
- [ ] **Step 4: Export Dev** — `export-solution` (unmanaged) for `OpenProject365` and `OpenProject365SupplierPortal` into `out/dev/`, `unpack-solution` each into `dev/solutions/<Solution>/src` (`solution-type: Unmanaged`). Skipped when `skip-drift-check`.
- [ ] **Step 5: Compare** — bash: `git archive "$BASELINE" solutions | tar -x -C base`; `python tools/alm/compare_solution.py base/solutions dev/solutions --summary summary.md`; exit 0 → `drift=false`, exit 1 → `drift=true`, other → fail. `cat summary.md >> $GITHUB_STEP_SUMMARY`. Upload `dev-export` (path `dev/solutions`) and `drift-summary` when drift. With `skip-drift-check`: `drift=false` and a summary line saying the check was skipped.
- [ ] **Step 6: Stop conditions** — all later steps `if: steps.compare.outputs.drift == 'false' && !inputs.check-only`.
- [ ] **Step 7: Pack and import main** — copy `src/webresources/*` over the files of the same name under `solutions/OpenProject365/src/WebResources` (pwsh `Get-ChildItem -Recurse` match by file name, `.data.xml` untouched); `pack-solution` (unmanaged) both into `out/main/`; `import-solution` `OpenProject365` with `publish-changes: true`, `activate-plugins: true`, `run-asynchronously: true`, `max-async-wait-time: 60`, no deployment settings, no `stage-and-upgrade`.
- [ ] **Step 8: Plugins from source** — `dotnet build src/plugins/OpenProject365.Plugins -c Release`; `python tools/dataverse/plugins.py` with env `PAC_ENVIRONMENT_URL`, `PAC_TENANT_ID`, `PAC_CLIENT_ID`, `PAC_CLIENT_SECRET` mapped from the `PP_*` secrets.
- [ ] **Step 9: PCF from source** — `npm ci` in `src/pcf`; `pac auth create --name dev --applicationId … --clientSecret … --tenant … --environment …`; bash `tools/pcf/push.sh`.
- [ ] **Step 10: Portal and publish** — `import-solution` `OpenProject365SupplierPortal` (same options, no `activate-plugins`); `publish-solution`.
- [ ] **Step 11: Verify** — export + unpack both again into `verify/solutions`; `python tools/alm/compare_solution.py solutions verify/solutions --summary verify.md`; append to step summary; non-zero exit fails the job with `::error::Dev does not match main after the import: see the summary`.
- [ ] **Step 12: Validate the YAML**

Run: `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/deploy-dev.yml'))" && pip install -q actionlint-py && actionlint .github/workflows/deploy-dev.yml`
Expected: no output from actionlint (exit 0).

- [ ] **Step 13: Commit**

```bash
git add .github/workflows/deploy-dev.yml
git commit -m "deploy-dev: drift check and import of main into Dev"
```

### Task 3: Jobs `drift-pr` and `tag`

**Files:**
- Modify: `.github/workflows/deploy-dev.yml`

**Interfaces:**
- Consumes: `needs.deploy.outputs.drift`, `needs.deploy.outputs.baseline`, artifacts `dev-export`, `drift-summary` (Task 2).

- [ ] **Step 1: `drift-pr`** — `needs: deploy`, `if: needs.deploy.outputs.drift == 'true'`, `runs-on: ubuntu-latest`, `permissions: { contents: write, pull-requests: write }`, no environment. Steps: checkout `fetch-depth: 0`; download both artifacts; bash: `BRANCH=drift/$(date -u +%Y%m%d-%H%M)`, `git switch -c "$BRANCH" "$BASELINE"`, replace `solutions/OpenProject365/src` and `solutions/OpenProject365SupplierPortal/src` with the export, commit as `github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>` with message `Dev drift since <short baseline>`, `git push origin "$BRANCH"`; `gh pr create --draft --base main --head "$BRANCH" --title "Dev drift since <short baseline>" --body-file pr.md` (`GH_TOKEN: ${{ github.token }}`), where `pr.md` = summary + a line saying that checks start after the next push to the branch; final step `echo "::error::Dev has changes not in main: see the draft pull request"; exit 1`.
- [ ] **Step 2: `tag`** — `needs: deploy`, `if: needs.deploy.result == 'success' && needs.deploy.outputs.drift == 'false' && !inputs.check-only`, `runs-on: ubuntu-latest`, `permissions: contents: write`. Steps: checkout; `git tag -f dev-deployed "$GITHUB_SHA"`; `git push -f origin refs/tags/dev-deployed`.
- [ ] **Step 3: Validate** — same command as Task 2 Step 12. Expected: exit 0.
- [ ] **Step 4: Commit**

```bash
git add .github/workflows/deploy-dev.yml
git commit -m "deploy-dev: drift pull request and dev-deployed tag"
```

### Task 4: Documentation and first run

**Files:**
- Modify: `docs/dev-environment.md` (sections *Environments and deployment*, *GitHub repository security*)
- Delete: `docs/superpowers/plans/2026-10-27-deploy-dev.md` (the ADR is the permanent record)

- [ ] **Step 1: Environments and deployment** — diagram: add `R -->|"deploy-dev<br/>after approval"| D`; Dev row of the table: "with `deploy-dev` after each merge (approval in environment `dev`); by hand for work in progress"; replace the bold paragraph with: Dev follows `main` through `deploy-dev`, `deploy-test` still exports from Dev; Roles: add *Dev approver* (required reviewer of `dev`); new step **3b. Deploy to Dev**: what triggers it, approve in *Review deployments*, the three outcomes (deployed + tag moved / drift PR / verification failed), inputs `check-only`, `baseline`, `skip-drift-check`; Troubleshooting rows: *No tag dev-deployed: run the workflow with the baseline input…*, *Dev has changes not in main: see the draft pull request*, *Dev does not match main after the import: see the summary*, a failed run followed by drift → `skip-drift-check`.
- [ ] **Step 2: GitHub repository security** — bullet **Environment `dev`**: required reviewer, deployment branches `main`, secrets `PP_ENVIRONMENT_URL`, `PP_TENANT_ID`, `PP_CLIENT_ID`, `PP_CLIENT_SECRET` (application user of Dev with System Customizer or System Administrator); mention that `drift-pr` and `tag` use `GITHUB_TOKEN` with write scope only in those jobs, and that Settings > Actions > General > *Allow GitHub Actions to create and approve pull requests* must be on for `drift-pr`.
- [ ] **Step 3: Delete the plan file, run the checks**

Run: `python3 tools/docs/check_docs.py && python3 -m unittest discover -s tools/alm`
Expected: `0 errors`, `OK`.

- [ ] **Step 4: Commit and open the pull request**

```bash
git add -A docs
git commit -m "Docs: deploy-dev in environments and deployment"
```

- [ ] **Step 5: First run (after merge, by the maintainer)** — create environment `dev`; turn on *Allow GitHub Actions to create and approve pull requests*; Actions > deploy-dev > Run workflow with `check-only` and `baseline` = the commit that matches Dev; expected: drift summary (or none), no import; then a full run; expected: tag `dev-deployed` on `main`.
