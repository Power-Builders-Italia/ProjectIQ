"""FormXml helpers shared by the phase scripts: compact layout description -> main forms."""
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
    'MultiSelectPicklist': '{4AA28AB7-9C13-4F57-A73D-AD894D048B5F}', 'Status': '{5D68B988-0661-4db2-BC3E-17598AD3BE6C}',
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
_prefix = ['op365-phase1-forms']
def use_ids(prefix):
    """Each script draws ids from its own namespace so that adding a form doesn't renumber the others."""
    global _ids
    _prefix[0] = prefix; _ids = itertools.count()


def gid():
    # deterministic ids (stable across runs) keep the unpacked FormXml diffs small
    return '{%s}' % uuid.uuid5(uuid.NAMESPACE_URL, f'{_prefix[0]}-{next(_ids)}')


def lbl(text):
    return f'<labels><label description="{escape(text)}" languagecode="1033" /></labels>'


def field_cell(table, name, pcf=None, showlabel=False):
    """name ending with '!' = read-only. pcf: field code component (e.g. op365_OP365.CostSummary) on every form factor;
    showlabel keeps the field label next to the component."""
    disabled = name.endswith('!')
    name = name.rstrip('!')
    a = attr(table, name)
    label = (a['DisplayName'].get('UserLocalizedLabel') or {}).get('Label', name)
    cls = CLASSID[a['AttributeType']]
    extra = ' disabled="true"' if disabled else ''
    cell = ''
    if pcf:
        uid = gid()
        extra += f' uniqueid="{uid}"'
        cell = '' if showlabel else ' showlabel="false"'
        _descriptions.append(
            f'<controlDescription forControl="{uid}">'
            f'<customControl id="{cls}"><parameters><datafieldname>{name}</datafieldname></parameters></customControl>'
            + ''.join(f'<customControl formFactor="{ff}" name="{pcf}"><parameters><value>{name}</value>'
                      '</parameters></customControl>' for ff in (0, 1, 2))
            + '</controlDescription>')
    return f'<cell id="{gid()}"{cell}>{lbl(label)}<control id="{name}" classid="{cls}" datafieldname="{name}"{extra} /></cell>'


def default_view(table, name=None):
    cond = f"name eq '{name}'" if name else 'isdefault eq true'
    return S.get(API + f"savedqueries?$select=savedqueryid&$filter=returnedtypecode eq '{table}' "
                 f"and querytype eq 0 and {cond}").json()['value'][0]['savedqueryid']


_descriptions = []


def subgrid_cell(name, label, target, relationship, rows=8, pcf=None, view=None, dataset='nodes', colspan=1):
    """pcf: name of a dataset code component (e.g. op365_OP365.GanttChart) that renders the subgrid on every form factor.
    relationship None = all records of the view (dashboards); view: view name instead of the default view;
    dataset: name of the code component's data-set; colspan: 3 to fill a dashboard section (columns '111')."""
    vid = default_view(target, view)
    rel = f'<RelationshipName>{relationship}</RelationshipName>' if relationship else ''
    params = (f'<ViewId>{{{vid}}}</ViewId><IsUserView>false</IsUserView>'
              f'{rel}<TargetEntityType>{target}</TargetEntityType>'
              '<AutoExpand>Fixed</AutoExpand><EnableQuickFind>false</EnableQuickFind><EnableViewPicker>false</EnableViewPicker>'
              '<EnableJumpBar>false</EnableJumpBar><ChartGridMode>Grid</ChartGridMode><VisualizationId />'
              f'<IsUserChart>false</IsUserChart><EnableChartPicker>false</EnableChartPicker><RecordsPerPage>{rows}</RecordsPerPage>')
    unique = ''
    if pcf:
        uid = gid()
        unique = f' uniqueid="{uid}"'
        dataset = (f'<data-set name="{dataset}"><ViewId>{{{vid}}}</ViewId><IsUserView>false</IsUserView>'
                   f'{rel}<TargetEntityType>{target}</TargetEntityType>'
                   '<EnableViewPicker>false</EnableViewPicker><EnableQuickFind>false</EnableQuickFind>'
                   f'<RecordsPerPage>{rows}</RecordsPerPage></data-set>')
        _descriptions.append(
            f'<controlDescription forControl="{uid}">'
            f'<customControl id="{SUBGRID}"><parameters>{params}</parameters></customControl>'
            + ''.join(f'<customControl formFactor="{ff}" name="{pcf}"><parameters>{dataset}</parameters></customControl>'
                      for ff in (0, 1, 2))
            + '</controlDescription>')
    return (f'<cell id="{gid()}" showlabel="{"false" if pcf else "true"}" rowspan="{rows}" colspan="{colspan}" auto="false">{lbl(label)}'
            f'<control id="{name}" classid="{SUBGRID}" indicationOfSubgrid="true"{unique}><parameters>{params}'
            '</parameters></control></cell>')


