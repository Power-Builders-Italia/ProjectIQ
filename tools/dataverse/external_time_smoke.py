"""End-to-end checks of external resources and supplier portal time entries (plugins ResourceLink, TimeEntryValidate,
DecideTimeEntries). Writes as the supplier portal does by impersonating the site's application user ("# Portals-<site>").

Needs a supplier contact (PORTAL_CONTACT, default the first contact of a supplier that has an Active project supplier
with WBS scope on a project In Progress). Creates a resource and time entries, then removes everything it created.
Reads the PAC_* variables:  python3 tools/dataverse/external_time_smoke.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API

DRAFT, SUBMITTED, APPROVED, REJECTED = 1, 365000000, 365000001, 365000002
results = []


def check(name, cond, detail=''):
    cond = bool(cond)
    results.append(cond)
    print(('PASS' if cond else 'FAIL'), name, detail if not cond else '')


def get(url):
    r = S.get(API + url)
    r.raise_for_status()
    return r.json().get('value', r.json())


def post(es, body, headers=None):
    r = S.post(API + es, json=body, headers=dict(headers or {}, Prefer='return=representation'))
    return r


def error(r):
    try:
        return r.json()['error']['message']
    except Exception:
        return r.text[:200]


portal_user = get("systemusers?$select=systemuserid,fullname&$filter=startswith(fullname,'%23 Portals-')")
if not portal_user:
    sys.exit('no "# Portals-<site>" application user: is the supplier portal installed?')
PORTAL = {'MSCRMCallerID': portal_user[0]['systemuserid']}

# an Active project supplier with scope on a project In Progress
scopes = get("op365_projectsuppliers?$select=op365_projectsupplierid,_op365_supplierid_value,_op365_projectid_value"
             "&$filter=statecode eq 0 and statuscode eq 1 and op365_ProjectId/statuscode eq 1"
             "&$expand=op365_projectsupplier_wbsnode($select=op365_wbsnodeid,op365_name)")
scopes = [s for s in scopes if s['op365_projectsupplier_wbsnode']]
contact = None
for ps in scopes:
    flt = f"_parentcustomerid_value eq {ps['_op365_supplierid_value']} and statecode eq 0"
    if os.environ.get('PORTAL_CONTACT'):
        flt += f" and fullname eq '{os.environ['PORTAL_CONTACT']}'"
    found = get(f"contacts?$select=contactid,fullname&$filter={flt}")
    if found:
        contact, scope = found[0], ps
        break
if not contact:
    sys.exit('no supplier contact with an Active project supplier and WBS scope on a project In Progress')
supplier, project = scope['_op365_supplierid_value'], scope['_op365_projectid_value']
node = scope['op365_projectsupplier_wbsnode'][0]['op365_wbsnodeid']
scope_ids = {n['op365_wbsnodeid'] for n in scope['op365_projectsupplier_wbsnode']}
outside = [n for n in get(f"op365_wbsnodes?$select=op365_wbsnodeid&$filter=_op365_projectid_value eq {project} and statecode eq 0")
           if n['op365_wbsnodeid'] not in scope_ids]
print('contact', contact['fullname'], '| node', scope['op365_projectsupplier_wbsnode'][0]['op365_name'])
me = get('WhoAmI')['UserId']
created_resources, created_entries = [], []
try:
    # ResourceLink
    r = post('op365_resources', {'op365_name': 'Smoke external both', 'op365_UserId@odata.bind': f'/systemusers({me})',
                                 'op365_ContactId@odata.bind': f'/contacts({contact["contactid"]})'})
    check('user and contact refused', r.status_code >= 400 and 'not both' in error(r), error(r))
    old = get(f"op365_resources?$select=op365_resourceid,op365_name&$filter=_op365_contactid_value eq {contact['contactid']} and statecode eq 0")
    if old:
        res_id = old[0]['op365_resourceid']
        print('using the existing resource', old[0]['op365_name'])
        r = post('op365_resources', {'op365_name': 'Smoke external twin', 'op365_ContactId@odata.bind': f'/contacts({contact["contactid"]})'})
        check('second resource of the same contact refused', r.status_code >= 400 and 'already linked' in error(r), error(r))
    else:
        r = post('op365_resources', {'op365_name': 'Smoke external ' + contact['fullname'],
                                     'op365_ContactId@odata.bind': f'/contacts({contact["contactid"]})'})
        check('external resource created', r.status_code < 300, error(r))
        res_id = r.json()['op365_resourceid']
        created_resources.append(res_id)
    res = get(f"op365_resources({res_id})?$select=_op365_supplierid_value")
    check('supplier filled from the contact', res['_op365_supplierid_value'] == supplier, res)

    # portal entries
    entry = {'op365_entrydate': '2026-11-02', 'op365_hours': 4,
             'op365_ResourceId@odata.bind': f'/op365_resources({res_id})', 'op365_WbsNodeId@odata.bind': f'/op365_wbsnodes({node})'}
    r = post('op365_timeentries', entry, PORTAL)
    check('portal entry on a scope node', r.status_code < 300, error(r))
    if r.status_code < 300:
        e = r.json()
        created_entries.append(e['op365_timeentryid'])
        check('project filled from the node', e['_op365_projectid_value'] == project, e['_op365_projectid_value'])
        check('entry is Draft', e['statuscode'] == DRAFT, e['statuscode'])
        eid = e['op365_timeentryid']
        r = S.patch(API + f'op365_timeentries({eid})', json={'statuscode': APPROVED}, headers=PORTAL)
        check('portal cannot approve', r.status_code >= 400 and 'only be submitted' in error(r), error(r))
        r = S.patch(API + f'op365_timeentries({eid})', json={'op365_hours': 5}, headers=PORTAL)
        check('portal changes a draft', r.status_code < 300, error(r))
        r = S.patch(API + f'op365_timeentries({eid})', json={'statuscode': SUBMITTED}, headers=PORTAL)
        check('portal submits', r.status_code < 300, error(r))
        e = get(f'op365_timeentries({eid})?$select=statuscode,op365_submittedon,op365_hours')
        check('entry Submitted (or Approved when approval is off)', e['statuscode'] in (SUBMITTED, APPROVED) and e['op365_submittedon'], e)
        r = S.patch(API + f'op365_timeentries({eid})', json={'op365_hours': 6}, headers=PORTAL)
        check('submitted entry locked', r.status_code >= 400, error(r))
        if e['statuscode'] == SUBMITTED:
            r = S.post(API + 'op365_DecideTimeEntries', json={'TimeEntryIds': [eid], 'Approve': False, 'Note': 'Smoke: wrong day'})
            check('reject (e-mail to the contact when the queue is set)', r.status_code < 300, error(r))
            r = S.patch(API + f'op365_timeentries({eid})', json={'op365_hours': 3}, headers=PORTAL)
            check('portal corrects a rejected entry', r.status_code < 300, error(r))
            r = S.patch(API + f'op365_timeentries({eid})', json={'statuscode': SUBMITTED}, headers=PORTAL)
            check('portal submits again', r.status_code < 300, error(r))
            e = get(f'op365_timeentries({eid})?$select=statuscode,op365_decisionnote')
            check('resubmitted, note cleared', e['statuscode'] == SUBMITTED and not e['op365_decisionnote'], e)
            r = S.post(API + 'op365_DecideTimeEntries', json={'TimeEntryIds': [eid], 'Approve': False, 'Note': 'Smoke cleanup'})
    if outside:
        r = post('op365_timeentries', dict(entry, **{'op365_WbsNodeId@odata.bind': f"/op365_wbsnodes({outside[0]['op365_wbsnodeid']})"}), PORTAL)
        check('node outside the scope refused', r.status_code >= 400 and 'assigned to your company' in error(r), error(r))
        if r.status_code < 300: created_entries.append(r.json()['op365_timeentryid'])
    internal = get(f"op365_resources?$select=op365_resourceid&$filter=_op365_userid_value ne null and statecode eq 0&$top=1")
    if internal:
        r = post('op365_timeentries', dict(entry, **{'op365_ResourceId@odata.bind': f"/op365_resources({internal[0]['op365_resourceid']})"}), PORTAL)
        check('internal resource refused on the portal', r.status_code >= 400 and 'external resource' in error(r), error(r))
        if r.status_code < 300: created_entries.append(r.json()['op365_timeentryid'])
finally:
    for eid in created_entries:
        S.delete(API + f'op365_timeentries({eid})')
    for rid in created_resources:
        S.delete(API + f'op365_resources({rid})')
print(f'{sum(results)}/{len(results)} passed')
sys.exit(0 if all(results) else 1)
