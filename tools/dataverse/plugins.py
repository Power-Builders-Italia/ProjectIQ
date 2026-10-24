"""Plugin registration (all phases): OpenProject365.Plugins assembly, steps, images and Custom APIs.

Build the assembly first:  dotnet build src/plugins/OpenProject365.Plugins -c Release
Idempotent: the assembly content is updated, missing types/steps/images are created.
"""
import base64, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API
from meta import ok

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DLL = os.path.join(ROOT, 'src/plugins/OpenProject365.Plugins/bin/Release/net462/OpenProject365.Plugins.dll')
NSP = 'OpenProject365.Plugins.'
PREVAL, PRE, POST = 10, 20, 40
TE_IMAGE = 'statuscode,op365_projectid,op365_wbsnodeid,op365_resourceid,op365_entrydate,op365_hours'
MU_IMAGE = 'op365_projectid,op365_wbsnodeid,op365_itemid,op365_supplierid,op365_quantity,op365_unitcost,op365_name,op365_uom'

# class, message, table, stage, filtering attributes, pre-image attributes
STEPS = [
  ('ResourceDefaults', 'Create', 'op365_resource', PRE, None, None),
  ('ResourceCostSync', 'Create', 'op365_resourcecost', POST, None, None),
  ('ResourceCostSync', 'Update', 'op365_resourcecost', POST, 'op365_validfrom,op365_hourlycost,op365_resourceid,statecode', 'op365_resourceid'),
  ('ResourceCostSync', 'Delete', 'op365_resourcecost', POST, None, 'op365_resourceid'),
  ('ProjectMemberName', 'Create', 'op365_projectmember', PRE, None, None),
  ('ProjectMemberSync', 'Create', 'op365_projectmember', POST, None, None),
  ('ProjectMemberSync', 'Update', 'op365_projectmember', POST, 'op365_userid,op365_projectrole', 'op365_projectid,op365_userid,op365_projectrole'),
  ('ProjectMemberSync', 'Delete', 'op365_projectmember', POST, None, 'op365_projectid,op365_userid,op365_projectrole'),
  ('ProjectSync', 'Create', 'op365_project', POST, None, None),
  ('ProjectSync', 'Update', 'op365_project', POST, 'op365_projectmanagerid,op365_customerid,op365_contractvalue,statecode', 'op365_customerid'),
  ('ProjectSync', 'Delete', 'op365_project', POST, None, 'op365_customerid'),
  ('WbsNodeBudget', 'Create', 'op365_wbsnode', PRE, None, None),
  ('WbsNodeBudget', 'Update', 'op365_wbsnode', PRE, 'op365_budgetlabour,op365_budgetmaterials,op365_budgetother',
   'op365_budgetlabour,op365_budgetmaterials,op365_budgetother'),
  ('WbsNodeRollup', 'Create', 'op365_wbsnode', POST, None, None),
  ('WbsNodeRollup', 'Update', 'op365_wbsnode', POST,
   'op365_budgetlabour,op365_budgetmaterials,op365_budgetother,op365_budgettotal,op365_budgethours,op365_progresspct,op365_parentid,statecode',
   'op365_projectid'),
  ('WbsNodeRollup', 'Delete', 'op365_wbsnode', POST, None, 'op365_projectid'),
  ('WbsNodeDelete', 'Delete', 'op365_wbsnode', PREVAL, None, None),  # before the lookups are cleared
  ('WbsDependencyValidate', 'Create', 'op365_wbsdependency', PRE, None, None),
  ('WbsDependencyValidate', 'Update', 'op365_wbsdependency', PRE, 'op365_predecessorid,op365_successorid',
   'op365_predecessorid,op365_successorid'),
  ('BaselineReference', 'Create', 'op365_baseline', POST, None, None),
  ('BaselineReference', 'Update', 'op365_baseline', POST, 'op365_isreference', 'op365_projectid'),
  # Phase 3
  ('TimeEntryValidate', 'Create', 'op365_timeentry', PRE, None, None),
  ('TimeEntryValidate', 'Update', 'op365_timeentry', PRE, TE_IMAGE + ',statecode,op365_notes,op365_cost,op365_revenue', TE_IMAGE),
  ('TimeEntryDelete', 'Delete', 'op365_timeentry', PRE, None, 'statuscode'),
  ('ActualsRollup', 'Create', 'op365_timeentry', POST, None, None),
  ('ActualsRollup', 'Update', 'op365_timeentry', POST, 'op365_projectid,op365_wbsnodeid,op365_hours,op365_cost,statuscode', 'op365_projectid'),
  ('ActualsRollup', 'Delete', 'op365_timeentry', POST, None, 'op365_projectid'),
  ('MaterialUsageValidate', 'Create', 'op365_materialusage', PRE, None, None),
  ('MaterialUsageValidate', 'Update', 'op365_materialusage', PRE,
   'op365_projectid,op365_wbsnodeid,op365_itemid,op365_supplierid,op365_quantity,op365_unitcost', MU_IMAGE),
  ('ActualsRollup', 'Create', 'op365_materialusage', POST, None, None),
  ('ActualsRollup', 'Update', 'op365_materialusage', POST, 'op365_projectid,op365_wbsnodeid,op365_totalcost,statecode', 'op365_projectid'),
  ('ActualsRollup', 'Delete', 'op365_materialusage', POST, None, 'op365_projectid'),
]

