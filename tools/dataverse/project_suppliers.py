"""Project suppliers: which suppliers work on a project and which WBS branches they see on the supplier portal.

- table op365_projectsupplier (child of the project, one row per project and supplier): Role, status reasons
  Active / Invited, Can Update Progress (filled on read from the variable op365_SupplierProgressUpdates);
- N:N op365_projectsupplier_wbsnode: the WBS nodes of the supplier's scope (the plugins add the descendants);
- form, view, Suppliers subgrid on the Project form (Purchasing tab) and Projects subgrid on the Supplier account form;
- privileges of the OP365 roles.

The plugins create the rows from RFQ invitations (Invited) and sent purchase orders (Active, with the WBS nodes of
the lines); the buyer adds others by hand. Idempotent; reads the PAC_* variables. Run plugins.py, settings_env.py
and tools/portal/supplier_portal.py afterwards, then backfill_project_suppliers.py for the existing orders.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from meta import (col, create_tables, create_columns, create_lookups, create_keys, status_reasons, grant_roles, publish,
                  exists, ok, L, NS, BASE as S0, S, API)
from viewlib import view
import formlib
from formlib import section, subgrid_cell, use_ids

T = 'op365_projectsupplier'
NN = 'op365_projectsupplier_wbsnode'

create_tables([('ProjectSupplier', 'Project Supplier', 'Project Suppliers',
                'Supplier that works on a project, with the WBS nodes it sees on the supplier portal',
                ('Name', 'Name', 400, False))])
create_lookups([
    (T, 'ProjectId', 'Project', 'op365_project', 'parental', True),
    (T, 'SupplierId', 'Supplier', 'account', 'restrict', True),
])
create_columns({T: [
    col('text', 'Role', 'Role', 'Trade or role of the supplier on the project (e.g. electrical works)', max=100),
    col('bool', 'CanUpdateProgress', 'Can Update Progress',
        'Read-only: the value of the environment variable Supplier Progress Updates, filled when the row is read '
        '(used by the supplier portal)'),
]})
status_reasons(T, [(1, 0, 'Active'), (S0, 0, 'Invited')])
create_keys([(T, 'op365_key_projectsupplier', 'Project and Supplier', ['op365_projectid', 'op365_supplierid'])])

if exists(f"RelationshipDefinitions(SchemaName='{NN}')?$select=SchemaName"):
    print('skip', NN)
else:
    menu = {'Behavior': 'UseLabel', 'Group': 'Details', 'Order': 10000}
    ok(S.post(API + 'RelationshipDefinitions', json={
        '@odata.type': NS + 'ManyToManyRelationshipMetadata', 'SchemaName': NN, 'IntersectEntityName': NN,
        'Entity1LogicalName': T, 'Entity2LogicalName': 'op365_wbsnode',
        'Entity1AssociatedMenuConfiguration': dict(menu, Label=L('WBS Scope')),
        'Entity2AssociatedMenuConfiguration': dict(menu, Label=L('Project Suppliers'))}), 'N:N ' + NN)

ALL = ['Create', 'Read', 'Write', 'Delete', 'Append', 'AppendTo', 'Assign', 'Share']
grant_roles({
    'OP365 Administrator': {T: (ALL, 'Global')},
    'OP365 User': {T: (['Create', 'Read', 'Write', 'Delete', 'Append', 'AppendTo'], 'Basic')},
})

COLS = [('op365_projectid', 220), ('op365_supplierid', 220), ('op365_role', 180), ('statuscode', 110)]
view(T, 'Active Project Suppliers', COLS, [('op365_projectid', False)], default=True)

use_ids('op365-project-suppliers')
formlib.form(T, 'Project Supplier', [formlib.tab('General', [('100%', [
    section(T, 'Project Supplier', ['op365_projectid', 'op365_supplierid', 'op365_role', 'statuscode']),
    section(T, 'WBS Scope', [('subgrid', 'wbs_scope', 'WBS Scope', 'op365_wbsnode', NN)]),
])])], description='Supplier of a project and its WBS scope on the supplier portal (ProjectIQ)')


def add_section(table, form_name, after, name, xml):
    """Inserts a section after the section named after, unless the form already has it (patches the live form)."""
    f = formlib.S.get(formlib.API + f"systemforms?$select=formid,formxml&$filter=objecttypecode eq '{table}' and type eq 2 "
                      f"and name eq '{form_name}'").json()['value'][0]
    if f'<section name="{name}"' in f['formxml']:
        print('skip', form_name, name); return
    head, tail = f['formxml'].split(f'<section name="{after}"', 1)
    end = tail.index('</section>') + len('</section>')
    formlib.ok(formlib.S.patch(formlib.API + f"systemforms({f['formid']})", json={
        'formxml': head + f'<section name="{after}"' + tail[:end] + xml + tail[end:]}), f'form {form_name}: {name}')


def grid_section(name, label, relationship):
    return section(T, label, [('subgrid', name, label, T, relationship)]).replace(
        f'<section name="{label.lower().replace(" ", "_")}"', f'<section name="{name}"', 1)


add_section('op365_project', 'Project', 'purchase_orders', 'suppliers',
            grid_section('suppliers', 'Suppliers', 'op365_project_projectsupplier_projectid'))
add_section('account', 'Supplier', 'document_alerts', 'supplier_projects',
            grid_section('supplier_projects', 'Projects', 'op365_account_projectsupplier_supplierid'))
publish()
