"""External resources: a resource linked to a supplier contact records its hours on the supplier portal.

- op365_resource: lookups Contact (op365_contactid, the supplier's person) and Supplier (op365_supplierid, read-only,
  the contact's company, filled by the plugin ResourceLink); a resource has a User or a Contact, never both;
- Resource form: section External Resource; Active Resources view with the two new columns.

The supplier portal page Timesheet (tools/portal/supplier_portal.py) shows the contact's resource and lets it record
hours on the WBS nodes of its company's scope (Project Supplier rows). Idempotent; reads the PAC_* variables. Run
plugins.py, settings_env.py, supplier_email_templates.py and tools/portal/supplier_portal.py afterwards.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from meta import create_lookups, publish
from viewlib import view
import formlib
from formlib import section, use_ids

T = 'op365_resource'

create_lookups([
    (T, 'ContactId', 'Contact', 'contact', False, False),
    (T, 'SupplierId', 'Supplier', 'account', False, False),
])

view(T, 'Active Resources',
     [('op365_name', 200), ('op365_role', 150), ('op365_hourlycost', 110), ('op365_weeklyhours', 110),
      ('op365_userid', 180), ('op365_contactid', 180), ('op365_supplierid', 180)], [('op365_name', False)], default=True)


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


use_ids('op365-external-resource')
add_section(T, 'Resource', 'resource', 'external_resource',
            section(T, 'External Resource', ['op365_contactid', 'op365_supplierid']))
publish()
