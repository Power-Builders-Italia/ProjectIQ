"""Phase 2 security: OP365 roles on the project tables.

OP365 User gets User-level privileges only: a project and its children become visible
through the project access teams (OP365 Project Manager / Contributor / Reader), which the
ProjectMemberSync plugin keeps aligned with Project Member rows. Children are parental, so
they inherit the share of the project.
Idempotent; reads the PAC_* environment variables.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from meta import grant_roles

ALL = ['Create', 'Read', 'Write', 'Delete', 'Append', 'AppendTo', 'Assign', 'Share']
CHILDREN = ['op365_projectmember', 'op365_wbsnode', 'op365_wbsdependency', 'op365_wbsallocation',
            'op365_baseline', 'op365_baselinenode']

user = {'op365_project': (['Read', 'Write', 'Append', 'AppendTo', 'Share'], 'Basic')}
user.update({t: (['Create', 'Read', 'Write', 'Delete', 'Append', 'AppendTo'], 'Basic') for t in CHILDREN})

grant_roles({
    'OP365 Administrator': {t: (ALL, 'Global') for t in ['op365_project'] + CHILDREN},
    'OP365 User': user,
})
