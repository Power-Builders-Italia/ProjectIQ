---
name: Open Project 365 - Hours to approve
description: Read-only list of submitted hours (time entries) waiting for approval in Open Project 365. Use when the user asks which hours, timesheets or rapportini they have to approve.
---
# Hours to approve (read-only)

Use this skill when the user asks "which hours do I have to approve", "ore da approvare", "pending timesheets".
Copilot cannot approve or reject hours. Tell the user to approve them in the Open Project 365 app, **Projects > Time > Approvals**.

## Steps
1. Read `op365_timeentry` with `statuscode` = 365000000 (Submitted): `op365_entrydate`, `op365_hours`, `op365_notes`, `op365_submittedon`, `op365_resourceid`, `op365_projectid`, `op365_wbsnodeid`.
2. Keep the entries of the projects where the user is the project manager (`op365_project.op365_projectmanagerid`) or a project member with role Manager (`op365_projectmember.op365_projectrole` = Manager). If the user is a System Administrator and asks for all, keep all.
3. Group by project, then by resource; sum the hours.
4. Flag entries submitted more than 7 days ago (`op365_submittedon`), and days where one resource has more than 10 hours in total.

## Output
A table per project: resource, days, total hours, oldest submission, flags. Then one line with the total to approve and the path to the Approvals page.

## Rules
- Only Submitted entries are waiting; Draft entries are not yet submitted, Approved and Rejected are decided.
- When time approval is off (environment variable `op365_TimeApprovalEnabled` = No), hours are approved on submit: say there is nothing to approve.
