"""Supplier portal content (Power Pages, enhanced data model) on the Supplier Portal site, through the Dataverse Web API.

Creates or updates the Supplier web role, the table permissions, the Web API site settings, the shared web templates
(style, sidebar, project cards), the pages (dashboard, projects, requests for quotation and quote, purchase orders and
order confirmation, invoices, company documents; Liquid and CSS in portal_ui.py) and the menu links. Records are matched by name, so the script
is idempotent. Run it against Dev (PAC_* variables), then export the OpenProject365SupplierPortal solution:

    python3 tools/portal/supplier_portal.py
"""
import json
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dataverse'))
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API
import portal_ui as ui

S.headers['MSCRM.SolutionUniqueName'] = 'OpenProject365SupplierPortal'   # site records belong to the portal solution

SITE_NAME = os.environ.get('PORTAL_SITE', 'Supplier Portal')
CONTACT, ACCOUNT, PARENT = 756150001, 756150002, 756150003   # table permission scopes
INVITED, RESPONDED, DECLINED = 365000000, 365000001, 365000002
PO_SENT, PO_CONFIRMED, PO_RECEIVED = 365000000, 365000001, 365000002


def fill(text, *values):
    """Replaces each %d in order (the templates are full of Liquid {% %}, so no % formatting)."""
    for v in values:
        text = text.replace('%d', str(v), 1)
    return text


def rows(es, filt, select):
    return S.get(API + f'{es}?$select={select}&$filter={filt}').json().get('value', [])


def upsert(es, key, filt, body):
    """Creates or updates the record of the site matching filt; returns its id."""
    found = rows(es, f"_mspp_websiteid_value eq {SITE} and {filt}", key)
    body = dict(body, **{'mspp_websiteid@odata.bind': f'/mspp_websites({SITE})'})
    if found:
        r = S.patch(API + f"{es}({found[0][key]})", json=body)
        rid = found[0][key]
    else:
        r = S.post(API + es, json=body)
        rid = r.headers.get('OData-EntityId', '').split('(')[-1].rstrip(')')
    if r.status_code >= 300:
        raise SystemExit(f'{es} {filt}: {r.status_code} {r.text[:400]}')
    print('ok  ', es, filt)
    return rid


def q(text):
    return text.replace("'", "''")


sites = rows('mspp_websites', f"startswith(mspp_name,'{q(SITE_NAME)}')", 'mspp_websiteid,mspp_name')
if len(sites) != 1:
    raise SystemExit(f'expected one site named {SITE_NAME}*, found {[s["mspp_name"] for s in sites]}')
SITE = sites[0]['mspp_websiteid']
PUBLISHED = rows('mspp_publishingstates', "mspp_name eq 'Published'", 'mspp_publishingstateid')[0]['mspp_publishingstateid']
TEMPLATE = rows('mspp_pagetemplates', "mspp_name eq 'Default studio template'", 'mspp_pagetemplateid')[0]['mspp_pagetemplateid']
HOME = rows('mspp_webpages', "mspp_isroot eq true and mspp_partialurl eq '/'", 'mspp_webpageid')[0]['mspp_webpageid']
MENU = rows('mspp_weblinksets', "mspp_name eq 'Default'", 'mspp_weblinksetid')[0]['mspp_weblinksetid']
LANGUAGE = rows('mspp_websitelanguages', "statecode eq 0", 'mspp_websitelanguageid')[0]['mspp_websitelanguageid']

# ---------- web role ----------
SUPPLIER = upsert('mspp_webroles', 'mspp_webroleid', "mspp_name eq 'Supplier'", {
    'mspp_name': 'Supplier', 'mspp_anonymoususersrole': False, 'mspp_authenticatedusersrole': False,
    'mspp_description': 'Contacts of a supplier account: answer RFQs and confirm purchase orders'})

# ---------- table permissions ----------
PERMISSIONS = {}


