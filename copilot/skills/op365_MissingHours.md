---
name: ProjectIQ - Missing hours
description: Read-only check of who has not recorded their hours on a day or week in ProjectIQ. Use when the user asks who is missing hours, who did not fill in the timesheet, or chi non ha inserito le ore.
---
# Missing hours (read-only)

Use this skill when the user asks "who has not entered their hours yesterday / this week".

## Inputs
- Date or week. Default: the previous working day (Monday to Friday) in Europe/Rome time.

## Steps
1. If an `op365_absence` with `op365_absencetype` = Closure and empty `op365_resourceid` covers the date, answer that it is a company closure and stop.
2. Read active resources with a user: `op365_resource` with `statecode` = 0 and `op365_userid` not empty; read `op365_weeklyhours`.
3. Expected hours per day = `op365_weeklyhours` / 5. Subtract absences of the resource on the date (`op365_absence` between `op365_fromdate` and `op365_todate`; `op365_hours` when it is a part-day absence, otherwise the whole day).
4. Recorded hours = sum of `op365_timeentry.op365_hours` of the resource on `op365_entrydate`, in any status.
5. List the resources whose recorded hours are below the expected hours.

## Output
A table: resource, expected hours, recorded hours, missing hours. Mention that the "Daily time reminder" flow already notifies these people in the app every working day.

## Rules
- Read-only: do not create time entries for anyone.
