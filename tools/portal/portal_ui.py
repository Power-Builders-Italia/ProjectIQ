"""Liquid + CSS of the supplier portal: shared style and navigation (web templates) and the module pages.

Layout: sidebar with the modules and their to-do counters, Dashboard (KPIs, compliance ring of the company documents,
To do list, project cards), portfolio cards for projects, requests for quotation, purchase orders and invoices (with
CSS-only status filters), and a grid with upload form for the company documents. Used by supplier_portal.py.
Records are read with the Liquid fetchxml tag, so the table permissions of the Supplier web role filter them.
"""
import re

VALUES = {
    'INVITED': 365000000, 'RESPONDED': 365000001, 'DECLINED': 365000002,
    'PO_SENT': 365000000, 'PO_CONFIRMED': 365000001, 'PO_RECEIVED': 365000002,
    'INV_TO_REVIEW': 1, 'INV_APPROVED': 365000000, 'INV_REJECTED': 365000001,
    'DOC_APPROVED': 1, 'DOC_PENDING': 365000000, 'DOC_REJECTED': 365000001,
    'EXP_VALID': 365000000, 'EXP_EXPIRING': 365000001, 'EXP_EXPIRED': 365000002, 'EXP_REPLACED': 365000003,
}
DOCUMENT_TYPES = [(365000000, 'DURC'), (365000001, 'Company Report'), (365000002, 'Certification'),
                  (365000003, 'Insurance'), (365000004, 'Contract'), (365000005, 'Other')]


STYLE_NAME = 'OP365 Supplier Style'
NAV_NAME = 'OP365 Supplier Nav'
PROJECT_CARDS_NAME = 'OP365 Supplier Project Cards'


def tokens(text):
    """Replaces @NAME@ with the choice values above (the templates are full of Liquid {% %}, so no % formatting)."""
    for k, v in VALUES.items():
        text = text.replace(f'@{k}@', str(v))
    text = text.replace('@DOCUMENT_TYPES@', ''.join(f'<option value="{v}">{n}</option>' for v, n in DOCUMENT_TYPES))
    text = text.replace('@PROJECT_CARDS@', PROJECT_CARDS_NAME)
    left = re.findall(r'@[A-Z_]+@', text)
    if left:
        raise ValueError(f'unknown tokens {left}')
    return text


def shell(active, body):
    """Sidebar and main area around the content of a page."""
    return (f"{{% include '{STYLE_NAME}' %}}\n<div class=\"op-shell\">\n{{% include '{NAV_NAME}' active: '{active}' %}}\n"
            f"<main class=\"op-main\" id=\"op-main\">\n{body}\n</main>\n</div>")


STYLE = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--op-navy:#0f2a44;--op-navy-2:#1e4a72;--op-sky:#38bdf8;--op-accent:#1d4ed8;--op-ink:#0f172a;--op-muted:#475569;
  --op-line:#e2e8f0;--op-bg:#f1f5f9;--op-green:#16a34a;--op-amber:#f59e0b;--op-red:#dc2626}
.page-copy:has(.op-shell){padding:0;margin:0;max-width:none}
/* the sidebar replaces the site header and footer on portal pages */
body:has(.op-shell){background:var(--op-bg);margin:0}
body:has(.op-shell) header,body:has(.op-shell) .navbar,body:has(.op-shell) footer,body:has(.op-shell) .footer{display:none!important}
.op-shell{display:flex;flex-wrap:wrap;min-height:100vh;background:var(--op-bg);color:var(--op-ink);
  font-family:Inter,"Segoe UI",system-ui,sans-serif;text-align:left}
.op-shell a{color:var(--op-accent)}
.op-shell .d-none{display:none!important}
.op-nav{flex:1 1 232px;max-width:256px;background:var(--op-navy);color:#e2e8f0;padding:24px 16px;box-sizing:border-box;
  display:flex;flex-direction:column;gap:4px}
.op-brand{display:flex;align-items:center;gap:10px;padding:0 8px 24px;font-weight:700;font-size:16px;color:#fff!important;text-decoration:none}
.op-logo{width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,var(--op-sky),var(--op-accent))}
.op-nav a.op-link{display:flex;justify-content:space-between;align-items:center;padding:12px;border-radius:8px;color:#cbd5e1;
  text-decoration:none;font-size:14px;transition:background .15s}
