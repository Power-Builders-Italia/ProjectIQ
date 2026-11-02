"""Supplier invoices from the supplier portal and their payment (docs/en/purchasing.md#5-supplier-invoices).

- status reason Draft (365000002, active) of op365_supplierinvoice: invoices uploaded on the portal stay Draft until the
  supplier sends them (Draft -> To Review);
- reading of the file by the plugin SupplierInvoiceExtract (FatturaPA XML, or PDF/image with AI Builder): Extraction
  Status (Pending, Ready, To Check, Blocked), Extraction Source, Extraction Notes, Fields to Check, Extract Requested,
  From Supplier Portal and the Supplier Note;
- payment: Due Date, Payment Status (Not Paid, Scheduled, Partially Paid, Paid), Paid Amount, Paid On, Payment Reference.

Adds the sections Supplier Portal and Payment to the Supplier Invoice form (patches the live form) and the views Invoices to
Pay and Supplier Invoice Drafts; the review views leave the drafts out. Idempotent; reads the PAC_* variables.
Run plugins.py and settings_env.py afterwards.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from meta import col, create_columns, status_reasons, publish, BASE as S
from viewlib import view
import formlib
from formlib import section, use_ids

T = 'op365_supplierinvoice'

status_reasons(T, [(S + 2, 0, 'Draft')])

create_columns({T: [
    col('choice', 'ExtractionStatus', 'Extraction Status',
        'Pending while the file is read; Ready, To Check (low confidence, differences from the order, order to choose) or '
        'Blocked (duplicate of another invoice) afterwards. Set by plugin',
        options=['Pending', 'Ready', 'To Check', 'Blocked']),
    col('choice', 'ExtractionSource', 'Extraction Source', 'How the data were read from the file. Set by plugin',
        options=['FatturaPA XML', 'AI Builder', 'Manual']),
    col('memo', 'ExtractionNotes', 'Extraction Notes', 'What the supplier and the reviewer should check. Set by plugin', max=4000),
    col('text', 'CheckFields', 'Fields to Check', 'Columns read with low confidence or missing. Set by plugin', max=400),
    col('bool', 'ExtractRequested', 'Extract Requested', 'Set to Yes to read the file again (the plugin sets it back to No)'),
    col('bool', 'FromPortal', 'From Supplier Portal', 'The supplier uploaded the invoice in the supplier portal'),
    col('memo', 'SupplierNote', 'Supplier Note', 'Note of the supplier for the reviewer, for example about a difference from the order', max=2000),
    col('date', 'DueDate', 'Due Date', 'Payment due date, from the FatturaPA or the PDF when present'),
    col('choice', 'PaymentStatus', 'Payment Status', 'Set by the accounting staff on approved invoices; shown to the supplier',
        options=['Not Paid', 'Scheduled', 'Partially Paid', 'Paid'], default=0),
    col('currency', 'PaidAmount', 'Paid Amount', 'Amount paid so far; Paid fills it with the total when empty'),
    col('date', 'PaidOn', 'Paid On', 'Date of the (last) payment; Paid fills it with today when empty'),
    col('text', 'PaymentReference', 'Payment Reference', 'Bank transfer reference (CRO/TRN) shown to the supplier', max=100),
]})

INV = [('op365_number', 100), ('op365_supplierid', 200), ('op365_invoicenumber', 110), ('op365_invoicedate', 100),
       ('op365_purchaseorderid', 110), ('op365_projectid', 180), ('statuscode', 100), ('op365_totalamount', 120)]
LATEST = [('op365_invoicedate', True)]
DRAFT = str(S + 2)
view(T, 'All Supplier Invoices', INV + [('op365_paymentstatus', 110)], LATEST, [('statuscode', 'ne', DRAFT)], default=True,
     description='Invoices received (supplier drafts not yet sent are left out)')
view(T, 'Invoices to Review', INV + [('op365_fromportal', 90), ('op365_extractionstatus', 110)], LATEST, [('statuscode', 'eq', 1)])
view(T, 'Invoices to Pay', INV + [('op365_duedate', 100), ('op365_paymentstatus', 110), ('op365_paidamount', 110)],
     [('op365_duedate', False)], [('op365_paymentstatus', 'ne', str(S + 3)), ('op365_paymentstatus', 'null', None)],
     filter_type='or', also=[('statuscode', 'eq', str(S))],
     description='Approved invoices not yet paid, by due date')
view(T, 'Supplier Invoice Drafts', INV + [('op365_extractionstatus', 110), ('modifiedon', 140)], [('modifiedon', False)],
     [('statuscode', 'eq', DRAFT)], description='Invoices the suppliers uploaded on the portal and have not sent yet')

# Supplier Portal and Payment sections after Attachment
use_ids('op365-supplier-invoices')
SECTIONS = (section(T, 'Supplier Portal', ['op365_fromportal!', 'op365_extractionstatus!', 'op365_extractionsource!',
                                           'op365_checkfields!', 'op365_extractionnotes!', 'op365_suppliernote!'], columns=1)
            + section(T, 'Payment', ['op365_duedate', 'op365_paymentstatus', 'op365_paidamount', 'op365_paidon',
                                     'op365_paymentreference'], columns=1))
f = formlib.S.get(formlib.API + f"systemforms?$select=formid,formxml&$filter=objecttypecode eq '{T}' and type eq 2 "
                  "and name eq 'Supplier Invoice'").json()['value'][0]
if 'name="payment"' not in f['formxml']:
    head, tail = f['formxml'].split('<section name="attachment"', 1)
    end = tail.index('</section>') + len('</section>')
    xml = head + '<section name="attachment"' + tail[:end] + SECTIONS + tail[end:]
    formlib.ok(formlib.S.patch(formlib.API + f"systemforms({f['formid']})", json={'formxml': xml}),
               'form Supplier Invoice: Supplier Portal and Payment sections')
publish()