def permission(name, table, scope, write=False, relationship=None, parent=None, create=False, delete=False, append=False,
               appendto=False):
    body = {'mspp_entityname': name, 'mspp_entitylogicalname': table, 'mspp_scope': scope, 'mspp_read': True, 'mspp_write': write,
            'mspp_create': create, 'mspp_delete': delete, 'mspp_append': append, 'mspp_appendto': appendto}
    if scope == CONTACT:
        body['mspp_contactrelationship'] = relationship
    elif scope == ACCOUNT:
        body['mspp_accountrelationship'] = relationship
    else:
        body['mspp_parentrelationship'] = relationship
        body['mspp_parententitypermission@odata.bind'] = f'/mspp_entitypermissions({PERMISSIONS[parent]})'
    pid = upsert('mspp_entitypermissions', 'mspp_entitypermissionid', f"mspp_entityname eq '{q(name)}'", body)
    # the link lives in the powerpagecomponent self N:N: the virtual mspp_entitypermission_webrole expand always reads empty
    linked = S.get(API + 'powerpagecomponent_powerpagecomponentset?$select=powerpagecomponentidone'
                   f'&$filter=powerpagecomponentidone eq {pid} and powerpagecomponentidtwo eq {SUPPLIER}').json()['value']
    if not linked:
        r = S.post(API + f'powerpagecomponents({pid})/powerpagecomponent_powerpagecomponent/$ref',
                   json={'@odata.id': API + f'powerpagecomponents({SUPPLIER})'})
        if r.status_code >= 300:
            raise SystemExit(f'link {name} to Supplier: {r.text[:300]}')
    # the site runtime reads the roles from the component JSON, not from the N:N above
    content = json.loads(S.get(API + f'powerpagecomponents({pid})?$select=content').json()['content'])
    if content.get('adx_entitypermission_webrole') != [SUPPLIER]:
        content['adx_entitypermission_webrole'] = [SUPPLIER]
        r = S.patch(API + f'powerpagecomponents({pid})', json={'content': json.dumps(content)})
        if r.status_code >= 300:
            raise SystemExit(f'roles of {name}: {r.text[:300]}')
    PERMISSIONS[name] = pid


permission('Supplier RFQ invitations', 'op365_rfqinvitation', ACCOUNT, write=True, relationship='op365_account_rfqinvitation_supplierid')
permission('Supplier RFQ quotes', 'op365_rfqquote', PARENT, write=True, relationship='op365_rfqinvitation_rfqquote_invitationid',
           parent='Supplier RFQ invitations')
permission('Supplier purchase orders', 'op365_purchaseorder', ACCOUNT, write=True, relationship='op365_account_purchaseorder_supplierid')
permission('Supplier purchase order lines', 'op365_purchaseorderline', PARENT,
           relationship='op365_purchaseorder_purchaseorderline_purchaseorderid', parent='Supplier purchase orders')
# read-only: the projects of the supplier's orders and the supplier's invoices
permission('Supplier projects', 'op365_project', PARENT, relationship='op365_project_purchaseorder_projectid',
           parent='Supplier purchase orders')
permission('Supplier invoices', 'op365_supplierinvoice', ACCOUNT, relationship='op365_account_supplierinvoice_supplierid')
# own company documents: upload, change and delete (the plugins refuse changes to approved documents);
# Append/Append To on both sides (the site checks the account -> document association) let a new document be linked to
# the supplier's own account (the contact's Company Name)
permission('Supplier company', 'account', CONTACT, append=True, appendto=True, relationship='contact_customer_accounts')
# child of Supplier company through the lookup the portal binds (op365_SupplierId): the association check on create
# needs the parent/child chain, an independent Account-scope permission is refused
permission('Supplier documents', 'op365_supplierdocument', PARENT, write=True, create=True, delete=True, append=True, appendto=True,
           relationship='op365_account_supplierdocument_supplierid', parent='Supplier company')

