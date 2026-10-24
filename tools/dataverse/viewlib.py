"""Saved query (system view) helpers shared by the phase scripts."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API

ACTIVE = [('statecode', 'eq', '0')]


def ok(r, what):
    if r.status_code >= 300:
        print('FAIL', what, r.status_code, r.text[:600]); sys.exit(1)
    print('ok  ', what)


_meta = {}
def meta(table):
    if table not in _meta:
        _meta[table] = S.get(API + f"EntityDefinitions(LogicalName='{table}')"
                             "?$select=ObjectTypeCode,PrimaryIdAttribute").json()
    return _meta[table]


def fetch(table, cols, order, conds, filter_type='and', quickfind=None, active=True, also=()):
    pk = meta(table)['PrimaryIdAttribute']
    x = f'<fetch version="1.0" mapping="logical"><entity name="{table}">'
    x += ''.join(f'<attribute name="{c}" />' for c in dict.fromkeys(cols + [pk]))
    for attr, desc in order:
        x += f'<order attribute="{attr}" descending="{str(desc).lower()}" />'
    base = (ACTIVE if active else []) + list(also)
    if base:
        x += f'<filter type="and">' + ''.join(
            f'<condition attribute="{a}" operator="{o}" value="{v}" />' for a, o, v in base) + '</filter>'
    if conds:
        x += f'<filter type="{filter_type}">' + ''.join(
            f'<condition attribute="{a}" operator="{o}"' + (f' value="{v}"' if v is not None else '') + ' />'
            for a, o, v in conds) + '</filter>'
    if quickfind:
        x += '<filter type="or" isquickfindfields="1">' + ''.join(
            f'<condition attribute="{a}" operator="like" value="{{0}}" />' for a in quickfind) + '</filter>'
    return x + '</entity></fetch>'


def layout(table, cols):
    m = meta(table)
    cells = ''.join(f'<cell name="{c}" width="{w}" />' for c, w in cols)
    return (f'<grid name="resultset" object="{m["ObjectTypeCode"]}" jump="{cols[0][0]}" select="1" icon="1" preview="1">'
            f'<row name="result" id="{m["PrimaryIdAttribute"]}">{cells}</row></grid>')


def view(table, name, cols, order, conds=(), filter_type='and', default=False, querytype=0, quickfind=None,
         replace=None, description='', active=True, also=()):
    """cols: list of (attribute, width). replace: name of an existing view to rename/overwrite.
    active=False drops the statecode = Active filter; also: conditions ANDed with conds."""
    body = {'name': name, 'description': description, 'returnedtypecode': table, 'querytype': querytype,
            'fetchxml': fetch(table, [c for c, _ in cols], order, list(conds), filter_type, quickfind, active, also),
            'layoutxml': layout(table, cols)}
    if default:
        body['isdefault'] = True
    existing = None
    for n in ([name] + ([replace] if replace else [])):
        v = S.get(API + f"savedqueries?$select=savedqueryid&$filter=returnedtypecode eq '{table}' "
                  f"and querytype eq {querytype} and name eq '{n}'").json()['value']
        if v:
            existing = v[0]['savedqueryid']; break
    if existing:
        ok(S.patch(API + f'savedqueries({existing})', json=body), f'update view {table}: {name}')
    else:
        ok(S.post(API + 'savedqueries', json=body), f'create view {table}: {name}')
