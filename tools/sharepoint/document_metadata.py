"""ProjectIQ columns of the SharePoint document libraries (Project, Purchase Order, Supplier Document).

Adds the columns of tools/dataverse/flow_definitions.py to the op365_project, op365_purchaseorder and
op365_supplierdocument libraries of the site (and to their default view), then prints the library ids: the values
of the environment variables op365_ProjectLibraryId, op365_PurchaseOrderLibraryId and op365_SupplierDocumentLibraryId
(GitHub environment secrets OP365_*_LIBRARY_ID for deploy-test). New files are tagged by the "Tag ... documents" flows.

--backfill also tags the files already in the libraries: reads the record of each folder from Dataverse (PAC_*
environment variables of the same environment) and fills the empty columns; files outside a record folder are skipped.

Uses the CLI for Microsoft 365 signed in as a site owner (m365 login). Idempotent. The site URL comes from
SHAREPOINT_SITE_URL and is never printed.
"""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dataverse'))
from flow_definitions import COLUMNS, LIBRARIES, MANAGER, RECORDS, library_columns, record_values

SITE = os.environ.get('SHAREPOINT_SITE_URL', '').strip().rstrip('/')
if not SITE:
    sys.exit('Set SHAREPOINT_SITE_URL to the SharePoint site of the ProjectIQ document libraries')
RECORD_TYPES = [RECORDS[library][1] for library in RECORDS]


def m365(*args):
    r = subprocess.run(['m365', *args, '--output', 'json'], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout).strip().replace(SITE, '<site>'))
    return json.loads(r.stdout) if r.stdout.strip() else None


def field_xml(name):
    label, kind, field_id = COLUMNS[name]
    attrs = f'ID="{{{field_id}}}" Name="{name}" StaticName="{name}" DisplayName="{label}" Group="ProjectIQ"'
    if name == 'ProjectIQRecordId':
        attrs += ' ShowInNewForm="FALSE" ShowInEditForm="FALSE"'
    if kind == 'Choice':
        choices = ''.join(f'<CHOICE>{c}</CHOICE>' for c in RECORD_TYPES)
        return f'<Field Type="Choice" {attrs} Format="Dropdown"><CHOICES>{choices}</CHOICES></Field>'
    if kind == 'User':
        return f'<Field Type="User" {attrs} List="UserInfo" UserSelectionMode="PeopleOnly" ShowField="ImnName" />'
    return f'<Field Type="Text" {attrs} MaxLength="255" />'


def ensure_columns(library):
    fields = {f['InternalName'] for f in m365('spo', 'field', 'list', '--webUrl', SITE, '--listUrl', library)}
    view = next(v for v in m365('spo', 'list', 'view', 'list', '--webUrl', SITE, '--listUrl', library) if v.get('DefaultView'))
    for name in library_columns(library):
        if name in fields:
            print('skip ', library, name); continue
        # AddFieldInternalNameHint: keep Name as internal name (SharePoint otherwise derives it from DisplayName)
        m365('spo', 'field', 'add', '--webUrl', SITE, '--listUrl', library, '--xml', field_xml(name),
             '--options', 'AddFieldInternalNameHint')
        if name != 'ProjectIQRecordId':
            m365('spo', 'list', 'view', 'field', 'add', '--webUrl', SITE, '--listUrl', library,
                 '--viewId', view['Id'], '--id', COLUMNS[name][2])
        print('ok   ', library, name)
    return m365('spo', 'list', 'get', '--webUrl', SITE, '--url', library, '--properties', 'Id')['Id']


def backfill(library):
    from dv import S, API  # Dataverse only for the backfill
    entity_set, record_type, select, expand, _ = RECORDS[library]
    items = m365('spo', 'listitem', 'list', '--webUrl', SITE, '--listUrl', library,
                 '--fields', 'Id,FileRef,FSObjType,ProjectIQRecordId', '--pageSize', '500')
    done = skipped = 0
    for item in items:
        if str(item.get('FSObjType')) != '0' or item.get('ProjectIQRecordId'):
            continue
        parts = item['FileRef'].split(f'/{library}/', 1)[-1].split('/')
        hex_id = parts[0][-32:].lower() if len(parts) > 1 else ''
        if not re.fullmatch('[0-9a-f]{32}', hex_id):
            skipped += 1; continue
        record_id = f'{hex_id[:8]}-{hex_id[8:12]}-{hex_id[12:16]}-{hex_id[16:20]}-{hex_id[20:]}'
        r = S.get(API + f'{entity_set}({record_id})?$select={select}&$expand={expand}')
        if r.status_code == 404:
            skipped += 1; continue
        r.raise_for_status()
        values = record_values(library, r.json())
        args = ['--ProjectIQRecordType', record_type, '--ProjectIQRecordId', record_id]
        for column, value in values.items():
            if value and column == MANAGER:
                args += [f'--{column}', json.dumps([{'Key': f'i:0#.f|membership|{value}'}])]
            elif value:
                args += [f'--{column}', str(value)]
        m365('spo', 'listitem', 'set', '--webUrl', SITE, '--listUrl', library, '--id', str(item['Id']), '--systemUpdate', *args)
        done += 1
    print(f'backfill {library}: {done} file(s) tagged, {skipped} outside a record folder')


for library, (variable, _, _) in LIBRARIES.items():
    library_id = ensure_columns(library)
    print(f'{variable} = {library_id}')
    if '--backfill' in sys.argv:
        backfill(library)