# ---------- Web API: only the columns a supplier may write ----------
SETTINGS = {
    'Webapi/op365_rfqinvitation/enabled': 'true',
    'Webapi/op365_rfqinvitation/fields': 'op365_deliverydays,op365_suppliernotes,statuscode',
    'Webapi/op365_rfqquote/enabled': 'true',
    'Webapi/op365_rfqquote/fields': 'op365_price,op365_notes',
    'Webapi/op365_purchaseorder/enabled': 'true',
    'Webapi/op365_purchaseorder/fields': 'op365_supplierconfirmed',
    # never statuscode or the review columns: the plugins set them
    'Webapi/op365_supplierdocument/enabled': 'true',
    'Webapi/op365_supplierdocument/fields': 'op365_documenttype,op365_description,op365_number,op365_issuedate,'
                                            'op365_expirydate,op365_notes,op365_file,op365_supplierid,op365_SupplierId',
    # the related table of a lookup bound on create must be Web API enabled too; Supplier company grants no write
    'Webapi/account/enabled': 'true',
    'Webapi/account/fields': 'accountid',
    'Webapi/error/innererror': 'false',
}
# ---------- sign-in: local accounts (e-mail + password) for suppliers outside the tenant ----------
# PORTAL_LOCAL_LOGIN=false keeps Microsoft Entra ID only. With local login suppliers sign in with their e-mail and
# reset the password themselves. PORTAL_SELF_REGISTRATION=false allows only invited users (Power Pages Management >
# Invitations); otherwise anyone can register, but sees nothing until the buyer links the contact to the supplier
# account and gives it the Supplier web role.
def flag(name):
    return os.environ.get(name, 'true').strip().lower() != 'false'
LOCAL_LOGIN, SELF_REGISTRATION = flag('PORTAL_LOCAL_LOGIN'), flag('PORTAL_SELF_REGISTRATION')
SETTINGS.update({
    'Authentication/Registration/LocalLoginEnabled': str(LOCAL_LOGIN).lower(),
    'Authentication/Registration/LocalLoginDeprecated': 'false',
    'Authentication/Registration/LocalLoginByEmail': 'true',
    'Authentication/Registration/ResetPasswordEnabled': 'true',
    'Authentication/Registration/InvitationEnabled': 'true',
    'Authentication/Registration/Enabled': 'true',
    'Authentication/Registration/OpenRegistrationEnabled': str(SELF_REGISTRATION).lower(),
    'Authentication/Registration/RequiresInvitation': str(not SELF_REGISTRATION).lower(),
    'Authentication/Registration/RequireUniqueEmail': 'true',
})
for k, v in SETTINGS.items():
    upsert('mspp_sitesettings', 'mspp_sitesettingid', f"mspp_name eq '{k}'", {'mspp_name': k, 'mspp_value': v})

# ---------- pages ----------
GUARD_OPEN = """{% assign supplier = false %}{% if user %}{% for r in user.roles %}{% if r == 'Supplier' %}{% assign supplier = true %}{% endif %}{% endfor %}{% endif %}
{% if supplier == false %}
<div class="container py-5"><div class="alert alert-warning">This area is reserved to suppliers. <a href="/SignIn?returnUrl={{ request.path_and_query | escape }}">Sign in</a> with the account your customer invited.</div></div>
{% else %}
"""
GUARD_CLOSE = "\n{% endif %}\n"

WEBAPI_JS = """// Power Pages Web API with the anti-forgery token
function op365Api(method, url, body) {
  var d = $.Deferred();
  shell.getTokenDeferred().done(function (token) {
    $.ajax({ type: method, url: url, contentType: 'application/json', data: body ? JSON.stringify(body) : null,
             headers: { '__RequestVerificationToken': token } })
      .done(function () { d.resolve(); })
      .fail(function (x) { var m = x.responseJSON && x.responseJSON.error ? x.responseJSON.error.message : x.statusText; d.reject(m); });
  }).fail(function () { d.reject('Session expired: sign in again.'); });
  return d.promise();
}
function op365Error(text) { $('#op365-error').text(text).removeClass('d-none'); }
"""

