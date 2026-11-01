"""Company settings as environment variables of the OpenProject365 solution; removes the former op365_settings table.

Definitions carry the defaults only: per-environment values are set in the target environment
(Solutions > Environment variables) or by deploy-test through the deployment settings. Idempotent.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API
import json
from flow_definitions import LIBRARIES, SITE
from supplier_email_templates import default_mapping

STRING, NUMBER, BOOLEAN, JSON = 100000000, 100000001, 100000002, 100000003

VARIABLES = [
    ('op365_TimeApprovalEnabled', 'Time Approval Enabled', BOOLEAN, 'yes',
     'Yes: submitted hours wait for the approval of a project manager. No: Submit approves hours immediately.'),
    ('op365_PurchaseRequestThreshold', 'Purchase Request Threshold', NUMBER, None,
     'Amount above which a purchase request also needs second-level approval. Empty or 0 = never.'),
    ('op365_PurchasingApprover', 'Purchasing Approver', STRING, None,
     'User Name (UPN) or primary email of the user who approves purchase requests above the threshold and decides '
     'supplier invoices. Empty = every OP365 Administrator.'),
    ('op365_SupplierEmailTemplates', 'Supplier Email Templates', JSON, json.dumps(default_mapping(), ensure_ascii=False),
     'E-mail templates (Account type) of the messages to suppliers, by message and supplier Language: '
     '{"DocumentExpiring": {"Italian": "<template title>", "English": "<template title>", "default": "English"}, '
     '"DocumentExpired": {...}}. Default: the templates of tools/dataverse/supplier_email_templates.py.'),
    ('op365_SupplierEmailSender', 'Supplier Email Sender', STRING, None,
     'Name or e-mail address of the queue (mailbox with server-side synchronization) that sends the e-mails to suppliers. '
     'Empty = no e-mails.'),
]
# document metadata flows: SharePoint site and library ids, set by tools/sharepoint/document_metadata.py (no default)
VARIABLES += [(schema, label, STRING, None, desc) for schema, label, desc in [SITE, *LIBRARIES.values()]]


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
