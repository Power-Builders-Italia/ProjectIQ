"""Plugin registration (all phases): OpenProject365.Plugins assembly, steps, images and Custom APIs.

Build the assembly first:  dotnet build src/plugins/OpenProject365.Plugins -c Release
Idempotent: the assembly content is updated, missing types/steps/images are created.
"""
import base64, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API
from meta import ok

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DLL = os.path.join(ROOT, 'src/plugins/OpenProject365.Plugins/bin/Release/net462/OpenProject365.Plugins.dll')
NSP = 'OpenProject365.Plugins.'
PREVAL, PRE, POST = 10, 20, 40
TE_IMAGE = 'statuscode,op365_projectid,op365_wbsnodeid,op365_resourceid,op365_entrydate,op365_hours'
MU_IMAGE = 'op365_projectid,op365_wbsnodeid,op365_itemid,op365_supplierid,op365_quantity,op365_unitcost,op365_name,op365_uom'

MU_FIELDS = 'op365_projectid,op365_itemid,op365_supplierid,op365_quantity,op365_unitcost,op365_usagedate,op365_name,op365_uom,statecode'
PR_FIELDS = ('statuscode,statecode,op365_title,op365_justification,op365_neededby,op365_projectid,op365_wbsnodeid,'
             'op365_preferredsupplierid,op365_requesterid')
PRL_FIELDS = 'op365_purchaserequestid,op365_itemid,op365_name,op365_quantity,op365_uom,op365_estimatedprice,op365_notes'
PO_FIELDS = ('statuscode,statecode,op365_supplierid,op365_projectid,op365_purchaserequestid,op365_orderdate,op365_expecteddelivery,'
             'op365_deliveryplace,op365_paymentterms,op365_notes,op365_supplierconfirmed')
POL_FIELDS = 'op365_purchaseorderid,op365_itemid,op365_wbsnodeid,op365_name,op365_quantity,op365_uom,op365_price,op365_receivedquantity'
INV_FIELDS = ('statuscode,statecode,op365_supplierid,op365_purchaseorderid,op365_projectid,op365_invoicenumber,op365_invoicedate,'
              'op365_documenttype,op365_taxableamount,op365_vatamount,op365_totalamount,op365_sellername,op365_sellervatnumber')

