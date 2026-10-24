"""Phase 1 system views (spec views 6, 9-14, 24, 25 plus Quick Find and default views of the F1 tables).

Views needing rollups from later phases (projects, spend, usage) are added with those phases.
Idempotent: views are matched by table + name; default views are updated in place.
"""
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


def fetch(table, cols, order, conds, filter_type='and', quickfind=None):
    pk = meta(table)['PrimaryIdAttribute']
    x = f'<fetch version="1.0" mapping="logical"><entity name="{table}">'
    x += ''.join(f'<attribute name="{c}" />' for c in dict.fromkeys(cols + [pk]))
    for attr, desc in order:
        x += f'<order attribute="{attr}" descending="{str(desc).lower()}" />'
    x += f'<filter type="and">' + ''.join(
        f'<condition attribute="{a}" operator="{o}" value="{v}" />' for a, o, v in ACTIVE) + '</filter>'
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
         replace=None, description=''):
    """cols: list of (attribute, width). replace: name of an existing view to rename/overwrite."""
    body = {'name': name, 'description': description, 'returnedtypecode': table, 'querytype': querytype,
            'fetchxml': fetch(table, [c for c, _ in cols], order, list(conds), filter_type, quickfind),
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


# ---------- Account (spec 6, 9-13) ----------
CUST = [('name', 250), ('op365_customertype', 120), ('op365_vatnumber', 130), ('primarycontactid', 180),
        ('telephone1', 120), ('emailaddress1', 200)]
SUPP = [('name', 250), ('op365_supplierstatus', 120), ('op365_suppliercategory', 150), ('op365_vatnumber', 130),
        ('op365_expireddocs', 110), ('op365_expiringdocs', 110)]
view('account', 'All Customers', CUST, [('name', False)], [('op365_iscustomer', 'eq', '1')], default=True)
view('account', 'Prospects', CUST, [('name', False)], [('op365_customertype', 'eq', '365000000')])
view('account', 'All Suppliers', SUPP, [('name', False)], [('op365_issupplier', 'eq', '1')])
view('account', 'Active Suppliers', SUPP, [('name', False)],
     [('op365_issupplier', 'eq', '1'), ('op365_supplierstatus', 'eq', '365000000')])
view('account', 'Blocked Suppliers', SUPP, [('name', False)],
     [('op365_issupplier', 'eq', '1'), ('op365_supplierstatus', 'eq', '365000001')])
view('account', 'Suppliers with Document Alerts', SUPP, [('op365_expireddocs', True), ('op365_expiringdocs', True)],
     [('op365_expireddocs', 'gt', '0'), ('op365_expiringdocs', 'gt', '0')], filter_type='or')
view('account', 'Quick Find Active Accounts', [('name', 250), ('op365_vatnumber', 130), ('primarycontactid', 180)],
     [('name', False)], querytype=4, default=True, quickfind=['name', 'op365_vatnumber', 'primarycontactid'])

# ---------- Item (spec 14) ----------
ITEM = [('op365_code', 120), ('op365_name', 250), ('op365_category', 150), ('op365_defaultsupplierid', 200),
        ('op365_uom', 80), ('op365_unitcost', 110)]
view('op365_item', 'All Items', ITEM, [('op365_code', False)], default=True, replace='Active Items')
view('op365_item', 'Quick Find Active Items', ITEM, [('op365_code', False)], querytype=4, default=True,
     quickfind=['op365_code', 'op365_name', 'op365_category'])
view('op365_itemsupplier', 'Active Item Suppliers',
     [('op365_itemid', 200), ('op365_supplierid', 200), ('op365_suppliercode', 120), ('op365_price', 110),
      ('op365_leadtimedays', 110), ('op365_minimumlot', 110)], [('op365_itemid', False)], default=True)
view('op365_supplierdocument', 'Active Supplier Documents',
     [('op365_documenttype', 140), ('op365_description', 250), ('op365_supplierid', 200), ('op365_number', 110),
      ('op365_issuedate', 110), ('op365_expirydate', 110)], [('op365_expirydate', False)], default=True)

# ---------- Resources (spec 24, 25) ----------
view('op365_resource', 'Active Resources',
     [('op365_name', 200), ('op365_role', 150), ('op365_hourlycost', 110), ('op365_weeklyhours', 110),
      ('op365_userid', 180)], [('op365_name', False)], default=True)
view('op365_resourcecost', 'Active Resource Costs',
     [('op365_resourceid', 200), ('op365_validfrom', 110), ('op365_hourlycost', 110)],
     [('op365_resourceid', False), ('op365_validfrom', True)], default=True)
view('op365_absence', 'Absences',
     [('op365_resourceid', 200), ('op365_absencetype', 120), ('op365_fromdate', 110), ('op365_todate', 110),
      ('op365_hours', 80), ('op365_notes', 250)], [('op365_fromdate', True)], default=True, replace='Active Absences')
