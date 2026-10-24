"""Phase 4 system views: purchase requests (spec 26-29), RFQs (30-32), purchase orders (33-36), supplier invoices (37-40),
goods receipts, the line subgrids and the purchasing columns on Account and Item.

Idempotent: views are matched by table + name; default views are updated in place.
Views are read back in their published state, so run app.py (publish) afterwards.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from viewlib import view

S = 365000000
NEWEST = [('op365_number', True)]

# ---------- Purchase requests (26-29) ----------
PR = [('op365_number', 100), ('op365_title', 220), ('op365_projectid', 200), ('op365_requesterid', 150),
      ('op365_neededby', 100), ('statuscode', 100), ('op365_estimatedamount', 120)]
view('op365_purchaserequest', 'All Purchase Requests', PR, NEWEST, default=True, replace='Active Purchase Requests')
view('op365_purchaserequest', 'My Purchase Requests', PR, NEWEST, [('op365_requesterid', 'eq-userid', None)])
view('op365_purchaserequest', 'Purchase Requests to Decide', PR + [('op365_approvallevel', 110)], [('op365_neededby', False)],
     [('statuscode', 'eq', S), ('op365_currentapproverid', 'eq-userid', None)])
view('op365_purchaserequest', 'Open Purchase Requests', PR, NEWEST, [('statuscode', 'eq', 1), ('statuscode', 'eq', S), ('statuscode', 'eq', S + 2)],
     filter_type='or')
view('op365_purchaserequest', 'Purchase Requests by Project',
     [c for c in PR if c[0] != 'op365_projectid'] + [('op365_wbsnodeid', 150)], NEWEST)
view('op365_purchaserequest', 'Quick Find Active Purchase Requests', PR, NEWEST, querytype=4, default=True,
     quickfind=['op365_number', 'op365_title'])
LINES = [('op365_name', 240), ('op365_itemid', 160), ('op365_quantity', 80), ('op365_uom', 60), ('op365_estimatedprice', 100),
         ('op365_amount', 110)]
view('op365_purchaserequestline', 'Purchase Request Lines', LINES, [('op365_sortorder', False), ('op365_name', False)], default=True,
     replace='Active Purchase Request Lines')

# ---------- RFQs (30-32) ----------
RFQ = [('op365_number', 100), ('op365_purchaserequestid', 120), ('op365_projectid', 200), ('op365_deadline', 100),
       ('op365_responsecount', 90), ('statuscode', 100)]
view('op365_rfq', 'All RFQs', RFQ, NEWEST, default=True, replace='Active Requests for Quotation')
view('op365_rfq', 'Open RFQs', RFQ, [('op365_deadline', False)], [('statuscode', 'eq', 1), ('statuscode', 'eq', S)], filter_type='or')
view('op365_rfq', 'Awarded RFQs', RFQ + [('op365_purchaseorderid', 120)], NEWEST, [('statuscode', 'eq', S + 1)])
view('op365_rfq', 'Quick Find Active Requests for Quotation', RFQ, NEWEST, querytype=4, default=True, quickfind=['op365_number'])
view('op365_rfqinvitation', 'RFQ Invitations',
     [('op365_supplierid', 200), ('op365_email', 180), ('statuscode', 100), ('op365_quotedamount', 120), ('op365_deliverydays', 90),
      ('op365_invitedon', 130), ('op365_respondedon', 130)], [('op365_name', False)], default=True, replace='Active RFQ Invitations')
view('op365_rfqquote', 'RFQ Quotes', [('op365_requestlineid', 240), ('op365_price', 100), ('op365_notes', 240)], [('op365_name', False)],
     default=True, replace='Active RFQ Quotes')

# ---------- Purchase orders (33-36) ----------
PO = [('op365_number', 100), ('op365_supplierid', 200), ('op365_projectid', 200), ('op365_orderdate', 100),
      ('op365_expecteddelivery', 110), ('statuscode', 100), ('op365_totalamount', 120)]
view('op365_purchaseorder', 'All Purchase Orders', PO, NEWEST, default=True, replace='Active Purchase Orders')
view('op365_purchaseorder', 'Open Purchase Orders', PO, NEWEST, [('statuscode', 'eq', 1), ('statuscode', 'eq', S)], filter_type='or')
view('op365_purchaseorder', 'Confirmed Purchase Orders', PO, [('op365_expecteddelivery', False)], [('statuscode', 'eq', S + 1)])
view('op365_purchaseorder', 'Received Purchase Orders', PO + [('op365_receivedon', 120)], NEWEST, [('statuscode', 'eq', S + 2)])
view('op365_purchaseorder', 'Purchase Orders by Project',
     [c for c in PO if c[0] != 'op365_projectid'] + [('op365_receivedamount', 120)], NEWEST)
view('op365_purchaseorder', 'Purchase Orders by Supplier',
     [c for c in PO if c[0] != 'op365_supplierid'], NEWEST)
view('op365_purchaseorder', 'Quick Find Active Purchase Orders', PO, NEWEST, querytype=4, default=True,
     quickfind=['op365_number', 'op365_supplierid', 'op365_projectid'])
view('op365_purchaseorderline', 'Purchase Order Lines',
     [('op365_name', 240), ('op365_itemid', 150), ('op365_wbsnodeid', 150), ('op365_quantity', 80), ('op365_uom', 60),
      ('op365_price', 100), ('op365_amount', 110), ('op365_receivedquantity', 90)],
     [('op365_sortorder', False), ('op365_name', False)], default=True, replace='Active Purchase Order Lines')

# ---------- Goods receipts ----------
GR = [('op365_number', 100), ('op365_purchaseorderid', 110), ('op365_projectid', 200), ('op365_receiptdate', 100),
      ('op365_deliverynotenumber', 130), ('op365_deliverynotedate', 110)]
view('op365_goodsreceipt', 'All Goods Receipts', GR, NEWEST, default=True, replace='Active Goods Receipts')
view('op365_goodsreceipt', 'Goods Receipts by Order', [c for c in GR if c[0] != 'op365_purchaseorderid'], NEWEST)
view('op365_goodsreceipt', 'Quick Find Active Goods Receipts', GR, NEWEST, querytype=4, default=True,
     quickfind=['op365_number', 'op365_deliverynotenumber'])
view('op365_goodsreceiptline', 'Goods Receipt Lines', [('op365_orderlineid', 260), ('op365_quantity', 90)], [('op365_name', False)],
     default=True, replace='Active Goods Receipt Lines')

# ---------- Supplier invoices (37-40) ----------
INV = [('op365_number', 100), ('op365_supplierid', 200), ('op365_invoicenumber', 110), ('op365_invoicedate', 100),
       ('op365_purchaseorderid', 110), ('op365_projectid', 180), ('statuscode', 100), ('op365_totalamount', 120)]
LATEST = [('op365_invoicedate', True)]
view('op365_supplierinvoice', 'All Supplier Invoices', INV, LATEST, default=True, replace='Active Supplier Invoices')
view('op365_supplierinvoice', 'Invoices to Review', INV, LATEST, [('statuscode', 'eq', 1)])
view('op365_supplierinvoice', 'Approved Invoices', INV, LATEST, [('statuscode', 'eq', S)])
view('op365_supplierinvoice', 'Rejected Invoices', INV, LATEST, [('statuscode', 'eq', S + 1)])
view('op365_supplierinvoice', 'Supplier Invoices by Order', [c for c in INV if c[0] != 'op365_purchaseorderid'], LATEST)
view('op365_supplierinvoice', 'Quick Find Active Supplier Invoices', INV, LATEST, querytype=4, default=True,
     quickfind=['op365_number', 'op365_invoicenumber', 'op365_sellername'])
view('op365_supplierinvoiceline', 'Supplier Invoice Lines',
     [('op365_linenumber', 60), ('op365_code', 90), ('op365_name', 240), ('op365_quantity', 80), ('op365_uom', 60),
      ('op365_unitprice', 100), ('op365_totalprice', 110), ('op365_vatrate', 70)],
     [('op365_linenumber', False)], default=True, replace='Active Supplier Invoice Lines')

# ---------- purchasing columns on suppliers and items ----------
SUP = [('name', 250), ('op365_suppliercategory', 140), ('op365_supplierstatus', 110), ('op365_vatnumber', 130),
       ('op365_contactcount', 80), ('op365_spend', 120), ('op365_expireddocs', 90)]
view('account', 'All Suppliers', SUP, [('name', False)], [('op365_issupplier', 'eq', '1')])
view('op365_item', 'All Items',
     [('op365_code', 110), ('op365_name', 240), ('op365_category', 130), ('op365_uom', 60), ('op365_unitcost', 100),
      ('op365_defaultsupplierid', 180), ('op365_usagecount', 90), ('op365_spend', 110)],
     [('op365_code', False)], default=True)