# class, message, table, stage, filtering attributes, pre-image attributes
STEPS = [
  ('ResourceDefaults', 'Create', 'op365_resource', PRE, None, None),
  ('ResourceCostSync', 'Create', 'op365_resourcecost', POST, None, None),
  ('ResourceCostSync', 'Update', 'op365_resourcecost', POST, 'op365_validfrom,op365_hourlycost,op365_resourceid,statecode', 'op365_resourceid'),
  ('ResourceCostSync', 'Delete', 'op365_resourcecost', POST, None, 'op365_resourceid'),
  ('ProjectMemberName', 'Create', 'op365_projectmember', PRE, None, None),
  ('ProjectMemberSync', 'Create', 'op365_projectmember', POST, None, None),
  ('ProjectMemberSync', 'Update', 'op365_projectmember', POST, 'op365_userid,op365_projectrole', 'op365_projectid,op365_userid,op365_projectrole'),
  ('ProjectMemberSync', 'Delete', 'op365_projectmember', POST, None, 'op365_projectid,op365_userid,op365_projectrole'),
  ('ProjectSync', 'Create', 'op365_project', POST, None, None),
  ('ProjectSync', 'Update', 'op365_project', POST, 'op365_projectmanagerid,op365_customerid,op365_contractvalue,statecode', 'op365_customerid'),
  ('ProjectSync', 'Delete', 'op365_project', POST, None, 'op365_customerid'),
  ('WbsNodeBudget', 'Create', 'op365_wbsnode', PRE, None, None),
  ('WbsNodeBudget', 'Update', 'op365_wbsnode', PRE, 'op365_budgetlabour,op365_budgetmaterials,op365_budgetother',
   'op365_budgetlabour,op365_budgetmaterials,op365_budgetother'),
  ('WbsNodeRollup', 'Create', 'op365_wbsnode', POST, None, None),
  ('WbsNodeRollup', 'Update', 'op365_wbsnode', POST,
   'op365_budgetlabour,op365_budgetmaterials,op365_budgetother,op365_budgettotal,op365_budgethours,op365_progresspct,op365_parentid,statecode',
   'op365_projectid'),
  ('WbsNodeRollup', 'Delete', 'op365_wbsnode', POST, None, 'op365_projectid'),
  ('WbsNodeDelete', 'Delete', 'op365_wbsnode', PREVAL, None, None),  # before the lookups are cleared
  ('WbsDependencyValidate', 'Create', 'op365_wbsdependency', PRE, None, None),
  ('WbsDependencyValidate', 'Update', 'op365_wbsdependency', PRE, 'op365_predecessorid,op365_successorid',
   'op365_predecessorid,op365_successorid'),
  ('BaselineReference', 'Create', 'op365_baseline', POST, None, None),
  ('BaselineReference', 'Update', 'op365_baseline', POST, 'op365_isreference', 'op365_projectid'),
  # Phase 3
  ('TimeEntryValidate', 'Create', 'op365_timeentry', PRE, None, None),
  ('TimeEntryValidate', 'Update', 'op365_timeentry', PRE, TE_IMAGE + ',statecode,op365_notes,op365_cost,op365_revenue', TE_IMAGE),
  ('TimeEntryDelete', 'Delete', 'op365_timeentry', PRE, None, 'statuscode'),
  ('ActualsRollup', 'Create', 'op365_timeentry', POST, None, None),
  ('ActualsRollup', 'Update', 'op365_timeentry', POST, 'op365_projectid,op365_wbsnodeid,op365_hours,op365_cost,statuscode', 'op365_projectid'),
  ('ActualsRollup', 'Delete', 'op365_timeentry', POST, None, 'op365_projectid'),
  ('MaterialUsageValidate', 'Create', 'op365_materialusage', PRE, None, None),
  ('MaterialUsageValidate', 'Update', 'op365_materialusage', PRE,
   'op365_projectid,op365_wbsnodeid,op365_itemid,op365_supplierid,op365_quantity,op365_unitcost', MU_IMAGE),
  ('ActualsRollup', 'Create', 'op365_materialusage', POST, None, None),
  ('ActualsRollup', 'Update', 'op365_materialusage', POST, 'op365_projectid,op365_wbsnodeid,op365_totalcost,statecode', 'op365_projectid'),
  ('ActualsRollup', 'Delete', 'op365_materialusage', POST, None, 'op365_projectid'),
  # Phase 4
  ('MaterialUsageReceiptGuard', 'Update', 'op365_materialusage', PREVAL, MU_FIELDS, 'op365_goodsreceiptlineid'),
  ('MaterialUsageReceiptGuard', 'Delete', 'op365_materialusage', PREVAL, None, 'op365_goodsreceiptlineid'),
  ('PurchaseRequestValidate', 'Create', 'op365_purchaserequest', PRE, None, None),
  ('PurchaseRequestValidate', 'Update', 'op365_purchaserequest', PRE, PR_FIELDS, 'statuscode,op365_projectid,op365_wbsnodeid'),
  ('PurchaseRequestDelete', 'Delete', 'op365_purchaserequest', PRE, None, 'statuscode'),
  ('PurchaseRequestLineValidate', 'Create', 'op365_purchaserequestline', PRE, None, None),
  ('PurchaseRequestLineValidate', 'Update', 'op365_purchaserequestline', PRE, PRL_FIELDS, PRL_FIELDS),
  ('PurchaseRequestLineValidate', 'Delete', 'op365_purchaserequestline', PRE, None, 'op365_purchaserequestid'),
  ('PurchaseRequestTotals', 'Create', 'op365_purchaserequestline', POST, None, None),
  ('PurchaseRequestTotals', 'Update', 'op365_purchaserequestline', POST, 'op365_amount,op365_purchaserequestid,statecode', 'op365_purchaserequestid'),
  ('PurchaseRequestTotals', 'Delete', 'op365_purchaserequestline', POST, None, 'op365_purchaserequestid'),
  ('RfqInvitationValidate', 'Create', 'op365_rfqinvitation', PRE, None, None),
  ('RfqInvitationValidate', 'Update', 'op365_rfqinvitation', PRE, 'statuscode,op365_supplierid,op365_email,op365_deliverydays,op365_suppliernotes',
   'statuscode,op365_rfqid,op365_supplierid,op365_email'),
  ('RfqResponses', 'Create', 'op365_rfqinvitation', POST, None, None),
  ('RfqResponses', 'Update', 'op365_rfqinvitation', POST, 'statuscode', 'op365_rfqid'),
  ('RfqResponses', 'Delete', 'op365_rfqinvitation', POST, None, 'op365_rfqid'),
  ('RfqQuoteValidate', 'Create', 'op365_rfqquote', PRE, None, None),
  ('RfqQuoteValidate', 'Update', 'op365_rfqquote', PRE, 'op365_price,op365_requestlineid,op365_invitationid', 'op365_invitationid,op365_requestlineid'),
  ('RfqQuoteValidate', 'Delete', 'op365_rfqquote', PRE, None, 'op365_invitationid'),
  ('RfqQuoteTotals', 'Create', 'op365_rfqquote', POST, None, None),
  ('RfqQuoteTotals', 'Update', 'op365_rfqquote', POST, 'op365_price,op365_requestlineid,statecode', 'op365_invitationid'),
  ('RfqQuoteTotals', 'Delete', 'op365_rfqquote', POST, None, 'op365_invitationid'),
  ('PurchaseOrderValidate', 'Create', 'op365_purchaseorder', PRE, None, None),
  ('PurchaseOrderValidate', 'Update', 'op365_purchaseorder', PRE, PO_FIELDS, 'statuscode,op365_projectid,op365_supplierid,op365_paymentterms'),
  ('PurchaseOrderDelete', 'Delete', 'op365_purchaseorder', PRE, None, 'statuscode'),
  ('PurchaseOrderLineValidate', 'Create', 'op365_purchaseorderline', PRE, None, None),
  ('PurchaseOrderLineValidate', 'Update', 'op365_purchaseorderline', PRE, POL_FIELDS, POL_FIELDS),
  ('PurchaseOrderLineValidate', 'Delete', 'op365_purchaseorderline', PRE, None, 'op365_purchaseorderid'),
  ('PurchaseTotals', 'Create', 'op365_purchaseorderline', POST, None, None),
  ('PurchaseTotals', 'Update', 'op365_purchaseorderline', POST, 'op365_amount,op365_quantity,op365_price,op365_receivedquantity,op365_itemid,statecode',
   'op365_purchaseorderid,op365_itemid'),
  ('PurchaseTotals', 'Delete', 'op365_purchaseorderline', POST, None, 'op365_purchaseorderid,op365_itemid'),
  ('PurchaseTotals', 'Update', 'op365_purchaseorder', POST, 'statuscode,op365_projectid,op365_supplierid,op365_totalamount,statecode',
   'op365_projectid,op365_supplierid'),
  ('PurchaseTotals', 'Delete', 'op365_purchaseorder', POST, None, 'op365_projectid,op365_supplierid'),
  ('GoodsReceiptGuard', 'Create', 'op365_goodsreceipt', PRE, None, None),
  ('GoodsReceiptGuard', 'Update', 'op365_goodsreceipt', PRE, 'op365_purchaseorderid,op365_projectid,op365_receiptdate,op365_deliverynotenumber,op365_deliverynotedate,op365_notes', None),
  ('GoodsReceiptGuard', 'Delete', 'op365_goodsreceipt', PRE, None, None),
  ('GoodsReceiptGuard', 'Create', 'op365_goodsreceiptline', PRE, None, None),
  ('GoodsReceiptGuard', 'Update', 'op365_goodsreceiptline', PRE, 'op365_quantity,op365_orderlineid,op365_goodsreceiptid', None),
  ('GoodsReceiptGuard', 'Delete', 'op365_goodsreceiptline', PRE, None, None),
  ('SupplierInvoiceValidate', 'Create', 'op365_supplierinvoice', PRE, None, None),
  ('SupplierInvoiceValidate', 'Update', 'op365_supplierinvoice', PRE, INV_FIELDS, 'statuscode,op365_supplierid,op365_purchaseorderid,op365_projectid,op365_sellername,op365_sellervatnumber'),
  ('SupplierInvoiceLineValidate', 'Create', 'op365_supplierinvoiceline', PRE, None, None),
  ('SupplierInvoiceLineValidate', 'Update', 'op365_supplierinvoiceline', PRE, 'op365_quantity,op365_unitprice,op365_totalprice,op365_vatrate,op365_name,op365_code',
   'op365_supplierinvoiceid,op365_quantity,op365_unitprice'),
  ('SupplierInvoiceLineValidate', 'Delete', 'op365_supplierinvoiceline', PRE, None, 'op365_supplierinvoiceid'),
  ('SupplierInvoiceTotals', 'Create', 'op365_supplierinvoiceline', POST, None, None),
  ('SupplierInvoiceTotals', 'Update', 'op365_supplierinvoiceline', POST, 'op365_totalprice,op365_vatrate,statecode', 'op365_supplierinvoiceid'),
  ('SupplierInvoiceTotals', 'Delete', 'op365_supplierinvoiceline', POST, None, 'op365_supplierinvoiceid'),
  ('ContactCount', 'Create', 'contact', POST, None, None),
  ('ContactCount', 'Update', 'contact', POST, 'parentcustomerid,statecode', 'parentcustomerid'),
  ('ContactCount', 'Delete', 'contact', POST, None, 'parentcustomerid'),
  # supplier documents: review and expiry (supplier_documents.py)
  ('SupplierDocumentValidate', 'Create', 'op365_supplierdocument', PRE, None, None),
  ('SupplierDocumentValidate', 'Update', 'op365_supplierdocument', PRE, None, 'statuscode,op365_expirydate'),
  ('SupplierDocumentDelete', 'Delete', 'op365_supplierdocument', PRE, None, 'statuscode'),
  ('SupplierDocumentAlerts', 'Create', 'op365_supplierdocument', POST, None, None),
  ('SupplierDocumentAlerts', 'Update', 'op365_supplierdocument', POST,
   'op365_expirydate,statuscode,statecode,op365_documenttype,op365_supplierid', 'op365_supplierid,statuscode,op365_description'),
  ('SupplierDocumentAlerts', 'Delete', 'op365_supplierdocument', POST, None, 'op365_supplierid'),
]

