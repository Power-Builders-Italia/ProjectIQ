"""SharePoint URL of the supplier documents filed before the column existed (one-off, idempotent).

The flow File approved supplier documents fills op365_sharepointurl with the link to the file. Documents it moved
earlier have no file in Dataverse and no URL: this script sets their URL to the SharePoint folder of the record
(site / library / record folder, from the document locations), because the file name is no longer known.
Only approved documents without file and without URL that have a record folder are changed.
Reads the PAC_* variables of the target environment; --dry-run only prints.
"""
import os, sys
from urllib.parse import quote
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API

DRY = '--dry-run' in sys.argv


def get(path):
    return S.get(API + path).json()['value']


sites = {s['sharepointsiteid']: s['absoluteurl'].rstrip('/') for s in get('sharepointsites?$select=absoluteurl')}
locations = {l['sharepointdocumentlocationid']: l for l in get(
    'sharepointdocumentlocations?$select=relativeurl,_parentsiteorlocation_value,_regardingobjectid_value&$filter=statecode eq 0')}


def url(location):
    """Absolute URL of a document location: its relative URLs up to the site."""
    parts = []
    while location:
        parts.insert(0, quote(location['relativeurl'], safe=''))
        parent = location['_parentsiteorlocation_value']
        if parent in sites:
            return sites[parent] + '/' + '/'.join(parts)
        location = locations.get(parent)
    return None


folders = {l['_regardingobjectid_value']: l for l in locations.values() if l['_regardingobjectid_value']}
docs = get('op365_supplierdocuments?$select=op365_description&$filter=statuscode eq 1 and op365_file eq null '
           'and op365_sharepointurl eq null')
done = 0
for d in docs:
    folder = folders.get(d['op365_supplierdocumentid'])
    link = url(folder) if folder else None
    if not link:
        continue
    print('set ' if not DRY else 'would set', d['op365_description'], link)
    if not DRY:
        r = S.patch(API + f"op365_supplierdocuments({d['op365_supplierdocumentid']})", json={'op365_sharepointurl': link})
        if r.status_code >= 300:
            sys.exit(f"{d['op365_supplierdocumentid']}: {r.status_code} {r.text[:300]}")
    done += 1
print(f'{done} of {len(docs)} approved documents without file and URL', 'would be updated' if DRY else 'updated')
