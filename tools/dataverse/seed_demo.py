"""Demo data for Open Project 365: customers, suppliers, items, resources, three projects with WBS, dependencies,
allocations, a baseline, time entries in every status and material usage.

Records are recognisable by the DEMO- codes and the "(demo)" suffix. Running again deletes the previous demo data
first; `--clean` only deletes it. Uses the PAC_* environment variables. The project manager and the first resource
are linked to the first interactive user (or DEMO_USER_EMAIL), so that user sees the timesheet and the approvals.
"""
import datetime as dt, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API

R = {'Prefer': 'return=representation'}
TODAY = dt.date.today()
MONDAY = TODAY - dt.timedelta(days=TODAY.weekday())
D = lambda days: (TODAY + dt.timedelta(days=days)).isoformat()


def get(q):
    return S.get(API + q).json().get('value', [])


def post(es, body):
    r = S.post(API + es, json=body, headers=R)
    if r.status_code >= 300:
        raise SystemExit(f'{es}: {r.status_code} {r.text[:400]}')
    return r.json()


def action(name, body):
    r = S.post(API + name, json=body)
    if r.status_code >= 300:
        raise SystemExit(f'{name}: {r.status_code} {r.text[:400]}')
    return r.json() if r.text else {}


def clean():
    for p in get("op365_projects?$select=op365_projectid&$filter=startswith(op365_code,'DEMO-')"):
        S.delete(API + f"op365_projects({p['op365_projectid']})")
    for i in get("op365_items?$select=op365_itemid&$filter=startswith(op365_code,'DEMO-')"):
        S.delete(API + f"op365_items({i['op365_itemid']})")
    for a in get("op365_absences?$select=op365_absenceid&$filter=endswith(op365_name,'(demo)')"):
        S.delete(API + f"op365_absences({a['op365_absenceid']})")
    for r in get("op365_resources?$select=op365_resourceid&$filter=endswith(op365_name,'(demo)')"):
        S.delete(API + f"op365_resources({r['op365_resourceid']})")
    for a in get("accounts?$select=accountid&$filter=endswith(name,'(demo)')"):
        S.delete(API + f"accounts({a['accountid']})")
    print('demo data deleted')


clean()
if '--clean' in sys.argv:
    sys.exit(0)

email = os.environ.get('DEMO_USER_EMAIL')
users = get("systemusers?$select=systemuserid,fullname&$filter=isdisabled eq false and accessmode eq 0 and applicationid eq null"
            + (f" and internalemailaddress eq '{email}'" if email else ''))
user = users[0] if users else None
me = user['systemuserid'] if user else S.get(API + 'WhoAmI').json()['UserId']
print('demo user:', user['fullname'] if user else 'application user')

# ---------- accounts ----------
acc = {}
for name, cust, supp, vat in [('Rossi Costruzioni (demo)', True, False, 'IT01234560011'),
                              ('Bianchi Energia (demo)', True, False, 'IT02345670022'),
                              ('Verdi Logistica (demo)', True, False, 'IT03456780033'),
                              ('Elettroforniture Nord (demo)', False, True, 'IT04567890044'),
                              ('Solare Italia Distribuzione (demo)', False, True, 'IT05678900055')]:
    body = {'name': name, 'op365_iscustomer': cust, 'op365_issupplier': supp, 'op365_vatnumber': vat}
    if cust:
        body['op365_customertype'] = 365000001
    if supp:
        body['op365_supplierstatus'] = 365000000
    acc[name.split()[0]] = post('accounts', body)['accountid']

# ---------- items ----------
items = {}
for code, name, uom, cost, supplier, price in [
        ('DEMO-CAV-01', 'Cavo FG16OR16 3G2.5', 'm', 1.20, 'Elettroforniture', 1.05),
        ('DEMO-QE-01', 'Quadro elettrico 24 moduli', 'pz', 180.00, 'Elettroforniture', 165.00),
        ('DEMO-PAN-01', 'Modulo fotovoltaico 430 W', 'pz', 135.00, 'Solare', 128.00),
        ('DEMO-INV-01', 'Inverter ibrido 6 kW', 'pz', 1450.00, 'Solare', 1390.00),
        ('DEMO-CTR-01', 'Cartongesso 12.5 mm', 'm2', 6.80, None, None)]:
    i = post('op365_items', {'op365_code': code, 'op365_name': name, 'op365_uom': uom, 'op365_unitcost': cost})['op365_itemid']
    items[code] = (i, acc.get(supplier))
    if supplier:
        post('op365_itemsuppliers', {'op365_ItemId@odata.bind': f'/op365_items({i})',
                                     'op365_SupplierId@odata.bind': f"/accounts({acc[supplier]})", 'op365_price': price,
                                     'op365_leadtimedays': 5})

# ---------- resources ----------
res = {}
mine = get(f"op365_resources?$select=op365_resourceid,op365_name&$filter=_op365_userid_value eq {me}") if user else []
if mine:
    res['pm'] = mine[0]['op365_resourceid']
    print('using resource', mine[0]['op365_name'])
