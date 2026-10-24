"""Phase 3 forms: Project (now with Time, Materials and Costs), Time Entry (main and quick create), Material Usage,
and the Timesheet, Time Approval and Resource Load dashboards built on the Phase 3 code components.

Run after tools/pcf/push.sh (the forms reference the code components). Idempotent.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API
from formlib import ok, section, tab, form, webresource, onload, use_ids

use_ids('op365-phase3-forms')
SRC = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'webresources')
EXEC_JS = 'op365_/scripts/execution.form.js'
webresource(EXEC_JS, os.path.join(SRC, 'execution.form.js'), 'Time Entry and Material Usage form script')

P = 'op365_project'
WBS_REL = 'op365_project_wbsnode_projectid'
form(P, 'Project', [
    tab('Summary', [
        ('60%', [section(P, 'Project', ['op365_code', 'op365_name', 'op365_customerid', 'op365_projectmanagerid',
                                        'statuscode', 'ownerid', 'op365_startdate', 'op365_enddate']),
                 section(P, 'Budget and Progress', ['op365_contractvalue', 'op365_budgettotal', 'op365_actualcost',
                                                    'op365_actualhours', 'op365_committedcost', 'op365_progresspct']),
                 section(P, 'Description', ['op365_description'], columns=1)]),
        ('40%', [section(P, 'Timeline', [('timeline',)])])]),
    tab('WBS', [('100%', [section(P, 'WBS', [('subgrid', 'WbsTree', 'WBS', 'op365_wbsnode', WBS_REL, 20, 'op365_OP365.WbsTreeGrid')])])]),
    tab('Gantt', [('100%', [section(P, 'Gantt', [('subgrid', 'Gantt', 'Gantt', 'op365_wbsnode', WBS_REL, 20, 'op365_OP365.GanttChart')]),
                            section(P, 'Baselines', [('subgrid', 'Baselines', 'Baselines', 'op365_baseline', 'op365_project_baseline_projectid', 5)])])]),
    tab('Costs', [('100%', [section(P, 'Cost Summary', [('pcf', 'op365_actualcost', 'op365_OP365.CostSummary')])])]),
    tab('Time', [('100%', [section(P, 'Time Entries', [('subgrid', 'TimeEntries', 'Time Entries', 'op365_timeentry',
                                                        'op365_project_timeentry_projectid', 12, None, 'Time Entries by Project')])])]),
    tab('Materials', [('100%', [section(P, 'Material Usage', [('subgrid', 'Materials', 'Material Usage', 'op365_materialusage',
                                                               'op365_project_materialusage_projectid', 12, None, 'Material Usage by Project')])])]),
    tab('Team', [('100%', [section(P, 'Team', [('subgrid', 'Team', 'Project Members', 'op365_projectmember', 'op365_project_projectmember_projectid', 10)])])]),
], replace='Information')

T = 'op365_timeentry'
script = lambda: onload(EXEC_JS, 'OP365.Execution.onLoad')
form(T, 'Time Entry', [
    tab('General', [('60%', [
        section(T, 'Time', ['op365_projectid', 'op365_wbsnodeid', 'op365_resourceid', 'op365_entrydate', 'op365_hours', 'statuscode!']),
        section(T, 'Notes', ['op365_notes'], columns=1)]),
        ('40%', [
        section(T, 'Approval', ['op365_submittedon!', 'op365_decidedbyid!', 'op365_decidedon!', 'op365_decisionnote!'], columns=1),
        section(T, 'Value', ['op365_cost!', 'op365_revenue!', 'op365_name!', 'ownerid'], columns=1)])]),
], replace='Information', extra=script())
form(T, 'Quick Time Entry', [
    tab('General', [('100%', [section(T, 'Time', ['op365_projectid', 'op365_wbsnodeid', 'op365_entrydate', 'op365_hours', 'op365_notes'], columns=1)])]),
], form_type=7, replace='Information', extra=script())

T = 'op365_materialusage'
form(T, 'Material Usage', [
    tab('General', [('60%', [
        section(T, 'Usage', ['op365_projectid', 'op365_wbsnodeid', 'op365_usagedate', 'op365_itemid', 'op365_name',
                             'op365_supplierid', 'op365_quantity', 'op365_uom'])]),
        ('40%', [section(T, 'Cost', ['op365_unitcost', 'op365_totalcost!', 'ownerid'], columns=1)])]),
], replace='Information', extra=script())

# ---------- dashboards (code components on subgrids) ----------
DASHBOARDS = {}
for name, desc, target, view, pcf, dataset in [
    ('Timesheet', 'Weekly time entry of the current user', 'op365_timeentry', 'My Time Entries', 'op365_OP365.WeeklyTimesheet', 'entries'),
    ('Time Approval', 'Submitted time entries to approve', 'op365_timeentry', 'Time Entries to Approve', 'op365_OP365.TimeApproval', 'entries'),
    ('Resource Load', 'Allocated hours against capacity by week', 'op365_resource', None, 'op365_OP365.ResourceLoad', 'resources'),
]:
    item = ('subgrid', 'Board', name, target, None, 30, pcf, view if view != 'My Time Entries' else None, dataset)
    DASHBOARDS[name] = form('none', name, [tab(name, [('100%', [section('none', name, [item])])])], description=desc, form_type=0)

ok(S.post(API + 'PublishAllXml', json={}), 'publish')
for name, fid in DASHBOARDS.items():
    print(f'dashboard {name}: {fid}')

# quick create forms are used only when the table allows them
for table in ['op365_timeentry', 'op365_materialusage']:
    md = S.get(API + f"EntityDefinitions(LogicalName='{table}')").json()
    if md.get('IsQuickCreateEnabled'):
        print('skip quick create', table); continue
    md['IsQuickCreateEnabled'] = True
    ok(S.put(API + f"EntityDefinitions(LogicalName='{table}')", json=md, headers={'MSCRM.MergeLabels': 'true'}),
       'quick create enabled ' + table)