QUOTE = """<div>
  {% assign id = request.params['id'] %}
  {% fetchxml inv %}
  <fetch top="1">
    <entity name="op365_rfqinvitation">
      <attribute name="op365_rfqinvitationid" /><attribute name="op365_rfqnumber" /><attribute name="op365_deadline" />
      <attribute name="op365_rfqnotes" /><attribute name="statuscode" /><attribute name="op365_deliverydays" /><attribute name="op365_suppliernotes" />
      <filter><condition attribute="op365_rfqinvitationid" operator="eq" value="{{ id | xml_escape }}" /></filter>
      <link-entity name="op365_rfqquote" from="op365_invitationid" to="op365_rfqinvitationid" link-type="outer" alias="q">
        <attribute name="op365_rfqquoteid" /><attribute name="op365_name" /><attribute name="op365_quantity" />
        <attribute name="op365_uom" /><attribute name="op365_price" /><attribute name="op365_notes" />
      </link-entity>
    </entity>
  </fetch>
  {% endfetchxml %}
  {% assign rows = inv.results.entities %}
  {% if rows.size == 0 %}
  <div class="alert alert-warning">Request for quotation not found.</div>
  {% else %}
  {% assign i = rows[0] %}
  {% assign today = now | date: 'yyyy-MM-dd' %}{% assign deadline = i.op365_deadline | date: 'yyyy-MM-dd' %}
  {% assign closed = false %}{% if i.statuscode.value == %d or deadline < today %}{% assign closed = true %}{% endif %}
  <a href="/rfqs/" class="small">&larr; Requests for quotation</a>
  <h1 class="h3 mt-2">{{ i.op365_rfqnumber }}</h1>
  <p class="text-muted mb-1">Deadline {{ i.op365_deadline | date: 'dd/MM/yyyy' }} &middot; {{ i.statuscode.label }}</p>
  {% if i.op365_rfqnotes %}<p>{{ i.op365_rfqnotes | escape | newline_to_br }}</p>{% endif %}
  <div id="op365-error" class="alert alert-danger d-none"></div>
  <div id="op365-ok" class="alert alert-success d-none">Your quote has been sent. You can change it until the deadline.</div>
  <form id="op365-quote" data-invitation="{{ i.op365_rfqinvitationid }}">
  <div class="table-responsive"><table class="table align-middle">
    <thead><tr><th>Item</th><th class="text-end">Quantity</th><th style="width:160px">Unit price</th><th>Notes</th></tr></thead>
    <tbody>
    {% for r in rows %}{% if r['q.op365_rfqquoteid'] %}
      <tr data-quote="{{ r['q.op365_rfqquoteid'] }}">
        <td>{{ r['q.op365_name'] }}</td>
        <td class="text-end">{{ r['q.op365_quantity'] }} {{ r['q.op365_uom'] }}</td>
        <td><input type="number" min="0" step="0.01" class="form-control op365-price" value="{{ r['q.op365_price'] }}" {% if closed %}disabled{% endif %}></td>
        <td><input type="text" maxlength="400" class="form-control op365-notes" value="{{ r['q.op365_notes'] | escape }}" {% if closed %}disabled{% endif %}></td>
      </tr>
    {% endif %}{% endfor %}
    </tbody>
  </table></div>
  <div class="row g-3 mb-3">
    <div class="col-sm-3"><label class="form-label" for="op365-days">Delivery days</label>
      <input id="op365-days" type="number" min="0" class="form-control" value="{{ i.op365_deliverydays }}" {% if closed %}disabled{% endif %}></div>
    <div class="col-sm-9"><label class="form-label" for="op365-snotes">Notes for the buyer</label>
      <textarea id="op365-snotes" class="form-control" rows="2" {% if closed %}disabled{% endif %}>{{ i.op365_suppliernotes | escape }}</textarea></div>
  </div>
  {% unless closed %}
  <button type="submit" class="btn btn-primary">Send quote</button>
  <button type="button" id="op365-decline" class="btn btn-outline-secondary ms-2">Decline</button>
  {% endunless %}
  </form>
  {% endif %}
</div>"""
QUOTE = fill(QUOTE, DECLINED)

