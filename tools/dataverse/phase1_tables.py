import sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
from dv import S, API

P = 'op365_'
NS = 'Microsoft.Dynamics.CRM.'
BASE = 365000000

def L(t):
    return {'@odata.type': NS+'Label', 'LocalizedLabels': [{'@odata.type': NS+'LocalizedLabel', 'Label': t, 'LanguageCode': 1033}]}

def req(r):
    return {'Value': 'ApplicationRequired' if r else 'None', 'CanBeChanged': True,
            'ManagedPropertyLogicalName': 'canmodifyrequirementlevelsettings'}

def opts(names):
    return [{'Value': BASE+i, 'Label': L(n)} for i, n in enumerate(names)]

def col(kind, schema, label, desc='', required=False, **kw):
    a = {'SchemaName': P+schema, 'DisplayName': L(label), 'Description': L(desc), 'RequiredLevel': req(required)}
    if kw.pop('secured', False):
        a['IsSecured'] = True
    if kind == 'text':
        a.update({'@odata.type': NS+'StringAttributeMetadata', 'MaxLength': kw.get('max', 100),
                  'FormatName': {'Value': kw.get('fmt', 'Text')}})
    elif kind == 'memo':
        a.update({'@odata.type': NS+'MemoAttributeMetadata', 'MaxLength': kw.get('max', 4000), 'Format': 'TextArea'})
    elif kind == 'whole':
        a.update({'@odata.type': NS+'IntegerAttributeMetadata', 'Format': 'None',
                  'MinValue': kw.get('min', 0), 'MaxValue': kw.get('maxv', 2147483647)})
    elif kind == 'decimal':
        a.update({'@odata.type': NS+'DecimalAttributeMetadata', 'Precision': kw.get('prec', 2),
                  'MinValue': kw.get('min', 0), 'MaxValue': kw.get('maxv', 100000000000)})
    elif kind == 'currency':
        a.update({'@odata.type': NS+'MoneyAttributeMetadata', 'Precision': 2, 'PrecisionSource': 2,
                  'MinValue': kw.get('min', 0), 'MaxValue': 922337203685477})
    elif kind == 'date':
        a.update({'@odata.type': NS+'DateTimeAttributeMetadata', 'Format': 'DateOnly',
                  'DateTimeBehavior': {'Value': 'DateOnly'}})
    elif kind == 'bool':
        a.update({'@odata.type': NS+'BooleanAttributeMetadata', 'DefaultValue': False,
                  'OptionSet': {'@odata.type': NS+'BooleanOptionSetMetadata', 'OptionSetType': 'Boolean',
                                'TrueOption': {'Value': 1, 'Label': L('Yes')},
                                'FalseOption': {'Value': 0, 'Label': L('No')}}})
    elif kind in ('choice', 'multichoice'):
        a.update({'@odata.type': NS+('PicklistAttributeMetadata' if kind == 'choice' else 'MultiSelectPicklistAttributeMetadata'),
                  'OptionSet': {'@odata.type': NS+'OptionSetMetadata', 'IsGlobal': False,
                                'OptionSetType': 'Picklist', 'Options': opts(kw['options'])}})
    elif kind == 'file':
        a.update({'@odata.type': NS+'FileAttributeMetadata', 'MaxSizeInKB': kw.get('kb', 32768)})
    return a

# ---------- model (Phase 1: master data, resources, settings) ----------
TABLES = [
  # schema, display, plural, description, primary (schema, label, max, required)
  ('Item', 'Item', 'Items', 'Purchased or consumed article', ('Name', 'Name', 200, True)),
  ('ItemSupplier', 'Item Supplier', 'Item Suppliers', 'Supplier price and conditions for an item', ('Name', 'Name', 200, False)),
  ('SupplierDocument', 'Supplier Document', 'Supplier Documents', 'Compliance document of a supplier (DURC, certifications, insurance...)', ('Description', 'Description', 200, True)),
  ('Resource', 'Resource', 'Resources', 'Person whose hours are planned and tracked, with or without a user license', ('Name', 'Name', 200, True)),
  ('ResourceCost', 'Resource Cost', 'Resource Costs', 'Hourly cost of a resource valid from a date', ('Name', 'Name', 200, False)),
  ('Absence', 'Absence', 'Absences', 'Absence of a resource or company closure', ('Name', 'Name', 200, False)),
  ('Settings', 'Settings', 'Settings', 'Company settings (single row)', ('Name', 'Name', 100, True)),
]

