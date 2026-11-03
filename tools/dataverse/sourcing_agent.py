"""Sourcing agent foundations: the Agent Proposal table and the roles OP365 Buyer and OP365 Sourcing Agent.

- table op365_agentproposal (child of the project, so the project access teams see the proposals of their projects):
  Kind (Proposal, Insight, Log), Action Type, typed lookups (purchase request, RFQ, invitation, order, supplier invoice,
  supplier, decided by), Rationale, Evidence (column-secured: OP365 Cost Visibility), Payload, Amount, Estimated Saving,
  Dedup Key, Expires On, Decided On, Decision Note, Result Id, Error;
- status reasons: active Pending (default), Open, Failed; inactive Executed (default), Rejected, Expired, Superseded,
  Acknowledged, Done;
- views (Open Agent Proposals, Agent Insights, Agent Log, My Agent Decisions), the Agent Proposal form and the Agent
  Proposals subgrid on the Project form (Purchasing tab);
- privileges of OP365 Administrator and OP365 User, and the new roles OP365 Buyer and OP365 Sourcing Agent.

The option order of Kind and Action Type defines the values (365000000, +1, ...) that ProposalLogic.cs relies on: do not
reorder. Assign the OP365 Cost Visibility profile to the buyers and to the application user of the agent by hand.
Idempotent; reads the PAC_* variables. Run plugins.py, settings_env.py and translations.py afterwards.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S as SESSION, API as WEBAPI
from meta import (col, create_tables, create_columns, create_lookups, status_reasons, grant_roles, publish, one, ok,
                  BASE as S)
from viewlib import view
import formlib
from formlib import section, use_ids

T = 'op365_agentproposal'
ALL = ['Create', 'Read', 'Write', 'Delete', 'Append', 'AppendTo', 'Assign', 'Share']
FULL = ['Create', 'Read', 'Write', 'Delete', 'Append', 'AppendTo']

create_tables([('AgentProposal', 'Agent Proposal', 'Agent Proposals',
                'Decision, insight or log written by the sourcing agent', ('Name', 'Name', 400, False))])
create_lookups([
    (T, 'ProjectId', 'Project', 'op365_project', 'parental', False),
    (T, 'PurchaseRequestId', 'Purchase Request', 'op365_purchaserequest', 'referential', False),
    (T, 'RfqId', 'RFQ', 'op365_rfq', 'referential', False),
    (T, 'InvitationId', 'Invitation', 'op365_rfqinvitation', 'referential', False),
    (T, 'PurchaseOrderId', 'Purchase Order', 'op365_purchaseorder', 'referential', False),
    (T, 'SupplierInvoiceId', 'Supplier Invoice', 'op365_supplierinvoice', 'referential', False),
    (T, 'SupplierId', 'Supplier', 'account', 'referential', False),
    (T, 'DecidedById', 'Decided By', 'systemuser', 'referential', False),
])
create_columns({T: [
    col('choice', 'Kind', 'Kind', 'Proposal waits for a decision, Insight is a finding to acknowledge, Log records '
        'something the agent already did. Set at creation', options=['Proposal', 'Insight', 'Log']),
    col('choice', 'ActionType', 'Action Type', 'What the agent proposes, reports or did. Set at creation',
        options=['Source via RFQ', 'Direct Order', 'Award RFQ', 'Approve Invoice', 'Reject Invoice', 'Invite Supplier',
                 'Supplier Reminder', 'Compliance Alert', 'Budget Alert', 'Late Delivery', 'Consolidation',
                 'New Supplier Needed']),
    col('memo', 'Rationale', 'Rationale', 'Explanation written by the agent. Set at creation', max=4000),
    col('memo', 'Evidence', 'Evidence', 'Output of the analysis behind the proposal (JSON). Visible with the profile '
        'OP365 Cost Visibility', max=100000, secured=True),
    col('memo', 'Payload', 'Payload', 'Inputs of the action, e.g. suppliers to invite, winning invitation (JSON)', max=4000),
    col('currency', 'Amount', 'Amount', 'Amount of the proposed order, award or invoice'),
    col('currency', 'EstimatedSaving', 'Estimated Saving', 'Saving the agent expects from the proposal'),
    col('text', 'DedupKey', 'Dedup Key', 'table:id:action, prevents the agent from proposing the same thing twice', max=200),
    col('date', 'ExpiresOn', 'Expires On', 'Pending proposals past this date expire'),
    col('datetime', 'DecidedOn', 'Decided On', 'When the proposal was approved or rejected. Set by Custom API'),
    col('memo', 'DecisionNote', 'Decision Note', 'Note of the person who decided; required to reject', max=2000),
    col('text', 'ResultId', 'Result Id', 'Id of the record created by the approved action. Set by Custom API', max=100),
    col('memo', 'Error', 'Error', 'Error message when the approved action failed. Set by Custom API', max=2000),
]})
status_reasons(T, [(1, 0, 'Pending'), (S, 0, 'Open'), (S + 1, 0, 'Failed'),
                   (2, 1, 'Executed'), (S + 2, 1, 'Rejected'), (S + 3, 1, 'Expired'), (S + 4, 1, 'Superseded'),
                   (S + 5, 1, 'Acknowledged'), (S + 6, 1, 'Done')])

# Evidence joins the OP365 Cost Visibility profile (read; create for the agent, never updated)
pid = one("fieldsecurityprofiles?$select=fieldsecurityprofileid&$filter=name eq 'OP365 Cost Visibility'")['fieldsecurityprofileid']
if one(f"fieldpermissions?$select=fieldpermissionid&$filter=_fieldsecurityprofileid_value eq {pid} "
       f"and entityname eq '{T}' and attributelogicalname eq 'op365_evidence'"):
    print('skip', T, 'op365_evidence')
else:
    ok(SESSION.post(WEBAPI + 'fieldpermissions', json={
        'fieldsecurityprofileid@odata.bind': f'/fieldsecurityprofiles({pid})',
        'entityname': T, 'attributelogicalname': 'op365_evidence', 'canread': 4, 'cancreate': 4, 'canupdate': 0}),
       f'field permission {T}.op365_evidence')

PROJECT = ['op365_project', 'op365_wbsnode', 'op365_wbsdependency', 'op365_wbsallocation', 'op365_projectmember',
           'op365_projectsupplier']
PURCHASING = ['op365_purchaserequest', 'op365_purchaserequestline', 'op365_rfq', 'op365_rfqinvitation', 'op365_rfqquote',
              'op365_purchaseorder', 'op365_purchaseorderline', 'op365_goodsreceipt', 'op365_goodsreceiptline']
INVOICES = ['op365_supplierinvoice', 'op365_supplierinvoiceline']
MASTER = ['account', 'contact', 'op365_item', 'op365_itemsupplier', 'op365_resource', 'op365_supplierdocument']
grant_roles({
    'OP365 Administrator': {T: (ALL, 'Global')},
    'OP365 User': {T: (['Read'], 'Basic')},
    'OP365 Buyer': {
        T: (['Read', 'Write', 'Append', 'AppendTo'], 'Global'),
        **{t: (['Read'], 'Global') for t in PROJECT},
        **{t: (FULL, 'Global') for t in PURCHASING + ['account', 'contact']},
        **{t: (['Read', 'AppendTo'], 'Global') for t in INVOICES},
    },
    'OP365 Sourcing Agent': {
        T: (['Create', 'Read', 'Append'], 'Global'),
        **{t: (['Read'], 'Global') for t in PROJECT + PURCHASING + INVOICES + MASTER},
    },
})

PROPOSAL = str(S)
COLS = [('op365_name', 300), ('op365_actiontype', 150), ('op365_projectid', 200), ('op365_supplierid', 200),
        ('op365_amount', 110), ('op365_expireson', 100), ('statuscode', 110)]
view(T, 'Open Agent Proposals', COLS, [('op365_expireson', False)], [('op365_kind', 'eq', PROPOSAL)], default=True,
     description='Proposals of the sourcing agent waiting for a decision, soonest expiry first')
view(T, 'Agent Insights', COLS, [('createdon', True)], [('op365_kind', 'eq', str(S + 1))], also=[('statuscode', 'eq', str(S))],
     description='Findings of the sourcing agent to acknowledge')
view(T, 'Agent Log', COLS + [('op365_kind', 100), ('createdon', 140)], [('createdon', True)], active=False,
     description='Everything the sourcing agent proposed, found or did, newest first')
view(T, 'My Agent Decisions', COLS + [('op365_decidedon', 140)], [('op365_decidedon', True)],
     [('op365_decidedbyid', 'eq-userid', None)], active=False, description='Proposals I approved or rejected')

use_ids('op365-agent-proposals')
formlib.form(T, 'Agent Proposal', [formlib.tab('General', [('100%', [
    section(T, 'General', ['op365_name!', 'op365_kind!', 'op365_actiontype!', 'statuscode!', 'op365_projectid!',
                           'op365_supplierid!', 'op365_purchaserequestid!', 'op365_rfqid!', 'op365_invitationid!',
                           'op365_purchaseorderid!', 'op365_supplierinvoiceid!', 'op365_amount!',
                           'op365_estimatedsaving!', 'op365_expireson!']),
    section(T, 'Rationale', ['op365_rationale!'], columns=1),
    section(T, 'Evidence', ['op365_evidence!'], columns=1),
    section(T, 'Decision', ['op365_decidedbyid!', 'op365_decidedon!', 'op365_decisionnote', 'op365_resultid!',
                            'op365_error!']),
])])], description='Proposal, insight or log of the sourcing agent (ProjectIQ)')


def add_section(table, form_name, after, name, xml):
    """Inserts a section after the section named after, unless the form already has it (patches the live form)."""
    f = formlib.S.get(formlib.API + f"systemforms?$select=formid,formxml&$filter=objecttypecode eq '{table}' and type eq 2 "
                      f"and name eq '{form_name}'").json()['value'][0]
    if f'<section name="{name}"' in f['formxml']:
        print('skip', form_name, name); return
    if f'<section name="{after}"' not in f['formxml']:
        after = 'purchase_orders'   # Suppliers section (project_suppliers.py) not there yet
    head, tail = f['formxml'].split(f'<section name="{after}"', 1)
    end = tail.index('</section>') + len('</section>')
    formlib.ok(formlib.S.patch(formlib.API + f"systemforms({f['formid']})", json={
        'formxml': head + f'<section name="{after}"' + tail[:end] + xml + tail[end:]}), f'form {form_name}: {name}')


add_section('op365_project', 'Project', 'suppliers', 'agent_proposals',
            section(T, 'Agent Proposals', [('subgrid', 'agent_proposals', 'Agent Proposals', T,
                                            'op365_project_agentproposal_projectid')]))
publish()
