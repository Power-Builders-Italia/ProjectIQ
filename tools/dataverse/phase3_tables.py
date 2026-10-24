"""Phase 3 tables: time entries and material usage, plus actual-cost columns on WBS Node and Project.

Cost, revenue and totals are plain columns set by the OpenProject365.Plugins assembly.
Idempotent; reads the PAC_* environment variables.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from meta import col, create_tables, create_columns, create_lookups, status_reasons, publish

TABLES = [
  ('TimeEntry', 'Time Entry', 'Time Entries', 'Hours of a resource on a project and WBS node', ('Name', 'Name', 200, False)),
  ('MaterialUsage', 'Material Usage', 'Material Usage', 'Material consumed by a project', ('Name', 'Description', 200, True)),
]

COLUMNS = {
  'op365_timeentry': [
    col('date', 'EntryDate', 'Date', required=True),
    col('decimal', 'Hours', 'Hours', required=True, min=0, maxv=24),
    col('memo', 'Notes', 'Notes'),
    col('datetime', 'SubmittedOn', 'Submitted On'),
    col('datetime', 'DecidedOn', 'Decided On'),
    col('memo', 'DecisionNote', 'Decision Note'),
    col('currency', 'Cost', 'Cost', 'Hours x hourly cost valid on the date. Set by plugin', secured=True),
    col('currency', 'Revenue', 'Revenue', 'Hours x hourly rate of the project member. Set by plugin'),
  ],
  'op365_materialusage': [
    col('date', 'UsageDate', 'Date', required=True),
    col('decimal', 'Quantity', 'Quantity', required=True, min=0, prec=3),
    col('text', 'Uom', 'Unit of Measure', max=20),
    col('currency', 'UnitCost', 'Unit Cost', secured=True),
    col('currency', 'TotalCost', 'Total Cost', 'Quantity x unit cost. Set by plugin', secured=True),
  ],
  'op365_wbsnode': [
    col('currency', 'ActualCost', 'Actual Cost', 'Approved hours and material usage. Set by plugin'),
  ],
  'op365_project': [
    col('decimal', 'ActualHours', 'Actual Hours', 'Approved hours. Set by plugin'),
  ],
}

LOOKUPS = [
  ('op365_timeentry', 'ProjectId', 'Project', 'op365_project', True, True),
  ('op365_timeentry', 'WbsNodeId', 'WBS Node', 'op365_wbsnode', False, False),
  ('op365_timeentry', 'ResourceId', 'Resource', 'op365_resource', 'restrict', True),
  ('op365_timeentry', 'DecidedById', 'Decided By', 'systemuser', False, False),
  ('op365_materialusage', 'ProjectId', 'Project', 'op365_project', True, True),
  ('op365_materialusage', 'WbsNodeId', 'WBS Node', 'op365_wbsnode', False, False),
  ('op365_materialusage', 'ItemId', 'Item', 'op365_item', False, False),
  ('op365_materialusage', 'SupplierId', 'Supplier', 'account', False, False),
]

# Time entry status reasons (active state): Draft, Submitted, Approved, Rejected. Only the Custom APIs change them.
STATUS = [(1, 0, 'Draft'), (365000000, 0, 'Submitted'), (365000001, 0, 'Approved'), (365000002, 0, 'Rejected')]


create_tables(TABLES)
create_columns(COLUMNS)
create_lookups(LOOKUPS)
status_reasons('op365_timeentry', STATUS)
publish()