# Custom APIs: unique name -> class, display name, description, binding table (None = unbound), function,
# request parameters (name, type, optional, description), response properties (name, type, description).
# Types: 0 Boolean, 1 DateTime, 2 Decimal, 7 Integer, 10 String, 11 StringArray, 12 Guid.
APIS = {
  'op365_SaveBaseline': ('SaveBaseline', 'Save Baseline',
      'Saves the current WBS budget and dates of the project as a new baseline', 'op365_project', False,
      [('Name', 10, True, 'Baseline name; default "Baseline <date>"'),
       ('KeepReference', 0, True, 'Keep the current reference baseline instead of replacing it (default false)')],
      [('BaselineId', 12, 'Id of the new baseline')]),
  'op365_SubmitTimeEntries': ('SubmitTimeEntries', 'Submit Time Entries',
      'Submits draft or rejected time entries for approval (approves them when time approval is off)', None, False,
      [('TimeEntryIds', 11, False, 'Ids of the time entries')],
      [('Count', 7, 'Number of entries submitted')]),
  'op365_DecideTimeEntries': ('DecideTimeEntries', 'Decide Time Entries',
      'Approves or rejects submitted time entries (project managers and administrators)', None, False,
      [('TimeEntryIds', 11, False, 'Ids of the time entries'),
       ('Approve', 0, False, 'True to approve, false to reject'),
       ('Note', 10, True, 'Decision note; required to reject')],
      [('Count', 7, 'Number of entries decided')]),
  'op365_GetLabourCost': ('GetLabourCost', 'Get Labour Cost',
      'Hourly cost of a resource on a date (requires the Cost Visibility profile)', None, True,
      [('ResourceId', 12, False, 'Resource'), ('Date', 1, False, 'Date')],
      [('HourlyCost', 2, 'Hourly cost valid on the date')]),
  'op365_SendTimeReminders': ('SendTimeReminders', 'Send Time Reminders',
      'Notifies the users who recorded fewer hours than expected on the date (daily time reminder flow)', None, False,
      [('Date', 1, True, 'Date; default today in Europe/Rome')],
      [('Count', 7, 'Number of reminders sent')]),
  # Phase 4: purchasing
  'op365_SubmitPurchaseRequest': ('SubmitPurchaseRequest', 'Submit Purchase Request',
      'Submits a draft or rejected purchase request to the project manager', 'op365_purchaserequest', False, [], []),
  'op365_DecidePurchaseRequest': ('DecidePurchaseRequest', 'Decide Purchase Request',
      'Approves or rejects a submitted purchase request (above the threshold a second approval is needed)', 'op365_purchaserequest', False,
      [('Approve', 0, False, 'True to approve, false to reject'), ('Note', 10, True, 'Decision note; required to reject')], []),
  'op365_CancelPurchaseRequest': ('CancelPurchaseRequest', 'Cancel Purchase Request',
      'Cancels a purchase request that is not ordered', 'op365_purchaserequest', False, [], []),
  'op365_CreateRfq': ('CreateRfq', 'Create RFQ', 'Creates a request for quotation with supplier invitations from an approved purchase request',
      'op365_purchaserequest', False,
      [('Deadline', 1, True, 'Deadline; default in 7 days'), ('SupplierIds', 11, True, 'Suppliers to invite; default preferred and item suppliers')],
      [('RfqId', 12, 'New request for quotation')]),
  'op365_SendRfq': ('SendRfq', 'Send RFQ', 'Sends the request for quotation to the invited suppliers', 'op365_rfq', False, [],
      [('Count', 7, 'Suppliers invited')]),
  'op365_AwardRfq': ('AwardRfq', 'Award RFQ', 'Awards the request for quotation to a supplier and creates the purchase order', 'op365_rfq', False,
      [('InvitationId', 12, False, 'Winning invitation')], [('PurchaseOrderId', 12, 'New purchase order')]),
  'op365_CancelRfq': ('CancelRfq', 'Cancel RFQ', 'Cancels a draft or sent request for quotation', 'op365_rfq', False, [], []),
  'op365_CreatePurchaseOrder': ('CreatePurchaseOrder', 'Create Purchase Order', 'Creates a draft purchase order from an approved purchase request',
      'op365_purchaserequest', False, [('SupplierId', 12, True, 'Supplier; default the preferred supplier')],
      [('PurchaseOrderId', 12, 'New purchase order')]),
  'op365_SetPurchaseOrderStatus': ('SetPurchaseOrderStatus', 'Set Purchase Order Status',
      'Moves a purchase order to Sent, Confirmed, Draft or Cancelled', 'op365_purchaseorder', False,
      [('Status', 10, False, 'Sent, Confirmed, Draft or Cancelled')], []),
  'op365_RegisterGoodsReceipt': ('RegisterGoodsReceipt', 'Register Goods Receipt',
      'Registers a goods receipt and the material usage of the received lines', 'op365_purchaseorder', False,
      [('ReceiptDate', 1, True, 'Receipt date; default today'), ('DeliveryNoteNumber', 10, True, 'Delivery note number'),
       ('DeliveryNoteDate', 1, True, 'Delivery note date'), ('Lines', 11, True, '"orderLineId=quantity"; default everything still to receive')],
      [('GoodsReceiptId', 12, 'New goods receipt')]),
  'op365_CancelGoodsReceipt': ('CancelGoodsReceipt', 'Cancel Goods Receipt',
      'Deletes a goods receipt with its material usage and restores the order quantities', 'op365_goodsreceipt', False, [], []),
  'op365_DecideSupplierInvoice': ('DecideSupplierInvoice', 'Decide Supplier Invoice', 'Approves or rejects a supplier invoice',
      'op365_supplierinvoice', False,
      [('Approve', 0, False, 'True to approve, false to reject'), ('Note', 10, True, 'Decision note; required to reject')], []),
  'op365_DecideSupplierDocument': ('DecideSupplierDocument', 'Decide Supplier Document',
      'Approves or rejects a supplier document pending review', 'op365_supplierdocument', False,
      [('Approve', 0, False, 'True to approve, false to reject'), ('Note', 10, True, 'Review note; required to reject')], []),
  'op365_UpdateDocumentExpiry': ('UpdateDocumentExpiry', 'Update Document Expiry',
      'Refreshes the expiry status of the supplier documents and the supplier alert counters, and e-mails the expiry notices '
      '(daily document expiry flow)', None, False,
      [('Date', 1, True, 'Date; default today in Europe/Rome')],
      [('Count', 7, 'Documents whose expiry status changed'), ('Sent', 7, 'E-mails sent to suppliers')]),
}


