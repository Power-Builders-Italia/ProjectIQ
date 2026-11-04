"""End-to-end check of the sourcing agent proposals (table, plugins, Custom APIs) in a Dev environment.

Creates its own test data (customer, two suppliers, a project, approved purchase requests, RFQs, one supplier invoice and
the agent proposals) and deletes it at the end, also after a failure. Every case prints PASS or FAIL with the reason;
the exit code is 1 when any case fails. Run it only against Dev: it creates and deletes records.

Cases: approve Source via RFQ as the buyer (app path); decide as the agent client with DecidedBy (Teams path); forged
DecidedBy; double decision; concurrent double decision; Award RFQ superseded by a hand award; Source via RFQ superseded
by an open RFQ; failure rolls back, RecordProposalError and Retry; Approve Invoice by a buyer; duplicate open proposal;
Log created as Done; unentitled Teams responder (Decide and RecordProposalError refused); route a request as the agent
(op365_SourcingSuggestSuppliers ranks the cheaper supplier first, op365_SourcingRouteRequest returns a proposal that the
buyer approves); expiry (reported as SKIP when Expires On cannot be backdated from outside the plugins).

Prerequisites
  * Tasks 3-7 of "Sourcing agent Foundations" are deployed in the target Dev environment (proposal table, plugins and
    Custom APIs op365_DecideAgentProposal / op365_RetryAgentProposal / op365_RecordProposalError / op365_ExpireAgentProposals,
    security roles, sourcing agent user setting).
  * PAC_TENANT_ID, PAC_ENVIRONMENT_URL, PAC_CLIENT_ID, PAC_CLIENT_SECRET: the admin application user (see dv.py).
  * SOURCING_AGENT_CLIENT_ID, SOURCING_AGENT_CLIENT_SECRET: the application registration of the sourcing agent, the
    application user set as the sourcing agent user of the environment. It creates the proposals and acts as the agent.
  * SOURCING_TEST_BUYER: User Name, full name or e-mail of an enabled user with the OP365 Buyer role who is neither
    an administrator, nor a Purchasing Approver, nor a project manager of the test project.
  * SOURCING_TEST_OTHER: the same kind of identifier for a second, different enabled user who cannot decide proposals
    (no OP365 Buyer role, not an administrator, Purchasing Approver or project manager of the test project): target of the
    forged DecidedBy and the unentitled Teams responder.
  * A client-credentials token cannot sign in as a person, so "as the buyer" is done with the Dataverse impersonation
    header MSCRMCallerID on the admin application user session. The admin application user must therefore hold the
    prvActOnBehalfOfAnotherUser privilege (e.g. the Delegate role). The plugins see the buyer as the calling user.
  * The admin application user is the project manager and approver of the test purchase requests.

Exit codes: 0 all cases passed; 1 at least one case failed; 2 no failure but at least one case was skipped (the run is
not complete: a green 0 means every case ran).

Expiry (manual part): Expires On is set by the create plugin and cannot be edited, so the script cannot make a proposal
overdue and reports that case as SKIP (it does not call op365_ExpireAgentProposals, which would expire other people's
overdue proposals in the shared Dev environment). Check it by hand: create a proposal, back-date its Expires On with an
admin tool (e.g. direct database/bulk-edit tool) or wait until it is past, run the "Daily agent proposal expiry" flow (or
call op365_ExpireAgentProposals), and confirm the proposal is Expired and Count >= 1.

Run:  python3 tools/dataverse/sourcing_smoke.py
"""
import datetime as dt, json, os, sys, threading
from concurrent.futures import ThreadPoolExecutor
import requests

sys.path.insert(0, os.path.dirname(__file__))

NEEDED = ['PAC_TENANT_ID', 'PAC_ENVIRONMENT_URL', 'PAC_CLIENT_ID', 'PAC_CLIENT_SECRET',
          'SOURCING_AGENT_CLIENT_ID', 'SOURCING_AGENT_CLIENT_SECRET', 'SOURCING_TEST_BUYER', 'SOURCING_TEST_OTHER']
missing = [n for n in NEEDED if not os.environ.get(n)]
if missing:
    sys.exit('Missing environment variables: ' + ', '.join(missing))

from dv import S, API, ENV  # admin application user session

R = {'Prefer': 'return=representation'}
KIND_PROPOSAL, KIND_LOG = 365000000, 365000002
A_SOURCE, A_DIRECT, A_AWARD, A_APPROVE_INV, A_REJECT_INV, A_INVITE, A_REMINDER = (365000000 + i for i in range(7))
ST_PENDING, ST_FAILED, ST_EXECUTED, ST_REJECTED, ST_EXPIRED, ST_SUPERSEDED, ST_DONE = (
    1, 365000001, 2, 365000002, 365000003, 365000004, 365000006)