# Custom APIs: unique name -> class, display name, description, binding table (None = unbound), function,
# request parameters (name, type, optional, description), response properties (name, type, description).
# Types: 0 Boolean, 1 DateTime, 2 Decimal, 7 Integer, 10 String, 11 StringArray, 12 Guid.
APIS = {
  'op365_SaveBaseline': ('SaveBaseline', 'Save Baseline',
      'Saves the current WBS budget and dates of the project as a new baseline', 'op365_project', False,
      [('Name', 10, True, 'Baseline name; default "Baseline <date>"'),
       ('KeepReference', 0, True, 'Keep the current reference baseline instead of replacing it (default false)')],
      [('BaselineId', 12, 'Id of the new baseline')]),
  'op365_SubmitTimeEntries': ('SubmitTimeEntries', 'Submit Time Entries',
      'Submits draft or rejected time entries for approval (approves them when time approval is off)', None, False,
      [('TimeEntryIds', 11, False, 'Ids of the time entries')],
      [('Count', 7, 'Number of entries submitted')]),
  'op365_DecideTimeEntries': ('DecideTimeEntries', 'Decide Time Entries',
      'Approves or rejects submitted time entries (project managers and administrators)', None, False,
      [('TimeEntryIds', 11, False, 'Ids of the time entries'),
       ('Approve', 0, False, 'True to approve, false to reject'),
       ('Note', 10, True, 'Decision note; required to reject')],
      [('Count', 7, 'Number of entries decided')]),
  'op365_GetLabourCost': ('GetLabourCost', 'Get Labour Cost',
      'Hourly cost of a resource on a date (requires the Cost Visibility profile)', None, True,
      [('ResourceId', 12, False, 'Resource'), ('Date', 1, False, 'Date')],
      [('HourlyCost', 2, 'Hourly cost valid on the date')]),
}


def one(url):
    v = S.get(API + url).json().get('value', [])
    return v[0] if v else None


def created_id(r):
    return r.headers['OData-EntityId'].rsplit('(', 1)[1].rstrip(')')


# ---------- assembly ----------
content = base64.b64encode(open(DLL, 'rb').read()).decode()
asm = one("pluginassemblies?$select=pluginassemblyid&$filter=name eq 'OpenProject365.Plugins'")
if asm:
    asm_id = asm['pluginassemblyid']
    ok(S.patch(API + f'pluginassemblies({asm_id})', json={'content': content}), 'assembly updated')
else:
    r = S.post(API + 'pluginassemblies', json={'name': 'OpenProject365.Plugins', 'content': content,
                                                'isolationmode': 2, 'sourcetype': 0})
    ok(r, 'assembly created'); asm_id = created_id(r)

# ---------- types ----------
types = {}
for cls in sorted({s[0] for s in STEPS} | {a[0] for a in APIS.values()}):
    t = one(f"plugintypes?$select=plugintypeid&$filter=typename eq '{NSP + cls}'")
    if t:
        types[cls] = t['plugintypeid']; continue
    r = S.post(API + 'plugintypes', json={'typename': NSP + cls, 'name': NSP + cls, 'friendlyname': cls,
                                          'pluginassemblyid@odata.bind': f'/pluginassemblies({asm_id})'})
    ok(r, 'type ' + cls); types[cls] = created_id(r)