def one(url):
    v = S.get(API + url).json().get('value', [])
    return v[0] if v else None


def created_id(r):
    return r.headers['OData-EntityId'].rsplit('(', 1)[1].rstrip(')')


# ---------- assembly ----------
content = base64.b64encode(open(DLL, 'rb').read()).decode()
asm = one("pluginassemblies?$select=pluginassemblyid&$filter=name eq 'OpenProject365.Plugins'")
if asm:
    asm_id = asm['pluginassemblyid']
    ok(S.patch(API + f'pluginassemblies({asm_id})', json={'content': content}), 'assembly updated')
else:
    r = S.post(API + 'pluginassemblies', json={'name': 'OpenProject365.Plugins', 'content': content,
                                                'isolationmode': 2, 'sourcetype': 0})
    ok(r, 'assembly created'); asm_id = created_id(r)

# ---------- types ----------
types = {}
for cls in sorted({s[0] for s in STEPS} | {a[0] for a in APIS.values()}):
    t = one(f"plugintypes?$select=plugintypeid&$filter=typename eq '{NSP + cls}'")
    if t:
        types[cls] = t['plugintypeid']; continue
    r = S.post(API + 'plugintypes', json={'typename': NSP + cls, 'name': NSP + cls, 'friendlyname': cls,
                                          'pluginassemblyid@odata.bind': f'/pluginassemblies({asm_id})'})
    ok(r, 'type ' + cls); types[cls] = created_id(r)

