# Open Project 365

Project and job management solution built on **Microsoft Dataverse** as a **Power Apps model-driven app**.
Rewrite of Commesse.Cloud; single-tenant (one Dataverse environment per customer company).

- Publisher prefix: `op365`
- Base language: English (1033); translations: Italian (1040), French (1036), German (1031)
- PCF controls: React virtual controls with Fluent UI v9

## Repository layout

| Folder | Content |
|---|---|
| `solutions/OpenProject365` | Unpacked Dataverse solution (`pac solution unpack`) |
| `src/plugins` | C# plugins and Custom API implementations |
| `src/pcf` | PCF controls (GanttChart, WbsTreeGrid, WeeklyTimesheet, TimeApproval, ResourceLoad, CostSummary, QuoteComparison) |
| `src/webresources` | Form scripts |
| `portal` | Power Pages supplier portal |
| `docs` | Analysis, specification, ADRs, [dev environment setup](docs/dev-environment.md), [data model](docs/data-model.md) |
| `tools/dataverse` | Scripts that create schema in the dev environment via the Web API |
| `tools/pcf` | Push of the PCF controls to an environment |

## Out of scope
Sales opportunities, mobile app, data migration from Commesse.Cloud, AI features (planned as a Cowork plugin).

## Specification
See the "Open Project 365 - Analisi e specifica" document in the PROGETTI SharePoint library.
