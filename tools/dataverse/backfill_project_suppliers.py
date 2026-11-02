"""Project suppliers of the orders and RFQ invitations that existed before the table (one-off, idempotent).

The plugins create the rows from now on. This script does the same for the existing data:
- every Sent, Confirmed or Received purchase order: Active project supplier of its project, WBS nodes of its lines added
  to the scope (the plugin ProjectSupplierScope adds their descendants);
- every RFQ invitation in status Invited: Invited project supplier of the project of the RFQ (when not there yet).
Cancelled and draft orders are ignored. Reads the PAC_* variables of the target environment; --dry-run only prints.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API

DRY = '--dry-run' in sys.argv
T, NN = 'op365_projectsupplier', 'op365_projectsupplier_wbsnode'
ACTIVE, INVITED = 1, 365000000
PO_SENT, PO_CONFIRMED, PO_RECEIVED = 365000000, 365000001, 365000002
INVITATION_INVITED = 365000000


def get(path):
    rows, url = [], API + path
    while url:
        r = S.get(url, headers={'Prefer': 'odata.maxpagesize=5000'}).json()
        rows += r['value']
        url = r.get('@odata.nextLink')
    return rows


def check(r, what):
    if r.status_code >= 300:
        sys.exit(f'{what}: {r.status_code} {r.text[:300]}')
    return r


rows = {(r['_op365_projectid_value'], r['_op365_supplierid_value']): r for r in get(
    f'{T}s?$select=statecode,statuscode,_op365_projectid_value,_op365_supplierid_value')}
scope = {}
for link in get(f'{NN}set?$select=op365_projectsupplierid,op365_wbsnodeid'):
    scope.setdefault(link['op365_projectsupplierid'], set()).add(link['op365_wbsnodeid'])


def ensure(project, supplier, active):
    """Id of the project supplier row (None in dry run when it would be created)."""
    row = rows.get((project, supplier))
    if row is None:
        print('create' if not DRY else 'would create', 'Active' if active else 'Invited', project, supplier)
        if DRY:
            rows[(project, supplier)] = {f'{T}id': None, 'statuscode': ACTIVE if active else INVITED}
            return None
        r = check(S.post(API + f'{T}s', headers={'Prefer': 'return=representation'}, json={
            'op365_ProjectId@odata.bind': f'/op365_projects({project})', 'op365_SupplierId@odata.bind': f'/accounts({supplier})',
            'statuscode': ACTIVE if active else INVITED}), 'create project supplier')
        row = rows[(project, supplier)] = r.json()
    elif active and row['statuscode'] != ACTIVE:
        print('activate' if not DRY else 'would activate', row[f'{T}id'])
        if not DRY:
            check(S.patch(API + f"{T}s({row[f'{T}id']})", json={'statecode': 0, 'statuscode': ACTIVE}), 'activate')
        row['statuscode'] = ACTIVE
    return row[f'{T}id']


orders = get('op365_purchaseorders?$select=op365_number,_op365_projectid_value,_op365_supplierid_value'
             f'&$filter=statuscode eq {PO_SENT} or statuscode eq {PO_CONFIRMED} or statuscode eq {PO_RECEIVED}')
lines = {}
for l in get('op365_purchaseorderlines?$select=_op365_purchaseorderid_value,_op365_wbsnodeid_value'
             '&$filter=statecode eq 0 and _op365_wbsnodeid_value ne null'):
    lines.setdefault(l['_op365_purchaseorderid_value'], set()).add(l['_op365_wbsnodeid_value'])
added = 0
for po in orders:
    project, supplier = po['_op365_projectid_value'], po['_op365_supplierid_value']
    if not project or not supplier:
        continue
    row = ensure(project, supplier, True)
    missing = lines.get(po['op365_purchaseorderid'], set()) - scope.get(row, set())
    for node in sorted(missing):
        print(' scope' if not DRY else ' would scope', po.get('op365_number'), node)
        if not DRY:
            check(S.post(API + f'{T}s({row})/{NN}/$ref', json={'@odata.id': API + f'op365_wbsnodes({node})'}), 'associate')
        scope.setdefault(row, set()).add(node)
        added += 1

invitations = get('op365_rfqinvitations?$select=_op365_supplierid_value,_op365_rfqid_value'
                  f'&$filter=statuscode eq {INVITATION_INVITED}')
rfqs = {r['op365_rfqid']: r['_op365_projectid_value'] for r in get('op365_rfqs?$select=_op365_projectid_value')}
for inv in invitations:
    project = rfqs.get(inv['_op365_rfqid_value'])
    if project and inv['_op365_supplierid_value'] and (project, inv['_op365_supplierid_value']) not in rows:
        ensure(project, inv['_op365_supplierid_value'], False)

print(f'{len(orders)} orders, {len(invitations)} open invitations, {len(rows)} project suppliers, {added} scope nodes',
      'would be added' if DRY else 'added')
