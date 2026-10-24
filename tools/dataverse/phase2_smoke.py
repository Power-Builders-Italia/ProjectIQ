"""End-to-end check of the Phase 2 plugins in an environment. Creates test records and deletes them at the end."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API

R = {'Prefer': 'return=representation'}
failures = []


def post(es, body):
    r = S.post(API + es, json=body, headers=R)
    if r.status_code >= 300:
        raise SystemExit(f'{es}: {r.status_code} {r.text[:400]}')
    return r.json()


def get(es, id_, sel):
    return S.get(API + f'{es}({id_})?$select={sel}').json()


def check(what, cond):
    """Returns True when the check passes."""
    print(('ok  ' if cond else 'FAIL'), what)
    if not cond:
        failures.append(what)
    return cond


me = S.get(API + 'WhoAmI').json()['UserId']
acc = post('accounts', {'name': 'OP365 smoke customer', 'op365_iscustomer': True})['accountid']
res = post('op365_resources', {'op365_name': 'OP365 smoke resource'})
try:
    check('resource weekly hours default 40', float(res['op365_weeklyhours']) == 40)
    post('op365_resourcecosts', {'op365_ResourceId@odata.bind': f"/op365_resources({res['op365_resourceid']})",
                                 'op365_validfrom': '2020-01-01', 'op365_hourlycost': 35})
    check('resource hourly cost synced', float(get('op365_resources', res['op365_resourceid'], 'op365_hourlycost')['op365_hourlycost']) == 35)

    prj = post('op365_projects', {'op365_code': 'SMOKE-001', 'op365_name': 'Smoke project', 'op365_contractvalue': 1000,
                                  'op365_CustomerId@odata.bind': f'/accounts({acc})',
                                  'op365_ProjectManagerId@odata.bind': f'/systemusers({me})'})['op365_projectid']
    a = get('accounts', acc, 'op365_projectcount,op365_contractvaluetotal')
    check('account project count / contract value', a['op365_projectcount'] == 1 and float(a['op365_contractvaluetotal']) == 1000)
    members = S.get(API + f'op365_projectmembers?$select=op365_projectrole,op365_name&$filter=_op365_projectid_value eq {prj}').json()['value']
    check('project manager added as Manager member', len(members) == 1 and members[0]['op365_projectrole'] == 365000000)

    bind = {'op365_ProjectId@odata.bind': f'/op365_projects({prj})'}
    n1 = post('op365_wbsnodes', {**bind, 'op365_name': 'Phase 1', 'op365_code': '1'})['op365_wbsnodeid']
    n2 = post('op365_wbsnodes', {**bind, 'op365_name': 'Task A', 'op365_code': '1.1', 'op365_ParentId@odata.bind': f'/op365_wbsnodes({n1})',
                                 'op365_budgetlabour': 300, 'op365_budgetmaterials': 100, 'op365_progresspct': 50})
    check('node budget total = labour + materials + other', float(n2['op365_budgettotal']) == 400)
    n3 = post('op365_wbsnodes', {**bind, 'op365_name': 'Task B', 'op365_code': '1.2', 'op365_ParentId@odata.bind': f'/op365_wbsnodes({n1})',
                                 'op365_budgetother': 400})['op365_wbsnodeid']
    p = get('op365_projects', prj, 'op365_budgettotal,op365_progresspct')
    check('project budget total and progress', float(p['op365_budgettotal']) == 800 and float(p['op365_progresspct']) == 25)

    d = post('op365_wbsdependencies', {'op365_PredecessorId@odata.bind': f"/op365_wbsnodes({n2['op365_wbsnodeid']})",
                                        'op365_SuccessorId@odata.bind': f'/op365_wbsnodes({n3})'})
    check('dependency gets project and name', d['_op365_projectid_value'] == prj and '→' in d['op365_name'])
    r = S.post(API + 'op365_wbsdependencies', json={'op365_PredecessorId@odata.bind': f'/op365_wbsnodes({n3})',
                                                     'op365_SuccessorId@odata.bind': f"/op365_wbsnodes({n2['op365_wbsnodeid']})"})
    check('cycle rejected', r.status_code >= 400 and 'cycle' in r.text)

    b1 = S.post(API + f'op365_projects({prj})/Microsoft.Dynamics.CRM.op365_SaveBaseline', json={'Name': 'B1'}).json()
    b2 = S.post(API + f'op365_projects({prj})/Microsoft.Dynamics.CRM.op365_SaveBaseline', json={}).json()
    nodes = S.get(API + f"op365_baselinenodes?$select=op365_name&$filter=_op365_baselineid_value eq {b1.get('BaselineId')}").json()['value']
    check('SaveBaseline copies the 3 nodes', len(nodes) == 3)
    refs = S.get(API + f'op365_baselines?$select=op365_name&$filter=_op365_projectid_value eq {prj} and op365_isreference eq true').json()['value']
    check('only the latest baseline is reference', len(refs) == 1 and refs[0]['op365_baselineid'] == b2.get('BaselineId'))

    r = S.delete(API + f'op365_wbsnodes({n1})')
    left = S.get(API + f'op365_wbsnodes?$select=op365_name&$filter=_op365_projectid_value eq {prj}').json()['value']
    check('deleting a node deletes its subtree', r.status_code < 300 and not left) or print(r.status_code, r.text[:300], left)
    check('project totals after delete', float(get('op365_projects', prj, 'op365_budgettotal')['op365_budgettotal']) == 0)

    r = S.delete(API + f'op365_projects({prj})')
    check('project delete', r.status_code < 300)
    check('account count back to 0', get('accounts', acc, 'op365_projectcount')['op365_projectcount'] == 0)
finally:
    S.delete(API + f'accounts({acc})')
    S.delete(API + f"op365_resources({res['op365_resourceid']})")

sys.exit(1 if failures else 0)