.op-nav a.op-link:hover,.op-nav a.op-link:focus-visible{background:#163a5c;color:#fff}
.op-nav a.op-link.active{background:var(--op-navy-2);color:#fff;font-weight:600}
.op-count{background:var(--op-sky);color:var(--op-navy);border-radius:10px;padding:0 8px;font-weight:700;font-size:12px}
.op-count.warn{background:var(--op-amber);color:#1f1300}
.op-who{margin-top:auto;padding:16px 8px 0;border-top:1px solid var(--op-navy-2);font-size:13px;color:#cbd5e1}
.op-who span{color:#94a3b8}.op-who a{color:#cbd5e1!important}
.op-main{flex:999 1 560px;min-width:0;padding:32px 40px;box-sizing:border-box;display:flex;flex-direction:column;gap:20px}
.op-head{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:flex-end;gap:16px}
.op-crumb{font-size:13px;color:var(--op-muted)}
.op-h1{margin:4px 0 0;font-size:28px;font-weight:700;color:var(--op-ink)}
.op-h2{margin:0;font-size:18px;font-weight:700;color:var(--op-ink)}
.op-muted{font-size:13px;color:var(--op-muted);margin:0}
.op-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px}
.op-kpi{background:#fff;border:1px solid var(--op-line);border-radius:12px;padding:18px}
.op-kpi b{display:block;font-size:26px;margin-top:4px}
.op-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}
.op-panels{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,2fr);gap:16px}
.op-card{background:#fff;border:1px solid var(--op-line);border-radius:14px;padding:18px;display:flex;flex-direction:column;
  gap:14px;transition:box-shadow .15s,transform .15s}
.op-grid>.op-card:hover{box-shadow:0 8px 24px rgba(15,42,68,.10);transform:translateY(-2px)}
.op-card.attention{border:2px solid var(--op-amber)}
.op-card.closed{opacity:.8}
.op-row{display:flex;justify-content:space-between;align-items:baseline;gap:12px}
.op-amount{font-size:20px;font-weight:700;white-space:nowrap}
.op-badge{font-size:11px;font-weight:700;padding:3px 8px;border-radius:6px;white-space:nowrap}
.b-blue{color:#1d4ed8;background:#dbeafe}.b-green{color:#047857;background:#d1fae5}.b-amber{color:#92400e;background:#fef3c7}
.b-red{color:#b91c1c;background:#fee2e2}.b-grey{color:#334155;background:#e2e8f0}
.op-steps{display:grid;grid-auto-flow:column;grid-auto-columns:1fr;gap:4px;list-style:none;margin:0;padding:0;font-size:11px;
  color:var(--op-muted);text-align:center}
.op-steps li::before{content:"";display:block;height:4px;border-radius:2px;background:var(--op-line);margin-bottom:4px}
.op-steps li.done::before{background:var(--op-accent)}.op-steps li.ok::before{background:var(--op-green)}
.op-steps li.ko::before{background:var(--op-red)}
.op-meter{font-size:12px;color:var(--op-muted)}
.op-meter .op-row{margin-bottom:6px}
.op-bar{height:8px;border-radius:4px;background:var(--op-line);overflow:hidden}
.op-bar>span{display:block;height:100%;width:var(--w);background:var(--op-green);border-radius:4px}
.op-bar.blue>span{background:var(--op-accent)}.op-bar.amber>span{background:var(--op-amber)}.op-bar.red>span{background:var(--op-red)}
.op-dl{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));margin:0;font-size:12px;color:var(--op-muted)}
.op-dl dd{margin:2px 0 0;font-size:15px;font-weight:600;color:var(--op-ink)}
.op-actions{display:flex;gap:8px;flex-wrap:wrap}
.op-btn{display:inline-block;text-align:center;background:var(--op-accent);color:#fff!important;padding:10px 16px;border-radius:8px;
  text-decoration:none;font-weight:600;font-size:14px;border:0}
.op-btn:hover{background:#1e3a8a}.op-btn.grow{flex:1}
.op-btn.ghost{background:#fff;color:#334155!important;border:1px solid #cbd5e1;font-weight:500}
.op-btn.ghost:hover{background:var(--op-bg)}
.op-btn.small{padding:6px 10px;font-size:13px}
/* compliance ring: three conic sectors drawn from the Liquid percentages */
.op-ring{width:156px;height:156px;border-radius:50%;flex:none;display:grid;place-items:center;
  background:conic-gradient(var(--op-green) 0 var(--v),var(--op-amber) var(--v) var(--e),var(--op-red) var(--e) 100%)}
.op-ring.empty{background:var(--op-line)}
.op-ring>div{width:114px;height:114px;border-radius:50%;background:#fff;display:grid;place-items:center;text-align:center;
  font-size:12px;color:var(--op-muted)}
.op-ring b{display:block;font-size:28px;color:var(--op-ink)}
.op-legend{list-style:none;margin:0;padding:0;display:grid;gap:8px;font-size:13px}
.op-legend li{display:flex;align-items:center;gap:8px}
.op-dot{width:10px;height:10px;border-radius:50%;flex:none;background:var(--c)}
.op-todo{list-style:none;margin:0;padding:0;display:flex;flex-direction:column}
.op-todo li+li{border-top:1px solid var(--op-line)}
.op-todo a{display:flex;align-items:center;gap:12px;padding:12px 4px;text-decoration:none;color:var(--op-ink)!important}
.op-todo a:hover{background:var(--op-bg)}
.op-todo .op-what{flex:1;min-width:0}.op-todo .op-what small{display:block;color:var(--op-muted)}
.op-todo a::after{content:"\\203A";font-size:20px;color:#94a3b8}
.op-empty{padding:24px;text-align:center;color:var(--op-muted);background:#fff;border:1px dashed #cbd5e1;border-radius:14px}
/* status filters without JavaScript: a radio per chip hides the cards of the other statuses */
.op-filter>input{position:absolute;opacity:0;pointer-events:none}
.op-chips{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}
.op-chips label{background:#fff;color:#334155;border:1px solid #cbd5e1;border-radius:999px;padding:8px 16px;font-size:13px;cursor:pointer}
.op-filter>input:focus-visible+.op-chips label{outline:2px solid var(--op-accent)}
#f0:checked~.op-chips label[for=f0],#f1:checked~.op-chips label[for=f1],#f2:checked~.op-chips label[for=f2],
#f3:checked~.op-chips label[for=f3]{background:var(--op-navy);color:#fff;border-color:var(--op-navy);font-weight:600}
#f1:checked~.op-grid>:not(.s1),#f2:checked~.op-grid>:not(.s2),#f3:checked~.op-grid>:not(.s3){display:none}
.op-table{width:100%;border-collapse:collapse;background:#fff;font-size:14px}
.op-table th{font-size:12px;color:var(--op-muted);font-weight:600;text-align:left;padding:10px 12px;border-bottom:1px solid var(--op-line)}
.op-table td{padding:12px;border-bottom:1px solid var(--op-line);vertical-align:top}
.op-table small{display:block;color:var(--op-muted)}
.op-tablebox{background:#fff;border:1px solid var(--op-line);border-radius:14px;overflow-x:auto}
.op-form{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.op-form label{font-size:13px;font-weight:600;color:#334155;display:flex;flex-direction:column;gap:4px}
.op-form input,.op-form select,.op-form textarea{font:inherit;font-weight:400;padding:8px 10px;border:1px solid #cbd5e1;border-radius:8px;background:#fff}
.op-form .wide{grid-column:1/-1}
@media (max-width:900px){.op-panels{grid-template-columns:1fr}}
@media (max-width:720px){.op-main{padding:20px 16px}.op-nav{max-width:none;flex-basis:100%;flex-direction:row;flex-wrap:wrap}
  .op-brand{flex-basis:100%;padding-bottom:8px}.op-who{flex-basis:100%}.op-dl{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (prefers-reduced-motion:reduce){.op-card,.op-nav a.op-link{transition:none}.op-grid>.op-card:hover{transform:none}}
</style>"""

NAV = """{% assign op_today = now | date: 'yyyy-MM-dd' %}
{% fetchxml op_nav_rfq %}
<fetch><entity name="op365_rfqinvitation"><attribute name="op365_rfqinvitationid" />
  <filter><condition attribute="statuscode" operator="eq" value="@INVITED@" />
    <condition attribute="op365_deadline" operator="on-or-after" value="{{ op_today }}" /></filter></entity></fetch>
{% endfetchxml %}
{% fetchxml op_nav_po %}
<fetch><entity name="op365_purchaseorder"><attribute name="op365_purchaseorderid" />
  <filter><condition attribute="statuscode" operator="eq" value="@PO_SENT@" /></filter></entity></fetch>
{% endfetchxml %}
{% fetchxml op_nav_doc %}
<fetch><entity name="op365_supplierdocument"><attribute name="op365_supplierdocumentid" />
  <filter><condition attribute="statecode" operator="eq" value="0" />
    <filter type="or"><condition attribute="statuscode" operator="eq" value="@DOC_REJECTED@" />
      <filter><condition attribute="statuscode" operator="eq" value="@DOC_APPROVED@" />
        <condition attribute="op365_expirystatus" operator="in"><value>@EXP_EXPIRING@</value><value>@EXP_EXPIRED@</value></condition></filter>
    </filter></filter></entity></fetch>
{% endfetchxml %}
{% assign op_n_rfq = op_nav_rfq.results.entities.size %}{% assign op_n_po = op_nav_po.results.entities.size %}
{% assign op_n_doc = op_nav_doc.results.entities.size %}
<nav class="op-nav" aria-label="Supplier portal">
  <a class="op-brand" href="/dashboard/"><span class="op-logo" aria-hidden="true"></span>Supplier portal</a>
  <a class="op-link{% if active == 'dashboard' %} active{% endif %}" href="/dashboard/"{% if active == 'dashboard' %} aria-current="page"{% endif %}>Dashboard</a>
  <a class="op-link{% if active == 'projects' %} active{% endif %}" href="/projects/"{% if active == 'projects' %} aria-current="page"{% endif %}>Projects</a>
  <a class="op-link{% if active == 'rfqs' %} active{% endif %}" href="/rfqs/"{% if active == 'rfqs' %} aria-current="page"{% endif %}>Requests for quotation{% if op_n_rfq > 0 %} <span class="op-count" title="To quote">{{ op_n_rfq }}</span>{% endif %}</a>
  <a class="op-link{% if active == 'orders' %} active{% endif %}" href="/orders/"{% if active == 'orders' %} aria-current="page"{% endif %}>Purchase orders{% if op_n_po > 0 %} <span class="op-count" title="To confirm">{{ op_n_po }}</span>{% endif %}</a>
  <a class="op-link{% if active == 'invoices' %} active{% endif %}" href="/invoices/"{% if active == 'invoices' %} aria-current="page"{% endif %}>Invoices</a>
  <a class="op-link{% if active == 'documents' %} active{% endif %}" href="/documents/"{% if active == 'documents' %} aria-current="page"{% endif %}>Documents{% if op_n_doc > 0 %} <span class="op-count warn" title="To renew or replace">{{ op_n_doc }}</span>{% endif %}</a>
  <div class="op-who">{{ user.parentcustomerid.name | escape }}<br><span>{{ user.fullname | escape }} &middot; <a href="/Account/Login/LogOff?returnUrl=%2F">Sign out</a></span></div>
</nav>"""

# projects of the supplier's orders, one card per project (orders sorted by project, a card at each change)
PROJECT_CARDS = """{% fetchxml op_prj %}
<fetch><entity name="op365_purchaseorder">
  <attribute name="op365_purchaseorderid" /><attribute name="op365_projectid" /><attribute name="op365_totalamount" />
  <attribute name="op365_receivedamount" /><attribute name="statuscode" />
  <filter><condition attribute="statuscode" operator="in"><value>@PO_SENT@</value><value>@PO_CONFIRMED@</value><value>@PO_RECEIVED@</value></condition>
    <condition attribute="op365_projectid" operator="not-null" /></filter>
  <order attribute="op365_projectid" />
  <link-entity name="op365_project" from="op365_projectid" to="op365_projectid" link-type="inner" alias="pr">
    <attribute name="op365_name" /><attribute name="op365_code" /><attribute name="op365_enddate" /><attribute name="op365_progresspct" />
  </link-entity>
</entity></fetch>
{% endfetchxml %}
{% assign op_list = op_prj.results.entities %}
{% if op_list.size == 0 %}
<div class="op-empty">No projects yet: they appear here with your first purchase order.</div>
{% else %}
{% assign op_shown = 0 %}{% assign op_n = 0 %}{% assign op_open = 0 %}{% assign op_ordered = 0 %}{% assign op_received = 0 %}
<div class="op-grid">
{% for o in op_list %}
  {% assign op_t = o.op365_totalamount | default: 0 %}{% assign op_r = o.op365_receivedamount | default: 0 %}
  {% assign op_n = op_n | plus: 1 %}{% assign op_ordered = op_ordered | plus: op_t %}{% assign op_received = op_received | plus: op_r %}
  {% if o.statuscode.value == @PO_SENT@ %}{% assign op_open = op_open | plus: 1 %}{% endif %}
  {% assign op_close = forloop.last %}
  {% unless forloop.last %}{% assign op_next = op_list[forloop.index] %}{% if op_next.op365_projectid.id != o.op365_projectid.id %}{% assign op_close = true %}{% endif %}{% endunless %}
  {% if op_close %}
    {% if op_shown < limit %}
    {% assign op_progress = o['pr.op365_progresspct'] | default: 0 | round: 0 %}
    {% if op_ordered > 0 %}{% assign op_delivered = op_received | times: 100 | divided_by: op_ordered | round: 0 %}{% else %}{% assign op_delivered = 0 %}{% endif %}
    <article class="op-card{% if op_open > 0 %} attention{% endif %}">
      <div class="op-row"><span class="op-muted">{{ o['pr.op365_code'] | escape }}</span>
        {% if op_open > 0 %}<span class="op-badge b-amber">{{ op_open }} to confirm</span>{% elsif op_delivered >= 100 %}<span class="op-badge b-grey">Delivered</span>{% else %}<span class="op-badge b-green">Active</span>{% endif %}</div>
      <h2 class="op-h2">{{ o['pr.op365_name'] | escape }}</h2>
      <div class="op-meter"><div class="op-row"><span>Project progress</span><span>{{ op_progress }}%</span></div>
        <div class="op-bar blue"><span style="--w:{{ op_progress }}%"></span></div></div>
      <div class="op-meter"><div class="op-row"><span>Your deliveries</span><span>{{ op_delivered }}%</span></div>
        <div class="op-bar"><span style="--w:{{ op_delivered }}%"></span></div></div>
      <dl class="op-dl"><div><dt>Orders</dt><dd>{{ op_n }}</dd></div><div><dt>Ordered</dt><dd>{{ op_ordered | round: 0 }}</dd></div>
        <div><dt>End date</dt><dd>{% if o['pr.op365_enddate'] %}{{ o['pr.op365_enddate'] | date: 'dd/MM/yyyy' }}{% else %}&ndash;{% endif %}</dd></div></dl>
      <a href="/orders/" class="op-btn ghost">See orders</a>
    </article>
    {% assign op_shown = op_shown | plus: 1 %}
    {% endif %}
    {% assign op_n = 0 %}{% assign op_open = 0 %}{% assign op_ordered = 0 %}{% assign op_received = 0 %}
  {% endif %}
{% endfor %}
</div>
{% endif %}"""

DASHBOARD = """{% assign today = now | date: 'yyyy-MM-dd' %}{% assign year = now | date: 'yyyy' %}
{% fetchxml rfqs %}
<fetch><entity name="op365_rfqinvitation">
  <attribute name="op365_rfqinvitationid" /><attribute name="op365_rfqnumber" /><attribute name="op365_rfqid" /><attribute name="op365_deadline" />
  <filter><condition attribute="statuscode" operator="eq" value="@INVITED@" /><condition attribute="op365_deadline" operator="on-or-after" value="{{ today }}" /></filter>
  <order attribute="op365_deadline" />
</entity></fetch>
{% endfetchxml %}
{% fetchxml orders %}
<fetch><entity name="op365_purchaseorder">
  <attribute name="op365_purchaseorderid" /><attribute name="op365_number" /><attribute name="op365_orderdate" /><attribute name="op365_projectid" />
  <attribute name="op365_totalamount" /><attribute name="statuscode" />
  <filter><condition attribute="statuscode" operator="in"><value>@PO_SENT@</value><value>@PO_CONFIRMED@</value><value>@PO_RECEIVED@</value></condition></filter>
  <order attribute="op365_orderdate" descending="true" />
</entity></fetch>
{% endfetchxml %}
{% fetchxml docs %}
<fetch><entity name="op365_supplierdocument">
  <attribute name="op365_supplierdocumentid" /><attribute name="op365_documenttype" /><attribute name="op365_description" />
  <attribute name="op365_expirydate" /><attribute name="op365_expirystatus" /><attribute name="statuscode" /><attribute name="op365_reviewnote" />
  <filter><condition attribute="statecode" operator="eq" value="0" /></filter>
  <order attribute="op365_expirydate" />
</entity></fetch>
{% endfetchxml %}
{% fetchxml invoices %}
<fetch><entity name="op365_supplierinvoice"><attribute name="op365_supplierinvoiceid" /><attribute name="op365_totalamount" />
  <filter><condition attribute="statuscode" operator="eq" value="@INV_TO_REVIEW@" /></filter></entity></fetch>
{% endfetchxml %}
{% assign to_confirm = 0 %}{% assign ordered_year = 0 %}
{% for o in orders.results.entities %}
  {% if o.statuscode.value == @PO_SENT@ %}{% assign to_confirm = to_confirm | plus: 1 %}
  {% else %}{% assign oy = o.op365_orderdate | date: 'yyyy' %}{% if oy == year %}{% assign ordered_year = ordered_year | plus: o.op365_totalamount %}{% endif %}{% endif %}
{% endfor %}
{% assign under_review = 0 %}{% for i in invoices.results.entities %}{% assign under_review = under_review | plus: i.op365_totalamount %}{% endfor %}
{% assign valid = 0 %}{% assign expiring = 0 %}{% assign expired = 0 %}{% assign pending = 0 %}{% assign rejected = 0 %}
{% for d in docs.results.entities %}
  {% if d.statuscode.value == @DOC_APPROVED@ %}
    {% if d.op365_expirystatus.value == @EXP_EXPIRED@ %}{% assign expired = expired | plus: 1 %}
    {% elsif d.op365_expirystatus.value == @EXP_EXPIRING@ %}{% assign expiring = expiring | plus: 1 %}
    {% elsif d.op365_expirystatus.value != @EXP_REPLACED@ %}{% assign valid = valid | plus: 1 %}{% endif %}
  {% elsif d.statuscode.value == @DOC_PENDING@ %}{% assign pending = pending | plus: 1 %}
  {% else %}{% assign rejected = rejected | plus: 1 %}{% endif %}
{% endfor %}
{% assign total = valid | plus: expiring | plus: expired %}
{% if total > 0 %}{% assign pv = valid | times: 100 | divided_by: total %}{% assign pe = valid | plus: expiring | times: 100 | divided_by: total %}{% else %}{% assign pv = 0 %}{% assign pe = 0 %}{% endif %}
<div class="op-head">
  <div><div class="op-crumb">{{ user.parentcustomerid.name | escape }}</div><h1 class="op-h1">Welcome, {{ user.firstname | default: user.fullname | escape }}</h1></div>
  <a class="op-btn" href="/documents/#op-docform">New document</a>
</div>
<div class="op-kpis">
  <div class="op-kpi"><span class="op-muted">Requests to quote</span><b>{{ rfqs.results.entities.size }}</b></div>
  <div class="op-kpi"><span class="op-muted">Orders to confirm</span><b>{{ to_confirm }}</b></div>
  <div class="op-kpi"><span class="op-muted">Ordered in {{ year }}</span><b>{{ ordered_year | round: 0 }}</b></div>
  <div class="op-kpi"><span class="op-muted">Invoices under review</span><b>{{ under_review | round: 0 }}</b></div>
</div>
<div class="op-panels">
  <section class="op-card" aria-labelledby="op-compliance">
    <h2 class="op-h2" id="op-compliance">Document compliance</h2>
    <div class="op-row" style="align-items:center;flex-wrap:wrap;justify-content:flex-start;gap:20px">
      <div class="op-ring{% if total == 0 %} empty{% endif %}" style="--v:{{ pv }}%;--e:{{ pe }}%" role="img"
           aria-label="{{ valid }} valid, {{ expiring }} expiring, {{ expired }} expired approved documents">
        <div><span><b>{% if total > 0 %}{{ pv }}%{% else %}&ndash;{% endif %}</b>valid</span></div></div>
      <ul class="op-legend">
        <li><span class="op-dot" style="--c:var(--op-green)"></span>{{ valid }} valid</li>
        <li><span class="op-dot" style="--c:var(--op-amber)"></span>{{ expiring }} expiring within 30 days</li>
        <li><span class="op-dot" style="--c:var(--op-red)"></span>{{ expired }} expired</li>
        <li><span class="op-dot" style="--c:#94a3b8"></span>{{ pending }} waiting for review{% if rejected > 0 %}, {{ rejected }} rejected{% endif %}</li>
      </ul>
    </div>
    <a href="/documents/" class="op-btn ghost">Open documents</a>
  </section>
  <section class="op-card" aria-labelledby="op-todo">
    <div class="op-row"><h2 class="op-h2" id="op-todo">To do</h2><span class="op-muted">Things your customer is waiting for</span></div>
    {% assign todo = rfqs.results.entities.size | plus: to_confirm | plus: expired | plus: expiring | plus: rejected %}
    {% if todo == 0 %}<div class="op-empty">Nothing to do. Everything is up to date.</div>{% else %}
    <ul class="op-todo">
      {% for d in docs.results.entities %}{% if d.statuscode.value == @DOC_APPROVED@ and d.op365_expirystatus.value == @EXP_EXPIRED@ %}
      <li><a href="/documents/#op-docform"><span class="op-dot" style="--c:var(--op-red)"></span><span class="op-what">Renew {{ d.op365_documenttype.label }}: {{ d.op365_description | escape }}<small>Expired on {{ d.op365_expirydate | date: 'dd/MM/yyyy' }}</small></span><span class="op-badge b-red">Expired</span></a></li>
      {% endif %}{% endfor %}
      {% for d in docs.results.entities %}{% if d.statuscode.value == @DOC_REJECTED@ %}
      <li><a href="/documents/"><span class="op-dot" style="--c:var(--op-red)"></span><span class="op-what">Correct {{ d.op365_documenttype.label }}: {{ d.op365_description | escape }}<small>{{ d.op365_reviewnote | escape | default: 'Rejected by the buyer' }}</small></span><span class="op-badge b-red">Rejected</span></a></li>
      {% endif %}{% endfor %}
      {% for r in rfqs.results.entities %}
      <li><a href="/rfqs/quote/?id={{ r.op365_rfqinvitationid }}"><span class="op-dot" style="--c:var(--op-accent)"></span><span class="op-what">Quote {{ r.op365_rfqnumber | escape }}{% if r.op365_rfqid %}: {{ r.op365_rfqid.name | escape }}{% endif %}<small>Deadline {{ r.op365_deadline | date: 'dd/MM/yyyy' }}</small></span><span class="op-badge b-blue">RFQ</span></a></li>
      {% endfor %}
      {% for o in orders.results.entities %}{% if o.statuscode.value == @PO_SENT@ %}
      <li><a href="/orders/order/?id={{ o.op365_purchaseorderid }}"><span class="op-dot" style="--c:var(--op-amber)"></span><span class="op-what">Confirm order {{ o.op365_number | escape }}<small>{% if o.op365_projectid %}{{ o.op365_projectid.name | escape }} &middot; {% endif %}{{ o.op365_totalamount | round: 2 }}</small></span><span class="op-badge b-amber">Order</span></a></li>
      {% endif %}{% endfor %}
      {% for d in docs.results.entities %}{% if d.statuscode.value == @DOC_APPROVED@ and d.op365_expirystatus.value == @EXP_EXPIRING@ %}
      <li><a href="/documents/#op-docform"><span class="op-dot" style="--c:var(--op-amber)"></span><span class="op-what">Renew {{ d.op365_documenttype.label }}: {{ d.op365_description | escape }}<small>Expires on {{ d.op365_expirydate | date: 'dd/MM/yyyy' }}</small></span><span class="op-badge b-amber">Expiring</span></a></li>
      {% endif %}{% endfor %}
    </ul>
    {% endif %}
  </section>
</div>
<div class="op-row"><h2 class="op-h2">Your projects</h2><a href="/projects/" class="op-muted">All projects</a></div>
{% include '@PROJECT_CARDS@' limit: 3 %}"""

PROJECTS = """<div class="op-head"><div><div class="op-crumb"><a href="/dashboard/">Dashboard</a> / Projects</div>
  <h1 class="op-h1">Projects</h1></div></div>
<p class="op-muted">The projects of your purchase orders: progress of the project and of your deliveries.</p>
{% include '@PROJECT_CARDS@' limit: 1000 %}"""

RFQS = """{% assign today = now | date: 'yyyy-MM-dd' %}
{% fetchxml invitations %}
<fetch><entity name="op365_rfqinvitation">
  <attribute name="op365_rfqinvitationid" /><attribute name="op365_rfqnumber" /><attribute name="op365_rfqid" /><attribute name="op365_deadline" />
  <attribute name="statuscode" /><attribute name="op365_quotedamount" /><attribute name="op365_invitedon" /><attribute name="op365_rfqnotes" />
  <filter><condition attribute="statuscode" operator="in"><value>@INVITED@</value><value>@RESPONDED@</value><value>@DECLINED@</value></condition></filter>
  <order attribute="op365_deadline" descending="true" />
</entity></fetch>
{% endfetchxml %}
{% assign list = invitations.results.entities %}
{% assign n1 = 0 %}{% assign n2 = 0 %}{% assign n3 = 0 %}
{% for i in list %}{% assign dl = i.op365_deadline | date: 'yyyy-MM-dd' %}
  {% if i.statuscode.value == @DECLINED@ or dl < today %}{% assign n3 = n3 | plus: 1 %}{% elsif i.statuscode.value == @RESPONDED@ %}{% assign n2 = n2 | plus: 1 %}{% else %}{% assign n1 = n1 | plus: 1 %}{% endif %}
{% endfor %}
<div class="op-head"><div><div class="op-crumb"><a href="/dashboard/">Dashboard</a> / Requests for quotation</div>
  <h1 class="op-h1">Requests for quotation</h1></div></div>
{% if list.size == 0 %}<div class="op-empty">There are no requests for quotation for your company.</div>{% else %}
<div class="op-filter">
  <input type="radio" name="op-f" id="f0" checked><input type="radio" name="op-f" id="f1"><input type="radio" name="op-f" id="f2"><input type="radio" name="op-f" id="f3">
  <div class="op-chips" role="group" aria-label="Filter by status"><label for="f0">All &middot; {{ list.size }}</label><label for="f1">To quote &middot; {{ n1 }}</label>
    <label for="f2">Quoted &middot; {{ n2 }}</label><label for="f3">Closed &middot; {{ n3 }}</label></div>
  <div class="op-grid">
  {% for i in list %}
    {% assign dl = i.op365_deadline | date: 'yyyy-MM-dd' %}
    {% if i.statuscode.value == @DECLINED@ or dl < today %}{% assign s = 3 %}{% elsif i.statuscode.value == @RESPONDED@ %}{% assign s = 2 %}{% else %}{% assign s = 1 %}{% endif %}
    {% assign left = 99 %}
    {% if s != 3 %}{% for k in (0..30) %}{% assign day = now | date_add_days: k | date: 'yyyy-MM-dd' %}{% if day == dl %}{% assign left = k %}{% break %}{% endif %}{% endfor %}{% endif %}
    {% if left < 14 %}{% assign used = 14 | minus: left | times: 100 | divided_by: 14 %}{% else %}{% assign used = 5 %}{% endif %}
    <article class="op-card s{{ s }}{% if s == 1 %} attention{% elsif s == 3 %} closed{% endif %}">
      <div class="op-row"><span class="op-muted">Invited {{ i.op365_invitedon | date: 'dd/MM/yyyy' }}</span>
        {% if s == 1 %}<span class="op-badge b-amber">To quote</span>{% elsif s == 2 %}<span class="op-badge b-green">Quoted</span>{% elsif i.statuscode.value == @DECLINED@ %}<span class="op-badge b-grey">Declined</span>{% else %}<span class="op-badge b-grey">Closed</span>{% endif %}</div>
      <div class="op-row"><h2 class="op-h2">{{ i.op365_rfqnumber | escape }}</h2>{% if i.op365_quotedamount > 0 %}<span class="op-amount">{{ i.op365_quotedamount | round: 2 }}</span>{% endif %}</div>
      {% if i.op365_rfqid %}<p class="op-muted">{{ i.op365_rfqid.name | escape }}</p>{% endif %}
      {% if s != 3 %}<div class="op-meter"><div class="op-row"><span>Deadline {{ i.op365_deadline | date: 'dd/MM/yyyy' }}</span>
        <span>{% if left == 0 %}Due today{% elsif left == 1 %}1 day left{% elsif left < 99 %}{{ left }} days left{% else %}more than a month{% endif %}</span></div>
        <div class="op-bar {% if left <= 2 %}red{% elsif left <= 6 %}amber{% else %}blue{% endif %}"><span style="--w:{{ used }}%"></span></div></div>
      {% else %}<p class="op-muted">Deadline {{ i.op365_deadline | date: 'dd/MM/yyyy' }}</p>{% endif %}
      <div class="op-actions">{% if s == 1 %}<a class="op-btn grow" href="/rfqs/quote/?id={{ i.op365_rfqinvitationid }}">Quote now</a>{% elsif s == 2 %}<a class="op-btn ghost grow" href="/rfqs/quote/?id={{ i.op365_rfqinvitationid }}">Change quote</a>{% else %}<a class="op-btn ghost grow" href="/rfqs/quote/?id={{ i.op365_rfqinvitationid }}">Open</a>{% endif %}</div>
    </article>
  {% endfor %}
  </div>
</div>
{% endif %}"""

ORDERS = """{% fetchxml orders %}
<fetch><entity name="op365_purchaseorder">
  <attribute name="op365_purchaseorderid" /><attribute name="op365_number" /><attribute name="op365_orderdate" /><attribute name="op365_projectid" />
  <attribute name="op365_expecteddelivery" /><attribute name="op365_totalamount" /><attribute name="op365_receivedamount" /><attribute name="statuscode" />
  <attribute name="op365_deliveryplace" /><attribute name="op365_paymentterms" /><attribute name="op365_receivedon" />
  <filter><condition attribute="statuscode" operator="in"><value>@PO_SENT@</value><value>@PO_CONFIRMED@</value><value>@PO_RECEIVED@</value></condition></filter>
  <order attribute="op365_orderdate" descending="true" />
</entity></fetch>
{% endfetchxml %}
{% assign list = orders.results.entities %}
{% assign n1 = 0 %}{% assign n2 = 0 %}{% assign n3 = 0 %}
{% for o in list %}{% if o.statuscode.value == @PO_SENT@ %}{% assign n1 = n1 | plus: 1 %}{% elsif o.statuscode.value == @PO_CONFIRMED@ %}{% assign n2 = n2 | plus: 1 %}{% else %}{% assign n3 = n3 | plus: 1 %}{% endif %}{% endfor %}
<div class="op-head"><div><div class="op-crumb"><a href="/dashboard/">Dashboard</a> / Purchase orders</div>
  <h1 class="op-h1">Purchase orders</h1></div></div>
{% if list.size == 0 %}<div class="op-empty">There are no purchase orders for your company.</div>{% else %}
<div class="op-filter">
  <input type="radio" name="op-f" id="f0" checked><input type="radio" name="op-f" id="f1"><input type="radio" name="op-f" id="f2"><input type="radio" name="op-f" id="f3">
  <div class="op-chips" role="group" aria-label="Filter by status"><label for="f0">All &middot; {{ list.size }}</label><label for="f1">To confirm &middot; {{ n1 }}</label>
    <label for="f2">Confirmed &middot; {{ n2 }}</label><label for="f3">Received &middot; {{ n3 }}</label></div>
  <div class="op-grid">
  {% for o in list %}
    {% if o.statuscode.value == @PO_SENT@ %}{% assign s = 1 %}{% elsif o.statuscode.value == @PO_CONFIRMED@ %}{% assign s = 2 %}{% else %}{% assign s = 3 %}{% endif %}
    {% assign t = o.op365_totalamount | default: 0 %}{% assign r = o.op365_receivedamount | default: 0 %}
    {% if t > 0 %}{% assign pct = r | times: 100 | divided_by: t | round: 0 %}{% else %}{% assign pct = 0 %}{% endif %}{% if s == 3 %}{% assign pct = 100 %}{% endif %}
    <article class="op-card s{{ s }}{% if s == 1 %} attention{% elsif s == 3 %} closed{% endif %}">
      <div class="op-row"><span class="op-muted">{% if o.op365_projectid %}{{ o.op365_projectid.name | escape }} &middot; {% endif %}{{ o.op365_orderdate | date: 'dd/MM/yyyy' }}</span>
        {% if s == 1 %}<span class="op-badge b-amber">To confirm</span>{% elsif s == 2 %}<span class="op-badge b-green">Confirmed</span>{% else %}<span class="op-badge b-grey">Received</span>{% endif %}</div>
      <div class="op-row"><h2 class="op-h2">{{ o.op365_number | escape }}</h2><span class="op-amount">{{ t | round: 2 }}</span></div>
      {% if s == 1 %}
      <dl class="op-dl"><div><dt>Expected delivery</dt><dd>{% if o.op365_expecteddelivery %}{{ o.op365_expecteddelivery | date: 'dd/MM/yyyy' }}{% else %}&ndash;{% endif %}</dd></div>
        <div style="grid-column:span 2"><dt>Payment</dt><dd>{{ o.op365_paymentterms | escape | default: '&ndash;' }}</dd></div></dl>
      {% if o.op365_deliveryplace %}<p class="op-muted">Delivery place: {{ o.op365_deliveryplace | escape }}</p>{% endif %}
      <div class="op-actions"><a class="op-btn grow" href="/orders/order/?id={{ o.op365_purchaseorderid }}">Review and confirm</a></div>
      {% else %}
      <div class="op-meter"><div class="op-row"><span>Received</span><span>{{ pct }}%</span></div><div class="op-bar"><span style="--w:{{ pct }}%"></span></div></div>
      <p class="op-muted">{% if s == 3 and o.op365_receivedon %}Delivered {{ o.op365_receivedon | date: 'dd/MM/yyyy' }}{% elsif o.op365_expecteddelivery %}Expected delivery {{ o.op365_expecteddelivery | date: 'dd/MM/yyyy' }}{% endif %}</p>
      <div class="op-actions"><a class="op-btn ghost grow" href="/orders/order/?id={{ o.op365_purchaseorderid }}">Open</a></div>
      {% endif %}
    </article>
  {% endfor %}
  </div>
</div>
{% endif %}"""

INVOICES = """{% assign year = now | date: 'yyyy' %}
{% fetchxml invoices %}
<fetch><entity name="op365_supplierinvoice">
  <attribute name="op365_supplierinvoiceid" /><attribute name="op365_invoicenumber" /><attribute name="op365_invoicedate" />
  <attribute name="op365_totalamount" /><attribute name="statuscode" /><attribute name="op365_decisionnote" /><attribute name="op365_decidedon" />
  <attribute name="op365_purchaseorderid" /><attribute name="op365_projectid" /><attribute name="op365_documenttype" />
  <filter><condition attribute="statuscode" operator="in"><value>@INV_TO_REVIEW@</value><value>@INV_APPROVED@</value><value>@INV_REJECTED@</value></condition></filter>
  <order attribute="op365_invoicedate" descending="true" />
</entity></fetch>
{% endfetchxml %}
{% assign list = invoices.results.entities %}
{% assign n1 = 0 %}{% assign n2 = 0 %}{% assign n3 = 0 %}{% assign review = 0 %}{% assign approved = 0 %}
{% for i in list %}{% assign t = i.op365_totalamount | default: 0 %}
  {% if i.statuscode.value == @INV_TO_REVIEW@ %}{% assign n1 = n1 | plus: 1 %}{% assign review = review | plus: t %}
  {% elsif i.statuscode.value == @INV_APPROVED@ %}{% assign n2 = n2 | plus: 1 %}{% assign iy = i.op365_invoicedate | date: 'yyyy' %}{% if iy == year %}{% assign approved = approved | plus: t %}{% endif %}
  {% else %}{% assign n3 = n3 | plus: 1 %}{% endif %}
{% endfor %}
<div class="op-head"><div><div class="op-crumb"><a href="/dashboard/">Dashboard</a> / Invoices</div>
  <h1 class="op-h1">Invoices</h1></div></div>
<div class="op-kpis">
  <div class="op-kpi"><span class="op-muted">Under review</span><b>{{ review | round: 0 }}</b></div>
  <div class="op-kpi"><span class="op-muted">Approved in {{ year }}</span><b>{{ approved | round: 0 }}</b></div>
  <div class="op-kpi"><span class="op-muted">Rejected</span><b>{{ n3 }}</b></div>
</div>
{% if list.size == 0 %}<div class="op-empty">No invoices received from your company yet.</div>{% else %}
<div class="op-filter">
  <input type="radio" name="op-f" id="f0" checked><input type="radio" name="op-f" id="f1"><input type="radio" name="op-f" id="f2"><input type="radio" name="op-f" id="f3">
  <div class="op-chips" role="group" aria-label="Filter by status"><label for="f0">All &middot; {{ list.size }}</label><label for="f1">Under review &middot; {{ n1 }}</label>
    <label for="f2">Approved &middot; {{ n2 }}</label><label for="f3">Rejected &middot; {{ n3 }}</label></div>
  <div class="op-grid">
  {% for i in list %}
    {% if i.statuscode.value == @INV_TO_REVIEW@ %}{% assign s = 1 %}{% elsif i.statuscode.value == @INV_APPROVED@ %}{% assign s = 2 %}{% else %}{% assign s = 3 %}{% endif %}
    <article class="op-card s{{ s }}">
      <div class="op-row"><span class="op-muted">{% if i.op365_purchaseorderid %}{{ i.op365_purchaseorderid.name | escape }}{% endif %}{% if i.op365_projectid %} &middot; {{ i.op365_projectid.name | escape }}{% endif %}</span>
        {% if s == 1 %}<span class="op-badge b-blue">Under review</span>{% elsif s == 2 %}<span class="op-badge b-green">Approved</span>{% else %}<span class="op-badge b-red">Rejected</span>{% endif %}</div>
      <div class="op-row"><h2 class="op-h2">{{ i.op365_invoicenumber | escape }}</h2><span class="op-amount">{{ i.op365_totalamount | round: 2 }}</span></div>
      <ol class="op-steps" aria-label="Invoice status"><li class="done">Received</li><li class="{% if s == 1 %}{% else %}done{% endif %}">Reviewed</li>
        <li class="{% if s == 2 %}ok{% elsif s == 3 %}ko{% endif %}">{% if s == 3 %}Rejected{% else %}Approved{% endif %}</li></ol>
      <p class="op-muted">{{ i.op365_documenttype.label }} &middot; issued {{ i.op365_invoicedate | date: 'dd/MM/yyyy' }}{% if i.op365_decidedon %} &middot; decided {{ i.op365_decidedon | date: 'dd/MM/yyyy' }}{% endif %}</p>
      {% if s == 3 and i.op365_decisionnote %}<p class="op-muted"><strong>Reason:</strong> {{ i.op365_decisionnote | escape }}</p>{% endif %}
    </article>
  {% endfor %}
  </div>
</div>
{% endif %}"""

DOCUMENTS = """{% fetchxml docs %}
<fetch><entity name="op365_supplierdocument">
  <attribute name="op365_supplierdocumentid" /><attribute name="op365_documenttype" /><attribute name="op365_description" />
  <attribute name="op365_number" /><attribute name="op365_issuedate" /><attribute name="op365_expirydate" /><attribute name="op365_expirystatus" />
  <attribute name="statuscode" /><attribute name="op365_reviewnote" /><attribute name="op365_notes" /><attribute name="op365_file" />
  <filter><condition attribute="statecode" operator="eq" value="0" /></filter>
  <order attribute="op365_documenttype" /><order attribute="op365_expirydate" descending="true" />
</entity></fetch>
{% endfetchxml %}
{% assign list = docs.results.entities %}
<div class="op-head"><div><div class="op-crumb"><a href="/dashboard/">Dashboard</a> / Documents</div>
  <h1 class="op-h1">Company documents</h1></div>
  <a class="op-btn" href="#op-docform">New document</a></div>
<p class="op-muted">DURC, certifications, insurance and the other documents your customer needs. The buyer reviews each new
  document: you can change or delete it until it is approved. You receive an e-mail when an approved document is about to expire.</p>
<div id="op365-error" class="alert alert-danger d-none" role="alert"></div>
{% if list.size == 0 %}<div class="op-empty">No documents yet: upload the first one with the form below.</div>{% else %}
<div class="op-tablebox"><table class="op-table">
  <thead><tr><th scope="col">Document</th><th scope="col">Number</th><th scope="col">Issued</th><th scope="col">Expires</th>
    <th scope="col">Expiry</th><th scope="col">Review</th><th scope="col">File</th><th scope="col"><span class="visually-hidden">Actions</span></th></tr></thead>
  <tbody>
  {% for d in list %}
    {% assign approved = false %}{% if d.statuscode.value == @DOC_APPROVED@ %}{% assign approved = true %}{% endif %}
    <tr>
      <td><strong>{{ d.op365_documenttype.label }}</strong><small>{{ d.op365_description | escape }}</small></td>
      <td>{{ d.op365_number | escape }}</td>
      <td>{% if d.op365_issuedate %}{{ d.op365_issuedate | date: 'dd/MM/yyyy' }}{% endif %}</td>
      <td>{% if d.op365_expirydate %}{{ d.op365_expirydate | date: 'dd/MM/yyyy' }}{% else %}&ndash;{% endif %}</td>
      <td>{% if d.op365_expirydate == nil and d.op365_expirystatus.value != @EXP_REPLACED@ %}<span class="op-badge b-grey">No expiry</span>{% else %}{% case d.op365_expirystatus.value %}{% when @EXP_EXPIRED@ %}<span class="op-badge b-red">Expired</span>{% when @EXP_EXPIRING@ %}<span class="op-badge b-amber">Expiring</span>{% when @EXP_REPLACED@ %}<span class="op-badge b-grey">Replaced</span>{% else %}<span class="op-badge b-green">Valid</span>{% endcase %}{% endif %}</td>
      <td>{% if approved %}<span class="op-badge b-green">Approved</span>{% elsif d.statuscode.value == @DOC_REJECTED@ %}<span class="op-badge b-red">Rejected</span>{% if d.op365_reviewnote %}<small>{{ d.op365_reviewnote | escape }}</small>{% endif %}{% else %}<span class="op-badge b-blue">Pending review</span>{% endif %}</td>
      <td>{% if d.op365_file %}<a href="{{ d.op365_file.Url }}">{{ d.op365_file.Name | escape }}</a>{% elsif d.statuscode.value == 1 %}<span class="op-muted">Filed by your customer</span>{% endif %}</td>
      <td style="white-space:nowrap">{% unless approved %}
        <button type="button" class="op-btn ghost small op365-edit" data-id="{{ d.op365_supplierdocumentid }}" data-type="{{ d.op365_documenttype.value }}"
          data-description="{{ d.op365_description | escape }}" data-number="{{ d.op365_number | escape }}"
          data-issue="{% if d.op365_issuedate %}{{ d.op365_issuedate | date: 'yyyy-MM-dd' }}{% endif %}" data-expiry="{% if d.op365_expirydate %}{{ d.op365_expirydate | date: 'yyyy-MM-dd' }}{% endif %}"
          data-notes="{{ d.op365_notes | escape }}">Edit</button>
        <button type="button" class="op-btn ghost small op365-delete" data-id="{{ d.op365_supplierdocumentid }}">Delete</button>{% endunless %}</td>
    </tr>
  {% endfor %}
  </tbody>
</table></div>
{% endif %}
<section class="op-card" id="op-docform" aria-labelledby="op-docform-title">
  <h2 class="op-h2" id="op-docform-title">Upload a document</h2>
  <form id="op365-doc" class="op-form" data-account="{{ user.parentcustomerid.id }}">
    <input type="hidden" id="op-doc-id">
    <label>Type<select id="op-doc-type" required><option value=""></option>@DOCUMENT_TYPES@</select></label>
    <label>Description<input id="op-doc-description" maxlength="850" required></label>
    <label>Number<input id="op-doc-number" maxlength="100"></label>
    <label>Issue date<input id="op-doc-issue" type="date"></label>
    <label>Expiry date<input id="op-doc-expiry" type="date"></label>
    <label>File (PDF or image)<input id="op-doc-file" type="file" accept=".pdf,image/*"></label>
    <label class="wide">Notes<textarea id="op-doc-notes" rows="2" maxlength="2000"></textarea></label>
    <div class="op-actions wide"><button type="submit" class="op-btn" id="op-doc-save">Upload document</button>
      <button type="button" class="op-btn ghost d-none" id="op-doc-cancel">Cancel</button></div>
  </form>
</section>"""

DOCUMENTS_JS = """// Company documents: create, change and delete through the Power Pages Web API; the file goes to the op365_file column
function op365Call(method, url, body, file) {
  var d = $.Deferred();
  shell.getTokenDeferred().done(function (token) {
    var o = { type: method, url: url, headers: { '__RequestVerificationToken': token } };
    if (file) { o.data = file; o.processData = false; o.contentType = 'application/octet-stream'; }
    else if (body) { o.data = JSON.stringify(body); o.contentType = 'application/json'; }
    $.ajax(o).done(function (data, status, x) { d.resolve(x); })
      .fail(function (x) { var m = x.responseJSON && x.responseJSON.error ? x.responseJSON.error.message : x.statusText; d.reject(m); });
  }).fail(function () { d.reject('Session expired: sign in again.'); });
  return d.promise();
}
function op365Error(text) { $('#op365-error').text(text).removeClass('d-none')[0].scrollIntoView({ block: 'center' }); }
$(function () {
  var form = $('#op365-doc');
  if (!form.length) return;
  function reset() {
    form[0].reset(); $('#op-doc-id').val(''); $('#op-doc-save').text('Upload document').prop('disabled', false);
    $('#op-doc-cancel').addClass('d-none'); $('#op-docform-title').text('Upload a document');
  }
  $('.op365-edit').on('click', function () {
    var b = $(this);
    $('#op-doc-id').val(b.data('id')); $('#op-doc-type').val(String(b.data('type'))); $('#op-doc-description').val(b.data('description'));
    $('#op-doc-number').val(b.data('number')); $('#op-doc-issue').val(b.data('issue')); $('#op-doc-expiry').val(b.data('expiry'));
    $('#op-doc-notes').val(b.data('notes'));
    $('#op-docform-title').text('Change document'); $('#op-doc-save').text('Save changes'); $('#op-doc-cancel').removeClass('d-none');
    document.getElementById('op-docform').scrollIntoView({ behavior: 'smooth' }); $('#op-doc-type').focus();
  });
  $('#op-doc-cancel').on('click', reset);
  $('.op365-delete').on('click', function () {
    if (!confirm('Delete this document?')) return;
    op365Call('DELETE', '/_api/op365_supplierdocuments(' + $(this).data('id') + ')')
      .done(function () { location.reload(); }).fail(op365Error);
  });
  form.on('submit', function (e) {
    e.preventDefault();
    var id = $('#op-doc-id').val(), file = $('#op-doc-file')[0].files[0];
    if (!id && !file) { op365Error('Choose the file of the document.'); return; }
    if (file && file.size > 32 * 1024 * 1024) { op365Error('The file is larger than 32 MB.'); return; }
    var body = { op365_documenttype: parseInt($('#op-doc-type').val(), 10), op365_description: $('#op-doc-description').val(),
                 op365_number: $('#op-doc-number').val(), op365_issuedate: $('#op-doc-issue').val() || null,
                 op365_expirydate: $('#op-doc-expiry').val() || null, op365_notes: $('#op-doc-notes').val() };
    if (!id) body['op365_SupplierId@odata.bind'] = '/accounts(' + form.data('account') + ')';
    $('#op-doc-save').prop('disabled', true);
    var saved = id ? op365Call('PATCH', '/_api/op365_supplierdocuments(' + id + ')', body)
                   : op365Call('POST', '/_api/op365_supplierdocuments', body);
    saved.done(function (x) {
      if (!id) id = (x.getResponseHeader('entityid') || '').replace(/[{}]/g, '');
      if (!file) { location.reload(); return; }
      op365Call('PUT', '/_api/op365_supplierdocuments(' + id + ')/op365_file?x-ms-file-name=' + encodeURIComponent(file.name), null, file)
        .done(function () { location.reload(); })
        .fail(function (m) { op365Error('The document was saved but the file was not uploaded: ' + m); $('#op-doc-save').prop('disabled', false); });
    }).fail(function (m) { op365Error(m); $('#op-doc-save').prop('disabled', false); });
  });
});
"""
