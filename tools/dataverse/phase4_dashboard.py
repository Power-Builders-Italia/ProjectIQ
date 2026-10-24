"""Phase 4 Spend dashboard: system charts on purchase orders and supplier invoices, open orders and invoices to review.

Idempotent: charts are matched by table + name, the dashboard by name. Run after phase4_views.py.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API
from formlib import ok, lbl, gid, form, use_ids, default_view, SUBGRID

use_ids('op365-phase4-dashboard')
CANCELLED = 365000003

PRESENTATION = {
    'Bar': ('<Chart Palette="None" PaletteCustomColors="15,108,189; 0,120,212; 98,100,167; 0,153,188; 202,80,16; 135,100,184">'
            '<Series><Series ChartType="Bar" IsValueShownAsLabel="True" Font="{0}, 9.5px" LabelForeColor="59, 59, 59" '
            'CustomProperties="PointWidth=0.75, MaxPixelPointWidth=40"><SmartLabelStyle Enabled="True" /></Series></Series>'
            '<ChartAreas><ChartArea BorderColor="White" BorderDashStyle="Solid"><AxisY LabelAutoFitMinFontSize="8" TitleForeColor="59, 59, 59" '
            'TitleFont="{0}, 10.5px" LineColor="165, 172, 181" IntervalAutoMode="VariableCount"><MajorGrid LineColor="239, 242, 246" />'
            '<MajorTickMark LineColor="165, 172, 181" /><LabelStyle Font="{0}, 10.5px" ForeColor="59, 59, 59" /></AxisY>'
            '<AxisX LabelAutoFitMinFontSize="8" TitleForeColor="59, 59, 59" TitleFont="{0}, 10.5px" LineColor="165, 172, 181" '
            'IntervalAutoMode="VariableCount"><MajorTickMark LineColor="165, 172, 181" /><MajorGrid LineColor="Transparent" />'
            '<LabelStyle Font="{0}, 10.5px" ForeColor="59, 59, 59" /></AxisX></ChartArea></ChartAreas>'
            '<Titles><Title Alignment="TopLeft" DockingOffset="-3" Font="{0}, 13px" ForeColor="59, 59, 59"></Title></Titles></Chart>'),
    'Pie': ('<Chart Palette="None" PaletteCustomColors="15,108,189; 0,120,212; 98,100,167; 0,153,188; 202,80,16; 135,100,184">'
            '<Series><Series ChartType="Doughnut" IsValueShownAsLabel="True" Font="{0}, 9.5px" LabelForeColor="59, 59, 59" '
            'CustomProperties="PieLabelStyle=Outside, PieDrawingStyle=Default"><SmartLabelStyle Enabled="True" /></Series></Series>'
            '<ChartAreas><ChartArea BorderColor="White" BorderDashStyle="Solid"><Area3DStyle Enable3D="False" /></ChartArea></ChartAreas>'
            '<Legends><Legend Alignment="Center" LegendStyle="Table" Docking="Right" IsEquallySpacedItems="True" Font="{0}, 11px" '
            'ShadowColor="0, 0, 0, 0" ForeColor="59, 59, 59" /></Legends>'
            '<Titles><Title Alignment="TopLeft" DockingOffset="-3" Font="{0}, 13px" ForeColor="59, 59, 59"></Title></Titles></Chart>'),
}


def chart(table, name, measure, aggregate, group, kind, description, conditions=()):
    filt = ''.join(f'<condition attribute="{a}" operator="{o}" value="{v}" />' for a, o, v in conditions)
    data = (f'<datadefinition><fetchcollection><fetch mapping="logical" aggregate="true"><entity name="{table}">'
            f'<attribute name="{measure}" aggregate="{aggregate}" alias="aggregate_column" />'
            f'<attribute name="{group}" groupby="true" alias="groupby_column" />'
            + (f'<filter type="and">{filt}</filter>' if filt else '') +
            '</entity></fetch></fetchcollection><categorycollection><category><measurecollection>'
            '<measure alias="aggregate_column" /></measurecollection></category></categorycollection></datadefinition>')
    body = {'name': name, 'description': description, 'primaryentitytypecode': table, 'datadescription': data,
            'presentationdescription': PRESENTATION[kind], 'isdefault': False}
    v = S.get(API + f"savedqueryvisualizations?$select=savedqueryvisualizationid&$filter=primaryentitytypecode eq '{table}' "
              f"and name eq '{name}'").json()['value']
    if v:
        ok(S.patch(API + f"savedqueryvisualizations({v[0]['savedqueryvisualizationid']})", json=body), f'update chart {name}')
        return v[0]['savedqueryvisualizationid']
    r = S.post(API + 'savedqueryvisualizations', json=body)
    ok(r, f'create chart {name}')
    return r.headers['OData-EntityId'].split('(')[-1].rstrip(')')


def cell(name, label, target, view, chart_id=None, rows=12):
    vid = default_view(target, view)
    viz = f'<VisualizationId>{{{chart_id}}}</VisualizationId>' if chart_id else '<VisualizationId />'
    params = (f'<ViewId>{{{vid}}}</ViewId><IsUserView>false</IsUserView><TargetEntityType>{target}</TargetEntityType>'
              '<AutoExpand>Fixed</AutoExpand><EnableQuickFind>false</EnableQuickFind><EnableViewPicker>false</EnableViewPicker>'
              f'<EnableJumpBar>false</EnableJumpBar><ChartGridMode>{"Chart" if chart_id else "Grid"}</ChartGridMode>{viz}'
              f'<IsUserChart>false</IsUserChart><EnableChartPicker>false</EnableChartPicker><RecordsPerPage>{rows}</RecordsPerPage>')
    return (f'<cell id="{gid()}" showlabel="true" rowspan="{rows}" colspan="1" auto="false">{lbl(label)}'
            f'<control id="{name}" classid="{SUBGRID}" indicationOfSubgrid="true"><parameters>{params}</parameters></control></cell>')


def section(name, columns, cells):
    return (f'<section name="{name}" showlabel="false" showbar="false" columns="{columns}" id="{gid()}">{lbl(name)}'
            f'<rows><row>{"".join(cells)}</row></rows></section>')


PO, INV = 'op365_purchaseorder', 'op365_supplierinvoice'
NOT_CANCELLED = [('statuscode', 'ne', CANCELLED)]
by_supplier = chart(PO, 'Spend by Supplier', 'op365_totalamount', 'sum', 'op365_supplierid', 'Bar',
                    'Purchase orders not cancelled, by supplier', NOT_CANCELLED)
by_project = chart(PO, 'Spend by Project', 'op365_totalamount', 'sum', 'op365_projectid', 'Bar',
                   'Purchase orders not cancelled, by project', NOT_CANCELLED)
by_status = chart(PO, 'Purchase Orders by Status', 'op365_purchaseorderid', 'count', 'statuscode', 'Pie', 'Number of purchase orders by status')

tab = (f'<tab name="spend" id="{gid()}" expanded="true" showlabel="false" verticallayout="true">{lbl("Spend")}<columns>'
       '<column width="100%"><sections>'
       + section('charts', '111', [cell('BySupplier', 'Spend by Supplier', PO, 'All Purchase Orders', by_supplier),
                                   cell('ByProject', 'Spend by Project', PO, 'All Purchase Orders', by_project),
                                   cell('ByStatus', 'Purchase Orders by Status', PO, 'All Purchase Orders', by_status)])
       + section('lists', '11', [cell('OpenOrders', 'Open Purchase Orders', PO, 'Open Purchase Orders', rows=10),
                                 cell('InvoicesToReview', 'Invoices to Review', INV, 'Invoices to Review', rows=10)])
       + '</sections></column></columns></tab>')
fid = form('none', 'Spend', [tab], description='Purchasing spend by supplier and project, open orders and invoices to review',
           form_type=0)
ok(S.post(API + 'PublishAllXml', json={}), 'publish')
print('dashboard Spend:', fid)