RFQ_SENT, RFQ_AWARDED = 365000000, 365000001
PR_APPROVED = 365000001
E_AGENT_ONLY = 'Only the sourcing agent can decide on behalf of another user.'
E_DECIDED = 'This proposal has already been decided.'
E_CANNOT = 'You cannot decide this proposal.'
E_DUPLICATE = 'An open proposal for the same action already exists.'
E_NOTE = 'Add a note to reject the proposal.'
E_DECIDER_REQUIRED = 'The sourcing agent must give the user who decided.'
E_AGENT_OFF = 'The sourcing agent is switched off.'

SKIP = 'SKIP:'
results = []
created_proposals = []
created_prs = []
created_invoices = []
created_items = []


def agent_session():
    r = requests.post(f"https://login.microsoftonline.com/{os.environ['PAC_TENANT_ID']}/oauth2/v2.0/token", data={
        'grant_type': 'client_credentials', 'client_id': os.environ['SOURCING_AGENT_CLIENT_ID'],
        'client_secret': os.environ['SOURCING_AGENT_CLIENT_SECRET'], 'scope': ENV + '/.default'})
    r.raise_for_status()
    s = requests.Session()
    s.headers.update({'Authorization': 'Bearer ' + r.json()['access_token'], 'OData-MaxVersion': '4.0', 'OData-Version': '4.0',
                      'Accept': 'application/json', 'Content-Type': 'application/json; charset=utf-8'})
    return s


AGENT_SWITCH = 'op365_SourcingAgentEnabled'
switch_restore = []   # (value row id, previous value or None when the row was created by the smoke)


def agent_switch(on):
    """Sets op365_SourcingAgentEnabled in Dev; the finally block puts back the previous value."""
    d = S.get(API + f"environmentvariabledefinitions?$select=environmentvariabledefinitionid&$filter=schemaname eq '{AGENT_SWITCH}'"
              f"&$expand=environmentvariabledefinition_environmentvariablevalue($select=environmentvariablevalueid,value)").json()['value'][0]
    values = d['environmentvariabledefinition_environmentvariablevalue']
    value = 'yes' if on else 'no'
    if values:
        v = values[0]
        if not switch_restore:
            switch_restore.append((v['environmentvariablevalueid'], v['value']))
        must(S.patch(API + f"environmentvariablevalues({v['environmentvariablevalueid']})", json={'value': value}), 'agent switch')
    else:
        r = must(S.post(API + 'environmentvariablevalues', headers=R, json={
            'value': value, 'EnvironmentVariableDefinitionId@odata.bind': f"/environmentvariabledefinitions({d['environmentvariabledefinitionid']})"}),
            'agent switch')
        switch_restore.append((r['environmentvariablevalueid'], None))


def err(r):
    try:
        return r.json()['error']['message']
    except Exception:
        return r.text[:300]


def post(es, body, sess=None, caller=None):
    h = dict(R)
    if caller:
        h['MSCRMCallerID'] = caller
    r = (sess or S).post(API + es, json=body, headers=h)
    if r.status_code >= 300:
        raise RuntimeError(f'{es}: {r.status_code} {err(r)}')
    return r.json()


def get(es, id_, sel):
    r = S.get(API + f'{es}({id_})?$select={sel}')
    if r.status_code >= 300:
        raise RuntimeError(f'{es}({id_}): {r.status_code} {err(r)}')
    return r.json()


def rows(es, flt, sel):
    return S.get(API + f'{es}?$select={sel}&$filter={flt}').json()['value']


def bound(es, id_, name, body=None, sess=None, caller=None):
    h = {'MSCRMCallerID': caller} if caller else {}
    return (sess or S).post(API + f'{es}({id_})/Microsoft.Dynamics.CRM.{name}', json=body or {}, headers=h)


def unbound(name, body=None, sess=None, caller=None):
    h = {'MSCRMCallerID': caller} if caller else {}
    return (sess or S).post(API + name, json=body or {}, headers=h)


def must(r, what):
    if not r.ok:
        raise RuntimeError(f'{what}: {r.status_code} {err(r)}')
    return r.json() if r.text else {}


def case(name):
    """Runs the function as a case: PASS when it returns None/True, FAIL with the reason when it returns a string or raises."""
    def deco(fn):
        try:
            out = fn()
            ok, reason = (out is None or out is True), (out if isinstance(out, str) else '')
            if isinstance(out, str) and out.startswith(SKIP):
                print('SKIP ' + name + ' - ' + out[len(SKIP):].strip()[:500])
                results.append((name, None, 'skipped'))
                return fn
        except Exception as ex:  # noqa: BLE001 - a broken case must not stop the others
            ok, reason = False, f'{type(ex).__name__}: {ex}'
        print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f' - {reason[:500]}'))
        results.append((name, ok, reason))
        return fn
    return deco


def user(ident, variable=''):
    ident = ident.strip()   # a secret pasted with a trailing space or newline must still match
    safe = ident.replace("'", "''")
    flt = f"(fullname eq '{safe}' or domainname eq '{safe}' or internalemailaddress eq '{safe}') and isdisabled eq false"
    found = S.get(API + f'systemusers?$select=systemuserid,fullname,internalemailaddress&$filter={flt}').json().get('value', [])
    if len(found) != 1:
        # the value is a secret, masked in the GitHub log: say which one and its length instead
        raise SystemExit(f'{variable} "{ident}" ({len(ident)} characters): expected exactly one enabled user with this full name, '
                         f'User Name or primary e-mail, found {len(found)}')
    return found[0]


