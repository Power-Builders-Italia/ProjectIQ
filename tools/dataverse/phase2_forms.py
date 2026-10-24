"""Phase 2 main forms: WBS Node and the project child tables, plus the web resources of the Project form
(the Project form itself is defined in phase3_forms.py).

Run after tools/pcf/push.sh (the forms reference the code components). Idempotent.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API
from formlib import ok, section, tab, form, webresource, onload, use_ids

use_ids('op365-phase2-forms')
SRC = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'webresources')
PROJECT_JS = 'op365_/scripts/project.form.js'
WBS_JS = 'op365_/scripts/wbsnode.form.js'
webresource(PROJECT_JS, os.path.join(SRC, 'project.form.js'), 'Project form script')
webresource(WBS_JS, os.path.join(SRC, 'wbsnode.form.js'), 'WBS Node form script')

# The Project form moved to phase3_forms.py (Time, Materials and Costs tabs).

T = 'op365_wbsnode'
form(T, 'WBS Node', [
    tab('General', [('100%', [
        section(T, 'WBS Node', ['op365_projectid', 'op365_parentid', 'op365_code', 'op365_name', 'op365_ownerresourceid',
                                'op365_sortorder', 'op365_startdate', 'op365_enddate', 'op365_progresspct', 'ownerid'])])]),
    tab('Budget', [('100%', [
        section(T, 'Budget', ['op365_budgethours', 'op365_actualhours', 'op365_budgetlabour', 'op365_budgetmaterials',
                              'op365_budgetother', 'op365_budgettotal'])])]),
    tab('Dependencies', [('100%', [
        section(T, 'Predecessors', [('subgrid', 'Predecessors', 'Predecessors', 'op365_wbsdependency', 'op365_wbsnode_wbsdependency_successorid', 6)]),
        section(T, 'Successors', [('subgrid', 'Successors', 'Successors', 'op365_wbsdependency', 'op365_wbsnode_wbsdependency_predecessorid', 6)])])]),
    tab('Allocations', [('100%', [
        section(T, 'Allocations', [('subgrid', 'Allocations', 'Allocations', 'op365_wbsallocation', 'op365_wbsnode_wbsallocation_wbsnodeid', 8)])])]),
], replace='Information', extra=onload(WBS_JS, 'OP365.WbsNode.onLoad'))

T = 'op365_projectmember'
form(T, 'Project Member', [tab('General', [('100%', [
    section(T, 'Project Member', ['op365_projectid', 'op365_userid', 'op365_projectrole', 'op365_hourlyrate', 'op365_name', 'ownerid'])])])],
    replace='Information')

T = 'op365_wbsdependency'
form(T, 'WBS Dependency', [tab('General', [('100%', [
    section(T, 'Dependency', ['op365_predecessorid', 'op365_successorid', 'op365_dependencytype', 'op365_lagdays',
                              'op365_projectid', 'op365_name'])])])], replace='Information')

T = 'op365_wbsallocation'
form(T, 'WBS Allocation', [tab('General', [('100%', [
    section(T, 'Allocation', ['op365_wbsnodeid', 'op365_resourceid', 'op365_hours', 'op365_name'])])])], replace='Information')

T = 'op365_baseline'
form(T, 'Baseline', [tab('General', [('100%', [
    section(T, 'Baseline', ['op365_projectid', 'op365_name', 'op365_isreference', 'ownerid']),
    section(T, 'Description', ['op365_description'], columns=1),
    section(T, 'Nodes', [('subgrid', 'Nodes', 'Nodes', 'op365_baselinenode', 'op365_baseline_baselinenode_baselineid', 15)])])])],
    replace='Information')

T = 'op365_baselinenode'
form(T, 'Baseline Node', [tab('General', [('100%', [
    section(T, 'Baseline Node', ['op365_baselineid', 'op365_wbsnodeid', 'op365_code', 'op365_name', 'op365_budgethours',
                                 'op365_budgettotal', 'op365_startdate', 'op365_enddate'])])])], replace='Information')

ok(S.post(API + 'PublishAllXml', json={}), 'publish')
