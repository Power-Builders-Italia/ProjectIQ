"""Phase 4 forms: Project (now with Purchasing), purchase requests, RFQs, invitations, quotes, purchase orders,
goods receipts, supplier invoices and their lines, plus the purchasing web resources used by the commands.

Run after tools/pcf/push.sh (the RFQ form references the Quote Comparison control). Idempotent.
Status columns are read-only: they change through the commands (Custom APIs).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API
from formlib import ok, section, tab, form, webresource, use_ids

use_ids('op365-phase4-forms')
SRC = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'webresources')
webresource('op365_/scripts/purchasing.js', os.path.join(SRC, 'purchasing.js'), 'Purchasing commands')
webresource('op365_/pages/decision.html', os.path.join(SRC, 'decision.html'), 'Reject with a note')
webresource('op365_/pages/receipt.html', os.path.join(SRC, 'receipt.html'), 'Register goods receipt')


def rel(target, table, lookup):
    return f"op365_{target.replace('op365_', '')}_{table.replace('op365_', '')}_{lookup}"


def grid(name, label, table, parent, lookup, rows=8, view=None):
    return ('subgrid', name, label, table, rel(parent, table, lookup), rows, None, view)


# ---------- Project: Purchasing tab (the form was last defined in phase3_forms.py) ----------
P = 'op365_project'
WBS_REL = 'op365_project_wbsnode_projectid'
form(P, 'Project', [
    tab('Summary', [
        ('60%', [section(P, 'Project', ['op365_code', 'op365_name', 'op365_customerid', 'op365_projectmanagerid',
                                        'statuscode', 'ownerid', 'op365_startdate', 'op365_enddate']),
                 section(P, 'Budget and Progress', ['op365_contractvalue', 'op365_budgettotal', 'op365_actualcost!',
                                                    'op365_actualhours!', 'op365_committedcost!',
                                                    ('field', 'op365_progresspct!', 'op365_OP365.ProgressField')]),
                 section(P, 'Description', ['op365_description'], columns=1)]),
        ('40%', [section(P, 'Timeline', [('timeline',)])])]),
    tab('WBS', [('100%', [section(P, 'WBS', [('subgrid', 'WbsTree', 'WBS', 'op365_wbsnode', WBS_REL, 20, 'op365_OP365.WbsTreeGrid')])])]),
    tab('Gantt', [('100%', [section(P, 'Gantt', [('subgrid', 'Gantt', 'Gantt', 'op365_wbsnode', WBS_REL, 20, 'op365_OP365.GanttChart')]),
                            section(P, 'Baselines', [('subgrid', 'Baselines', 'Baselines', 'op365_baseline', 'op365_project_baseline_projectid', 5)])])]),
    tab('Costs', [('100%', [section(P, 'Cost Summary', [('pcf', 'op365_actualcost', 'op365_OP365.CostSummary')])])]),
    tab('Time', [('100%', [section(P, 'Time Entries', [('subgrid', 'TimeEntries', 'Time Entries', 'op365_timeentry',
                                                        'op365_project_timeentry_projectid', 12, None, 'Time Entries by Project')])])]),
    tab('Materials', [('100%', [section(P, 'Material Usage', [('subgrid', 'Materials', 'Material Usage', 'op365_materialusage',
                                                               'op365_project_materialusage_projectid', 12, None, 'Material Usage by Project')])])]),
    tab('Purchasing', [('100%', [
        section(P, 'Purchase Requests', [grid('PurchaseRequests', 'Purchase Requests', 'op365_purchaserequest', P, 'projectid', 6,
                                              'Purchase Requests by Project')]),
        section(P, 'Purchase Orders', [grid('PurchaseOrders', 'Purchase Orders', 'op365_purchaseorder', P, 'projectid', 6,
                                            'Purchase Orders by Project')])])]),
    tab('Team', [('100%', [section(P, 'Team', [('subgrid', 'Team', 'Project Members', 'op365_projectmember', 'op365_project_projectmember_projectid', 10)])])]),
], replace='Information')

# ---------- Purchase request ----------
T = 'op365_purchaserequest'
form(T, 'Purchase Request', [
    tab('General', [
        ('60%', [section(T, 'Request', ['op365_number!', 'statuscode!', 'op365_title', 'op365_neededby', 'op365_projectid',
                                        'op365_wbsnodeid', 'op365_preferredsupplierid', 'op365_requesterid']),
                 section(T, 'Justification', ['op365_justification'], columns=1),
                 section(T, 'Lines', [grid('Lines', 'Lines', 'op365_purchaserequestline', T, 'purchaserequestid', 10)])]),
        ('40%', [section(T, 'Approval', ['op365_estimatedamount!', 'op365_approvallevel!', 'op365_overbudget!', 'op365_abovethreshold!',
                                         'op365_currentapproverid!', 'op365_submittedon!', 'op365_managerapprovedbyid!',
                                         'op365_managerapprovedon!', 'op365_decidedbyid!', 'op365_decidedon!', 'op365_decisionnote!'], columns=1),
                 section(T, 'Timeline', [('timeline',)])])]),
    tab('Sourcing', [('100%', [
        section(T, 'Requests for Quotation', [grid('Rfqs', 'Requests for Quotation', 'op365_rfq', T, 'purchaserequestid', 5)]),
        section(T, 'Purchase Orders', [grid('Orders', 'Purchase Orders', 'op365_purchaseorder', T, 'purchaserequestid', 5)])])]),
], replace='Information')

T = 'op365_purchaserequestline'
form(T, 'Purchase Request Line', [tab('General', [('100%', [
    section(T, 'Line', ['op365_purchaserequestid', 'op365_itemid', 'op365_name', 'op365_quantity', 'op365_uom',
                        'op365_estimatedprice', 'op365_amount!', 'op365_sortorder']),
    section(T, 'Notes', ['op365_notes'], columns=1)])])], replace='Information')

# ---------- RFQ ----------
T = 'op365_rfq'
form(T, 'Request for Quotation', [
    tab('General', [
        ('60%', [section(T, 'Request for Quotation', ['op365_number!', 'statuscode!', 'op365_purchaserequestid', 'op365_projectid',
                                                      'op365_deadline', 'op365_responsecount!']),
                 section(T, 'Notes', ['op365_notes'], columns=1),
                 section(T, 'Invitations', [grid('Invitations', 'Invitations', 'op365_rfqinvitation', T, 'rfqid', 8)])]),
        ('40%', [section(T, 'Outcome', ['op365_senton!', 'op365_awardedon!', 'op365_winninginvitationid!', 'op365_purchaseorderid!',
                                        'op365_cancelledon!'], columns=1),
                 section(T, 'Timeline', [('timeline',)])])]),
    tab('Quote Comparison', [('100%', [section(T, 'Quote Comparison', [('pcf', 'op365_responsecount', 'op365_OP365.QuoteComparison')])])]),
], replace='Information')

T = 'op365_rfqinvitation'
form(T, 'RFQ Invitation', [tab('General', [
    ('50%', [section(T, 'Invitation', ['op365_rfqid', 'op365_supplierid', 'op365_email', 'statuscode!', 'op365_invitedon!',
                                       'op365_respondedon!'], columns=1)]),
    ('50%', [section(T, 'Answer', ['op365_quotedamount!', 'op365_deliverydays', 'op365_suppliernotes'], columns=1)])]),
    tab('Quotes', [('100%', [section(T, 'Quotes', [grid('Quotes', 'Quotes', 'op365_rfqquote', T, 'invitationid', 10)])])]),
], replace='Information')

T = 'op365_rfqquote'
form(T, 'RFQ Quote', [tab('General', [('100%', [
    section(T, 'Quote', ['op365_invitationid', 'op365_requestlineid', 'op365_price', 'op365_notes', 'op365_name!'])])])],
    replace='Information')

# ---------- Purchase order ----------
T = 'op365_purchaseorder'
form(T, 'Purchase Order', [
    tab('General', [
        ('60%', [section(T, 'Order', ['op365_number!', 'statuscode!', 'op365_supplierid', 'op365_projectid', 'op365_purchaserequestid',
                                      'op365_orderdate', 'op365_expecteddelivery', 'op365_deliveryplace', 'op365_paymentterms',
                                      'op365_totalamount!']),
                 section(T, 'Notes', ['op365_notes'], columns=1),
                 section(T, 'Lines', [grid('Lines', 'Lines', 'op365_purchaseorderline', T, 'purchaseorderid', 10)])]),
        ('40%', [section(T, 'Progress', ['op365_sentto!', 'op365_senton!', 'op365_supplierconfirmed!', 'op365_confirmedon!',
                                         'op365_receivedamount!', 'op365_receivedon!', 'op365_cancelledon!'], columns=1),
                 section(T, 'Timeline', [('timeline',)])])]),
    tab('Receipts', [('100%', [section(T, 'Goods Receipts', [grid('Receipts', 'Goods Receipts', 'op365_goodsreceipt', T, 'purchaseorderid', 8,
                                                                  'Goods Receipts by Order')])])]),
    tab('Invoices', [('100%', [section(T, 'Supplier Invoices', [grid('Invoices', 'Supplier Invoices', 'op365_supplierinvoice', T, 'purchaseorderid', 8,
                                                                     'Supplier Invoices by Order')])])]),
], replace='Information')

T = 'op365_purchaseorderline'
form(T, 'Purchase Order Line', [tab('General', [('100%', [
    section(T, 'Line', ['op365_purchaseorderid', 'op365_itemid', 'op365_name', 'op365_wbsnodeid', 'op365_quantity', 'op365_uom',
                        'op365_price', 'op365_amount!', 'op365_receivedquantity!', 'op365_sortorder', 'op365_requestlineid!']),
    section(T, 'Notes', ['op365_notes'], columns=1)])])], replace='Information')

# ---------- Goods receipt ----------
T = 'op365_goodsreceipt'
form(T, 'Goods Receipt', [tab('General', [
    ('60%', [section(T, 'Receipt', ['op365_number!', 'op365_purchaseorderid!', 'op365_projectid!', 'op365_receiptdate!',
                                    'op365_deliverynotenumber', 'op365_deliverynotedate']),
             section(T, 'Notes', ['op365_notes'], columns=1),
             section(T, 'Lines', [grid('Lines', 'Lines', 'op365_goodsreceiptline', T, 'goodsreceiptid', 10)])]),
    ('40%', [section(T, 'Timeline', [('timeline',)])])])], replace='Information')

T = 'op365_goodsreceiptline'
form(T, 'Goods Receipt Line', [tab('General', [('100%', [
    section(T, 'Line', ['op365_goodsreceiptid!', 'op365_orderlineid!', 'op365_quantity!', 'op365_name!'])])])], replace='Information')

# ---------- Supplier invoice ----------
T = 'op365_supplierinvoice'
form(T, 'Supplier Invoice', [
    tab('General', [
        ('60%', [section(T, 'Invoice', ['op365_number!', 'statuscode!', 'op365_supplierid', 'op365_documenttype', 'op365_invoicenumber',
                                        'op365_invoicedate', 'op365_sellername', 'op365_sellervatnumber', 'op365_purchaseorderid',
                                        'op365_projectid']),
                 section(T, 'Amounts', ['op365_taxableamount', 'op365_vatamount', 'op365_totalamount']),
                 section(T, 'Lines', [grid('Lines', 'Lines', 'op365_supplierinvoiceline', T, 'supplierinvoiceid', 10)])]),
        ('40%', [section(T, 'Attachment', ['op365_xmlfile'], columns=1),
                 section(T, 'References', ['op365_orderrefs', 'op365_deliverynoterefs'], columns=1),
                 section(T, 'Decision', ['op365_decidedbyid!', 'op365_decidedon!', 'op365_decisionnote!'], columns=1),
                 section(T, 'Timeline', [('timeline',)])])]),
], replace='Information')

T = 'op365_supplierinvoiceline'
form(T, 'Supplier Invoice Line', [tab('General', [('100%', [
    section(T, 'Line', ['op365_supplierinvoiceid', 'op365_linenumber', 'op365_code', 'op365_name', 'op365_quantity', 'op365_uom',
                        'op365_unitprice', 'op365_totalprice', 'op365_vatrate', 'op365_orderlineid'])])])], replace='Information')

ok(S.post(API + 'PublishAllXml', json={}), 'publish')
