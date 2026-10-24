"""Phase 1 main forms: Customer and Supplier forms on Account, main forms of the F1 tables.

Forms are generated from a compact layout description. Existing forms (matched by table + name)
are overwritten; the generated 'Information' form of each custom table is renamed and replaced.
"""
import itertools, os, sys, uuid
from xml.sax.saxutils import escape
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API

CLASSID = {
    'String': '{4273EDBD-AC1D-40d3-9FB2-095C621B552D}', 'Virtual': '{4273EDBD-AC1D-40d3-9FB2-095C621B552D}',
    'Memo': '{E0DECE4B-6FC8-4a8f-A065-082708572369}', 'Integer': '{C6D124CA-7EDA-4a60-AEA9-7FB8D318B68F}',
    'Decimal': '{C3EFE0C3-0EC6-42be-8349-CBD9079DFD8E}', 'Money': '{533B9E00-756B-4312-95A0-DC888637AC78}',
    'DateTime': '{5B773807-9FB2-42db-97C3-7A91EFF8ADFF}', 'Boolean': '{67FAC785-CD58-4f9f-ABB3-4B7DDC6ED5ED}',
    'Picklist': '{3EF39988-22BB-4f0b-BBBE-64B5A3748AEE}', 'Lookup': '{270BD3DB-D9AF-4782-9025-509E298DEC0A}',
    'Customer': '{270BD3DB-D9AF-4782-9025-509E298DEC0A}', 'Owner': '{270BD3DB-D9AF-4782-9025-509E298DEC0A}',
    'MultiSelectPicklist': '{4AA28AB7-9C13-4F57-A73D-AD894D048B5F}',
}
SUBGRID = '{E7A81278-8635-4d9e-8D4D-59480B391C5B}'
TIMELINE = '{06375649-c143-495e-a496-c962e5b4488e}'


def ok(r, what):
    if r.status_code >= 300:
        print('FAIL', what, r.status_code, r.text[:600]); sys.exit(1)
    print('ok  ', what)


_attrs = {}
def attr(table, name):
    if table not in _attrs:
        v = S.get(API + f"EntityDefinitions(LogicalName='{table}')/Attributes?$select=LogicalName,AttributeType,"
                  "DisplayName").json()['value']
        _attrs[table] = {a['LogicalName']: a for a in v}
    return _attrs[table][name]


_ids = itertools.count()
def gid():
    # deterministic ids (stable across runs) keep the unpacked FormXml diffs small
    return '{%s}' % uuid.uuid5(uuid.NAMESPACE_URL, f'op365-phase1-forms-{next(_ids)}')


def lbl(text):
    return f'<labels><label description="{escape(text)}" languagecode="1033" /></labels>'


def field_cell(table, name):
    a = attr(table, name)
    label = (a['DisplayName'].get('UserLocalizedLabel') or {}).get('Label', name)
    cls = CLASSID[a['AttributeType']]
    return f'<cell id="{gid()}">{lbl(label)}<control id="{name}" classid="{cls}" datafieldname="{name}" /></cell>'


def default_view(table):
    return S.get(API + f"savedqueries?$select=savedqueryid&$filter=returnedtypecode eq '{table}' "
                 "and querytype eq 0 and isdefault eq true").json()['value'][0]['savedqueryid']


def subgrid_cell(name, label, target, relationship, rows=8):
    return (f'<cell id="{gid()}" showlabel="true" rowspan="{rows}" colspan="1" auto="false">{lbl(label)}'
            f'<control id="{name}" classid="{SUBGRID}" indicationOfSubgrid="true"><parameters>'
            f'<ViewId>{{{default_view(target)}}}</ViewId><IsUserView>false</IsUserView>'
            f'<RelationshipName>{relationship}</RelationshipName><TargetEntityType>{target}</TargetEntityType>'
            '<AutoExpand>Fixed</AutoExpand><EnableQuickFind>false</EnableQuickFind><EnableViewPicker>false</EnableViewPicker>'
            '<EnableJumpBar>false</EnableJumpBar><ChartGridMode>Grid</ChartGridMode><VisualizationId />'
            f'<IsUserChart>false</IsUserChart><EnableChartPicker>false</EnableChartPicker><RecordsPerPage>{rows}</RecordsPerPage>'
            '</parameters></control></cell>')


def timeline_cell():
    return (f'<cell id="{gid()}" showlabel="false" rowspan="20" colspan="1" auto="false">{lbl("Timeline")}'
            f'<control id="notescontrol" classid="{TIMELINE}" disabled="false" /></cell>')


