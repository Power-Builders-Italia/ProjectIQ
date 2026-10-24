"""Phase 3 security: time entries and material usage.

OP365 User gets User-level privileges: own rows, plus the rows of the projects shared with the user
through the project access teams (both tables are parental children of the project).
Cost columns join the OP365 Cost Visibility profile.
Idempotent; reads the PAC_* environment variables.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API
from meta import grant_roles, ok, one

ALL = ['Create', 'Read', 'Write', 'Delete', 'Append', 'AppendTo', 'Assign', 'Share']
TABLES = ['op365_timeentry', 'op365_materialusage']
COST_COLUMNS = [('op365_timeentry', 'op365_cost'), ('op365_materialusage', 'op365_unitcost'),
                ('op365_materialusage', 'op365_totalcost')]

grant_roles({
    'OP365 Administrator': {t: (ALL, 'Global') for t in TABLES},
    'OP365 User': {t: (['Create', 'Read', 'Write', 'Delete', 'Append', 'AppendTo'], 'Basic') for t in TABLES},
})

pid = one("fieldsecurityprofiles?$select=fieldsecurityprofileid&$filter=name eq 'OP365 Cost Visibility'")['fieldsecurityprofileid']
for table, column in COST_COLUMNS:
    if one(f"fieldpermissions?$select=fieldpermissionid&$filter=_fieldsecurityprofileid_value eq {pid} "
           f"and entityname eq '{table}' and attributelogicalname eq '{column}'"):
        print('skip', table, column); continue
    ok(S.post(API + 'fieldpermissions', json={
        'fieldsecurityprofileid@odata.bind': f'/fieldsecurityprofiles({pid})',
        'entityname': table, 'attributelogicalname': column, 'canread': 4, 'cancreate': 4, 'canupdate': 4}),
       f'field permission {table}.{column}')