def propose(pr=None, rfq=None, inv=None, invoice=None, project=None, action=A_SOURCE, kind=KIND_PROPOSAL, payload=None, sess=None):
    body = {'op365_kind': kind, 'op365_actiontype': action}
    for key, es, val in [('op365_PurchaseRequestId', 'op365_purchaserequests', pr), ('op365_RfqId', 'op365_rfqs', rfq),
                         ('op365_InvitationId', 'op365_rfqinvitations', inv), ('op365_SupplierInvoiceId', 'op365_supplierinvoices', invoice),
                         ('op365_ProjectId', 'op365_projects', project)]:
        if val:
            body[key + '@odata.bind'] = f'/{es}({val})'
    if payload is not None:
        body['op365_payload'] = payload
    p = post('op365_agentproposals', body, sess=sess or AGENT)
    created_proposals.append(p['op365_agentproposalid'])
    return p['op365_agentproposalid']


def proposal(pid):
    return get('op365_agentproposals', pid, 'statuscode,statecode,op365_resultid,op365_error,op365_decisionnote,_op365_decidedbyid_value')


def approve(pid, sess=None, caller=None, decided_by=None, note=None):
    body = {'Approve': True}
    if decided_by:
        body['DecidedBy'] = decided_by
    if note:
        body['Note'] = note
    return bound('op365_agentproposals', pid, 'op365_DecideAgentProposal', body, sess=sess, caller=caller)


def payload(*suppliers, days=7):
    d = (dt.date.today() + dt.timedelta(days=days)).isoformat()
    return '{"supplierIds":[' + ','.join(f'"{s}"' for s in suppliers) + '],"deadline":"' + d + '"}'


def rfqs_of(pr):
    return rows('op365_rfqs', f'_op365_purchaserequestid_value eq {pr}', 'op365_rfqid,statuscode')


def expect_error(r, message):
    if r.ok:
        return f'call succeeded, expected error "{message}"'
    if message not in err(r):
        return f'wrong error: {err(r)[:300]}'
    return None


def make_pr(title):
    pr = post('op365_purchaserequests', {'op365_ProjectId@odata.bind': f'/op365_projects({prj})', 'op365_title': title})['op365_purchaserequestid']
    created_prs.append(pr)
    post('op365_purchaserequestlines', {'op365_PurchaseRequestId@odata.bind': f'/op365_purchaserequests({pr})', 'op365_name': 'Cable',
                                        'op365_quantity': 2, 'op365_estimatedprice': 10})
    must(bound('op365_purchaserequests', pr, 'op365_SubmitPurchaseRequest'), 'submit request')
    must(bound('op365_purchaserequests', pr, 'op365_DecidePurchaseRequest', {'Approve': True}), 'approve request')
    if get('op365_purchaserequests', pr, 'statuscode')['statuscode'] != PR_APPROVED:
        raise RuntimeError('purchase request not Approved')
    return pr


def sent_rfq(pr):
    """Creates and sends an RFQ by hand (admin); returns (rfq, [invitation ids])."""
    rfq = must(bound('op365_purchaserequests', pr, 'op365_CreateRfq', {'SupplierIds': [sup1, sup2]}), 'create RFQ')['RfqId']
    must(bound('op365_rfqs', rfq, 'op365_SendRfq'), 'send RFQ')
    return rfq, [i['op365_rfqinvitationid'] for i in rows('op365_rfqinvitations', f'_op365_rfqid_value eq {rfq}', 'op365_rfqinvitationid')]


buyer = user(os.environ['SOURCING_TEST_BUYER'], 'SOURCING_TEST_BUYER')
other = user(os.environ['SOURCING_TEST_OTHER'], 'SOURCING_TEST_OTHER')
BUYER, OTHER = buyer['systemuserid'], other['systemuserid']
if BUYER == OTHER:
    sys.exit('SOURCING_TEST_BUYER and SOURCING_TEST_OTHER must be different users')
BUYER_MAIL, OTHER_MAIL = buyer.get('internalemailaddress') or os.environ['SOURCING_TEST_BUYER'], other.get('internalemailaddress') or os.environ['SOURCING_TEST_OTHER']
AGENT = agent_session()
me = S.get(API + 'WhoAmI').json()['UserId']
agent_id = AGENT.get(API + 'WhoAmI').json()['UserId']

