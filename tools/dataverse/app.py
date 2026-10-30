"""Model-driven app 'ProjectIQ': sitemap and modern commands of every delivered phase.

Cumulative: run it after the phase scripts. Idempotent.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API

APP = 'op365_OpenProject365'
DEFAULT_ICON = '953b9fac-1e5e-e611-80d6-00155ded156f'  # standard model-driven app icon


def ok(r, what):
    if r.status_code >= 300:
        print('FAIL', what, r.status_code, r.text[:800]); sys.exit(1)
    print('ok  ', what)


def view_id(table, name):
    return S.get(API + f"savedqueries?$select=savedqueryid&$filter=returnedtypecode eq '{table}' and name eq '{name}'"
                 ).json()['value'][0]['savedqueryid']


def t(text):
    return f'<Titles><Title LCID="1033" Title="{text}" /></Titles>'


def entity(id, table, title):
    return f'<SubArea Id="{id}" Entity="{table}">{t(title)}</SubArea>'


def entity_view(id, table, title, view):
    url = f'/main.aspx?pagetype=entitylist&amp;etn={table}&amp;viewid=%7b{view_id(table, view)}%7d'
    return f'<SubArea Id="{id}" Entity="{table}" Url="{url}">{t(title)}</SubArea>'


def dashboard_id(name):
    return S.get(API + f"systemforms?$select=formid&$filter=type eq 0 and name eq '{name}'").json()['value'][0]['formid']


def dashboard(id, title, name):
    url = f'/main.aspx?pagetype=dashboard&amp;id=%7b{dashboard_id(name)}%7d&amp;type=system'
    return f'<SubArea Id="{id}" Url="{url}">{t(title)}</SubArea>'


def group(id, title, subs):
    return f'<Group Id="{id}">{t(title)}' + ''.join(subs) + '</Group>'


def area(id, title, groups):
    return f'<Area Id="{id}" ShowGroups="true">{t(title)}' + ''.join(groups) + '</Area>'


SITEMAP = '<SiteMap IntroducedVersion="7.0.0.0">' + ''.join([
    area('op365_projects', 'Projects', [
        group('op365_work', 'Work', [entity('op365_projectssub', 'op365_project', 'Projects'),
                                     entity('op365_materialusages', 'op365_materialusage', 'Material Usage')]),
        group('op365_time', 'Time', [dashboard('op365_timesheet', 'Timesheet', 'Timesheet'),
                                     dashboard('op365_timeapproval', 'Approvals', 'Time Approval'),
                                     entity('op365_timeentries', 'op365_timeentry', 'Time Entries')]),
        group('op365_planning', 'Planning', [dashboard('op365_resourceload', 'Resource Load', 'Resource Load'),
                                             entity('op365_absences', 'op365_absence', 'Absences')])]),
    area('op365_purchasing', 'Purchasing', [
        group('op365_procurement', 'Procurement', [
            entity('op365_purchaserequests', 'op365_purchaserequest', 'Purchase Requests'),
            entity('op365_rfqs', 'op365_rfq', 'RFQs'),
            entity('op365_purchaseorders', 'op365_purchaseorder', 'Purchase Orders'),
            entity('op365_goodsreceipts', 'op365_goodsreceipt', 'Goods Receipts'),
            entity('op365_supplierinvoices', 'op365_supplierinvoice', 'Supplier Invoices')]),
        group('op365_analysis', 'Analysis', [dashboard('op365_spend', 'Spend', 'Spend')])]),
    area('op365_masterdata', 'Master Data', [
        group('op365_records', 'Records', [
            entity_view('op365_customers', 'account', 'Customers', 'All Customers'),
            entity_view('op365_suppliers', 'account', 'Suppliers', 'All Suppliers'),
            entity('op365_contacts', 'contact', 'Contacts'),
            entity('op365_items', 'op365_item', 'Items'),
            entity('op365_resources', 'op365_resource', 'Resources')])]),
    area('op365_settingsarea', 'Settings', [
        group('op365_company', 'Company', [
            entity('op365_resourcecosts', 'op365_resourcecost', 'Resource Costs'),
            entity('op365_projectmembers', 'op365_projectmember', 'Project Members')])]),
]) + '</SiteMap>'

TABLES = ['account', 'contact', 'op365_item', 'op365_itemsupplier', 'op365_supplierdocument', 'op365_resource',
          'op365_resourcecost', 'op365_absence',
          'op365_project', 'op365_projectmember', 'op365_wbsnode', 'op365_wbsdependency', 'op365_wbsallocation',
          'op365_baseline', 'op365_baselinenode', 'op365_timeentry', 'op365_materialusage',
          'op365_purchaserequest', 'op365_purchaserequestline', 'op365_rfq', 'op365_rfqinvitation', 'op365_rfqquote',
          'op365_purchaseorder', 'op365_purchaseorderline', 'op365_goodsreceipt', 'op365_goodsreceiptline',
          'op365_supplierinvoice', 'op365_supplierinvoiceline',
          'activitypointer', 'task', 'phonecall', 'appointment', 'email', 'annotation',
          # Related > Documents is shown only when the app contains the SharePoint tables
          'sharepointdocument', 'sharepointdocumentlocation']
DASHBOARDS = ['Timesheet', 'Time Approval', 'Resource Load', 'Spend']

# modern commands: (unique name, label, table, location 0 = form, web resource, function, tooltip)
COMMANDS = [
    ('op365_project_savebaseline', 'Save Baseline', 'op365_project', 0, 'op365_/scripts/project.form.js',
     'OP365.Project.saveBaseline', 'Save the current WBS budget and dates as the reference baseline'),
]

# a new app stays unpublished until PublishXml, so look it up among unpublished rows too
app = [a for a in S.get(API + 'appmodules/Microsoft.Dynamics.CRM.RetrieveUnpublishedMultiple()'
                        '?$select=appmoduleid,uniquename').json()['value'] if a['uniquename'] == APP]
if app:
    app_id = app[0]['appmoduleid']; print('skip app')
else:
    r = S.post(API + 'appmodules', json={
        'name': 'ProjectIQ', 'uniquename': APP, 'clienttype': 4, 'navigationtype': 0,
        'description': 'Projects, planning, time, materials and purchasing on Dataverse',
        'webresourceid': DEFAULT_ICON})
    ok(r, 'app ' + APP); app_id = r.headers['OData-EntityId'].split('(')[-1].rstrip(')')

sm = [s for s in S.get(API + 'sitemaps/Microsoft.Dynamics.CRM.RetrieveUnpublishedMultiple()'
                       '?$select=sitemapid,sitemapnameunique').json()['value'] if s.get('sitemapnameunique') == APP]
if sm:
    sitemap_id = sm[0]['sitemapid']
    ok(S.patch(API + f'sitemaps({sitemap_id})', json={'sitemapxml': SITEMAP}), 'update sitemap')
else:
    r = S.post(API + 'sitemaps', json={
        'sitemapname': 'ProjectIQ', 'sitemapnameunique': APP, 'isappaware': True, 'sitemapxml': SITEMAP})
    ok(r, 'sitemap'); sitemap_id = r.headers['OData-EntityId'].split('(')[-1].rstrip(')')

components = [{'@odata.type': 'Microsoft.Dynamics.CRM.sitemap', 'sitemapid': sitemap_id}]
for table in TABLES:
    mid = S.get(API + f"EntityDefinitions(LogicalName='{table}')?$select=MetadataId").json()['MetadataId']
    components.append({'@odata.type': 'Microsoft.Dynamics.CRM.entity', 'entityid': mid})
# account: only the two ProjectIQ forms and views
for f in S.get(API + "systemforms?$select=formid&$filter=objecttypecode eq 'account' and type eq 2 "
               "and (name eq 'Customer' or name eq 'Supplier')").json()['value']:
    components.append({'@odata.type': 'Microsoft.Dynamics.CRM.systemform', 'formid': f['formid']})
for name in DASHBOARDS:
    components.append({'@odata.type': 'Microsoft.Dynamics.CRM.systemform', 'formid': dashboard_id(name)})
ok(S.post(API + 'AddAppComponents', json={'AppId': app_id, 'Components': components}), 'app components')

# in-app notifications (sent by the time approval plugins): older environments still have the app setting,
# newer ones show notifications without it
definition = S.get(API + "settingdefinitions?$select=settingdefinitionid&$filter=uniquename eq 'AppNotificationPolarisFeature'").json()['value']
if not definition:
    print('skip in-app notifications setting (not needed in this environment)')
else:
    definition = definition[0]['settingdefinitionid']
    current = S.get(API + f"appsettings?$select=appsettingid,value&$filter=_parentappmoduleid_value eq {app_id} "
                    f"and _settingdefinitionid_value eq {definition}").json()['value']
    if not current:
        ok(S.post(API + 'appsettings', json={
            'value': 'true', 'uniquename': f'{APP}_AppNotificationPolarisFeature',
            'parentappmoduleid@odata.bind': f'/appmodules({app_id})',
            'settingdefinitionid@odata.bind': f'/settingdefinitions({definition})'}), 'in-app notifications on')
    elif current[0]['value'] != 'true':
        ok(S.patch(API + f"appsettings({current[0]['appsettingid']})", json={'value': 'true'}), 'in-app notifications on')

for uname, label, table, location, library, function, tip in COMMANDS:
    body = {
        'name': label, 'buttonlabeltext': label, 'buttontooltiptitle': label, 'buttontooltipdescription': tip,
        'buttonaccessibilitytext': label, 'fonticon': 'Save', 'location': location, 'context': 1, 'contextvalue': table, 'type': 0,
        'sequence': 10, 'onclickeventtype': 2, 'onclickeventjavascriptfunctionname': function,
        'onclickeventjavascriptparameters': '[{"type":5}]',  # PrimaryControl
        'visibilitytype': 0, 'hidden': False,
        'AppModuleId@odata.bind': f'/appmodules({app_id})',
        'ContextEntity@odata.bind': '/entities(%s)' % S.get(API + f"EntityDefinitions(LogicalName='{table}')?$select=MetadataId").json()['MetadataId'],
        'OnClickEventJavaScriptWebResourceId@odata.bind': '/webresourceset(%s)' % S.get(
            API + f"webresourceset?$select=webresourceid&$filter=name eq '{library}'").json()['value'][0]['webresourceid'],
    }
    existing = S.get(API + f"appactions?$select=appactionid&$filter=uniquename eq '{uname}'").json()['value']
    if existing:
        ok(S.patch(API + f"appactions({existing[0]['appactionid']})", json=body), 'command ' + label)
    else:
        ok(S.post(API + 'appactions', json={'uniquename': uname, **body}), 'command ' + label)

v = S.get(API + f'ValidateApp(AppModuleId={app_id})').json()
print('validate:', v.get('AppValidationResponse', {}).get('ValidationSuccess'),
      [i.get('Message') for i in v.get('AppValidationResponse', {}).get('ValidationIssueList', [])][:10])
ok(S.post(API + 'PublishXml', json={'ParameterXml': f'<importexportxml><appmodules><appmodule>{app_id}</appmodule>'
                                    f'</appmodules><sitemaps><sitemap>{sitemap_id}</sitemap></sitemaps></importexportxml>'}),
   'publish app')