# ---------- steps ----------
_msg = {}
def message(name):
    if name not in _msg:
        _msg[name] = one(f"sdkmessages?$select=sdkmessageid&$filter=name eq '{name}'")['sdkmessageid']
    return _msg[name]


for cls, msg, table, stage, filtering, image in STEPS:
    name = f'{cls}: {msg} of {table} ({ {PREVAL: "PreValidation", PRE: "PreOperation", POST: "PostOperation"}[stage]})'
    step = one(f"sdkmessageprocessingsteps?$select=sdkmessageprocessingstepid,filteringattributes&$filter=name eq '{name}'")
    if step:
        sid = step['sdkmessageprocessingstepid']
        if filtering and step.get('filteringattributes') != filtering:
            ok(S.patch(API + f'sdkmessageprocessingsteps({sid})', json={'filteringattributes': filtering}), 'filter ' + name)
        else:
            print('skip', name)
    else:
        flt = one(f"sdkmessagefilters?$select=sdkmessagefilterid&$filter=primaryobjecttypecode eq '{table}' "
                  f"and _sdkmessageid_value eq {message(msg)}")['sdkmessagefilterid']
        body = {'name': name, 'stage': stage, 'mode': 0, 'rank': 1, 'supporteddeployment': 0,
                'sdkmessageid@odata.bind': f'/sdkmessages({message(msg)})',
                'sdkmessagefilterid@odata.bind': f'/sdkmessagefilters({flt})',
                'plugintypeid@odata.bind': f'/plugintypes({types[cls]})'}
        if filtering:
            body['filteringattributes'] = filtering
        r = S.post(API + 'sdkmessageprocessingsteps', json=body)
        ok(r, name); sid = created_id(r)
    if image and not one(f"sdkmessageprocessingstepimages?$select=sdkmessageprocessingstepimageid"
                         f"&$filter=_sdkmessageprocessingstepid_value eq {sid}"):
        ok(S.post(API + 'sdkmessageprocessingstepimages', json={
            'name': 'PreImage', 'entityalias': 'PreImage', 'imagetype': 0, 'messagepropertyname': 'Target',
            'attributes': image, 'sdkmessageprocessingstepid@odata.bind': f'/sdkmessageprocessingsteps({sid})'}),
           '  pre-image ' + image)

# ---------- Custom APIs ----------
for uname, (cls, display, desc, bound, function, params, props) in APIS.items():
    capi = one(f"customapis?$select=customapiid&$filter=uniquename eq '{uname}'")
    if capi:
        capi_id = capi['customapiid']; print('skip', uname)
    else:
        body = {'uniquename': uname, 'name': display, 'displayname': display, 'description': desc,
                'bindingtype': 1 if bound else 0, 'isfunction': function, 'allowedcustomprocessingsteptype': 0,
                'PluginTypeId@odata.bind': f'/plugintypes({types[cls]})'}
        if bound:
            body['boundentitylogicalname'] = bound
        r = S.post(API + 'customapis', json=body)
        ok(r, 'custom api ' + uname); capi_id = created_id(r)
    for pname, typ, optional, pdesc in params:
        if one(f"customapirequestparameters?$select=customapirequestparameterid&$filter=_customapiid_value eq {capi_id} "
               f"and uniquename eq '{pname}'"):
            continue
        ok(S.post(API + 'customapirequestparameters', json={
            'uniquename': pname, 'name': f'{uname}.{pname}', 'displayname': pname, 'description': pdesc,
            'type': typ, 'isoptional': optional, 'CustomAPIId@odata.bind': f'/customapis({capi_id})'}), '  parameter ' + pname)
    for pname, typ, pdesc in props:
        if one(f"customapiresponseproperties?$select=customapiresponsepropertyid&$filter=_customapiid_value eq {capi_id} "
               f"and uniquename eq '{pname}'"):
            continue
        ok(S.post(API + 'customapiresponseproperties', json={
            'uniquename': pname, 'name': f'{uname}.{pname}', 'displayname': pname, 'description': pdesc,
            'type': typ, 'CustomAPIId@odata.bind': f'/customapis({capi_id})'}), '  response ' + pname)