cust = sup1 = sup2 = prj = invoice = None
try:
    cust = post('accounts', {'name': 'OP365 sourcing smoke customer', 'op365_iscustomer': True})['accountid']
    sup1 = post('accounts', {'name': 'OP365 sourcing smoke supplier A', 'op365_issupplier': True, 'emailaddress1': 'a@example.com'})['accountid']
    sup2 = post('accounts', {'name': 'OP365 sourcing smoke supplier B', 'op365_issupplier': True, 'emailaddress1': 'b@example.com'})['accountid']
    prj = post('op365_projects', {'op365_code': 'SMOKE-SRC', 'op365_name': 'Sourcing smoke project', 'statuscode': 1,
                                  'op365_CustomerId@odata.bind': f'/accounts({cust})',
                                  'op365_ProjectManagerId@odata.bind': f'/systemusers({me})'})['op365_projectid']

    # ---------- 1. approve Source via RFQ as the buyer (app path) ----------
    pr1 = pid1 = None

    @case('Approve Source via RFQ as the buyer: Executed, RFQ Sent with two invitations, decided by the buyer')
    def _():
        global pr1, pid1
        pr1 = make_pr('Smoke 1')
        pid1 = propose(pr=pr1, project=prj, payload=payload(sup1, sup2))
        if proposal(pid1)['statuscode'] != ST_PENDING:
            return 'new proposal is not Pending'
        r = approve(pid1, caller=BUYER)
        if not r.ok:
            return f'decide failed: {err(r)}'
        p = proposal(pid1)
        rfq = r.json().get('ResultId')
        if p['statuscode'] != ST_EXECUTED:
            return f'proposal statuscode {p["statuscode"]}, expected Executed'
        if not rfq or p['op365_resultid'] != rfq:
            return f'ResultId {rfq} does not match the proposal result {p["op365_resultid"]}'
        h = get('op365_rfqs', rfq, 'statuscode,_op365_purchaserequestid_value')
        n = len(rows('op365_rfqinvitations', f'_op365_rfqid_value eq {rfq}', 'op365_rfqinvitationid'))
        if h['statuscode'] != RFQ_SENT or n != 2:
            return f'RFQ statuscode {h["statuscode"]} with {n} invitations, expected Sent with 2'
        # the Custom APIs write with the SYSTEM service, so the RFQ does not show the buyer: the proposal records the decider,
        # and the inner APIs check the decider's rights (case 12: an unentitled responder is refused)
        if p['_op365_decidedbyid_value'] != BUYER:
            return f'proposal decided by {p["_op365_decidedbyid_value"]}, expected the buyer {BUYER}'

    # ---------- 2. Teams path: the agent client decides with DecidedBy = buyer e-mail ----------
    @case('Teams path: agent client with DecidedBy = buyer e-mail, Executed, one RFQ, decided by the buyer and not by the agent')
    def _():
        pr = make_pr('Smoke 2')
        pid = propose(pr=pr, project=prj, payload=payload(sup1, sup2))
        r = approve(pid, sess=AGENT, decided_by=BUYER_MAIL)
        if not r.ok:
            return f'decide failed: {err(r)}'
        p = proposal(pid)
        if p['statuscode'] != ST_EXECUTED:
            return 'proposal not Executed'
        rf = rfqs_of(pr)
        if len(rf) != 1:
            return f'{len(rf)} RFQs for the request, expected 1'
        if p['_op365_decidedbyid_value'] == agent_id:
            return 'proposal decided by the agent'
        if p['_op365_decidedbyid_value'] != BUYER:
            return f'proposal decided by {p["_op365_decidedbyid_value"]}, expected the buyer'

    # ---------- 3 + 8. forged DecidedBy, then duplicate on the same (still Pending) target ----------
    pr3 = pid3 = None

    @case('Forged DecidedBy: buyer naming another user is refused, proposal still Pending')
    def _():
        global pr3, pid3
        pr3 = make_pr('Smoke 3')
        pid3 = propose(pr=pr3, project=prj, payload=payload(sup1, sup2))
        r = approve(pid3, caller=BUYER, decided_by=OTHER_MAIL)
        e = expect_error(r, E_AGENT_ONLY)
        if e:
            return e
        if proposal(pid3)['statuscode'] != ST_PENDING:
            return 'proposal is no longer Pending'
        if rfqs_of(pr3):
            return 'an RFQ was created'

    # ---------- 4. double decision ----------
    @case('Double decision: second Approve on an Executed proposal is refused')
    def _():
        if not pid1:
            return 'case 1 left no proposal'
        return expect_error(approve(pid1, caller=BUYER), E_DECIDED)

    # ---------- 5. Award RFQ superseded by a hand award ----------
    @case('Award RFQ proposal superseded when the RFQ was awarded by hand: Superseded, no new order')
    def _():
        pr = make_pr('Smoke 5')
        rfq, invs = sent_rfq(pr)
        for inv_id in invs:
            for q in rows('op365_rfqquotes', f'_op365_invitationid_value eq {inv_id}', 'op365_rfqquoteid'):
                S.patch(API + f"op365_rfqquotes({q['op365_rfqquoteid']})", json={'op365_price': 10})
        pid = propose(rfq=rfq, inv=invs[0], pr=None, project=prj, action=A_AWARD)
        must(bound('op365_rfqs', rfq, 'op365_AwardRfq', {'InvitationId': invs[1]}), 'award by hand')
        orders = len(rows('op365_purchaseorders', f'_op365_purchaserequestid_value eq {pr}', 'op365_purchaseorderid'))
        r = approve(pid, caller=BUYER)
        if not r.ok:
            return f'decide failed: {err(r)}'
        st = proposal(pid)['statuscode']
        if st != ST_SUPERSEDED:
            return f'proposal statuscode {st}, expected Superseded'
        after = len(rows('op365_purchaseorders', f'_op365_purchaserequestid_value eq {pr}', 'op365_purchaseorderid'))
        if after != orders:
            return f'purchase orders went from {orders} to {after}'

    # ---------- 6. failure rolls back ----------
    @case('Failure rolls back: past deadline returns an error and leaves no RFQ; RecordProposalError -> Failed; Retry -> Pending')
    def _():
        pr = make_pr('Smoke 6')
        pid = propose(pr=pr, project=prj, payload=payload(sup1, sup2, days=-3))
        r = approve(pid, caller=BUYER)
        if r.ok:
            return 'approve succeeded with a deadline in the past'
        # the Source via RFQ action runs CreateRfq first, which itself refuses a past deadline before inserting the RFQ
        # (Purchasing.cs); SendRfq's "The deadline has passed" check cannot be reached through the payload
        if 'The deadline must be today or later.' not in err(r):
            return f'wrong error: {err(r)[:300]}'
        if rfqs_of(pr):
            return 'an RFQ was left behind after the failed approve'
        if proposal(pid)['statuscode'] != ST_PENDING:
            return 'proposal is not Pending after the rolled-back approve'
        msg = err(r)
        r = unbound('op365_RecordProposalError', {'ProposalId': pid, 'Error': msg, 'DecidedBy': BUYER_MAIL}, sess=AGENT)
        if not r.ok:
            return f'RecordProposalError failed: {err(r)}'
        p = proposal(pid)
        if p['statuscode'] != ST_FAILED or not p['op365_error'] or msg[:40] not in p['op365_error']:
            return f'after RecordProposalError: statuscode {p["statuscode"]}, error {p["op365_error"]!r}'
        r = bound('op365_agentproposals', pid, 'op365_RetryAgentProposal', caller=BUYER)
        if not r.ok:
            return f'Retry failed: {err(r)}'
        p = proposal(pid)
        if p['statuscode'] != ST_PENDING:
            return f'after Retry: statuscode {p["statuscode"]}, expected Pending'

    # ---------- 7. invoice by a buyer ----------
    @case('Approve Invoice proposal decided by the buyer (not a Purchasing Approver) is refused')
    def _():
        global invoice
        invoice = post('op365_supplierinvoices', {'op365_invoicenumber': 'SMOKE-SRC-1', 'op365_invoicedate': dt.date.today().isoformat(),
                                                  'op365_SupplierId@odata.bind': f'/accounts({sup1})'})['op365_supplierinvoiceid']
        created_invoices.append(invoice)
        pid = propose(invoice=invoice, project=prj, action=A_APPROVE_INV)
        e = expect_error(approve(pid, caller=BUYER), E_CANNOT)
        if e:
            p = proposal(pid)
            inv = get('op365_supplierinvoices', invoice, 'statuscode')
            return (f'{e} (proposal statuscode {p["statuscode"]}, decided by {p["_op365_decidedbyid_value"]}, buyer {BUYER}; '
                    f'invoice statuscode {inv["statuscode"]})')
        if proposal(pid)['statuscode'] != ST_PENDING:
            return 'proposal is no longer Pending'

    # ---------- 8. duplicate ----------
    @case('Duplicate: second open proposal with the same target and action is refused')
    def _():
        if not pr3:
            return 'case 3 left no purchase request'
        try:
            propose(pr=pr3, project=prj, payload=payload(sup1))
        except RuntimeError as ex:
            return None if E_DUPLICATE in str(ex) else f'wrong error: {ex}'
        return f'second proposal created, expected "{E_DUPLICATE}"'

    # ---------- 9. expiry ----------
    @case('Expiry: proposal with ExpiresOn yesterday -> Expired by op365_ExpireAgentProposals (Count >= 1)')
    def _():
        pr = make_pr('Smoke 9')
        pid = propose(pr=pr, project=prj, payload=payload(sup1))
        yesterday = (dt.date.today() - dt.timedelta(days=1)).isoformat()
        r = S.patch(API + f'op365_agentproposals({pid})', json={'op365_expireson': yesterday})
        if not r.ok:
            # do NOT run op365_ExpireAgentProposals: it would expire other people's overdue proposals in the shared Dev environment
            return SKIP + 'expiry needs a proposal past its Expires On: check by hand in Dev (see docstring)'
        r2 = unbound('op365_ExpireAgentProposals')
        if not r2.ok:
            return f'ExpireAgentProposals failed: {err(r2)}'
        count = r2.json().get('Count')
        st = proposal(pid)['statuscode']
        if st != ST_EXPIRED or not count or count < 1:
            return f'statuscode {st}, Count {count}, expected Expired and Count >= 1'

    # ---------- 10. concurrent double decision ----------
    @case('Concurrent double decision: two simultaneous Approve -> exactly one succeeds, the other "already decided", one RFQ')
    def _():
        pr = make_pr('Smoke 10')
        pid = propose(pr=pr, project=prj, payload=payload(sup1, sup2))
        barrier = threading.Barrier(2)

        def go(_):
            barrier.wait()
            return approve(pid, caller=BUYER)
        with ThreadPoolExecutor(2) as pool:
            out = list(pool.map(go, range(2)))
        ok = [r for r in out if r.ok]
        bad = [r for r in out if not r.ok]
        if len(ok) != 1 or len(bad) != 1:
            return f'{len(ok)} succeeded and {len(bad)} failed, expected 1 and 1 ({[err(r)[:80] for r in bad]})'
        if E_DECIDED not in err(bad[0]):
            return f'loser got: {err(bad[0])[:300]}'
        n = len(rfqs_of(pr))
        if n != 1:
            return f'{n} RFQs created, expected 1'
        if proposal(pid)['statuscode'] != ST_EXECUTED:
            return 'proposal not Executed'

    # ---------- 11. Log created as Done ----------
    @case('Log created as Done: Kind = Log -> statuscode 365000006, statecode 1')
    def _():
        pid = propose(project=prj, action=A_REMINDER, kind=KIND_LOG)
        p = proposal(pid)
        if p['statuscode'] != ST_DONE or p['statecode'] != 1:
            return f'statuscode {p["statuscode"]}, statecode {p["statecode"]}, expected 365000006 and 1'

    # ---------- 12. Source via RFQ superseded by an open RFQ ----------
    @case('Source via RFQ on a request that already has a Sent RFQ: Superseded, no second RFQ')
    def _():
        pr = make_pr('Smoke 12')
        rfq, _invs = sent_rfq(pr)
        pid = propose(pr=pr, project=prj, payload=payload(sup1, sup2))
        r = approve(pid, caller=BUYER)
        if not r.ok:
            return f'decide failed: {err(r)}'
        st = proposal(pid)['statuscode']
        if st != ST_SUPERSEDED:
            return f'proposal statuscode {st}, expected Superseded'
        n = len(rfqs_of(pr))
        if n != 1:
            return f'{n} RFQs for the request, expected 1'

    # ---------- 13. unentitled Teams responder ----------
    @case('Unentitled Teams responder: agent client with DecidedBy = other user -> Decide and RecordProposalError refused, still Pending')
    def _():
        pr = make_pr('Smoke 13')
        pid = propose(pr=pr, project=prj, payload=payload(sup1, sup2))
        e = expect_error(approve(pid, sess=AGENT, decided_by=OTHER_MAIL), E_CANNOT)
        if e:
            return 'Decide: ' + e
        e = expect_error(unbound('op365_RecordProposalError', {'ProposalId': pid, 'Error': 'smoke', 'DecidedBy': OTHER_MAIL},
                                 sess=AGENT), E_CANNOT)
        if e:
            return 'RecordProposalError with DecidedBy: ' + e
        e = expect_error(unbound('op365_RecordProposalError', {'ProposalId': pid, 'Error': 'smoke'}, sess=AGENT), E_DECIDER_REQUIRED)
        if e:
            return 'RecordProposalError without DecidedBy: ' + e
        p = proposal(pid)
        if p['statuscode'] != ST_PENDING or p['op365_error']:
            return f'statuscode {p["statuscode"]}, error {p["op365_error"]!r}, expected Pending without error'
        if rfqs_of(pr):
            return 'an RFQ was created'

    # ---------- 14. route a purchase request as the agent (tasks 1-2) ----------
    @case('Route as the agent: cheaper supplier ranked first, RouteRequest payload approved by the buyer -> Executed')
    def _():
        item = post('op365_items', {'op365_code': 'SMOKE-SRC-ITEM', 'op365_name': 'Smoke cable', 'op365_unitcost': 10})['op365_itemid']
        created_items.append(item)
        for sup, price, lead in ((sup1, 8, 3), (sup2, 12, 10)):
            post('op365_itemsuppliers', {'op365_ItemId@odata.bind': f'/op365_items({item})', 'op365_SupplierId@odata.bind': f'/accounts({sup})',
                                         'op365_price': price, 'op365_leadtimedays': lead})
        pr = post('op365_purchaserequests', {'op365_ProjectId@odata.bind': f'/op365_projects({prj})', 'op365_title': 'Smoke 14'})['op365_purchaserequestid']
        created_prs.append(pr)
        post('op365_purchaserequestlines', {'op365_PurchaseRequestId@odata.bind': f'/op365_purchaserequests({pr})',
                                            'op365_ItemId@odata.bind': f'/op365_items({item})', 'op365_quantity': 5, 'op365_estimatedprice': 10})
        must(bound('op365_purchaserequests', pr, 'op365_SubmitPurchaseRequest'), 'submit request')
        must(bound('op365_purchaserequests', pr, 'op365_DecidePurchaseRequest', {'Approve': True}), 'approve request')
        ranked = json.loads(must(bound('op365_purchaserequests', pr, 'op365_SourcingSuggestSuppliers', sess=AGENT), 'suggest')['Result'])
        order = [x['supplierId'] for x in ranked if x['supplierId'] in (sup1, sup2)]
        if order != [sup1, sup2]:
            return f'suppliers ranked {order}, expected the cheaper and faster supplier A first'
        route = must(bound('op365_purchaserequests', pr, 'op365_SourcingRouteRequest', sess=AGENT), 'route')
        if route['Route'] not in ('SourceViaRfq', 'DirectOrder') or route['ActionType'] not in (A_SOURCE, A_DIRECT):
            return f'route {route["Route"]} / {route["ActionType"]}, expected SourceViaRfq or DirectOrder'
        body = json.loads(route['Payload'])
        chosen = body.get('supplierIds') or [body.get('supplierId')]
        if chosen[0] != sup1 or not set(chosen) <= {sup1, sup2}:
            return f'payload suppliers {chosen}, expected supplier A first'
        pid = propose(pr=pr, project=prj, action=route['ActionType'], payload=route['Payload'])
        r = approve(pid, caller=BUYER)
        if not r.ok:
            return f'decide failed: {err(r)}'
        if proposal(pid)['statuscode'] != ST_EXECUTED:
            return 'proposal not Executed'
        again = must(bound('op365_purchaserequests', pr, 'op365_SourcingRouteRequest', sess=AGENT), 'route again')
        if again['Route'] != 'NotApplicable':
            return f'route after sourcing {again["Route"]}, expected NotApplicable'
    # ---------- 15. the agent creates the proposal with op365_SourcingProposeRoute ----------
    @case('ProposeRoute as the agent: refused while switched off; on: proposal with the route payload, evidence and rationale; '
          'second call refused as duplicate')
    def _():
        item = post('op365_items', {'op365_code': 'SMOKE-SRC-ITEM15', 'op365_name': 'Smoke pipe', 'op365_unitcost': 10})['op365_itemid']
        created_items.append(item)
        post('op365_itemsuppliers', {'op365_ItemId@odata.bind': f'/op365_items({item})', 'op365_SupplierId@odata.bind': f'/accounts({sup1})',
                                     'op365_price': 9, 'op365_leadtimedays': 2})
        pr = post('op365_purchaserequests', {'op365_ProjectId@odata.bind': f'/op365_projects({prj})', 'op365_title': 'Smoke 15'})['op365_purchaserequestid']
        created_prs.append(pr)
        post('op365_purchaserequestlines', {'op365_PurchaseRequestId@odata.bind': f'/op365_purchaserequests({pr})',
                                            'op365_ItemId@odata.bind': f'/op365_items({item})', 'op365_quantity': 2, 'op365_estimatedprice': 10})
        must(bound('op365_purchaserequests', pr, 'op365_SubmitPurchaseRequest'), 'submit request')
        must(bound('op365_purchaserequests', pr, 'op365_DecidePurchaseRequest', {'Approve': True}), 'approve request')
        why = {'Rationale': 'Smoke: supplier A sells every line.'}
        agent_switch(False)
        off = expect_error(bound('op365_purchaserequests', pr, 'op365_SourcingProposeRoute', why, sess=AGENT), E_AGENT_OFF)
        if off:
            return 'switched off: ' + off
        agent_switch(True)
        route = must(bound('op365_purchaserequests', pr, 'op365_SourcingRouteRequest', sess=AGENT), 'route')
        made = must(bound('op365_purchaserequests', pr, 'op365_SourcingProposeRoute', why, sess=AGENT), 'propose')
        if not made.get('ProposalId'):
            return f'no proposal created (route {made.get("Route")})'
        created_proposals.append(made['ProposalId'])
        p = get('op365_agentproposals', made['ProposalId'],
                'op365_kind,op365_actiontype,op365_payload,op365_rationale,op365_evidence,statuscode,_op365_purchaserequestid_value,'
                '_op365_projectid_value,_createdby_value')
        if (made['Route'], p['op365_actiontype'], p['op365_payload']) != (route['Route'], route['ActionType'], route['Payload']):
            return f'proposal {made["Route"]}/{p["op365_actiontype"]} {p["op365_payload"]}, route {route["Route"]}/{route["ActionType"]} {route["Payload"]}'
        if p['op365_kind'] != KIND_PROPOSAL or p['statuscode'] != ST_PENDING or p['op365_rationale'] != why['Rationale']:
            return f'kind {p["op365_kind"]}, status {p["statuscode"]}, rationale {p["op365_rationale"]!r}'
        if p['_op365_purchaserequestid_value'] != pr or p['_op365_projectid_value'] != prj or p['_createdby_value'] != agent_id:
            return 'lookups or creator wrong'
        if not p.get('op365_evidence') or json.loads(p['op365_evidence']).get('route') != route['Route']:
            return 'evidence missing'
        dup = expect_error(bound('op365_purchaserequests', pr, 'op365_SourcingProposeRoute', why, sess=AGENT), E_DUPLICATE)
        if dup:
            return 'second call: ' + dup