COLUMNS = {
  'account': [
    col('bool', 'IsCustomer', 'Is Customer'),
    col('bool', 'IsSupplier', 'Is Supplier'),
    col('choice', 'CustomerType', 'Customer Type', options=['Prospect', 'Customer']),
    col('text', 'VatNumber', 'VAT Number', max=20),
    col('text', 'TaxCode', 'Tax Code', max=20),
    col('choice', 'SupplierStatus', 'Supplier Status', options=['Active', 'Blocked']),
    col('text', 'SupplierCategory', 'Supplier Category'),
    col('text', 'Pec', 'PEC', 'Certified email address', max=100, fmt='Email'),
    col('text', 'Iban', 'IBAN', max=34),
    col('choice', 'Language', 'Language', 'Language for documents and emails sent to the account', options=['Italian', 'English', 'German', 'French']),
    col('text', 'PaymentTerms', 'Payment Terms'),
    col('whole', 'ExpiredDocs', 'Expired Documents', 'Updated daily by flow'),
    col('whole', 'ExpiringDocs', 'Expiring Documents', 'Updated daily by flow'),
  ],
  'contact': [
    col('bool', 'IsDecisionMaker', 'Is Decision Maker'),
  ],
  'op365_item': [
    col('text', 'Code', 'Code', required=True, max=50),
    col('text', 'Category', 'Category'),
    col('text', 'Uom', 'Unit of Measure', max=20),
    col('currency', 'UnitCost', 'Unit Cost'),
    col('memo', 'Notes', 'Notes'),
  ],
  'op365_itemsupplier': [
    col('text', 'SupplierCode', 'Supplier Code', max=50),
    col('currency', 'Price', 'Price'),
    col('whole', 'LeadTimeDays', 'Lead Time (Days)'),
    col('decimal', 'MinimumLot', 'Minimum Lot'),
    col('memo', 'Notes', 'Notes'),
  ],
  'op365_supplierdocument': [
    col('choice', 'DocumentType', 'Document Type', required=True,
        options=['DURC', 'Company Report', 'Certification', 'Insurance', 'Contract', 'Other']),
    col('text', 'Number', 'Number', max=50),
    col('date', 'IssueDate', 'Issue Date'),
    col('date', 'ExpiryDate', 'Expiry Date'),
    col('text', 'ExternalUrl', 'External URL', max=500, fmt='Url'),
    col('file', 'File', 'File'),
    col('memo', 'Notes', 'Notes'),
  ],
  'op365_resource': [
    col('text', 'Role', 'Role'),
    col('currency', 'HourlyCost', 'Hourly Cost', 'Current hourly cost, kept in sync from Resource Cost', secured=True),
    col('decimal', 'WeeklyHours', 'Weekly Hours', min=0, maxv=80),
    col('multichoice', 'WorkingDays', 'Working Days',
        options=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']),
  ],
  'op365_resourcecost': [
    col('date', 'ValidFrom', 'Valid From', required=True),
    col('currency', 'HourlyCost', 'Hourly Cost', required=True, secured=True),
  ],
  'op365_absence': [
    col('choice', 'AbsenceType', 'Absence Type', required=True, options=['Vacation', 'Leave', 'Sickness', 'Closure']),
    col('date', 'FromDate', 'From', required=True),
    col('date', 'ToDate', 'To', required=True),
    col('decimal', 'Hours', 'Hours', 'Only for single-day absences', min=0, maxv=24),
    col('memo', 'Notes', 'Notes'),
  ],
  # company settings are environment variables: see settings_env.py
}

# referencing table, lookup schema, label, referenced table, parental, required
LOOKUPS = [
  ('op365_item', 'DefaultSupplierId', 'Default Supplier', 'account', False, False),
  ('op365_itemsupplier', 'ItemId', 'Item', 'op365_item', True, True),
  ('op365_itemsupplier', 'SupplierId', 'Supplier', 'account', False, True),
  ('op365_supplierdocument', 'SupplierId', 'Supplier', 'account', True, True),
  ('op365_resource', 'UserId', 'User', 'systemuser', False, False),
  ('op365_resourcecost', 'ResourceId', 'Resource', 'op365_resource', True, True),
  ('op365_absence', 'ResourceId', 'Resource', 'op365_resource', False, False),
]

KEYS = [
  ('op365_item', 'op365_key_item_code', 'Item Code', ['op365_code']),
  ('op365_itemsupplier', 'op365_key_itemsupplier', 'Item and Supplier', ['op365_itemid', 'op365_supplierid']),
  ('op365_resourcecost', 'op365_key_resourcecost', 'Resource and Valid From', ['op365_resourceid', 'op365_validfrom']),
]

# ---------- helpers ----------
def ok(r, what):
    if r.status_code >= 300:
        print('FAIL', what, r.status_code, r.text[:600]); sys.exit(1)
    print('ok  ', what)

def exists(url):
    return S.get(API+url).status_code == 200

def ent(t): return f"EntityDefinitions(LogicalName='{t}')"

for schema, disp, plural, desc, (pn, pl, pmax, preq) in TABLES:
    ln = (P+schema).lower()
    if exists(ent(ln)+'?$select=LogicalName'):
        print('skip', ln); continue
    body = {'@odata.type': NS+'EntityMetadata', 'SchemaName': P+schema, 'DisplayName': L(disp),
            'DisplayCollectionName': L(plural), 'Description': L(desc), 'OwnershipType': 'UserOwned',
            'IsActivity': False, 'HasActivities': False, 'HasNotes': True,
            'IsAuditEnabled': {'Value': True, 'CanBeChanged': True, 'ManagedPropertyLogicalName': 'canmodifyauditsettings'},
            'Attributes': [dict(col('text', pn, pl, required=preq, max=pmax), IsPrimaryName=True)]}
    ok(S.post(API+'EntityDefinitions', json=body), 'table '+ln)

for t, cols in COLUMNS.items():
    for c in cols:
        ln = c['SchemaName'].lower()
        if exists(ent(t)+f"/Attributes(LogicalName='{ln}')?$select=LogicalName"):
            print('skip', t, ln); continue
        ok(S.post(API+ent(t)+'/Attributes', json=c), f'column {t}.{ln}')

for t, lk, label, target, parental, required in LOOKUPS:
    ln = (P+lk).lower()
    if exists(ent(t)+f"/Attributes(LogicalName='{ln}')?$select=LogicalName"):
        print('skip', t, ln); continue
    merge = 'Cascade' if target in ('account', 'contact') else 'NoCascade'
    if parental:
        cc = dict(Assign='Cascade', Delete='Cascade', Merge=merge, Reparent='Cascade', Share='Cascade', Unshare='Cascade')
    else:
        cc = dict(Assign='NoCascade', Delete='RemoveLink', Merge=merge, Reparent='NoCascade', Share='NoCascade', Unshare='NoCascade')
    name = f"op365_{target.replace('op365_','')}_{t.replace('op365_','')}_{lk.lower()}"
    body = {'@odata.type': NS+'OneToManyRelationshipMetadata', 'SchemaName': name,
            'ReferencedEntity': target, 'ReferencingEntity': t, 'CascadeConfiguration': cc,
            'AssociatedMenuConfiguration': {'Behavior': 'UseCollectionName', 'Group': 'Details', 'Order': 10000},
            'Lookup': {'@odata.type': NS+'LookupAttributeMetadata', 'SchemaName': P+lk,
                       'DisplayName': L(label), 'Description': L(''), 'RequiredLevel': req(required)}}
    ok(S.post(API+'RelationshipDefinitions', json=body), f'lookup {t}.{ln} -> {target}')

for t, ks, label, attrs in KEYS:
    if exists(ent(t)+f"/Keys(LogicalName='{ks}')?$select=LogicalName"):
        print('skip key', ks); continue
    body = {'SchemaName': ks, 'DisplayName': L(label), 'KeyAttributes': attrs}
    ok(S.post(API+ent(t)+'/Keys', json=body), f'key {t}.{ks}')

ok(S.post(API+'PublishAllXml', json={}), 'publish')
