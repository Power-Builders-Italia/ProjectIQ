"""Phase 3 system views: time entries (spec 19-21), material usage (17-18), actual columns on WBS nodes (22).

Idempotent: views are matched by table + name; default views are updated in place.
Views are read back in their published state, so run app.py (publish) afterwards.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from viewlib import view

# ---------- Time entries ----------
TE = [('op365_entrydate', 100), ('op365_resourceid', 160), ('op365_projectid', 200), ('op365_wbsnodeid', 180),
      ('op365_hours', 70), ('statuscode', 100), ('op365_notes', 220)]
NEWEST = [('op365_entrydate', True)]
view('op365_timeentry', 'All Time Entries', TE + [('op365_cost', 100)], NEWEST, default=True, replace='Active Time Entries')
view('op365_timeentry', 'My Time Entries', TE, NEWEST, [('ownerid', 'eq-userid', None)], querytype=8192)
view('op365_timeentry', 'Time Entries to Approve', TE + [('op365_submittedon', 130)], [('op365_submittedon', False)],
     [('statuscode', 'eq', '365000000')])
view('op365_timeentry', 'Time Entries by Project',
     [('op365_entrydate', 100), ('op365_resourceid', 160), ('op365_wbsnodeid', 180), ('op365_hours', 70),
      ('op365_cost', 100), ('op365_revenue', 100), ('statuscode', 100)], NEWEST)
view('op365_timeentry', 'Quick Find Active Time Entries', TE, NEWEST, querytype=4, default=True,
     quickfind=['op365_name', 'op365_notes'])

# ---------- Material usage ----------
MU = [('op365_usagedate', 100), ('op365_name', 200), ('op365_projectid', 200), ('op365_wbsnodeid', 160),
      ('op365_quantity', 80), ('op365_uom', 60), ('op365_unitcost', 90), ('op365_totalcost', 100), ('op365_supplierid', 160)]
view('op365_materialusage', 'All Material Usage', MU, [('op365_usagedate', True)], default=True,
     replace='Active Material Usage')
view('op365_materialusage', 'Material Usage by Project', [c for c in MU if c[0] != 'op365_projectid'], [('op365_usagedate', True)])
view('op365_materialusage', 'Quick Find Active Material Usage', MU, [('op365_usagedate', True)], querytype=4, default=True,
     quickfind=['op365_name'])

# ---------- WBS nodes (spec 22): actuals next to budget ----------
view('op365_wbsnode', 'WBS Nodes by Project',
     [('op365_code', 90), ('op365_name', 220), ('op365_ownerresourceid', 150), ('op365_budgethours', 90),
      ('op365_actualhours', 90), ('op365_budgettotal', 110), ('op365_actualcost', 110), ('op365_progresspct', 90),
      ('op365_startdate', 100), ('op365_enddate', 100)],
     [('op365_sortorder', False), ('op365_code', False)], default=True)

# ---------- Projects: actual cost ----------
PRJ = [('op365_code', 110), ('op365_name', 220), ('op365_customerid', 180), ('op365_projectmanagerid', 150),
       ('statuscode', 110), ('op365_enddate', 100), ('op365_contractvalue', 120), ('op365_budgettotal', 120),
       ('op365_actualcost', 120), ('op365_progresspct', 90)]
view('op365_project', 'In Progress Projects', PRJ, [('op365_code', False)], [('statuscode', 'eq', '1')])
