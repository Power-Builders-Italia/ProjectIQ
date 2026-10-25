"""Issue #16: Project Code becomes an optional autonumber (PRJ-######), Project Name becomes required."""
from dv import S, API

ENT = "EntityDefinitions(LogicalName='op365_project')"


def update(col, **changes):
    url = API + ENT + f"/Attributes(LogicalName='{col}')/Microsoft.Dynamics.CRM.StringAttributeMetadata"
    attr = S.get(url).json()
    if all((attr['RequiredLevel']['Value'] if k == 'RequiredLevel' else attr.get(k)) == v for k, v in changes.items()):
        print('skip', col); return
    for k, v in changes.items():
        if k == 'RequiredLevel':
            attr['RequiredLevel']['Value'] = v
        else:
            attr[k] = v
    attr.pop('@odata.context', None)
    attr['@odata.type'] = 'Microsoft.Dynamics.CRM.StringAttributeMetadata'
    r = S.put(API + ENT + f"/Attributes({attr['MetadataId']})", json=attr, headers={'MSCRM.MergeLabels': 'true'})
    r.raise_for_status(); print('updated', col, changes)


update('op365_code', RequiredLevel='None', AutoNumberFormat='PRJ-{SEQNUM:6}')
update('op365_name', RequiredLevel='ApplicationRequired')
r = S.post(API + 'PublishXml', json={'ParameterXml': '<importexportxml><entities><entity>op365_project</entity></entities></importexportxml>'})
r.raise_for_status(); print('published')

# The platform starts every autonumber at 1000. Start from PRJ-000001, but only while no PRJ- code exists
# (re-seeding later would produce duplicates). The seed is per environment: run this once in each one.
if not S.get(API + "op365_projects?$select=op365_code&$top=1&$filter=startswith(op365_code,'PRJ-')").json()['value']:
    r = S.post(API + 'SetAutoNumberSeed', json={'EntityName': 'op365_project', 'AttributeName': 'op365_code', 'Value': 1})
    r.raise_for_status(); print('seed 1')
