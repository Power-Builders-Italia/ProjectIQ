---
name: ProjectIQ - Resource load
description: Read-only check of planned hours against capacity of resources in ProjectIQ. Use when the user asks who is overloaded or available in a period, or carico risorse.
---
# Resource load (read-only)

Use this skill for "who is overloaded next month", "who is free in week 45", "carico di Mario a novembre".

## Inputs
- Period (default: the next 4 weeks) and optionally a resource or a project.

## Steps
1. Capacity of each active resource (`op365_resource`, `statecode` = 0) in the period = `op365_weeklyhours` / 5 x working days (Monday to Friday), less absences (`op365_absence` of the resource and company closures without resource).
2. Planned hours = `op365_wbsallocation.op365_hours` of the resource on WBS nodes (`op365_wbsnodeid`) whose dates (`op365_startdate`, `op365_enddate`) overlap the period. Spread the allocation evenly over the working days of the node and keep the part inside the period.
3. Load % = planned / capacity. Over 100% is overloaded; under 50% is available.
4. Only count nodes of projects In Progress (`op365_project.statuscode` = 1) unless the user asks to include offers.

## Output
A table per resource: capacity, planned hours, load %, the projects that contribute most. The same view is in the app on **Projects > Planning > Resource Load**.

## Rules
- Read-only: allocations are changed in the WBS of the project in the app.
