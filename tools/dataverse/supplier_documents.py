"""Supplier documents: review by the buyer and expiry tracking (docs/en/master-data.md#supplier-documents).

- status reasons of op365_supplierdocument: Approved (1, the former Active, so existing documents stay valid),
  Pending Review and Rejected; the plugins move a document between them (portal upload, Approve/Reject);
- columns Expiry Status, Expiry Notice, From Supplier Portal, Reviewed By, Reviewed On, Review Note;
- activities on the table, so the expiry e-mails sent to the supplier are regarding the document.

Adds the read-only Review sections to the Supplier Document form (patches the live form, so that the supplier
lookup view set on it stays as it is). Also the views Active Supplier Documents (with review and expiry status), Supplier Documents to Review and
Expiring and Expired Supplier Documents.
Idempotent; reads the PAC_* variables. Run plugins.py and settings_env.py afterwards.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from meta import col, create_columns, create_lookups, status_reasons, enable_timeline, publish, BASE as S
from viewlib import view
import formlib
from formlib import section, use_ids

T = 'op365_supplierdocument'

status_reasons(T, [(1, 0, 'Approved'), (S, 0, 'Pending Review'), (S + 1, 0, 'Rejected')])

create_columns({T: [
    col('choice', 'ExpiryStatus', 'Expiry Status',
        'Valid, Expiring (expires within 30 days), Expired, or Replaced by a newer approved document of the same type; '
        'kept by the plugins and the Daily document expiry flow',
        options=['Valid', 'Expiring', 'Expired', 'Replaced']),
    col('choice', 'ExpiryNotice', 'Expiry Notice Sent',
        'Last expiry e-mail sent to the supplier for this document; cleared when the expiry date changes',
        options=['Expiring', 'Expired']),
    col('bool', 'FromPortal', 'From Supplier Portal', 'The supplier uploaded the document in the supplier portal'),
    col('datetime', 'ReviewedOn', 'Reviewed On', 'When the document was approved or rejected'),
    col('memo', 'ReviewNote', 'Review Note', 'Note of the reviewer; the reason when the document is rejected', max=2000),
]})
create_lookups([(T, 'ReviewedById', 'Reviewed By', 'systemuser', False, False)])
enable_timeline(T, activities=True)

COLS = [('op365_documenttype', 130), ('op365_description', 240), ('op365_supplierid', 200), ('op365_number', 110),
        ('op365_expirydate', 110), ('op365_expirystatus', 110), ('statuscode', 120)]
view(T, 'Active Supplier Documents', COLS, [('op365_expirydate', False)], default=True)
view(T, 'Supplier Documents to Review', COLS + [('op365_fromportal', 110), ('modifiedon', 140)], [('modifiedon', False)],
     [('statuscode', 'eq', str(S))], description='Documents sent by suppliers that wait for Approve or Reject')
view(T, 'Expiring and Expired Supplier Documents', COLS, [('op365_expirydate', False)],
     [('op365_expirystatus', 'eq', str(S + 1)), ('op365_expirystatus', 'eq', str(S + 2))], filter_type='or',
     also=[('statuscode', 'eq', '1')], description='Approved documents that expire within 30 days or are expired')

# Review sections after the Document section of the main form, read-only (Approve and Reject change them)
use_ids('op365-supplier-documents')
REVIEW = (section(T, 'Review', ['statuscode!', 'op365_expirystatus!', 'op365_reviewedbyid!', 'op365_reviewedon!',
                                'op365_fromportal!', 'op365_expirynotice!'])
          + section(T, 'Review Note', ['op365_reviewnote!'], columns=1))
f = formlib.S.get(formlib.API + f"systemforms?$select=formid,formxml&$filter=objecttypecode eq '{T}' and type eq 2 "
                  "and name eq 'Supplier Document'").json()['value'][0]
if 'name="review"' not in f['formxml']:
    head, tail = f['formxml'].split('<section name="document"', 1)
    end = tail.index('</section>') + len('</section>')
    xml = head + '<section name="document"' + tail[:end] + REVIEW + tail[end:]
    formlib.ok(formlib.S.patch(formlib.API + f"systemforms({f['formid']})", json={'formxml': xml}),
               'form Supplier Document: Review sections')
publish()
