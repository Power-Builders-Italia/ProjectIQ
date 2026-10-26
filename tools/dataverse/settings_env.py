"""Company settings as environment variables of the OpenProject365 solution; removes the former op365_settings table.

Definitions carry the defaults only: per-environment values are set in the target environment
(Solutions > Environment variables) or by deploy-test through the deployment settings. Idempotent.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API

STRING, NUMBER, BOOLEAN = 100000000, 100000001, 100000002

VARIABLES = [
    ('op365_TimeApprovalEnabled', 'Time Approval Enabled', BOOLEAN, 'yes',
     'Yes: submitted hours wait for the approval of a project manager. No: Submit approves hours immediately.'),
    ('op365_PurchaseRequestThreshold', 'Purchase Request Threshold', NUMBER, None,
     'Amount above which a purchase request also needs second-level approval. Empty or 0 = never.'),
    ('op365_PurchasingApprover', 'Purchasing Approver', STRING, None,
     'User Name (UPN) or primary email of the user who approves purchase requests above the threshold and decides '
     'supplier invoices. Empty = every OP365 Administrator.'),
]


def ok(r, what):
    if r.status_code >= 300:
        sys.exit(f'{what}: {r.status_code} {r.text[:400]}')
    print('ok  ', what)


for schema, label, kind, default, desc in VARIABLES:
    found = S.get(API + f"environmentvariabledefinitions?$select=environmentvariabledefinitionid&$filter=schemaname eq '{schema}'").json()['value']
    body = {'displayname': label, 'description': desc, 'type': kind, 'defaultvalue': default}
    if found:
        ok(S.patch(API + f"environmentvariabledefinitions({found[0]['environmentvariabledefinitionid']})", json=body), f'update {schema}')
    else:
        ok(S.post(API + 'environmentvariabledefinitions', json=dict(body, schemaname=schema)), f'create {schema}')

table = S.get(API + "EntityDefinitions?$select=MetadataId&$filter=LogicalName eq 'op365_settings'").json()['value']
if table:
    ok(S.delete(API + f"EntityDefinitions({table[0]['MetadataId']})"), 'delete table op365_settings')
else:
    print('skip  table op365_settings already removed')
