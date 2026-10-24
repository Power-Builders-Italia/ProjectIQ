"""Phase 3 forms: Time Entry (main and quick create), Material Usage,
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

# The Project form moved to phase4_forms.py (Purchasing tab).

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
    # dashboards lay sections out on a 3-column grid: the subgrid spans all of it to fill the page
    item = ('subgrid', 'Board', name, target, None, 30, pcf, view if view != 'My Time Entries' else None, dataset, 3)
    DASHBOARDS[name] = form('none', name, [tab(name, [('100%', [section('none', name, [item], grid='111')])])],
                           description=desc, form_type=0)

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
