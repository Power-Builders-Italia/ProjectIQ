"""Phase 4 tables: purchase requests, RFQs with invitations and quotes, purchase orders, goods receipts and supplier
invoices, plus the purchasing totals on Settings, Account, Item and Material Usage.

Amounts, totals and counters are plain columns set by the OpenProject365.Plugins assembly; statuses change only
through the Custom APIs. Idempotent; reads the PAC_* environment variables.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from meta import col, create_tables, create_columns, create_lookups, status_reasons, enable_timeline, publish

TABLES = [
  ('PurchaseRequest', 'Purchase Request', 'Purchase Requests', 'Request to buy materials or services for a project',
   ('Number', 'Number', 20, False, 'PR-{SEQNUM:5}')),
  ('PurchaseRequestLine', 'Purchase Request Line', 'Purchase Request Lines', 'Item or service of a purchase request',
   ('Name', 'Description', 200, True)),
  ('Rfq', 'Request for Quotation', 'Requests for Quotation', 'Request for quotation sent to suppliers',
   ('Number', 'Number', 20, False, 'RFQ-{SEQNUM:5}')),
  ('RfqInvitation', 'RFQ Invitation', 'RFQ Invitations', 'Supplier invited to quote', ('Name', 'Name', 200, False)),
  ('RfqQuote', 'RFQ Quote', 'RFQ Quotes', 'Price quoted by a supplier for a request line', ('Name', 'Name', 200, False)),
  ('PurchaseOrder', 'Purchase Order', 'Purchase Orders', 'Order to a supplier for a project',
   ('Number', 'Number', 20, False, 'PO-{SEQNUM:5}')),
  ('PurchaseOrderLine', 'Purchase Order Line', 'Purchase Order Lines', 'Ordered item or service',
   ('Name', 'Description', 200, True)),
  ('GoodsReceipt', 'Goods Receipt', 'Goods Receipts', 'Delivery received against a purchase order',
   ('Number', 'Number', 20, False, 'GR-{SEQNUM:5}')),
  ('GoodsReceiptLine', 'Goods Receipt Line', 'Goods Receipt Lines', 'Quantity received for an order line',
   ('Name', 'Name', 200, False)),
  ('SupplierInvoice', 'Supplier Invoice', 'Supplier Invoices', 'Supplier invoice with its XML or PDF attached',
   ('Number', 'Number', 20, False, 'INV-{SEQNUM:5}')),
  ('SupplierInvoiceLine', 'Supplier Invoice Line', 'Supplier Invoice Lines', 'Line of a supplier invoice',
   ('Name', 'Description', 400, True)),
]

QTY = dict(min=0, prec=3, maxv=1000000000)
COLUMNS = {
  'op365_purchaserequest': [
    col('text', 'Title', 'Title', required=True, max=200),
    col('memo', 'Justification', 'Justification'),
    col('date', 'NeededBy', 'Needed By'),
    col('choice', 'ApprovalLevel', 'Approval Level', 'Manager, or Administrator above the threshold',
        options=['Manager', 'Administrator']),
    col('bool', 'OverBudget', 'Over Budget', 'Actual + committed + this request exceed the budget. Set on submit'),
    col('bool', 'AboveThreshold', 'Above Threshold', 'Estimated amount above the Settings threshold. Set on submit'),
    col('datetime', 'SubmittedOn', 'Submitted On'),
    col('datetime', 'ManagerApprovedOn', 'Manager Approved On'),
    col('datetime', 'DecidedOn', 'Decided On'),
    col('memo', 'DecisionNote', 'Decision Note'),
    col('currency', 'EstimatedAmount', 'Estimated Amount', 'Sum of the lines. Set by plugin'),
  ],
  'op365_purchaserequestline': [
    col('decimal', 'Quantity', 'Quantity', required=True, **QTY),
    col('text', 'Uom', 'Unit of Measure', max=20),
    col('currency', 'EstimatedPrice', 'Estimated Price'),
    col('currency', 'Amount', 'Amount', 'Quantity x estimated price. Set by plugin'),
    col('whole', 'SortOrder', 'Sort Order'),
    col('memo', 'Notes', 'Notes'),
  ],
  'op365_rfq': [
    col('date', 'Deadline', 'Deadline', required=True),
    col('memo', 'Notes', 'Notes'),
    col('datetime', 'SentOn', 'Sent On'),
    col('datetime', 'AwardedOn', 'Awarded On'),
    col('datetime', 'CancelledOn', 'Cancelled On'),
    col('whole', 'ResponseCount', 'Responses', 'Invitations answered. Set by plugin'),
  ],
  'op365_rfqinvitation': [
    col('text', 'Email', 'Email', max=100, fmt='Email'),
    col('datetime', 'InvitedOn', 'Invited On'),
    col('datetime', 'RespondedOn', 'Responded On'),
    col('whole', 'DeliveryDays', 'Delivery Days'),
    col('memo', 'SupplierNotes', 'Supplier Notes'),
    col('currency', 'QuotedAmount', 'Quoted Amount', 'Quoted prices x requested quantities. Set by plugin'),
    col('text', 'RfqNumber', 'RFQ Number', 'Copied from the RFQ on Send (read by the supplier portal)', max=100),
    col('date', 'Deadline', 'Deadline', 'Copied from the RFQ on Send'),
    col('memo', 'RfqNotes', 'RFQ Notes', 'Copied from the RFQ on Send'),
  ],
  'op365_rfqquote': [
    col('currency', 'Price', 'Unit Price', 'Empty until the supplier quotes the line'),
    col('text', 'Notes', 'Notes', max=400),
    col('decimal', 'Quantity', 'Quantity', 'Requested quantity, copied from the request line'),
    col('text', 'Uom', 'Unit', max=20),
  ],
  'op365_purchaseorder': [
    col('date', 'OrderDate', 'Order Date'),
    col('date', 'ExpectedDelivery', 'Expected Delivery'),
    col('text', 'DeliveryPlace', 'Delivery Place', max=200),
    col('text', 'PaymentTerms', 'Payment Terms', max=200),
    col('memo', 'Notes', 'Notes'),
    col('text', 'SentTo', 'Sent To', max=200),
    col('datetime', 'SentOn', 'Sent On'),
    col('bool', 'SupplierConfirmed', 'Supplier Confirmed'),
    col('datetime', 'ConfirmedOn', 'Confirmed On'),
    col('datetime', 'ReceivedOn', 'Received On'),
    col('datetime', 'CancelledOn', 'Cancelled On'),
    col('currency', 'TotalAmount', 'Total Amount', 'Sum of the lines. Set by plugin'),
    col('currency', 'ReceivedAmount', 'Received Amount', 'Received quantities x prices. Set by plugin'),
  ],
  'op365_purchaseorderline': [
    col('decimal', 'Quantity', 'Quantity', required=True, **QTY),
    col('text', 'Uom', 'Unit of Measure', max=20),
    col('currency', 'Price', 'Unit Price'),
    col('currency', 'Amount', 'Amount', 'Quantity x unit price. Set by plugin'),
    col('decimal', 'ReceivedQuantity', 'Received Quantity', 'Sum of the goods receipt lines. Set by plugin', **QTY),
    col('whole', 'SortOrder', 'Sort Order'),
    col('memo', 'Notes', 'Notes'),
  ],
  'op365_goodsreceipt': [
    col('date', 'ReceiptDate', 'Receipt Date', required=True),
    col('text', 'DeliveryNoteNumber', 'Delivery Note Number', max=50),
    col('date', 'DeliveryNoteDate', 'Delivery Note Date'),
    col('memo', 'Notes', 'Notes'),
  ],
  'op365_goodsreceiptline': [
    col('decimal', 'Quantity', 'Quantity', required=True, **QTY),
  ],
  'op365_supplierinvoice': [
    col('text', 'InvoiceNumber', 'Invoice Number', required=True, max=50),
    col('date', 'InvoiceDate', 'Invoice Date', required=True),
    col('choice', 'DocumentType', 'Document Type', 'FatturaPA document type', default=0,
        options=['TD01 Invoice', 'TD02 Advance invoice', 'TD04 Credit note', 'TD05 Debit note', 'TD06 Fee note',
                 'TD24 Deferred invoice', 'TD25 Deferred invoice (triangular)']),
    col('text', 'SellerName', 'Seller Name', max=200),
    col('text', 'SellerVatNumber', 'Seller VAT Number', max=30),
    col('currency', 'TaxableAmount', 'Taxable Amount', 'Sum of the lines when there are lines'),
    col('currency', 'VatAmount', 'VAT Amount', 'From the lines when there are lines'),
    col('currency', 'TotalAmount', 'Total Amount', 'Taxable + VAT when there are lines'),
    col('text', 'DeliveryNoteRefs', 'Delivery Note References', max=400),
    col('text', 'OrderRefs', 'Order References', max=400),
    col('datetime', 'DecidedOn', 'Decided On'),
    col('memo', 'DecisionNote', 'Decision Note'),
    col('file', 'XmlFile', 'Invoice File', 'FatturaPA XML or PDF, attached by hand', kb=10240),
  ],
  'op365_supplierinvoiceline': [
    col('whole', 'LineNumber', 'Line Number'),
    col('text', 'Code', 'Code', max=50),
    col('decimal', 'Quantity', 'Quantity', **QTY),
    col('text', 'Uom', 'Unit of Measure', max=20),
    col('currency', 'UnitPrice', 'Unit Price'),
    col('currency', 'TotalPrice', 'Total Price', 'Quantity x unit price when empty'),
    col('decimal', 'VatRate', 'VAT Rate %', min=0, maxv=100),
  ],
  # purchasing totals deferred from Phase 1
  'account': [
    col('currency', 'Spend', 'Spend', 'Purchase orders not cancelled. Set by plugin', secured=True),
    col('whole', 'ContactCount', 'Contacts', 'Set by plugin'),
  ],
  'op365_item': [
    col('whole', 'UsageCount', 'Order Lines', 'Purchase order lines not cancelled. Set by plugin'),
    col('currency', 'Spend', 'Spend', 'Purchase order lines not cancelled. Set by plugin', secured=True),
  ],
}

LOOKUPS = [
  ('op365_purchaserequest', 'ProjectId', 'Project', 'op365_project', True, True),
  ('op365_purchaserequest', 'WbsNodeId', 'WBS Node', 'op365_wbsnode', False, False),
  ('op365_purchaserequest', 'PreferredSupplierId', 'Preferred Supplier', 'account', False, False),
  ('op365_purchaserequest', 'RequesterId', 'Requester', 'systemuser', False, False),
  ('op365_purchaserequest', 'CurrentApproverId', 'Current Approver', 'systemuser', False, False),
  ('op365_purchaserequest', 'ManagerApprovedById', 'Manager Approved By', 'systemuser', False, False),
  ('op365_purchaserequest', 'DecidedById', 'Decided By', 'systemuser', False, False),
  ('op365_purchaserequestline', 'PurchaseRequestId', 'Purchase Request', 'op365_purchaserequest', True, True),
  ('op365_purchaserequestline', 'ItemId', 'Item', 'op365_item', False, False),
  ('op365_rfq', 'ProjectId', 'Project', 'op365_project', True, True),
  ('op365_rfq', 'PurchaseRequestId', 'Purchase Request', 'op365_purchaserequest', False, True),
  ('op365_rfqinvitation', 'RfqId', 'RFQ', 'op365_rfq', True, True),
  ('op365_rfqinvitation', 'SupplierId', 'Supplier', 'account', 'restrict', True),
  ('op365_rfq', 'WinningInvitationId', 'Winning Invitation', 'op365_rfqinvitation', False, False),
  ('op365_rfqquote', 'InvitationId', 'Invitation', 'op365_rfqinvitation', True, True),
  ('op365_rfqquote', 'RequestLineId', 'Request Line', 'op365_purchaserequestline', False, True),
  ('op365_purchaseorder', 'ProjectId', 'Project', 'op365_project', True, True),
  ('op365_purchaseorder', 'SupplierId', 'Supplier', 'account', 'restrict', True),
  ('op365_purchaseorder', 'PurchaseRequestId', 'Purchase Request', 'op365_purchaserequest', False, False),
  ('op365_rfq', 'PurchaseOrderId', 'Purchase Order', 'op365_purchaseorder', False, False),
  ('op365_purchaseorderline', 'PurchaseOrderId', 'Purchase Order', 'op365_purchaseorder', True, True),
  ('op365_purchaseorderline', 'ItemId', 'Item', 'op365_item', False, False),
  ('op365_purchaseorderline', 'WbsNodeId', 'WBS Node', 'op365_wbsnode', False, False),
  ('op365_purchaseorderline', 'RequestLineId', 'Request Line', 'op365_purchaserequestline', False, False),
  ('op365_goodsreceipt', 'ProjectId', 'Project', 'op365_project', True, True),
  ('op365_goodsreceipt', 'PurchaseOrderId', 'Purchase Order', 'op365_purchaseorder', False, True),
  ('op365_goodsreceiptline', 'GoodsReceiptId', 'Goods Receipt', 'op365_goodsreceipt', True, True),
  ('op365_goodsreceiptline', 'OrderLineId', 'Order Line', 'op365_purchaseorderline', False, True),
  ('op365_materialusage', 'GoodsReceiptLineId', 'Goods Receipt Line', 'op365_goodsreceiptline', False, False),
  ('op365_supplierinvoice', 'SupplierId', 'Supplier', 'account', 'restrict', True),
  ('op365_supplierinvoice', 'PurchaseOrderId', 'Purchase Order', 'op365_purchaseorder', False, False),
  ('op365_supplierinvoice', 'ProjectId', 'Project', 'op365_project', False, False),
  ('op365_supplierinvoice', 'DecidedById', 'Decided By', 'systemuser', False, False),
  ('op365_supplierinvoiceline', 'SupplierInvoiceId', 'Supplier Invoice', 'op365_supplierinvoice', True, True),
  ('op365_supplierinvoiceline', 'OrderLineId', 'Order Line', 'op365_purchaseorderline', False, False),
  ('op365_settings', 'PurchasingApproverId', 'Purchasing Approver',
   'systemuser', False, False),
]

# status reasons of the active state (value 1 is the default one); only the Custom APIs change them
S = 365000000
STATUS = {
  'op365_purchaserequest': ['Draft', 'Submitted', 'Approved', 'Rejected', 'Cancelled', 'Ordered'],
  'op365_rfq': ['Draft', 'Sent', 'Awarded', 'Cancelled'],
  'op365_rfqinvitation': ['To Invite', 'Invited', 'Responded', 'Declined'],
  'op365_purchaseorder': ['Draft', 'Sent', 'Confirmed', 'Received', 'Cancelled'],
  'op365_supplierinvoice': ['To Review', 'Approved', 'Rejected'],
}

create_tables(TABLES)
create_columns(COLUMNS)
create_lookups(LOOKUPS)
for table, names in STATUS.items():
    status_reasons(table, [(1, 0, names[0])] + [(S + i, 0, n) for i, n in enumerate(names[1:])])
for table in ['op365_purchaserequest', 'op365_rfq', 'op365_purchaseorder', 'op365_goodsreceipt', 'op365_supplierinvoice']:
    enable_timeline(table)
publish()
