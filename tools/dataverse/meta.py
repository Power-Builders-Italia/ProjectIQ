"""Shared Web API metadata helpers (labels, column definitions, idempotent create of tables/columns/lookups/keys)."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
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
    elif kind == 'datetime':
        a.update({'@odata.type': NS+'DateTimeAttributeMetadata', 'Format': 'DateAndTime',
                  'DateTimeBehavior': {'Value': 'UserLocal'}})
    elif kind == 'bool':
        a.update({'@odata.type': NS+'BooleanAttributeMetadata', 'DefaultValue': False,
                  'OptionSet': {'@odata.type': NS+'BooleanOptionSetMetadata', 'OptionSetType': 'Boolean',
                                'TrueOption': {'Value': 1, 'Label': L('Yes')},
                                'FalseOption': {'Value': 0, 'Label': L('No')}}})
    elif kind in ('choice', 'multichoice'):
        a.update({'@odata.type': NS+('PicklistAttributeMetadata' if kind == 'choice' else 'MultiSelectPicklistAttributeMetadata'),
                  'OptionSet': {'@odata.type': NS+'OptionSetMetadata', 'IsGlobal': False,
                                'OptionSetType': 'Picklist', 'Options': opts(kw['options'])}})
        if 'default' in kw:
            a['DefaultFormValue'] = BASE + kw['default']
    elif kind == 'file':
        a.update({'@odata.type': NS+'FileAttributeMetadata', 'MaxSizeInKB': kw.get('kb', 32768)})
    return a


def ok(r, what):
    if r.status_code >= 300:
        print('FAIL', what, r.status_code, r.text[:600]); sys.exit(1)
    print('ok  ', what)


def exists(url):
    return S.get(API+url).status_code == 200


def ent(t):
    return f"EntityDefinitions(LogicalName='{t}')"


def create_tables(tables):
    """tables: (schema, display, plural, description, (primary schema, label, max, required[, autonumber format]))"""
    for schema, disp, plural, desc, primary in tables:
        pn, pl, pmax, preq = primary[:4]
        ln = (P+schema).lower()
        if exists(ent(ln)+'?$select=LogicalName'):
            print('skip', ln); continue
        body = {'@odata.type': NS+'EntityMetadata', 'SchemaName': P+schema, 'DisplayName': L(disp),
                'DisplayCollectionName': L(plural), 'Description': L(desc), 'OwnershipType': 'UserOwned',
                'IsActivity': False, 'HasActivities': False, 'HasNotes': True,
                'IsAuditEnabled': {'Value': True, 'CanBeChanged': True, 'ManagedPropertyLogicalName': 'canmodifyauditsettings'},
                'Attributes': [dict(col('text', pn, pl, required=preq, max=pmax), IsPrimaryName=True)]}
        if len(primary) > 4:
            body['Attributes'][0]['AutoNumberFormat'] = primary[4]
        ok(S.post(API+'EntityDefinitions', json=body), 'table '+ln)


def status_reasons(table, values):
    attr = S.get(API + ent(table) + "/Attributes(LogicalName='statuscode')/Microsoft.Dynamics.CRM.StatusAttributeMetadata"
                 "?$select=LogicalName&$expand=OptionSet($select=Options)").json()
    have = {o['Value']: o['Label']['UserLocalizedLabel']['Label'] for o in attr['OptionSet']['Options']}
    for value, state, label in values:
        if have.get(value) == label:
            print('skip status', label); continue
        action = 'UpdateOptionValue' if value in have else 'InsertStatusValue'
        body = {'EntityLogicalName': table, 'AttributeLogicalName': 'statuscode', 'Value': value, 'Label': L(label),
                'SolutionUniqueName': 'OpenProject365'}
        body.update({'MergeLabels': True} if value in have else {'StateCode': state})
        ok(S.post(API + action, json=body), f'status {table}: {label}')


def enable_timeline(table, activities=False):
    """Notes (and activities) on a table; HasNotes in the create request is ignored, so set it afterwards.
    Activities cannot be turned off again once on."""
    md = S.get(API + ent(table)).json()
    if md['HasNotes'] and (md['HasActivities'] or not activities):
        print('skip timeline', table); return
    md['HasNotes'] = True
    if activities:
        md['HasActivities'] = True
    ok(S.put(API + ent(table), json=md, headers={'MSCRM.MergeLabels': 'true'}),
       f'notes{" and activities" if activities else ""} on {table}')


def create_columns(columns):
    for t, cols in columns.items():
        for c in cols:
            ln = c['SchemaName'].lower()
            if exists(ent(t)+f"/Attributes(LogicalName='{ln}')?$select=LogicalName"):
                print('skip', t, ln); continue
            ok(S.post(API+ent(t)+'/Attributes', json=c), f'column {t}.{ln}')


def create_lookups(lookups):
    """lookups: (referencing table, lookup schema, label, referenced table, kind, required).
    kind: True/'parental', False/'referential' (delete removes link), 'restrict', 'cascade' (delete cascades only)."""
    for t, lk, label, target, kind, required in lookups:
        ln = (P+lk).lower()
        if exists(ent(t)+f"/Attributes(LogicalName='{ln}')?$select=LogicalName"):
            print('skip', t, ln); continue
        merge = 'Cascade' if target in ('account', 'contact') else 'NoCascade'
        if kind in (True, 'parental'):
            cc = dict(Assign='Cascade', Delete='Cascade', Merge=merge, Reparent='Cascade', Share='Cascade', Unshare='Cascade')
        else:
            delete = {'restrict': 'Restrict', 'cascade': 'Cascade'}.get(kind, 'RemoveLink')
            cc = dict(Assign='NoCascade', Delete=delete, Merge=merge, Reparent='NoCascade', Share='NoCascade', Unshare='NoCascade')
        name = f"op365_{target.replace('op365_','')}_{t.replace('op365_','')}_{lk.lower()}"
        body = {'@odata.type': NS+'OneToManyRelationshipMetadata', 'SchemaName': name,
                'ReferencedEntity': target, 'ReferencingEntity': t, 'CascadeConfiguration': cc,
                'IsHierarchical': t == target,
                'AssociatedMenuConfiguration': {'Behavior': 'UseCollectionName', 'Group': 'Details', 'Order': 10000},
                'Lookup': {'@odata.type': NS+'LookupAttributeMetadata', 'SchemaName': P+lk,
                           'DisplayName': L(label), 'Description': L(''), 'RequiredLevel': req(required)}}
        ok(S.post(API+'RelationshipDefinitions', json=body), f'lookup {t}.{ln} -> {target}')


def create_keys(keys):
    for t, ks, label, attrs in keys:
        if exists(ent(t)+f"/Keys(LogicalName='{ks}')?$select=LogicalName"):
            print('skip key', ks); continue
        body = {'SchemaName': ks, 'DisplayName': L(label), 'KeyAttributes': attrs}
        ok(S.post(API+ent(t)+'/Keys', json=body), f'key {t}.{ks}')


def publish():
    ok(S.post(API+'PublishAllXml', json={}), 'publish')


def one(url):
    v = S.get(API + url).json().get('value', [])
    return v[0] if v else None


def grant_roles(roles):
    """roles: {role name: {table: (actions, depth)}}; creates missing roles in the root business unit, adds privileges."""
    root_bu = one('businessunits?$select=businessunitid&$filter=_parentbusinessunitid_value eq null')['businessunitid']
    schema = {}
    for name, grants in roles.items():
        role = one(f"roles?$select=roleid&$filter=name eq '{name}' and _businessunitid_value eq {root_bu}")
        if role:
            rid = role['roleid']
        else:
            r = S.post(API + 'roles', json={'name': name, 'businessunitid@odata.bind': f'/businessunits({root_bu})'},
                       headers={'Prefer': 'return=representation'})
            ok(r, 'role ' + name); rid = r.json()['roleid']
        privs = []
        for table, (actions, depth) in grants.items():
            if table not in schema:
                schema[table] = S.get(API + ent(table) + '?$select=SchemaName').json()['SchemaName']
            for a in actions:
                pname = f'prv{a}{schema[table]}'
                p = one(f"privileges?$select=privilegeid&$filter=name eq '{pname}'")
                if not p:
                    print('     no privilege', pname); continue
                privs.append({'@odata.type': NS + 'RolePrivilege', 'PrivilegeId': p['privilegeid'], 'Depth': depth,
                              'BusinessUnitId': root_bu, 'PrivilegeName': pname})
        ok(S.post(API + f'roles({rid})/Microsoft.Dynamics.CRM.AddPrivilegesRole', json={'Privileges': privs}),
           f'{len(privs)} privileges on {name}')
