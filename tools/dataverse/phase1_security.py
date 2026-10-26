"""Phase 1 security: OP365 Administrator / OP365 User roles and the OP365 Cost Visibility profile.

OP365 roles are additive: every internal user also gets the standard Basic User role.
Idempotent; reads the PAC_* environment variables.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API

ALL = ['Create', 'Read', 'Write', 'Delete', 'Append', 'AppendTo', 'Assign', 'Share']
F1_TABLES = ['op365_item', 'op365_itemsupplier', 'op365_supplierdocument', 'op365_resource',
             'op365_resourcecost', 'op365_absence']
MASTER = ['account', 'contact']

ROLES = {
    'OP365 Administrator': {t: (ALL, 'Global') for t in F1_TABLES + MASTER},
    'OP365 User': {t: (['Read', 'AppendTo'], 'Global') for t in F1_TABLES + MASTER},
}

# columns readable/editable only by holders of the profile (admins and project managers)
COST_COLUMNS = [('op365_resource', 'op365_hourlycost'), ('op365_resourcecost', 'op365_hourlycost')]


def ok(r, what):
    if r.status_code >= 300:
        print('FAIL', what, r.status_code, r.text[:600]); sys.exit(1)
    print('ok  ', what)


def one(url):
    v = S.get(API + url).json().get('value', [])
    return v[0] if v else None


def privilege_name(action, table):
    # entity privileges use the entity schema name, e.g. prvReadop365_Item / prvReadAccount
    schema = S.get(API + f"EntityDefinitions(LogicalName='{table}')?$select=SchemaName").json()['SchemaName']
    return f'prv{action}{schema}'


root_bu = one('businessunits?$select=businessunitid&$filter=_parentbusinessunitid_value eq null')['businessunitid']

for name, grants in ROLES.items():
    role = one(f"roles?$select=roleid&$filter=name eq '{name}' and _businessunitid_value eq {root_bu}")
    if role:
        print('skip role', name); rid = role['roleid']
    else:
        r = S.post(API + 'roles', json={'name': name, 'businessunitid@odata.bind': f'/businessunits({root_bu})'},
                   headers={'Prefer': 'return=representation'})
        ok(r, 'role ' + name); rid = r.json()['roleid']
    privs = []
    for table, (actions, depth) in grants.items():
        for a in actions:
            p = one(f"privileges?$select=privilegeid&$filter=name eq '{privilege_name(a, table)}'")
            if not p:
                print('     no privilege', a, table); continue
            privs.append({'PrivilegeId': p['privilegeid'], 'Depth': depth, 'BusinessUnitId': root_bu,
                          'PrivilegeName': privilege_name(a, table)})
    ok(S.post(API + f'roles({rid})/Microsoft.Dynamics.CRM.AddPrivilegesRole',
              json={'Privileges': [{'@odata.type': 'Microsoft.Dynamics.CRM.RolePrivilege', **p} for p in privs]}),
       f'{len(privs)} privileges on {name}')

prof = one("fieldsecurityprofiles?$select=fieldsecurityprofileid&$filter=name eq 'OP365 Cost Visibility'")
if prof:
    pid = prof['fieldsecurityprofileid']; print('skip profile')
else:
    r = S.post(API + 'fieldsecurityprofiles', json={
        'name': 'OP365 Cost Visibility',
        'description': 'Read and edit cost columns (hourly costs, material costs, spend). For administrators and project managers.'},
        headers={'Prefer': 'return=representation'})
    ok(r, 'profile OP365 Cost Visibility'); pid = r.json()['fieldsecurityprofileid']
for table, column in COST_COLUMNS:
    if one(f"fieldpermissions?$select=fieldpermissionid&$filter=_fieldsecurityprofileid_value eq {pid} "
           f"and entityname eq '{table}' and attributelogicalname eq '{column}'"):
        print('skip', table, column); continue
    ok(S.post(API + 'fieldpermissions', json={
        'fieldsecurityprofileid@odata.bind': f'/fieldsecurityprofiles({pid})',
        'entityname': table, 'attributelogicalname': column, 'canread': 4, 'cancreate': 4, 'canupdate': 4}),
       f'field permission {table}.{column}')