for key, name, role, cost, hours in [('pm', 'Project Manager (demo)', 'Project manager', 55, 40),
                                     ('ele', 'Luca Bassi (demo)', 'Electrician', 32, 40),
                                     ('ele2', 'Sara Conti (demo)', 'Electrician', 30, 40),
                                     ('mur', 'Paolo Neri (demo)', 'Mason', 28, 40),
                                     ('tec', 'Giulia Riva (demo)', 'Technician', 35, 24)]:
    if key in res:
        continue
    body = {'op365_name': name, 'op365_role': role, 'op365_weeklyhours': hours}
    if key == 'pm' and user:
        body['op365_UserId@odata.bind'] = f'/systemusers({me})'
    if hours == 24:
        body['op365_workingdays'] = '365000000,365000002,365000004'
    r = post('op365_resources', body)['op365_resourceid']
    res[key] = r
    post('op365_resourcecosts', {'op365_ResourceId@odata.bind': f'/op365_resources({r})', 'op365_validfrom': '2026-01-01',
                                 'op365_hourlycost': cost})
# make sure the user's own resource has a cost too
if mine and not get(f"op365_resourcecosts?$select=op365_resourcecostid&$filter=_op365_resourceid_value eq {res['pm']}"):
    post('op365_resourcecosts', {'op365_ResourceId@odata.bind': f"/op365_resources({res['pm']})", 'op365_validfrom': '2026-01-01',
                                 'op365_hourlycost': 55})
post('op365_absences', {'op365_name': 'Ferie Luca (demo)', 'op365_absencetype': 365000000, 'op365_fromdate': D(14), 'op365_todate': D(18),
                        'op365_ResourceId@odata.bind': f"/op365_resources({res['ele']})"})
post('op365_absences', {'op365_name': 'Chiusura Immacolata (demo)', 'op365_absencetype': 365000003, 'op365_fromdate': '2026-12-08',
                        'op365_todate': '2026-12-08'})


# ---------- projects ----------
def project(code, name, customer, start, end, value, status):
    return post('op365_projects', {'op365_code': code, 'op365_name': name, 'op365_contractvalue': value,
                                   'op365_startdate': start, 'op365_enddate': end, 'statuscode': 365000000,
                                   'op365_CustomerId@odata.bind': f'/accounts({customer})',
                                   'op365_ProjectManagerId@odata.bind': f'/systemusers({me})',
                                   'op365_description': f'{name} - demo data'})['op365_projectid'], status


def wbs(prj, nodes):
    """nodes: (code, name, parent code, start offset, end offset, hours, labour, materials, progress, resources)."""
    ids = {}
    for i, (code, name, parent, s, e, hours, labour, mat, prog, people) in enumerate(nodes):
        body = {'op365_ProjectId@odata.bind': f'/op365_projects({prj})', 'op365_code': code, 'op365_name': name,
                'op365_sortorder': i}
        if parent:
            body['op365_ParentId@odata.bind'] = f'/op365_wbsnodes({ids[parent]})'
        if s is not None:
            body.update({'op365_startdate': D(s), 'op365_enddate': D(e), 'op365_budgethours': hours,
                         'op365_budgetlabour': labour, 'op365_budgetmaterials': mat, 'op365_progresspct': prog})
        ids[code] = post('op365_wbsnodes', body)['op365_wbsnodeid']
        for who in people:
            post('op365_wbsallocations', {'op365_WbsNodeId@odata.bind': f'/op365_wbsnodes({ids[code]})',
                                          'op365_ResourceId@odata.bind': f'/op365_resources({res[who]})',
                                          'op365_hours': round(hours / len(people))})
    return ids


def link(ids, pred, succ):
    post('op365_wbsdependencies', {'op365_PredecessorId@odata.bind': f'/op365_wbsnodes({ids[pred]})',
                                   'op365_SuccessorId@odata.bind': f'/op365_wbsnodes({ids[succ]})'})


pa, sa = project('DEMO-001', 'Ristrutturazione uffici Rossi', acc['Rossi'], D(-45), D(60), 85000, 1)
na = wbs(pa, [
    ('1', 'Demolizioni e opere edili', None, None, None, 0, 0, 0, 0, []),
    ('1.1', 'Demolizioni', '1', -45, -30, 120, 3400, 600, 100, ['mur']),
    ('1.2', 'Pareti in cartongesso', '1', -29, -5, 200, 5600, 4200, 80, ['mur']),
    ('2', 'Impianto elettrico', None, None, None, 0, 0, 0, 0, []),
    ('2.1', 'Tracce e canalizzazioni', '2', -20, 5, 160, 5100, 2500, 60, ['ele', 'ele2']),
    ('2.2', 'Quadri e cablaggi', '2', 6, 35, 220, 7000, 6800, 0, ['ele', 'ele2']),
    ('3', 'Collaudo e consegna', None, 36, 60, 60, 2400, 0, 0, ['tec', 'pm']),
])
link(na, '1.1', '1.2'); link(na, '1.2', '2.2'); link(na, '2.1', '2.2'); link(na, '2.2', '3')

