"""End-to-end check of the Phase 4 plugins and Custom APIs. Creates test records and deletes them at the end."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API

R = {'Prefer': 'return=representation'}
PR_SUBMITTED, PR_APPROVED, PR_REJECTED, PR_CANCELLED, PR_ORDERED = 365000000, 365000001, 365000002, 365000003, 365000004
RFQ_SENT, RFQ_AWARDED = 365000000, 365000001
INV_INVITED, INV_RESPONDED = 365000000, 365000001
PO_SENT, PO_CONFIRMED, PO_RECEIVED, PO_CANCELLED = 365000000, 365000001, 365000002, 365000003
INVOICE_APPROVED = 365000000
failures = []


def post(es, body):
    r = S.post(API + es, json=body, headers=R)
    if r.status_code >= 300:
        raise SystemExit(f'{es}: {r.status_code} {r.text[:400]}')
    return r.json()


def get(es, id_, sel):
    return S.get(API + f'{es}({id_})?$select={sel}').json()


def rows(es, flt, sel):
    return S.get(API + f'{es}?$select={sel}&$filter={flt}').json()['value']


def bound(es, id_, name, body=None):
    return S.post(API + f'{es}({id_})/Microsoft.Dynamics.CRM.{name}', json=body or {})


def check(what, cond, detail=None):
    print(('ok  ' if cond else 'FAIL'), what)
    if not cond:
        failures.append(what)
        if detail is not None:
            print('     ', str(detail)[:400])
    return cond


def money(v):
    return float(v or 0)


me = S.get(API + 'WhoAmI').json()['UserId']
cust = post('accounts', {'name': 'OP365 smoke customer F4', 'op365_iscustomer': True})['accountid']
sup1 = post('accounts', {'name': 'OP365 smoke supplier A', 'op365_issupplier': True, 'emailaddress1': 'a@example.com',
                         'op365_paymentterms': '30 days'})['accountid']
sup2 = post('accounts', {'name': 'OP365 smoke supplier B', 'op365_issupplier': True})['accountid']
item = post('op365_items', {'op365_code': 'SMOKE-F4', 'op365_name': 'Smoke panel', 'op365_uom': 'pcs', 'op365_unitcost': 50,
                            'op365_DefaultSupplierId@odata.bind': f'/accounts({sup2})'})['op365_itemid']
prj = None
try:
    post('op365_itemsuppliers', {'op365_ItemId@odata.bind': f'/op365_items({item})', 'op365_SupplierId@odata.bind': f'/accounts({sup1})', 'op365_price': 40})
    contact = post('contacts', {'lastname': 'Smoke', 'parentcustomerid_account@odata.bind': f'/accounts({sup1})'})['contactid']
    check('account contact count', get('accounts', sup1, 'op365_contactcount')['op365_contactcount'] == 1)
    S.delete(API + f'contacts({contact})')
    check('contact count after delete', get('accounts', sup1, 'op365_contactcount')['op365_contactcount'] == 0)

    prj = post('op365_projects', {'op365_code': 'SMOKE-004', 'op365_name': 'Smoke project F4', 'statuscode': 1,
                                  'op365_CustomerId@odata.bind': f'/accounts({cust})',
                                  'op365_ProjectManagerId@odata.bind': f'/systemusers({me})'})['op365_projectid']
    bind = {'op365_ProjectId@odata.bind': f'/op365_projects({prj})'}
    node = post('op365_wbsnodes', {**bind, 'op365_name': 'Supply', 'op365_code': '1', 'op365_budgetmaterials': 1000})['op365_wbsnodeid']

    # ---------- purchase request ----------
    pr = post('op365_purchaserequests', {**bind, 'op365_title': 'Panels', 'op365_WbsNodeId@odata.bind': f'/op365_wbsnodes({node})',
                                         'op365_PreferredSupplierId@odata.bind': f'/accounts({sup1})'})
    prid = pr['op365_purchaserequestid']
    check('PR number and requester', pr['op365_number'].startswith('PR-') and pr['_op365_requesterid_value'] == me, pr)
    r = bound('op365_purchaserequests', prid, 'op365_SubmitPurchaseRequest')
    check('submit without lines refused', r.status_code >= 400)
    l1 = post('op365_purchaserequestlines', {'op365_PurchaseRequestId@odata.bind': f'/op365_purchaserequests({prid})',
                                             'op365_ItemId@odata.bind': f'/op365_items({item})', 'op365_quantity': 30})
    check('PR line: item name, uom, preferred supplier price 40, amount 1200',
          l1['op365_name'] == 'Smoke panel' and l1['op365_uom'] == 'pcs' and money(l1['op365_estimatedprice']) == 40
          and money(l1['op365_amount']) == 1200, l1)
    check('PR estimated amount', money(get('op365_purchaserequests', prid, 'op365_estimatedamount')['op365_estimatedamount']) == 1200)
    r = S.patch(API + f'op365_purchaserequests({prid})', json={'statuscode': PR_APPROVED})
    check('direct PR status change refused', r.status_code >= 400)
    r = bound('op365_purchaserequests', prid, 'op365_SubmitPurchaseRequest')
    p = get('op365_purchaserequests', prid, 'statuscode,op365_overbudget,_op365_currentapproverid_value,op365_approvallevel')
    check('submit: Submitted, over budget (1200 > 1000), PM is approver',
          r.ok and p['statuscode'] == PR_SUBMITTED and p['op365_overbudget'] and p['_op365_currentapproverid_value'] == me, r.text if not r.ok else p)
    r = S.patch(API + f'op365_purchaserequests({prid})', json={'op365_title': 'Changed'})
    check('submitted PR locked', r.status_code >= 400)
    r = bound('op365_purchaserequests', prid, 'op365_DecidePurchaseRequest', {'Approve': False})
    check('reject without note refused', r.status_code >= 400)
    r = bound('op365_purchaserequests', prid, 'op365_DecidePurchaseRequest', {'Approve': True})
    check('approve', r.ok and get('op365_purchaserequests', prid, 'statuscode')['statuscode'] == PR_APPROVED, r.text)

    # ---------- RFQ ----------
    r = bound('op365_purchaserequests', prid, 'op365_CreateRfq')
    rfq = r.json().get('RfqId') if r.ok else None
    invs = rows('op365_rfqinvitations', f'_op365_rfqid_value eq {rfq}', 'op365_rfqinvitationid,_op365_supplierid_value,op365_email,op365_name') if rfq else []
    check('create RFQ invites preferred + item default supplier', r.ok and len(invs) == 2, r.text)
    inv_a = next(i['op365_rfqinvitationid'] for i in invs if i['_op365_supplierid_value'] == sup1)
    inv_b = next(i['op365_rfqinvitationid'] for i in invs if i['_op365_supplierid_value'] == sup2)
    check('invitation name and email from supplier', any(i['op365_email'] == 'a@example.com' and i['op365_name'] == 'OP365 smoke supplier A' for i in invs), invs)
    r = bound('op365_rfqs', rfq, 'op365_SendRfq')
    check('send RFQ', r.ok and r.json().get('Count') == 2 and get('op365_rfqs', rfq, 'statuscode')['statuscode'] == RFQ_SENT, r.text)
    post('op365_rfqquotes', {'op365_InvitationId@odata.bind': f'/op365_rfqinvitations({inv_a})',
                             'op365_RequestLineId@odata.bind': f"/op365_purchaserequestlines({l1['op365_purchaserequestlineid']})", 'op365_price': 38})
    post('op365_rfqquotes', {'op365_InvitationId@odata.bind': f'/op365_rfqinvitations({inv_b})',
                             'op365_RequestLineId@odata.bind': f"/op365_purchaserequestlines({l1['op365_purchaserequestlineid']})", 'op365_price': 41})
    ia = get('op365_rfqinvitations', inv_a, 'statuscode,op365_quotedamount')
    check('quote: invitation Responded, quoted 30 x 38', ia['statuscode'] == INV_RESPONDED and money(ia['op365_quotedamount']) == 1140, ia)
    check('RFQ responses 2', get('op365_rfqs', rfq, 'op365_responsecount')['op365_responsecount'] == 2)
    r = bound('op365_rfqs', rfq, 'op365_AwardRfq', {'InvitationId': inv_a})
    po = r.json().get('PurchaseOrderId') if r.ok else None
    check('award creates PO, RFQ Awarded, PR Ordered', r.ok and get('op365_rfqs', rfq, 'statuscode')['statuscode'] == RFQ_AWARDED
          and get('op365_purchaserequests', prid, 'statuscode')['statuscode'] == PR_ORDERED, r.text)

    # ---------- purchase order ----------
    o = get('op365_purchaseorders', po, 'op365_number,op365_totalamount,_op365_supplierid_value,op365_paymentterms,statuscode')
    lines = rows('op365_purchaseorderlines', f'_op365_purchaseorderid_value eq {po}', 'op365_purchaseorderlineid,op365_price,op365_amount,_op365_wbsnodeid_value')
    check('PO from quote: supplier A, 30 x 38 = 1140, WBS node, payment terms',
          o['op365_number'].startswith('PO-') and o['_op365_supplierid_value'] == sup1 and money(o['op365_totalamount']) == 1140
          and len(lines) == 1 and lines[0]['_op365_wbsnodeid_value'] == node and o['op365_paymentterms'] == '30 days', (o, lines))
    pol = lines[0]['op365_purchaseorderlineid']
    check('supplier spend 1140', money(get('accounts', sup1, 'op365_spend')['op365_spend']) == 1140)
    it = get('op365_items', item, 'op365_usagecount,op365_spend')
    check('item usage 1 line, spend 1140', it['op365_usagecount'] == 1 and money(it['op365_spend']) == 1140, it)
    r = bound('op365_purchaseorders', po, 'op365_RegisterGoodsReceipt')
    check('receipt on draft PO refused', r.status_code >= 400)
    r = bound('op365_purchaseorders', po, 'op365_SetPurchaseOrderStatus', {'Status': 'Confirmed'})
    check('Draft -> Confirmed refused', r.status_code >= 400)
    r = bound('op365_purchaseorders', po, 'op365_SetPurchaseOrderStatus', {'Status': 'Sent'})
    o = get('op365_purchaseorders', po, 'statuscode,op365_sentto')
    check('send PO: Sent to the supplier email', r.ok and o['statuscode'] == PO_SENT and o['op365_sentto'] == 'a@example.com', r.text)
    check('committed cost 1140', money(get('op365_projects', prj, 'op365_committedcost')['op365_committedcost']) == 1140)
    r = S.patch(API + f'op365_purchaseorderlines({pol})', json={'op365_quantity': 5})
    check('sent PO lines locked', r.status_code >= 400)
    r = S.patch(API + f'op365_purchaseorders({po})', json={'op365_supplierconfirmed': True})
    check('supplier confirmation -> Confirmed', r.ok and get('op365_purchaseorders', po, 'statuscode')['statuscode'] == PO_CONFIRMED, r.text)

    # ---------- goods receipts ----------
    r = bound('op365_purchaseorders', po, 'op365_RegisterGoodsReceipt', {'Lines': [f'{pol}=40']})
    check('over-receipt refused', r.status_code >= 400)
    r = bound('op365_purchaseorders', po, 'op365_RegisterGoodsReceipt', {'Lines': [f'{pol}=10'], 'DeliveryNoteNumber': 'DDT-1'})
    gr1 = r.json().get('GoodsReceiptId') if r.ok else None
    check('partial receipt 10', r.ok, r.text)
    mu = rows('op365_materialusages', f'_op365_projectid_value eq {prj}', 'op365_quantity,op365_unitcost,op365_totalcost,_op365_wbsnodeid_value')
    check('material usage 10 x 38 on the node', len(mu) == 1 and money(mu[0]['op365_totalcost']) == 380 and mu[0]['_op365_wbsnodeid_value'] == node, mu)
    p = get('op365_projects', prj, 'op365_committedcost,op365_actualcost')
    check('committed 760, actual 380', money(p['op365_committedcost']) == 760 and money(p['op365_actualcost']) == 380, p)
    r = S.delete(API + f"op365_materialusages({mu[0]['op365_materialusageid']})")
    check('receipt material usage protected', r.status_code >= 400)
    r = S.post(API + 'op365_goodsreceipts', json={**bind, 'op365_receiptdate': '2026-10-01'})
    check('manual goods receipt refused', r.status_code >= 400)
    r = bound('op365_purchaseorders', po, 'op365_RegisterGoodsReceipt')
    o = get('op365_purchaseorders', po, 'statuscode,op365_receivedamount')
    check('receive the rest: PO Received, received 1140', r.ok and o['statuscode'] == PO_RECEIVED and money(o['op365_receivedamount']) == 1140, r.text if not r.ok else o)
    p = get('op365_projects', prj, 'op365_committedcost,op365_actualcost')
    check('committed 0, actual 1140', money(p['op365_committedcost']) == 0 and money(p['op365_actualcost']) == 1140, p)
    gr2 = r.json().get('GoodsReceiptId') if r.ok else None
    r = bound('op365_goodsreceipts', gr2, 'op365_CancelGoodsReceipt')
    o = get('op365_purchaseorders', po, 'statuscode')
    p = get('op365_projects', prj, 'op365_committedcost,op365_actualcost')
    check('cancel receipt: PO Confirmed, committed 760, actual 380',
          r.ok and o['statuscode'] == PO_CONFIRMED and money(p['op365_committedcost']) == 760 and money(p['op365_actualcost']) == 380, r.text if not r.ok else p)
    r = bound('op365_purchaseorders', po, 'op365_SetPurchaseOrderStatus', {'Status': 'Cancelled'})
    check('cancel PO with receipts refused', r.status_code >= 400)

    # ---------- direct order from a request ----------
    pr2 = post('op365_purchaserequests', {**bind, 'op365_title': 'Cables'})['op365_purchaserequestid']
    post('op365_purchaserequestlines', {'op365_PurchaseRequestId@odata.bind': f'/op365_purchaserequests({pr2})', 'op365_name': 'Cable',
                                        'op365_quantity': 2, 'op365_estimatedprice': 10})
    bound('op365_purchaserequests', pr2, 'op365_SubmitPurchaseRequest')
    bound('op365_purchaserequests', pr2, 'op365_DecidePurchaseRequest', {'Approve': True})
    r = bound('op365_purchaserequests', pr2, 'op365_CreatePurchaseOrder', {'SupplierId': sup2})
    po2 = r.json().get('PurchaseOrderId') if r.ok else None
    check('create PO from request (2 x 10)', r.ok and money(get('op365_purchaseorders', po2, 'op365_totalamount')['op365_totalamount']) == 20, r.text)
    r = bound('op365_purchaseorders', po2, 'op365_SetPurchaseOrderStatus', {'Status': 'Cancelled'})
    check('cancel draft PO', r.ok and get('op365_purchaseorders', po2, 'statuscode')['statuscode'] == PO_CANCELLED, r.text)
    check('cancelled PO out of supplier spend', money(get('accounts', sup2, 'op365_spend')['op365_spend']) == 0)
    pr3 = post('op365_purchaserequests', {**bind, 'op365_title': 'To cancel'})['op365_purchaserequestid']
    r = bound('op365_purchaserequests', pr3, 'op365_CancelPurchaseRequest')
    check('cancel PR', r.ok and get('op365_purchaserequests', pr3, 'statuscode')['statuscode'] == PR_CANCELLED, r.text)

    # ---------- supplier invoice ----------
    inv = post('op365_supplierinvoices', {'op365_invoicenumber': 'FT-1', 'op365_invoicedate': '2026-10-20',
                                          'op365_SupplierId@odata.bind': f'/accounts({sup1})',
                                          'op365_PurchaseOrderId@odata.bind': f'/op365_purchaseorders({po})'})
    invid = inv['op365_supplierinvoiceid']
    check('invoice: number, seller, project from PO', inv['op365_number'].startswith('INV-') and inv['op365_sellername'] == 'OP365 smoke supplier A'
          and inv['_op365_projectid_value'] == prj, inv)
    post('op365_supplierinvoicelines', {'op365_SupplierInvoiceId@odata.bind': f'/op365_supplierinvoices({invid})', 'op365_name': 'Panels',
                                        'op365_quantity': 10, 'op365_unitprice': 38, 'op365_vatrate': 22})
    i = get('op365_supplierinvoices', invid, 'op365_taxableamount,op365_vatamount,op365_totalamount')
    check('invoice totals 380 + 83.60', money(i['op365_taxableamount']) == 380 and money(i['op365_vatamount']) == 83.6
          and money(i['op365_totalamount']) == 463.6, i)
    r = bound('op365_supplierinvoices', invid, 'op365_DecideSupplierInvoice', {'Approve': True})
    check('approve invoice', r.ok and get('op365_supplierinvoices', invid, 'statuscode')['statuscode'] == INVOICE_APPROVED, r.text)
    r = S.patch(API + f'op365_supplierinvoices({invid})', json={'op365_invoicenumber': 'FT-2'})
    check('approved invoice locked', r.status_code >= 400)
    S.delete(API + f'op365_supplierinvoices({invid})')

    r = S.delete(API + f'op365_projects({prj})')
    check('project delete cascades purchasing', r.status_code < 300, r.text)
    if r.status_code < 300:
        prj = None
        check('supplier spend after project delete', money(get('accounts', sup1, 'op365_spend')['op365_spend']) == 0)
finally:
    if prj:
        S.delete(API + f'op365_projects({prj})')
    for es, id_ in [('op365_items', item), ('accounts', sup1), ('accounts', sup2), ('accounts', cust)]:
        S.delete(API + f'{es}({id_})')

print(f'{len(failures)} failures')
sys.exit(1 if failures else 0)