# ---------- steps ----------
_msg = {}
def message(name):
    if name not in _msg:
        _msg[name] = one(f"sdkmessages?$select=sdkmessageid&$filter=name eq '{name}'")['sdkmessageid']
    return _msg[name]


for cls, msg, table, stage, filtering, image in STEPS:
    name = f'{cls}: {msg} of {table} ({ {PREVAL: "PreValidation", PRE: "PreOperation", POST: "PostOperation"}[stage]})'
    step = one(f"sdkmessageprocessingsteps?$select=sdkmessageprocessingstepid,filteringattributes&$filter=name eq '{name}'")
    if step:
        sid = step['sdkmessageprocessingstepid']
        if filtering and step.get('filteringattributes') != filtering:
            ok(S.patch(API + f'sdkmessageprocessingsteps({sid})', json={'filteringattributes': filtering}), 'filter ' + name)
        else:
            print('skip', name)
    else:
        flt = one(f"sdkmessagefilters?$select=sdkmessagefilterid&$filter=primaryobjecttypecode eq '{table}' "
                  f"and _sdkmessageid_value eq {message(msg)}")['sdkmessagefilterid']
        body = {'name': name, 'stage': stage, 'mode': 0, 'rank': 1, 'supporteddeployment': 0,
                'sdkmessageid@odata.bind': f'/sdkmessages({message(msg)})',
                'sdkmessagefilterid@odata.bind': f'/sdkmessagefilters({flt})',
                'plugintypeid@odata.bind': f'/plugintypes({types[cls]})'}
        if filtering:
            body['filteringattributes'] = filtering
        r = S.post(API + 'sdkmessageprocessingsteps', json=body)
        ok(r, name); sid = created_id(r)
    if image and not one(f"sdkmessageprocessingstepimages?$select=sdkmessageprocessingstepimageid"
                         f"&$filter=_sdkmessageprocessingstepid_value eq {sid}"):
        ok(S.post(API + 'sdkmessageprocessingstepimages', json={
            'name': 'PreImage', 'entityalias': 'PreImage', 'imagetype': 0, 'messagepropertyname': 'Target',
            'attributes': image, 'sdkmessageprocessingstepid@odata.bind': f'/sdkmessageprocessingsteps({sid})'}),
           '  pre-image ' + image)