pb, sb = project('DEMO-002', 'Impianto fotovoltaico Bianchi', acc['Bianchi'], D(-14), D(110), 62000, 1)
nb = wbs(pb, [
    ('1', 'Progettazione e pratiche', None, -14, 10, 80, 3200, 0, 70, ['tec', 'pm']),
    ('2', 'Fornitura e installazione', None, None, None, 0, 0, 0, 0, []),
    ('2.1', 'Strutture e moduli', '2', 11, 50, 240, 7600, 26000, 0, ['ele', 'mur']),
    ('2.2', 'Inverter e collegamenti', '2', 51, 80, 120, 4000, 9000, 0, ['ele2']),
    ('3', 'Allaccio e collaudo', None, 81, 110, 40, 1600, 0, 0, ['tec']),
])
link(nb, '1', '2.1'); link(nb, '2.1', '2.2'); link(nb, '2.2', '3')

pc, sc = project('DEMO-003', 'Cablaggio magazzino Verdi', acc['Verdi'], D(70), D(150), 38000, 365000000)
wbs(pc, [('1', 'Cablaggio strutturato', None, 70, 130, 300, 9500, 7000, 0, ['ele2']),
         ('2', 'Certificazione', None, 131, 150, 40, 1400, 0, 0, ['tec'])])

for prj, status in [(pa, sa), (pb, sb)]:
    S.patch(API + f'op365_projects({prj})', json={'statuscode': status})
action(f'op365_projects({pa})/Microsoft.Dynamics.CRM.op365_SaveBaseline', {'Name': 'Contratto'})
# the plan slipped a little after the contract baseline
S.patch(API + f"op365_wbsnodes({na['2.2']})", json={'op365_startdate': D(9), 'op365_enddate': D(40)})

# ---------- time entries: approved weeks, a rejected day, last week submitted, this week draft ----------
plan = [(pa, na['1.2'], 'mur', 8), (pa, na['2.1'], 'ele', 7), (pa, na['2.1'], 'ele2', 6), (pb, nb['1'], 'tec', 4),
        (pb, nb['1'], 'pm', 3), (pa, None, 'pm', 2)]
weeks = {}
for back in range(4, -1, -1):
    week = MONDAY - dt.timedelta(weeks=back)
    for prj, node, who, hours in plan:
        for d in range(5):
            day = week + dt.timedelta(days=d)
            if day > TODAY or (who == 'tec' and d in (1, 3)):
                continue
            body = {'op365_ProjectId@odata.bind': f'/op365_projects({prj})', 'op365_entrydate': day.isoformat(),
                    'op365_hours': hours, 'op365_ResourceId@odata.bind': f'/op365_resources({res[who]})'}
            if node:
                body['op365_WbsNodeId@odata.bind'] = f'/op365_wbsnodes({node})'
            if who == 'pm' and user:
                body['ownerid@odata.bind'] = f'/systemusers({me})'
            weeks.setdefault(back, []).append(post('op365_timeentries', body)['op365_timeentryid'])

older = [i for b in (4, 3, 2) for i in weeks.get(b, [])]
if older:
    action('op365_SubmitTimeEntries', {'TimeEntryIds': older})
    action('op365_DecideTimeEntries', {'TimeEntryIds': older[1:], 'Approve': True})
    action('op365_DecideTimeEntries', {'TimeEntryIds': older[:1], 'Approve': False, 'Note': 'Ore sul nodo sbagliato, correggi (demo)'})
if weeks.get(1):
    action('op365_SubmitTimeEntries', {'TimeEntryIds': weeks[1]})

# ---------- material usage ----------
for prj, node, code, qty, days in [(pa, na['1.2'], 'DEMO-CTR-01', 320, -20), (pa, na['2.1'], 'DEMO-CAV-01', 850, -10),
                                   (pa, na['2.1'], 'DEMO-QE-01', 2, -3), (pb, nb['1'], 'DEMO-PAN-01', 4, -2)]:
    item, supplier = items[code]
    body = {'op365_ProjectId@odata.bind': f'/op365_projects({prj})', 'op365_WbsNodeId@odata.bind': f'/op365_wbsnodes({node})',
            'op365_ItemId@odata.bind': f'/op365_items({item})', 'op365_quantity': qty, 'op365_usagedate': D(days)}
    if supplier:
        body['op365_SupplierId@odata.bind'] = f'/accounts({supplier})'
    post('op365_materialusages', body)

for prj in (pa, pb, pc):
    p = S.get(API + f'op365_projects({prj})?$select=op365_code,op365_budgettotal,op365_actualcost,op365_actualhours,op365_progresspct').json()
    print(p['op365_code'], 'budget', p['op365_budgettotal'], 'actual', p['op365_actualcost'], 'hours', p['op365_actualhours'],
          'progress', p['op365_progresspct'])
print('time entries:', sum(len(v) for v in weeks.values()))