def section(table, title, items, columns=2):
    """items: column names, or ('subgrid', id, label, target, relationship) / ('timeline',)."""
    rows, pending = [], []
    for it in items:
        if isinstance(it, tuple):
            if pending:
                rows.append(pending); pending = []
            rows.append([subgrid_cell(*it[1:]) if it[0] == 'subgrid' else timeline_cell()])
            continue
        pending.append(field_cell(table, it))
        if len(pending) == columns:
            rows.append(pending); pending = []
    if pending:
        rows.append(pending)
    special = any(isinstance(i, tuple) for i in items)
    cols = 1 if special else columns
    body = ''.join('<row>' + ''.join(r) + '</row>' for r in rows)
    return (f'<section name="{title.lower().replace(" ", "_")}" showlabel="true" showbar="false" columns="{cols}" '
            f'id="{gid()}">{lbl(title)}<rows>{body}</rows></section>')


def tab(title, columns):
    """columns: list of (width, [section xml])."""
    cols = ''.join(f'<column width="{w}"><sections>{"".join(s)}</sections></column>' for w, s in columns)
    return (f'<tab name="{title.lower().replace(" ", "_")}" id="{gid()}" expanded="true" showlabel="true" '
            f'verticallayout="true">{lbl(title)}<columns>{cols}</columns></tab>')


ACCOUNT_JS = 'op365_/scripts/account.form.js'


def webresource(name, path, display):
    import base64
    content = base64.b64encode(open(path, 'rb').read()).decode()
    v = S.get(API + f"webresourceset?$select=webresourceid&$filter=name eq '{name}'").json()['value']
    body = {'displayname': display, 'content': content}
    if v:
        ok(S.patch(API + f"webresourceset({v[0]['webresourceid']})", json=body), 'update web resource ' + name)
    else:
        body.update({'name': name, 'webresourcetype': 3})
        ok(S.post(API + 'webresourceset', json=body), 'create web resource ' + name)


def onload(library, function):
    return (f'<formLibraries><Library name="{library}" libraryUniqueId="{gid()}" /></formLibraries>'
            '<events><event name="onload" application="false" active="false"><Handlers>'
            f'<Handler functionName="{function}" libraryName="{library}" handlerUniqueId="{gid()}" enabled="true" '
            'parameters="" passExecutionContext="true" /></Handlers></event></events>')


def form(table, name, tabs, replace=None, description='', extra=''):
    xml = '<form><tabs>' + ''.join(tabs) + '</tabs>' + extra + '</form>'
    existing = None
    for n in [name] + ([replace] if replace else []):
        v = S.get(API + f"systemforms?$select=formid&$filter=objecttypecode eq '{table}' and type eq 2 "
                  f"and name eq '{n}'").json()['value']
        if v:
            existing = v[0]['formid']; break
    body = {'name': name, 'description': description, 'formxml': xml}
    if existing:
        ok(S.patch(API + f'systemforms({existing})', json=body), f'update form {table}: {name}')
    else:
        body.update({'objecttypecode': table, 'type': 2, 'formactivationstate': 1})
        r = S.post(API + 'systemforms', json=body)
        ok(r, f'create form {table}: {name}')
        existing = r.headers['OData-EntityId'].split('(')[-1].rstrip(')')
    # renamed forms can lose their localized name, and a form without one fails to import
    ok(S.post(API + 'SetLocLabels', json={
        'EntityMoniker': {'@odata.type': 'Microsoft.Dynamics.CRM.systemform', 'formid': existing},
        'AttributeName': 'name',
        'Labels': [{'@odata.type': 'Microsoft.Dynamics.CRM.LocalizedLabel', 'Label': name, 'LanguageCode': 1033}]}),
       f'label form {name}')


A = 'account'
webresource(ACCOUNT_JS, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'webresources', 'account.form.js'),
            'Account form script')
ADDRESS = ['address1_line1', 'address1_city', 'address1_postalcode', 'address1_stateorprovince', 'address1_country']
form(A, 'Customer', [
    tab('Summary', [
        ('60%', [section(A, 'Customer', ['name', 'op365_iscustomer', 'op365_customertype', 'op365_vatnumber',
                                         'op365_taxcode', 'primarycontactid', 'telephone1', 'emailaddress1',
                                         'websiteurl', 'ownerid']),
                 section(A, 'Address', ADDRESS),
                 section(A, 'Billing', ['op365_paymentterms', 'op365_iban', 'op365_pec', 'op365_language'])]),
        ('40%', [section(A, 'Timeline', [('timeline',)])])]),
    tab('Contacts', [('100%', [section(A, 'Contacts', [('subgrid', 'Contacts', 'Contacts', 'contact', 'contact_customer_accounts')])])]),
], description='Account as customer (Open Project 365)', extra=onload(ACCOUNT_JS, 'OP365.Account.onLoad'))

