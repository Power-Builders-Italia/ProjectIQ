"""End-to-end check of the Phase 3 plugins and Custom APIs. Creates test records and deletes them at the end."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API

R = {'Prefer': 'return=representation'}
SUBMITTED, APPROVED, REJECTED = 365000000, 365000001, 365000002
failures = []


def post(es, body):
    r = S.post(API + es, json=body, headers=R)
    if r.status_code >= 300:
        raise SystemExit(f'{es}: {r.status_code} {r.text[:400]}')
    return r.json()


def get(es, id_, sel):
    return S.get(API + f'{es}({id_})?$select={sel}').json()


def action(name, body):
    return S.post(API + name, json=body)


def check(what, cond):
    print(('ok  ' if cond else 'FAIL'), what)
    if not cond:
        failures.append(what)
    return cond


me = S.get(API + 'WhoAmI').json()['UserId']
settings = S.get(API + 'op365_settingses?$select=op365_timeapprovalenabled&$top=1').json().get('value', [])
approval = not settings or settings[0].get('op365_timeapprovalenabled') is not False
acc = post('accounts', {'name': 'OP365 smoke customer', 'op365_iscustomer': True, 'op365_issupplier': True})['accountid']
res = post('op365_resources', {'op365_name': 'OP365 smoke resource', 'op365_UserId@odata.bind': f'/systemusers({me})'})['op365_resourceid']
item = post('op365_items', {'op365_code': 'SMOKE-IT', 'op365_name': 'Smoke cable', 'op365_uom': 'm', 'op365_unitcost': 2})['op365_itemid']
prj = None
try:
    post('op365_resourcecosts', {'op365_ResourceId@odata.bind': f'/op365_resources({res})', 'op365_validfrom': '2020-01-01', 'op365_hourlycost': 30})
    post('op365_resourcecosts', {'op365_ResourceId@odata.bind': f'/op365_resources({res})', 'op365_validfrom': '2026-01-01', 'op365_hourlycost': 40})
    post('op365_itemsuppliers', {'op365_ItemId@odata.bind': f'/op365_items({item})', 'op365_SupplierId@odata.bind': f'/accounts({acc})', 'op365_price': 1.5})
    r = S.get(API + f"op365_GetLabourCost(ResourceId={res},Date=2025-06-01T00:00:00Z)")
    check('GetLabourCost uses the cost valid on the date', r.ok and float(r.json().get('HourlyCost', 0)) == 30) or print(r.text[:300])

    prj = post('op365_projects', {'op365_code': 'SMOKE-003', 'op365_name': 'Smoke project F3', 'statuscode': 365000000,
                                  'op365_CustomerId@odata.bind': f'/accounts({acc})',
                                  'op365_ProjectManagerId@odata.bind': f'/systemusers({me})'})['op365_projectid']
    bind = {'op365_ProjectId@odata.bind': f'/op365_projects({prj})'}
    node = post('op365_wbsnodes', {**bind, 'op365_name': 'Task', 'op365_code': '1'})['op365_wbsnodeid']
    te = {**bind, 'op365_WbsNodeId@odata.bind': f'/op365_wbsnodes({node})', 'op365_entrydate': '2026-03-02', 'op365_hours': 8}
    r = S.post(API + 'op365_timeentries', json=te)
    check('time on an offer project rejected', r.status_code >= 400 and 'In Progress' in r.text) or print(r.text[:300])

    member = S.get(API + f'op365_projectmembers?$select=op365_projectmemberid&$filter=_op365_projectid_value eq {prj}').json()['value'][0]
    S.patch(API + f"op365_projectmembers({member['op365_projectmemberid']})", json={'op365_hourlyrate': 60})
    S.patch(API + f'op365_projects({prj})', json={'statuscode': 1})
    t1 = post('op365_timeentries', te)
    check('time entry: caller resource, cost 8x40, revenue 8x60, name',
          t1['_op365_resourceid_value'] == res and float(t1['op365_cost']) == 320 and float(t1['op365_revenue']) == 480
          and t1['op365_name'] == 'OP365 smoke resource 2026-03-02') or print(t1)
    r = S.patch(API + f"op365_timeentries({t1['op365_timeentryid']})", json={'statuscode': APPROVED})
    check('direct status change rejected', r.status_code >= 400)
    t2 = post('op365_timeentries', {**te, 'op365_hours': 2})

    ids = [t1['op365_timeentryid'], t2['op365_timeentryid']]
    r = action('op365_SubmitTimeEntries', {'TimeEntryIds': ids})
    check('submit 2 entries', r.ok and r.json().get('Count') == 2) or print(r.text[:300])
    check('status after submit', get('op365_timeentries', ids[0], 'statuscode')['statuscode'] == (SUBMITTED if approval else APPROVED))
    r = S.patch(API + f'op365_timeentries({ids[0]})', json={'op365_hours': 7})
    check('submitted entry locked', r.status_code >= 400)
    r = S.delete(API + f'op365_timeentries({ids[0]})')
    check('submitted entry cannot be deleted', r.status_code >= 400)
    if approval:
        r = action('op365_DecideTimeEntries', {'TimeEntryIds': [ids[1]], 'Approve': False})
        check('reject without note refused', r.status_code >= 400)
        r = action('op365_DecideTimeEntries', {'TimeEntryIds': [ids[1]], 'Approve': False, 'Note': 'wrong task'})
        check('reject with note', r.ok and get('op365_timeentries', ids[1], 'statuscode')['statuscode'] == REJECTED)
        r = action('op365_DecideTimeEntries', {'TimeEntryIds': [ids[0]], 'Approve': True})
        check('approve', r.ok and r.json().get('Count') == 1) or print(r.text[:300])
    n = get('op365_wbsnodes', node, 'op365_actualhours,op365_actualcost')
    check('node actuals from approved time (8 h, 320)', float(n['op365_actualhours']) == 8 and float(n['op365_actualcost']) == 320) or print(n)

    mu = post('op365_materialusages', {**bind, 'op365_WbsNodeId@odata.bind': f'/op365_wbsnodes({node})', 'op365_usagedate': '2026-03-03',
                                       'op365_ItemId@odata.bind': f'/op365_items({item})', 'op365_SupplierId@odata.bind': f'/accounts({acc})',
                                       'op365_quantity': 10})
    check('material: name/uom from item, supplier price, total 15',
          mu['op365_name'] == 'Smoke cable' and mu['op365_uom'] == 'm' and float(mu['op365_unitcost']) == 1.5
          and float(mu['op365_totalcost']) == 15) or print(mu)
    p = get('op365_projects', prj, 'op365_actualhours,op365_actualcost')
    check('project actuals (8 h, 335)', float(p['op365_actualhours']) == 8 and float(p['op365_actualcost']) == 335) or print(p)
    S.delete(API + f"op365_materialusages({mu['op365_materialusageid']})")
    check('actuals after material delete', float(get('op365_projects', prj, 'op365_actualcost')['op365_actualcost']) == 320)

    r = S.delete(API + f'op365_projects({prj})')
    check('project delete cascades approved time', r.status_code < 300) or print(r.text[:300])
    prj = None
finally:
    if prj:
        S.delete(API + f'op365_projects({prj})')
    S.delete(API + f'op365_items({item})')
    S.delete(API + f'op365_resources({res})')
    S.delete(API + f'accounts({acc})')

sys.exit(1 if failures else 0)