def timeline_cell():
    return (f'<cell id="{gid()}" showlabel="false" rowspan="20" colspan="1" auto="false">{lbl("Timeline")}'
            f'<control id="notescontrol" classid="{TIMELINE}" disabled="false" /></cell>')


def section(table, title, items, columns=2, grid=None):
    """items: column names, or ('subgrid', id, label, target, relationship, ...) / ('timeline',) / ('pcf', column, control);
    ('field', column, control) is a labelled column drawn by a field code component, laid out like a column name.
    grid: explicit columns attribute (dashboards use '111')."""
    rows, pending = [], []
    for it in items:
        if isinstance(it, tuple) and it[0] == 'field':
            pending.append(field_cell(table, it[1], it[2], showlabel=True))
            if len(pending) == columns:
                rows.append(pending); pending = []
            continue
        if isinstance(it, tuple):
            if pending:
                rows.append(pending); pending = []
            if it[0] == 'pcf':
                rows.append([field_cell(table, it[1], it[2])])
            else:
                rows.append([subgrid_cell(*it[1:]) if it[0] == 'subgrid' else timeline_cell()])
            continue
        pending.append(field_cell(table, it))
        if len(pending) == columns:
            rows.append(pending); pending = []
    if pending:
        rows.append(pending)
    special = any(isinstance(i, tuple) and i[0] != 'field' for i in items)
    cols = grid or (1 if special else columns)
    body = ''.join('<row>' + ''.join(r) + '</row>' for r in rows)
    return (f'<section name="{title.lower().replace(" ", "_")}" showlabel="true" showbar="false" columns="{cols}" '
            f'id="{gid()}">{lbl(title)}<rows>{body}</rows></section>')


def tab(title, columns):
    """columns: list of (width, [section xml])."""
    cols = ''.join(f'<column width="{w}"><sections>{"".join(s)}</sections></column>' for w, s in columns)
    return (f'<tab name="{title.lower().replace(" ", "_")}" id="{gid()}" expanded="true" showlabel="true" '
            f'verticallayout="true">{lbl(title)}<columns>{cols}</columns></tab>')


def webresource(name, path, display):
    import base64
    content = base64.b64encode(open(path, 'rb').read()).decode()
    v = S.get(API + f"webresourceset?$select=webresourceid&$filter=name eq '{name}'").json()['value']
    body = {'displayname': display, 'content': content}
    if v:
        ok(S.patch(API + f"webresourceset({v[0]['webresourceid']})", json=body), 'update web resource ' + name)
    else:
        body.update({'name': name, 'webresourcetype': {'.html': 1, '.htm': 1, '.css': 2, '.svg': 11}.get(os.path.splitext(name)[1], 3)})
        ok(S.post(API + 'webresourceset', json=body), 'create web resource ' + name)


def onload(library, function):
    return (f'<formLibraries><Library name="{library}" libraryUniqueId="{gid()}" /></formLibraries>'
            '<events><event name="onload" application="false" active="false"><Handlers>'
            f'<Handler functionName="{function}" libraryName="{library}" handlerUniqueId="{gid()}" enabled="true" '
            'parameters="" passExecutionContext="true" /></Handlers></event></events>')


def form(table, name, tabs, replace=None, description='', extra='', form_type=2):
    """form_type: 2 main, 7 quick create, 0 dashboard (table 'none')."""
    descriptions = ''
    if _descriptions:
        descriptions = '<controlDescriptions>' + ''.join(_descriptions) + '</controlDescriptions>'
        _descriptions.clear()
    xml = '<form><tabs>' + ''.join(tabs) + '</tabs>' + extra + descriptions + '</form>'
    existing = None
    for n in [name] + ([replace] if replace else []):
        v = S.get(API + f"systemforms?$select=formid&$filter=objecttypecode eq '{table}' and type eq {form_type} "
                  f"and name eq '{n}'").json()['value']
        if v:
            existing = v[0]['formid']; break
    body = {'name': name, 'description': description, 'formxml': xml}
    if existing:
        ok(S.patch(API + f'systemforms({existing})', json=body), f'update form {table}: {name}')
    else:
        body.update({'objecttypecode': table, 'type': form_type, 'formactivationstate': 1})
        r = S.post(API + 'systemforms', json=body)
        ok(r, f'create form {table}: {name}')
        existing = r.headers['OData-EntityId'].split('(')[-1].rstrip(')')
    # renamed forms can lose their localized name, and a form without one fails to import
    ok(S.post(API + 'SetLocLabels', json={
        'EntityMoniker': {'@odata.type': 'Microsoft.Dynamics.CRM.systemform', 'formid': existing},
        'AttributeName': 'name',
        'Labels': [{'@odata.type': 'Microsoft.Dynamics.CRM.LocalizedLabel', 'Label': name, 'LanguageCode': 1033}]}),
       f'label form {name}')
    return existing