# ---------- Custom APIs ----------
for uname, (cls, display, desc, bound, function, params, props) in APIS.items():
    capi = one(f"customapis?$select=customapiid&$filter=uniquename eq '{uname}'")
    if capi:
        capi_id = capi['customapiid']; print('skip', uname)
    else:
        body = {'uniquename': uname, 'name': display, 'displayname': display, 'description': desc,
                'bindingtype': 1 if bound else 0, 'isfunction': function, 'allowedcustomprocessingsteptype': 0,
                'PluginTypeId@odata.bind': f'/plugintypes({types[cls]})'}
        if bound:
            body['boundentitylogicalname'] = bound
        r = S.post(API + 'customapis', json=body)
        ok(r, 'custom api ' + uname); capi_id = created_id(r)
    for pname, typ, optional, pdesc in params:
        if one(f"customapirequestparameters?$select=customapirequestparameterid&$filter=_customapiid_value eq {capi_id} "
               f"and uniquename eq '{pname}'"):
            continue
        ok(S.post(API + 'customapirequestparameters', json={
            'uniquename': pname, 'name': f'{uname}.{pname}', 'displayname': pname, 'description': pdesc,
            'type': typ, 'isoptional': optional, 'CustomAPIId@odata.bind': f'/customapis({capi_id})'}), '  parameter ' + pname)
    for pname, typ, pdesc in props:
        if one(f"customapiresponseproperties?$select=customapiresponsepropertyid&$filter=_customapiid_value eq {capi_id} "
               f"and uniquename eq '{pname}'"):
            continue
        ok(S.post(API + 'customapiresponseproperties', json={
            'uniquename': pname, 'name': f'{uname}.{pname}', 'displayname': pname, 'description': pdesc,
            'type': typ, 'CustomAPIId@odata.bind': f'/customapis({capi_id})'}), '  response ' + pname)

# an unmanaged solution import (e.g. after ribbon.py) leaves the steps of the assembly disabled: turn them back on
disabled = S.get(API + "sdkmessageprocessingsteps?$select=sdkmessageprocessingstepid&$filter=statecode eq 1"
                       f" and _plugintypeid_value ne null&$expand=plugintypeid($select=assemblyname)").json()['value']
for st in disabled:
    if (st.get('plugintypeid') or {}).get('assemblyname') == 'OpenProject365.Plugins':
        ok(S.patch(API + f"sdkmessageprocessingsteps({st['sdkmessageprocessingstepid']})", json={'statecode': 0, 'statuscode': 1}),
           'enable step ' + st['sdkmessageprocessingstepid'])
