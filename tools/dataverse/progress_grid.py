"""Power Apps grid with the Progress Bar customizer on the Project and WBS Node tables. Idempotent; reads PAC_*.

Run after tools/pcf/push.sh (the grid references the op365_OP365.ProgressBar code component). The table-level
control applies to every view of the table; the Progress % column is then drawn as a bar from 0 to 100.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API
from meta import publish

TABLES = ['op365_project', 'op365_wbsnode']
CUSTOMIZER = 'op365_OP365.ProgressBar'
CLASSIC_GRID = '{E7A81278-8635-4d9e-8D4D-59480B391C5B}'

# Read-only Power Apps grid with the settings of the standard grid (no editing, filter and sort on, paging)
SETTINGS = dict(EnableEditing='no', DisableChildItemsEditing='no', EnableFiltering='yes', EnableSorting='yes',
                EnableGrouping='no', EnableAggregation='no', EnableColumnMoving='no', EnableMultipleSelection='yes',
                EnableRangeSelection='yes', EnableJumpBar='no', EnablePagination='yes', EnableDropdownColor='no',
                EnableStatusIcons='yes', EnableTypeIcons='no', NavigationTypesAllowed='all', ReflowBehavior='Reflow',
                ShowAvatar='yes', ShowFooter='yes', ShowColumnHeaders='yes', EnableStatusColumn='yes')


def grid(ff=None):
    params = '<data-set name="Items"><columnsDefaultView /></data-set>'
    params += ''.join(f'<{k} static="true" type="Enum">{v}</{k}>' for k, v in SETTINGS.items())
    params += f'<GridCustomizerControlFullName static="true" type="SingleLine.Text">{CUSTOMIZER}</GridCustomizerControlFullName>'
    factor = '' if ff is None else f' formFactor="{ff}"'
    return f'<customControl{factor} name="Microsoft.PowerApps.PowerAppsOneGrid"><parameters>{params}</parameters></customControl>'


XML = ('<controlDescriptions><controlDescription>'
       f'<customControl id="{CLASSIC_GRID}"><parameters /></customControl>'
       # the entry without formFactor is the one the grid reads (the classic Controls tab writes it too)
       + grid() + ''.join(grid(ff) for ff in (0, 1, 2)) + '</controlDescription></controlDescriptions>')

for table in TABLES:
    rows = S.get(API + f"customcontroldefaultconfigs?$select=customcontroldefaultconfigid"
                 f"&$filter=primaryentitytypecode eq '{table}'").json()['value']
    body = {'controldescriptionxml': XML}
    if rows:
        r = S.patch(API + f"customcontroldefaultconfigs({rows[0]['customcontroldefaultconfigid']})", json=body)
    else:
        r = S.post(API + 'customcontroldefaultconfigs', json=dict(body, primaryentitytypecode=table))
    if r.status_code >= 300:
        sys.exit(f'FAIL {table} {r.status_code} {r.text[:600]}')
    print('ok   Power Apps grid + Progress Bar on', table)
publish()