form(A, 'Supplier', [
    tab('Summary', [
        ('60%', [section(A, 'Supplier', ['name', 'op365_issupplier', 'op365_supplierstatus', 'op365_suppliercategory',
                                         'op365_vatnumber', 'op365_taxcode', 'primarycontactid', 'telephone1',
                                         'emailaddress1', 'ownerid']),
                 section(A, 'Address', ADDRESS),
                 section(A, 'Payment', ['op365_paymentterms', 'op365_iban', 'op365_pec', 'op365_language'])]),
        ('40%', [section(A, 'Timeline', [('timeline',)])])]),
    tab('Documents', [('100%', [
        section(A, 'Document Alerts', ['op365_expireddocs', 'op365_expiringdocs']),
        section(A, 'Documents', [('subgrid', 'Documents', 'Documents', 'op365_supplierdocument', 'op365_account_supplierdocument_supplierid')])])]),
    tab('Item Prices', [('100%', [section(A, 'Item Prices', [('subgrid', 'ItemPrices', 'Item Prices', 'op365_itemsupplier', 'op365_account_itemsupplier_supplierid')])])]),
    tab('Contacts', [('100%', [section(A, 'Contacts', [('subgrid', 'Contacts', 'Contacts', 'contact', 'contact_customer_accounts')])])]),
], description='Account as supplier (Open Project 365)', extra=onload(ACCOUNT_JS, 'OP365.Account.onLoad'))

T = 'op365_item'
form(T, 'Item', [
    tab('General', [
        ('60%', [section(T, 'Item', ['op365_code', 'op365_name', 'op365_category', 'op365_uom', 'op365_unitcost',
                                     'op365_defaultsupplierid', 'ownerid']),
                 section(T, 'Notes', ['op365_notes'], columns=1),
                 section(T, 'Suppliers', [('subgrid', 'Suppliers', 'Suppliers', 'op365_itemsupplier', 'op365_item_itemsupplier_itemid')])]),
        ('40%', [section(T, 'Timeline', [('timeline',)])])]),
], replace='Information')

T = 'op365_itemsupplier'
form(T, 'Item Supplier', [tab('General', [('100%', [
    section(T, 'Item Supplier', ['op365_itemid', 'op365_supplierid', 'op365_name', 'op365_suppliercode',
                                 'op365_price', 'op365_leadtimedays', 'op365_minimumlot', 'ownerid']),
    section(T, 'Notes', ['op365_notes'], columns=1)])])], replace='Information')

T = 'op365_supplierdocument'
form(T, 'Supplier Document', [tab('General', [
    ('60%', [section(T, 'Document', ['op365_supplierid', 'op365_documenttype', 'op365_description', 'op365_number',
                                     'op365_issuedate', 'op365_expirydate', 'op365_externalurl', 'ownerid']),
             section(T, 'File', ['op365_file'], columns=1),
             section(T, 'Notes', ['op365_notes'], columns=1)]),
    ('40%', [section(T, 'Timeline', [('timeline',)])])])], replace='Information')

T = 'op365_resource'
form(T, 'Resource', [
    tab('General', [('100%', [
        section(T, 'Resource', ['op365_name', 'op365_role', 'op365_userid', 'ownerid']),
        section(T, 'Capacity and Cost', ['op365_weeklyhours', 'op365_hourlycost', 'op365_workingdays'])])]),
    tab('Costs', [('100%', [section(T, 'Hourly Costs', [('subgrid', 'Costs', 'Hourly Costs', 'op365_resourcecost', 'op365_resource_resourcecost_resourceid')])])]),
    tab('Absences', [('100%', [section(T, 'Absences', [('subgrid', 'Absences', 'Absences', 'op365_absence', 'op365_resource_absence_resourceid')])])]),
], replace='Information')

T = 'op365_resourcecost'
form(T, 'Resource Cost', [tab('General', [('100%', [
    section(T, 'Resource Cost', ['op365_resourceid', 'op365_validfrom', 'op365_hourlycost', 'op365_name', 'ownerid'])])])],
    replace='Information')

T = 'op365_absence'
form(T, 'Absence', [tab('General', [('100%', [
    section(T, 'Absence', ['op365_resourceid', 'op365_absencetype', 'op365_fromdate', 'op365_todate',
                           'op365_hours', 'op365_name', 'ownerid']),
    section(T, 'Notes', ['op365_notes'], columns=1)])])], replace='Information')

T = 'op365_settings'
form(T, 'Settings', [tab('General', [('100%', [
    section(T, 'Company', ['op365_name', 'ownerid']),
    section(T, 'Time Tracking', ['op365_timeapprovalenabled']),
    section(T, 'Purchasing', ['op365_purchaserequestthreshold'])])])], replace='Information')

ok(S.post(API + 'PublishAllXml', json={}), 'publish')
