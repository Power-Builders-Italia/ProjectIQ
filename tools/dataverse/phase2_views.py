"""Phase 2 system views: spec views 1-5, 7, 8, 22, 23, Quick Find Project, Account customer columns.

Idempotent: views are matched by table + name; default views are updated in place.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from viewlib import view

# ---------- Project (spec 1-5) ----------
PRJ = [('op365_code', 110), ('op365_name', 220), ('op365_customerid', 180), ('op365_projectmanagerid', 150),
       ('statuscode', 110), ('op365_startdate', 100), ('op365_enddate', 100), ('op365_contractvalue', 120),
       ('op365_budgettotal', 120), ('op365_progresspct', 90)]
CODE = [('op365_code', False)]
view('op365_project', 'All Projects', PRJ, CODE, default=True, replace='Active Projects')
view('op365_project', 'In Progress Projects', PRJ, CODE, [('statuscode', 'eq', '1')])
view('op365_project', 'Offers', PRJ, CODE, [('statuscode', 'eq', '365000000')])
view('op365_project', 'Suspended Projects', PRJ, CODE, [('statuscode', 'eq', '365000001')])
view('op365_project', 'Closed Projects', PRJ, [('op365_enddate', True)], [('statuscode', 'eq', '2')], active=False)
view('op365_project', 'Quick Find Active Projects', PRJ, CODE, querytype=4, default=True,
     quickfind=['op365_code', 'op365_name', 'op365_customerid'])

# ---------- Account customers (spec 6-8: projects and contract value now available) ----------
CUST = [('name', 250), ('op365_customertype', 120), ('op365_vatnumber', 130), ('primarycontactid', 180),
        ('op365_projectcount', 90), ('op365_contractvaluetotal', 140)]
NAME = [('name', False)]
view('account', 'All Customers', CUST, NAME, [('op365_iscustomer', 'eq', '1')], default=True)
view('account', 'Customers with Projects', CUST, NAME, [('op365_iscustomer', 'eq', '1'), ('op365_projectcount', 'gt', '0')])
# projectcount is empty until the customer's first project
view('account', 'Customers without Projects', CUST, NAME, [('op365_projectcount', 'eq', '0'), ('op365_projectcount', 'null', None)],
     filter_type='or', also=[('op365_iscustomer', 'eq', '1')])
view('account', 'Prospects', CUST, NAME, [('op365_customertype', 'eq', '365000000')])

# ---------- Project children (spec 22, 23) ----------
view('op365_wbsnode', 'WBS Nodes by Project',
     [('op365_code', 90), ('op365_name', 220), ('op365_ownerresourceid', 150), ('op365_actualhours', 100),
      ('op365_budgethours', 100), ('op365_budgettotal', 120), ('op365_progresspct', 90),
      ('op365_startdate', 100), ('op365_enddate', 100)],
     [('op365_sortorder', False), ('op365_code', False)], default=True, replace='Active WBS Nodes')
view('op365_projectmember', 'Project Members',
     [('op365_userid', 200), ('op365_projectrole', 130), ('op365_hourlyrate', 110), ('op365_projectid', 200)],
     [('op365_userid', False)], default=True, replace='Active Project Members')
view('op365_wbsdependency', 'WBS Dependencies',
     [('op365_predecessorid', 200), ('op365_successorid', 200), ('op365_dependencytype', 130), ('op365_lagdays', 90)],
     [('op365_predecessorid', False)], default=True, replace='Active WBS Dependencies')
view('op365_wbsallocation', 'WBS Allocations',
     [('op365_resourceid', 200), ('op365_wbsnodeid', 200), ('op365_hours', 90)],
     [('op365_resourceid', False)], default=True, replace='Active WBS Allocations')
view('op365_baseline', 'Baselines',
     [('op365_name', 220), ('op365_isreference', 100), ('createdon', 130), ('createdby', 150)],
     [('createdon', True)], default=True, replace='Active Baselines')