QUOTE_JS = WEBAPI_JS + """
$(function () {
  var form = $('#op365-quote');
  if (!form.length) return;
  var inv = form.data('invitation');
  form.on('submit', function (e) {
    e.preventDefault();
    var calls = [], missing = false;
    form.find('tr[data-quote]').each(function () {
      var price = $(this).find('.op365-price').val();
      if (price === '') { missing = true; return; }
      calls.push({ url: '/_api/op365_rfqquotes(' + $(this).data('quote') + ')',
                   body: { op365_price: parseFloat(price), op365_notes: $(this).find('.op365-notes').val() } });
    });
    if (!calls.length) { op365Error('Enter at least one price.'); return; }
    var days = $('#op365-days').val();
    calls.push({ url: '/_api/op365_rfqinvitations(' + inv + ')',
                 body: { op365_deliverydays: days === '' ? null : parseInt(days, 10), op365_suppliernotes: $('#op365-snotes').val() } });
    form.find('button').prop('disabled', true);
    var run = function (k) {
      if (k === calls.length) { $('#op365-ok').removeClass('d-none'); $('#op365-error').addClass('d-none'); form.find('button').prop('disabled', false); return; }
      op365Api('PATCH', calls[k].url, calls[k].body).done(function () { run(k + 1); })
        .fail(function (m) { op365Error(m); form.find('button').prop('disabled', false); });
    };
    run(0);
    if (missing) { $('#op365-ok').text('Your quote has been sent. Lines without a price are not quoted.'); }
  });
  $('#op365-decline').on('click', function () {
    if (!confirm('Decline this request for quotation?')) return;
    op365Api('PATCH', '/_api/op365_rfqinvitations(' + inv + ')', { statuscode: %d })
      .done(function () { location.reload(); }).fail(op365Error);
  });
});
"""
QUOTE_JS = fill(QUOTE_JS, DECLINED)

ORDER = """<div>
  {% assign id = request.params['id'] %}
  {% fetchxml po %}
  <fetch top="1">
    <entity name="op365_purchaseorder">
      <attribute name="op365_purchaseorderid" /><attribute name="op365_number" /><attribute name="op365_orderdate" />
      <attribute name="op365_expecteddelivery" /><attribute name="op365_deliveryplace" /><attribute name="op365_paymentterms" />
      <attribute name="op365_totalamount" /><attribute name="statuscode" /><attribute name="op365_confirmedon" />
      <filter><condition attribute="op365_purchaseorderid" operator="eq" value="{{ id | xml_escape }}" />
        <condition attribute="statuscode" operator="in"><value>%d</value><value>%d</value><value>%d</value></condition></filter>
    </entity>
  </fetch>
  {% endfetchxml %}
  {% if po.results.entities.size == 0 %}
  <div class="alert alert-warning">Purchase order not found.</div>
  {% else %}
  {% assign o = po.results.entities[0] %}
  {% fetchxml lines %}
  <fetch>
    <entity name="op365_purchaseorderline">
      <attribute name="op365_name" /><attribute name="op365_quantity" /><attribute name="op365_uom" />
      <attribute name="op365_price" /><attribute name="op365_amount" /><attribute name="op365_receivedquantity" />
      <filter><condition attribute="op365_purchaseorderid" operator="eq" value="{{ o.op365_purchaseorderid }}" />
        <condition attribute="statecode" operator="eq" value="0" /></filter>
      <order attribute="op365_sortorder" />
    </entity>
  </fetch>
  {% endfetchxml %}
  <a href="/orders/" class="small">&larr; Purchase orders</a>
  <h1 class="h3 mt-2">{{ o.op365_number }}</h1>
  <dl class="row mb-3">
    <dt class="col-sm-3">Order date</dt><dd class="col-sm-9">{{ o.op365_orderdate | date: 'dd/MM/yyyy' }}</dd>
    <dt class="col-sm-3">Expected delivery</dt><dd class="col-sm-9">{{ o.op365_expecteddelivery | date: 'dd/MM/yyyy' }}</dd>
    <dt class="col-sm-3">Delivery place</dt><dd class="col-sm-9">{{ o.op365_deliveryplace | escape }}</dd>
    <dt class="col-sm-3">Payment terms</dt><dd class="col-sm-9">{{ o.op365_paymentterms | escape }}</dd>
    <dt class="col-sm-3">Status</dt><dd class="col-sm-9">{{ o.statuscode.label }}{% if o.op365_confirmedon %} &middot; confirmed {{ o.op365_confirmedon | date: 'dd/MM/yyyy' }}{% endif %}</dd>
  </dl>
  <div class="table-responsive"><table class="table align-middle">
    <thead><tr><th>Item</th><th class="text-end">Quantity</th><th class="text-end">Unit price</th><th class="text-end">Amount</th><th class="text-end">Received</th></tr></thead>
    <tbody>
    {% for l in lines.results.entities %}
      <tr><td>{{ l.op365_name }}</td><td class="text-end">{{ l.op365_quantity }} {{ l.op365_uom }}</td>
        <td class="text-end">{{ l.op365_price | round: 2 }}</td><td class="text-end">{{ l.op365_amount | round: 2 }}</td>
        <td class="text-end">{{ l.op365_receivedquantity }}</td></tr>
    {% endfor %}
    </tbody>
    <tfoot><tr><th colspan="3">Total</th><th class="text-end">{{ o.op365_totalamount | round: 2 }}</th><th></th></tr></tfoot>
  </table></div>
  <div id="op365-error" class="alert alert-danger d-none"></div>
  {% if o.statuscode.value == %d %}
  <button id="op365-confirm" class="btn btn-primary" data-order="{{ o.op365_purchaseorderid }}">Confirm order</button>
  {% endif %}
  {% endif %}
</div>"""
ORDER = fill(ORDER, PO_SENT, PO_CONFIRMED, PO_RECEIVED, PO_SENT)