finally:
    left = []
    refused = []   # deletes refused while their parent was still there: the project delete usually removes them by cascade

    def drop(es, id_):
        try:
            r = S.delete(API + f'{es}({id_})')
            if r.status_code >= 300 and r.status_code != 404:
                refused.append((es, id_, f'{es}({id_}): {r.status_code} {err(r)[:120]}'))
        except Exception as ex:  # noqa: BLE001
            left.append(f'{es}({id_}): {ex}')

    def children(es, col, id_, key):
        try:
            return [x[key] for x in rows(es, f'{col} eq {id_}', key)]
        except Exception as ex:  # noqa: BLE001
            left.append(f'query {es} where {col} = {id_} failed ({type(ex).__name__}: {ex}): its rows may be left behind')
            return []
    # Order, from the relationship kinds in phase4_tables.py: proposals first (their target lookups are referential, but
    # they are ours); then per request the purchase orders (referential to request/RFQ/invoice: no block) with their
    # receipts and lines, then RFQs with invitations and quotes (RFQ -> winning invitation/order lookups are referential, so
    # they do not block), then request lines and the request (parental children go before it). Supplier invoices and
    # invitations/orders that point to a supplier must go before the suppliers, the only restrict relationships
    # (invitation, order, invoice -> supplier). Last the project and the customer. Project supplier rows (op365_projectsupplier, created by the plugins on RFQ send,
    # restrict on supplier) are parental children of the project, so deleting the project before the suppliers removes them. Every step is guarded: nothing here can
    # skip the summary and the exit code.
    def safe(label, fn, *args):
        try:
            fn(*args)
        except Exception as ex:  # noqa: BLE001
            left.append(f'{label}: {type(ex).__name__}: {ex}')

    def clean_request(pr):
        for po in children('op365_purchaseorders', '_op365_purchaserequestid_value', pr, 'op365_purchaseorderid'):
            for gr in children('op365_goodsreceipts', '_op365_purchaseorderid_value', po, 'op365_goodsreceiptid'):
                for gl in children('op365_goodsreceiptlines', '_op365_goodsreceiptid_value', gr, 'op365_goodsreceiptlineid'):
                    drop('op365_goodsreceiptlines', gl)
                drop('op365_goodsreceipts', gr)
            for pl in children('op365_purchaseorderlines', '_op365_purchaseorderid_value', po, 'op365_purchaseorderlineid'):
                drop('op365_purchaseorderlines', pl)
            drop('op365_purchaseorders', po)
        for rfq in children('op365_rfqs', '_op365_purchaserequestid_value', pr, 'op365_rfqid'):
            for inv in children('op365_rfqinvitations', '_op365_rfqid_value', rfq, 'op365_rfqinvitationid'):
                for q in children('op365_rfqquotes', '_op365_invitationid_value', inv, 'op365_rfqquoteid'):
                    drop('op365_rfqquotes', q)
                drop('op365_rfqinvitations', inv)
            drop('op365_rfqs', rfq)
        for ln in children('op365_purchaserequestlines', '_op365_purchaserequestid_value', pr, 'op365_purchaserequestlineid'):
            drop('op365_purchaserequestlines', ln)
        drop('op365_purchaserequests', pr)

    for vid, previous in switch_restore:   # the agent switch back as it was (no value row when the smoke created it)
        safe('agent switch', lambda: S.delete(API + f'environmentvariablevalues({vid})') if previous is None
             else S.patch(API + f'environmentvariablevalues({vid})', json={'value': previous}))
    for pr in created_prs:   # proposals an agent created on our requests are ours too
        for pid in children('op365_agentproposals', '_op365_purchaserequestid_value', pr, 'op365_agentproposalid'):
            if pid not in created_proposals:
                created_proposals.append(pid)
    for pid in created_proposals:
        safe(f'proposal {pid}', drop, 'op365_agentproposals', pid)
    for pr in created_prs:
        safe(f'request {pr}', clean_request, pr)
    for inv in created_invoices:
        safe(f'invoice {inv}', drop, 'op365_supplierinvoices', inv)
    if prj:
        safe('project', drop, 'op365_projects', prj)
    # after the project: request lines of ordered requests cannot be deleted one by one, the project delete removes them
    for item in created_items:   # its item supplier rows are parental children: deleted with it
        safe(f'item {item}', drop, 'op365_items', item)
    for id_ in (sup1, sup2, cust):
        if id_:
            safe(f'account {id_}', drop, 'accounts', id_)
    for es, id_, message in refused:
        try:
            if S.get(API + f'{es}({id_})?$select=createdon').status_code != 404:
                left.append(message)
        except Exception as ex:  # noqa: BLE001
            left.append(f'{message} (check failed: {ex})')
    if left:
        print('WARNING: left behind in Dev (delete by hand):')
        for x in left:
            print('  ' + x)

passed = sum(1 for _, ok, _ in results if ok is True)
skipped = sum(1 for _, ok, _ in results if ok is None)
failed = [n for n, ok, _ in results if ok is False]
print(f'{passed} passed, {skipped} skipped, {len(failed)} failed')
sys.exit(1 if failed else (2 if skipped else 0))
