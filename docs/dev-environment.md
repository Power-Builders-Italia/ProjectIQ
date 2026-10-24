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
