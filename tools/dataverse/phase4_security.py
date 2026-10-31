"""Phase 4 security: purchasing tables.

OP365 User gets User-level privileges: own rows plus the purchasing rows of the projects shared through the project
access teams (requests, RFQs, orders and receipts are parental children of the project, their lines of the header).
Supplier invoices are not tied to a project share: users read their own, administrators handle them.
Spend columns join the OP365 Cost Visibility profile.
Idempotent; reads the PAC_* environment variables.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API
from meta import grant_roles, ok, one

ALL = ['Create', 'Read', 'Write', 'Delete', 'Append', 'AppendTo', 'Assign', 'Share']
PROJECT_TABLES = ['op365_purchaserequest', 'op365_purchaserequestline', 'op365_rfq', 'op365_rfqinvitation', 'op365_rfqquote',
                  'op365_purchaseorder', 'op365_purchaseorderline', 'op365_goodsreceipt', 'op365_goodsreceiptline']
INVOICES = ['op365_supplierinvoice', 'op365_supplierinvoiceline']
COST_COLUMNS = [('account', 'op365_spend'), ('account', 'op365_iban'), ('op365_item', 'op365_spend')]

user = {t: (['Create', 'Read', 'Write', 'Delete', 'Append', 'AppendTo'], 'Basic') for t in PROJECT_TABLES}
user.update({t: (['Read', 'AppendTo'], 'Basic') for t in INVOICES})
grant_roles({
    'OP365 Administrator': {t: (ALL, 'Global') for t in PROJECT_TABLES + INVOICES},
    'OP365 User': user,
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
