"""Cloud flows of the solution (all phases) and their Dataverse connection reference.

Flows are created off: a flow runs only once its connection reference has a connection. In Dev open the flow in
make.powerautomate.com (Solutions > ProjectIQ), pick or create the Dataverse connection and turn it on;
in other environments the connection comes from the deployment settings of the import.
Idempotent; reads the PAC_* environment variables.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API
from meta import ok, one

DATAVERSE = '/providers/Microsoft.PowerApps/apis/shared_commondataserviceforapps'
REFERENCE = 'op365_Dataverse'
WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']


def unbound_action(action, parameters=None):
    params = {'actionName': action}
    params.update({f'item/{k}': v for k, v in (parameters or {}).items()})
    return {'runAfter': {}, 'type': 'OpenApiConnection', 'inputs': {
        'host': {'connectionName': 'shared_commondataserviceforapps', 'operationId': 'PerformUnboundAction',
                 'apiId': DATAVERSE},
        'parameters': params, 'authentication': "@parameters('$authentication')"}}


def clientdata(trigger, actions):
    return json.dumps({'properties': {
        'connectionReferences': {'shared_commondataserviceforapps': {
            'runtimeSource': 'embedded', 'connection': {'connectionReferenceLogicalName': REFERENCE.lower()},
            'api': {'name': 'shared_commondataserviceforapps'}}},
        'definition': {
            '$schema': 'https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#',
            'contentVersion': '1.0.0.0',
            'parameters': {'$connections': {'defaultValue': {}, 'type': 'Object'},
                           '$authentication': {'defaultValue': {}, 'type': 'SecureObject'}},
            'triggers': trigger, 'actions': actions}},
        'schemaVersion': '1.0.0.0'})


FLOWS = [
    ('Daily time reminder',
     'Working days at 17:30 (Europe/Rome): reminds the users who recorded fewer hours than expected today',
     {'Recurrence': {'type': 'Recurrence', 'recurrence': {
         'frequency': 'Week', 'interval': 1, 'timeZone': 'W. Europe Standard Time',
         'schedule': {'weekDays': WEEKDAYS, 'hours': ['17'], 'minutes': [30]}}}},
     {'Send_time_reminders': unbound_action('op365_SendTimeReminders')}),
]

ref = one(f"connectionreferences?$select=connectionreferenceid,connectionid&$filter=connectionreferencelogicalname eq '{REFERENCE.lower()}'")
if ref:
    print('skip connection reference'); connection = ref.get('connectionid')
else:
    ok(S.post(API + 'connectionreferences', json={
        'connectionreferencelogicalname': REFERENCE.lower(), 'connectionreferencedisplayname': 'ProjectIQ Dataverse',
        'connectorid': DATAVERSE, 'description': 'Dataverse connection used by the ProjectIQ flows'}),
       'connection reference ' + REFERENCE)
    connection = None

for name, desc, trigger, actions in FLOWS:
    body = {'name': name, 'description': desc, 'clientdata': clientdata(trigger, actions)}
    flow = one(f"workflows?$select=workflowid,statecode&$filter=category eq 5 and name eq '{name}'")
    if flow:
        ok(S.patch(API + f"workflows({flow['workflowid']})", json=body), 'update flow ' + name)
    else:
        body.update({'category': 5, 'type': 1, 'primaryentity': 'none'})
        ok(S.post(API + 'workflows', json=body), 'create flow ' + name)
print('connection:', connection or 'none yet: set it in Power Automate and turn the flows on')
