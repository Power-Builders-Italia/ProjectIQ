"""SharePoint document management: Documents on Project, Purchase Order and Supplier Document.

Turns on IsDocumentManagementEnabled on the three tables (solution metadata) and grants the document location and
SharePoint site privileges to the ProjectIQ roles. With SHAREPOINT_SITE_URL set, also registers that site as the
default SharePoint site of the environment (environment data, not in the solution): the document libraries
(op365_project, op365_purchaseorder, op365_supplierdocument) and one folder per record are then created by Dataverse
the first time a user opens Documents on a record. Idempotent; reads the PAC_* environment variables.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API
from meta import ent, grant_roles, ok, one, publish

TABLES = ['op365_project', 'op365_purchaseorder', 'op365_supplierdocument']
ALL = ['Create', 'Read', 'Write', 'Delete', 'Append', 'AppendTo', 'Assign', 'Share']

for table in TABLES:
    md = S.get(API + ent(table)).json()
    if md['IsDocumentManagementEnabled']:
        print('skip documents', table); continue
    md['IsDocumentManagementEnabled'] = True
    ok(S.put(API + ent(table), json=md, headers={'MSCRM.MergeLabels': 'true'}), f'documents on {table}')

# Users create the folder of a record they can see (Basic) and read every location (folders of shared projects);
# SharePoint permissions still decide which files they see.
grant_roles({
    'OP365 Administrator': {'sharepointdocumentlocation': (ALL, 'Global'), 'sharepointsite': (['Read'], 'Global')},
    'OP365 User': {'sharepointdocumentlocation': (['Create', 'Write', 'Append'], 'Basic'),
                   'sharepointsite': (['Read'], 'Global')},
})
grant_roles({'OP365 User': {'sharepointdocumentlocation': (['Read', 'AppendTo'], 'Global')}})

site_url = os.environ.get('SHAREPOINT_SITE_URL', '').strip().rstrip('/')
if site_url:
    site = one(f"sharepointsites?$select=sharepointsiteid,isdefault&$filter=absoluteurl eq '{site_url}'")
    if site and site['isdefault']:
        print('skip site', site_url)
    elif site:
        ok(S.patch(API + f"sharepointsites({site['sharepointsiteid']})", json={'isdefault': True}), 'default site ' + site_url)
    else:
        ok(S.post(API + 'sharepointsites', json={'name': 'ProjectIQ Documents', 'absoluteurl': site_url, 'isdefault': True}),
           'site ' + site_url)
else:
    print('skip site: SHAREPOINT_SITE_URL not set')

publish()
