"""Cloud flows of the solution (all phases, defined in flow_definitions.py) and their connection references.

Flows are created off: a flow runs only once its connection reference has a connection. In Dev open the flow in
make.powerautomate.com (Solutions > ProjectIQ), pick or create the Dataverse connection and turn it on;
in other environments the connection comes from the deployment settings of the import.
Idempotent; reads the PAC_* environment variables.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API
from meta import ok, one
from flow_definitions import CONNECTORS, FLOWS

REFERENCES = {
    'op365_dataverse': ('ProjectIQ Dataverse', 'Dataverse connection used by the ProjectIQ flows'),
    'op365_sharepoint': ('ProjectIQ SharePoint', 'SharePoint connection (dedicated user) used by the ProjectIQ document flows'),
}

connections = {}
for name, connector in CONNECTORS.values():
    label, desc = REFERENCES[name]
    ref = one(f"connectionreferences?$select=connectionreferenceid,connectionid&$filter=connectionreferencelogicalname eq '{name}'")
    if ref:
        print('skip connection reference', name); connections[name] = ref.get('connectionid')
    else:
        ok(S.post(API + 'connectionreferences', json={
            'connectionreferencelogicalname': name, 'connectionreferencedisplayname': label,
            'connectorid': connector, 'description': desc}), 'connection reference ' + name)
        connections[name] = None

for flow_id, name, desc, data, _, _ in FLOWS:
    body = {'name': name, 'description': desc, 'clientdata': json.dumps(data)}
    flow = one(f"workflows?$select=workflowid,statecode&$filter=category eq 5 and name eq '{name}'")
    if flow:
        ok(S.patch(API + f"workflows({flow['workflowid']})", json=body), 'update flow ' + name)
    else:
        body.update({'workflowid': flow_id, 'category': 5, 'type': 1, 'primaryentity': 'none'})
        ok(S.post(API + 'workflows', json=body), 'create flow ' + name)
for name, connection in connections.items():
    print(f'{name}:', connection or 'no connection yet: set it in Power Automate and turn the flows on')