ORDER_JS = WEBAPI_JS + """
$(function () {
  $('#op365-confirm').on('click', function () {
    var b = $(this);
    if (!confirm('Confirm this purchase order?')) return;
    b.prop('disabled', true);
    op365Api('PATCH', '/_api/op365_purchaseorders(' + b.data('order') + ')', { op365_supplierconfirmed: true })
      .done(function () { location.reload(); }).fail(function (m) { op365Error(m); b.prop('disabled', false); });
  });
});
"""


def page(title, url, html, js='', parent=None, order=10, hidden=False):
    """Root page plus its English content page (the content page holds copy and JavaScript)."""
    common = {'mspp_name': title, 'mspp_title': title, 'mspp_partialurl': url, 'mspp_displayorder': order,
              'mspp_hiddenfromsitemap': hidden, 'mspp_excludefromsearch': True, 'mspp_enablerating': False,
              'mspp_sharedpageconfiguration': False,
              'mspp_pagetemplateid@odata.bind': f'/mspp_pagetemplates({TEMPLATE})',
              'mspp_publishingstateid@odata.bind': f'/mspp_publishingstates({PUBLISHED})',
              'mspp_parentpageid@odata.bind': f'/mspp_webpages({parent or HOME})'}
    root = upsert('mspp_webpages', 'mspp_webpageid', f"mspp_isroot eq true and mspp_name eq '{q(title)}'", dict(common, mspp_isroot=True))
    upsert('mspp_webpages', 'mspp_webpageid', f"mspp_isroot eq false and _mspp_rootwebpageid_value eq {root}", dict(
        common, mspp_isroot=False, mspp_copy=GUARD_OPEN + html + GUARD_CLOSE, mspp_customjavascript=js,
        **{'mspp_rootwebpageid@odata.bind': f'/mspp_webpages({root})',
           'mspp_webpagelanguageid@odata.bind': f'/mspp_websitelanguages({LANGUAGE})'}))
    return root


# ---------- shared web templates: style, sidebar, project cards ----------
for name, source in ((ui.STYLE_NAME, ui.STYLE), (ui.NAV_NAME, ui.tokens(ui.NAV)), (ui.PROJECT_CARDS_NAME, ui.tokens(ui.PROJECT_CARDS))):
    upsert('mspp_webtemplates', 'mspp_webtemplateid', f"mspp_name eq '{q(name)}'", {'mspp_name': name, 'mspp_source': source})

