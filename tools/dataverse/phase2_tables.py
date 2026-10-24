"""Phase 2 tables: projects, team, WBS, dependencies, allocations, baselines.

Totals (budget, progress, project count) are plain columns kept up to date by the
OpenProject365.Plugins assembly, so they are always current (no rollup refresh delay).
Idempotent; reads the PAC_* environment variables.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API
from meta import (L, col, ok, ent, create_tables, create_columns, create_lookups, create_keys, publish)

TABLES = [
  ('Project', 'Project', 'Projects', 'Customer project (commessa)', ('Name', 'Name', 200, True)),
  ('ProjectMember', 'Project Member', 'Project Members', 'User working on a project; grants record access through the project access teams', ('Name', 'Name', 200, False)),
  ('WbsNode', 'WBS Node', 'WBS Nodes', 'Work breakdown structure element of a project (phase, activity, task)', ('Name', 'Name', 200, True)),
  ('WbsDependency', 'WBS Dependency', 'WBS Dependencies', 'Finish-to-start link between two WBS nodes', ('Name', 'Name', 200, False)),
  ('WbsAllocation', 'WBS Allocation', 'WBS Allocations', 'Planned hours of a resource on a WBS node', ('Name', 'Name', 200, False)),
  ('Baseline', 'Baseline', 'Baselines', 'Snapshot of the WBS budget and dates of a project', ('Name', 'Name', 200, True)),
  ('BaselineNode', 'Baseline Node', 'Baseline Nodes', 'WBS node values saved in a baseline', ('Name', 'Name', 200, False)),
]

PCT = dict(min=0, maxv=100)
COLUMNS = {
  'account': [
    col('whole', 'ProjectCount', 'Project Count', 'Number of projects of the customer. Set by plugin'),
    col('currency', 'ContractValueTotal', 'Contract Value Total', 'Sum of the contract value of the customer projects. Set by plugin'),
  ],
  'op365_project': [
    col('text', 'Code', 'Code', required=True, max=50),
    col('date', 'StartDate', 'Start Date'),
    col('date', 'EndDate', 'End Date'),
    col('currency', 'ContractValue', 'Contract Value'),
    col('memo', 'Description', 'Description'),
    col('currency', 'BudgetTotal', 'Budget Total', 'Sum of the WBS budgets. Set by plugin'),
    col('currency', 'ActualCost', 'Actual Cost', 'Cost of approved hours and expenses. Set by plugin (Phase 3)'),
    col('currency', 'CommittedCost', 'Committed Cost', 'Open purchase orders. Set by plugin (Phase 4)'),
    col('decimal', 'ProgressPct', 'Progress %', 'Budget-weighted progress of the WBS. Set by plugin', **PCT),
  ],
  'op365_projectmember': [
    col('choice', 'ProjectRole', 'Project Role', required=True, options=['Manager', 'Contributor', 'Reader'], default=1),
    col('currency', 'HourlyRate', 'Hourly Rate', 'Billing rate of the member on this project'),
  ],
  'op365_wbsnode': [
    col('text', 'Code', 'Code', 'Outline code, e.g. 1.2.3', max=50),
    col('decimal', 'BudgetHours', 'Budget Hours'),
    col('currency', 'BudgetLabour', 'Budget Labour'),
    col('currency', 'BudgetMaterials', 'Budget Materials'),
    col('currency', 'BudgetOther', 'Budget Other'),
    col('currency', 'BudgetTotal', 'Budget Total', 'Labour + materials + other. Set by plugin'),
    col('decimal', 'ProgressPct', 'Progress %', **PCT),
    col('date', 'StartDate', 'Start Date'),
    col('date', 'EndDate', 'End Date'),
    col('whole', 'SortOrder', 'Sort Order', 'Position among the siblings'),
    col('decimal', 'ActualHours', 'Actual Hours', 'Approved hours. Set by plugin (Phase 3)'),
  ],
  'op365_wbsdependency': [
    col('choice', 'DependencyType', 'Dependency Type', required=True, options=['Finish-to-Start'], default=0),
    col('whole', 'LagDays', 'Lag (Days)', min=-3650, maxv=3650),
  ],
  'op365_wbsallocation': [
    col('decimal', 'Hours', 'Hours', required=True, min=0.01),
  ],
  'op365_baseline': [
    col('bool', 'IsReference', 'Is Reference', 'Baseline compared with the current plan; only one per project'),
    col('memo', 'Description', 'Description'),
  ],
  'op365_baselinenode': [
    col('text', 'Code', 'Code', max=50),
    col('decimal', 'BudgetHours', 'Budget Hours'),
    col('currency', 'BudgetTotal', 'Budget Total'),
    col('date', 'StartDate', 'Start Date'),
    col('date', 'EndDate', 'End Date'),
  ],
}

LOOKUPS = [
  ('op365_project', 'CustomerId', 'Customer', 'account', False, True),
  ('op365_project', 'ProjectManagerId', 'Project Manager', 'systemuser', False, False),
  ('op365_projectmember', 'ProjectId', 'Project', 'op365_project', True, True),
  ('op365_projectmember', 'UserId', 'User', 'systemuser', 'restrict', True),
  ('op365_wbsnode', 'ProjectId', 'Project', 'op365_project', True, True),
  ('op365_wbsnode', 'ParentId', 'Parent Node', 'op365_wbsnode', False, False),
  ('op365_wbsnode', 'OwnerResourceId', 'Owner Resource', 'op365_resource', False, False),
  ('op365_wbsdependency', 'ProjectId', 'Project', 'op365_project', True, True),
  ('op365_wbsdependency', 'PredecessorId', 'Predecessor', 'op365_wbsnode', False, True),
  ('op365_wbsdependency', 'SuccessorId', 'Successor', 'op365_wbsnode', False, True),
  ('op365_wbsallocation', 'WbsNodeId', 'WBS Node', 'op365_wbsnode', True, True),
  ('op365_wbsallocation', 'ResourceId', 'Resource', 'op365_resource', 'restrict', True),
  ('op365_baseline', 'ProjectId', 'Project', 'op365_project', True, True),
  ('op365_baselinenode', 'BaselineId', 'Baseline', 'op365_baseline', True, True),
  ('op365_baselinenode', 'WbsNodeId', 'WBS Node', 'op365_wbsnode', False, False),
]

KEYS = [
  ('op365_project', 'op365_key_project_code', 'Project Code', ['op365_code']),
  ('op365_projectmember', 'op365_key_projectmember', 'Project and User', ['op365_projectid', 'op365_userid']),
  ('op365_wbsdependency', 'op365_key_wbsdependency', 'Predecessor and Successor', ['op365_predecessorid', 'op365_successorid']),
  ('op365_wbsallocation', 'op365_key_wbsallocation', 'WBS Node and Resource', ['op365_wbsnodeid', 'op365_resourceid']),
]

# Project status reasons: Active = Offer, In Progress, Suspended; Inactive = Closed
STATUS = [(1, 0, 'In Progress'), (2, 1, 'Closed'), (365000000, 0, 'Offer'), (365000001, 0, 'Suspended')]


def project_status():
    attr = S.get(API + ent('op365_project') + "/Attributes(LogicalName='statuscode')/Microsoft.Dynamics.CRM.StatusAttributeMetadata"
                 "?$select=LogicalName&$expand=OptionSet($select=Options)").json()
    have = {o['Value']: o['Label']['UserLocalizedLabel']['Label'] for o in attr['OptionSet']['Options']}
    for value, state, label in STATUS:
        if have.get(value) == label:
            print('skip status', label); continue
        if value in have:
            ok(S.post(API + 'UpdateOptionValue', json={'EntityLogicalName': 'op365_project', 'AttributeLogicalName': 'statuscode',
                                                       'Value': value, 'Label': L(label), 'MergeLabels': True,
                                                       'SolutionUniqueName': 'OpenProject365'}), 'status ' + label)
        else:
            ok(S.post(API + 'InsertStatusValue', json={'EntityLogicalName': 'op365_project', 'AttributeLogicalName': 'statuscode',
                                                       'Value': value, 'StateCode': state, 'Label': L(label),
                                                       'SolutionUniqueName': 'OpenProject365'}), 'status ' + label)


def access_teams():
    # Access Team templates need AutoCreateAccessTeams on the table
    m = S.get(API + ent('op365_project')).json()
    if m.get('AutoCreateAccessTeams'):
        print('skip access teams flag'); return
    m['AutoCreateAccessTeams'] = True
    ok(S.put(API + ent('op365_project'), json=m, headers={'MSCRM.MergeLabels': 'true'}), 'project access teams enabled')


create_tables(TABLES)
create_columns(COLUMNS)
create_lookups(LOOKUPS)
create_keys(KEYS)
project_status()
access_teams()
publish()