dashboard = page('Dashboard', 'dashboard', ui.shell('dashboard', ui.tokens(ui.DASHBOARD)), order=1)
projects = page('Projects', 'projects', ui.shell('projects', ui.tokens(ui.PROJECTS)), order=2)
rfqs = page('Requests for quotation', 'rfqs', ui.shell('rfqs', ui.tokens(ui.RFQS)), order=3)
page('Quote', 'quote', ui.shell('rfqs', QUOTE), QUOTE_JS, parent=rfqs, hidden=True)
orders = page('Purchase orders', 'orders', ui.shell('orders', ui.tokens(ui.ORDERS)), order=4)
page('Order', 'order', ui.shell('orders', ORDER), ORDER_JS, parent=orders, hidden=True)
invoices = page('Invoices', 'invoices', ui.shell('invoices', ui.tokens(ui.INVOICES)), order=5)
documents = page('Documents', 'documents', ui.shell('documents', ui.tokens(ui.DOCUMENTS)), ui.DOCUMENTS_JS, order=6)

# ---------- home: suppliers go straight to the dashboard, everyone else gets the sign-in landing ----------
HOME_HTML = """{% include '""" + ui.STYLE_NAME + """' %}
{% assign supplier = false %}{% if user %}{% for r in user.roles %}{% if r == 'Supplier' %}{% assign supplier = true %}{% endif %}{% endfor %}{% endif %}
{% if supplier %}<script>location.replace('/dashboard/');</script>{% endif %}
<div class="op-shell" style="justify-content:center;align-items:center">
  <div style="max-width:560px;text-align:center;padding:48px 16px">
    <h1 style="font-weight:700">Supplier portal</h1>
    <p>Answer requests for quotation, confirm purchase orders, follow invoices and keep your company documents up to date.</p>
    {% if user %}
    <p>Your account is not yet linked to a supplier. Ask your customer to enable it.</p>
    {% else %}
    <p><a class="btn btn-primary" href="/SignIn?returnUrl=%2Fdashboard%2F">Sign in</a>
    """ + ("""<a class="btn btn-outline-primary ms-2" href="/Account/Login/Register?returnUrl=%2Fdashboard%2F">Register</a>""" if SELF_REGISTRATION else '') + """</p>
    {% endif %}
  </div>
</div>
"""
home_content = rows('mspp_webpages', f"mspp_isroot eq false and _mspp_rootwebpageid_value eq {HOME}", 'mspp_webpageid')
for row in home_content:
    r = S.patch(API + f"mspp_webpages({row['mspp_webpageid']})", json={'mspp_copy': HOME_HTML})
    if r.status_code >= 300:
        raise SystemExit(f'home: {r.text[:300]}')
print('ok   home page')

# ---------- menu ----------
for name, target, order in (('Dashboard', dashboard, 1), ('Projects', projects, 2), ('Requests for quotation', rfqs, 3),
                            ('Purchase orders', orders, 4), ('Invoices', invoices, 5), ('Documents', documents, 6)):
    found = rows('mspp_weblinks', f"_mspp_weblinksetid_value eq {MENU} and mspp_name eq '{q(name)}'", 'mspp_weblinkid')
    body = {'mspp_name': name, 'mspp_displayorder': order, 'mspp_robotsfollowlink': True, 'mspp_openinnewwindow': False,
            'mspp_pageid@odata.bind': f'/mspp_webpages({target})', 'mspp_weblinksetid@odata.bind': f'/mspp_weblinksets({MENU})',
            'mspp_publishingstateid@odata.bind': f'/mspp_publishingstates({PUBLISHED})'}
    r = S.patch(API + f"mspp_weblinks({found[0]['mspp_weblinkid']})", json=body) if found else S.post(API + 'mspp_weblinks', json=body)
    if r.status_code >= 300:
        raise SystemExit(f'weblink {name}: {r.text[:300]}')
    print('ok   weblink', name)
