"""Business Applications in Work IQ (Copilot, Cowork): read-only scope.

- column and lookup descriptions, read by the Dataverse semantic model;
- Microsoft Copilot on the ProjectIQ app, so Dataverse indexes the app tables;
- business skills from copilot/skills/*.md, added to the OpenProject365 solution;
- Dataverse search on the tables in scope: Copilot and Cowork read records through the search index;
- glossary of the app semantic model from copilot/glossary.md (`glossary` argument: only this step).

The table scope of the semantic model has no documented API: see docs/en/copilot.md.
Idempotent: run again after changing a description, a skill or the glossary.
"""
import os, sys, re
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API

NS = 'Microsoft.Dynamics.CRM.'
ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
APP = 'op365_OpenProject365'
SKILL_COMPONENT = 10441  # solutioncomponentdefinitions: Skill
# out of the semantic model scope (docs/adr/0001): not added to the search index
NOT_INDEXED = {'op365_resourcecost', 'op365_baselinenode', 'op365_wbsdependency'}


def L(t):
    return {'@odata.type': NS+'Label', 'LocalizedLabels': [{'@odata.type': NS+'LocalizedLabel', 'Label': t, 'LanguageCode': 1033}]}


def ok(r, what):
    if r.status_code >= 300:
        print('FAIL', what, r.status_code, r.text[:600]); sys.exit(1)
    print('ok  ', what)


# ---------- descriptions (table -> column logical name -> description) ----------
DESCRIPTIONS = {
  'account': {
    'op365_iscustomer': 'Yes when the account is a customer that can own projects',
    'op365_issupplier': 'Yes when the account is a supplier that can receive RFQs and purchase orders',
    'op365_customertype': 'Prospect (potential customer) or Customer (has or had projects)',
    'op365_vatnumber': 'VAT registration number (Partita IVA)',
    'op365_taxcode': 'Italian tax code (Codice Fiscale)',
    'op365_supplierstatus': 'Active suppliers can be invited and ordered from; Blocked suppliers cannot',
    'op365_suppliercategory': 'Free-text category of goods or services supplied',
    'op365_iban': 'Bank account (IBAN) for payments to the supplier',
    'op365_paymentterms': 'Agreed payment terms, e.g. 60 days end of month',
  },
  'contact': {
    'op365_isdecisionmaker': 'Yes when the contact takes purchasing or project decisions for the account',
  },
  'op365_item': {
    'op365_name': 'Name of the item (article) as it appears on requests and orders',
    'op365_code': 'Internal item code',
    'op365_category': 'Item category used to group materials',
    'op365_uom': 'Unit of measure of the item, e.g. pcs, m, kg, h',
    'op365_unitcost': 'Standard unit cost of the item',
    'op365_notes': 'Free-text notes on the item',
    'op365_defaultsupplierid': 'Supplier proposed by default when the item is requested or ordered',
  },
  'op365_itemsupplier': {
    'op365_name': 'Short description of the supplier conditions for the item',
    'op365_suppliercode': 'Code of the item in the supplier catalogue',
    'op365_price': 'Unit price agreed with the supplier',
    'op365_leadtimedays': 'Days between order and delivery',
    'op365_minimumlot': 'Minimum quantity the supplier accepts per order',
    'op365_notes': 'Free-text notes on the supplier conditions',
    'op365_itemid': 'Item the conditions refer to',
    'op365_supplierid': 'Supplier offering the item',
  },
  'op365_supplierdocument': {
    'op365_description': 'Short description of the document, e.g. DURC and supplier name',
    'op365_documenttype': 'Kind of compliance document: DURC, Company Report, Certification, Insurance, Contract or Other',
    'op365_number': 'Document number or protocol',
    'op365_issuedate': 'Date the document was issued',
    'op365_expirydate': 'Date the document expires; expired documents count in Expired Documents on the supplier',
    'op365_externalurl': 'Link to the document when it is stored outside Dataverse',
    'op365_file': 'Scanned or PDF copy of the document',
    'op365_notes': 'Free-text notes on the document',
    'op365_supplierid': 'Supplier the compliance document belongs to',
    'op365_expirystatus': 'Valid, Expiring (within 30 days), Expired, or Replaced by a newer approved document of the same type',
    'op365_expirynotice': 'Last expiry e-mail sent to the supplier for the document: Expiring or Expired',
    'op365_fromportal': 'Yes when the supplier uploaded the document in the supplier portal',
    'op365_reviewedbyid': 'User who approved or rejected the document',
    'op365_reviewedon': 'Date and time the document was approved or rejected',
    'op365_reviewnote': 'Note of the reviewer; the reason when the document is rejected',
  },
  'op365_resource': {
    'op365_name': 'Full name of the resource',
    'op365_workingdays': 'Days of the week the resource works, used for capacity and missing hours',
    'op365_role': 'Job role of the resource, e.g. engineer, technician',
    'op365_weeklyhours': 'Contract hours per week, used for resource load',
    'op365_userid': 'User account of the resource; empty for people without a license',
  },
  'op365_resourcecost': {
    'op365_name': 'Short description of the cost period',
    'op365_validfrom': 'Date from which the hourly cost applies',
    'op365_hourlycost': 'Hourly cost of the resource from Valid From',
    'op365_resourceid': 'Resource the cost belongs to',
  },
  'op365_absence': {
    'op365_name': 'Short description of the absence',
    'op365_absencetype': 'Vacation, Leave, Sickness, or Closure (company closure for everyone)',
    'op365_fromdate': 'First day of the absence',
    'op365_todate': 'Last day of the absence',
    'op365_notes': 'Free-text notes on the absence',
    'op365_resourceid': 'Absent resource; empty for a company closure',
  },
  'op365_project': {
    'op365_name': 'Name of the project (commessa); Code is the unique identifier',
    'op365_code': 'Project code, e.g. PRJ-000123',
    'op365_startdate': 'Planned start date of the project',
    'op365_enddate': 'Planned end date of the project',
    'op365_contractvalue': 'Value of the contract with the customer (revenue)',
    'op365_description': 'Description of the project scope',
    'op365_customerid': 'Customer the project is for',
    'op365_projectmanagerid': 'User responsible for the project',
  },
  'op365_projectmember': {
    'op365_name': 'Full name of the user, set automatically',
    'op365_projectrole': 'Manager, Contributor, or Reader: the access the member has to the project',
    'op365_projectid': 'Project the member works on',
    'op365_userid': 'User who is a member of the project',
  },
  'op365_wbsnode': {
    'op365_name': 'Name of the phase, activity or task',
    'op365_budgethours': 'Planned hours for the node',
    'op365_budgetlabour': 'Planned labour cost for the node',
    'op365_budgetmaterials': 'Planned materials cost for the node',
    'op365_budgetother': 'Planned other costs for the node',
    'op365_progresspct': 'Completion of the node in percent',
    'op365_startdate': 'Planned start date of the node',
    'op365_enddate': 'Planned end date of the node',
    'op365_projectid': 'Project the node belongs to',
    'op365_parentid': 'Parent node in the work breakdown structure; empty for a top-level phase',
    'op365_ownerresourceid': 'Resource responsible for the node',
  },
  'op365_wbsdependency': {
    'op365_name': 'Predecessor → successor, set automatically',
    'op365_dependencytype': 'Finish-to-Start: the successor starts after the predecessor ends',
    'op365_lagdays': 'Days between the end of the predecessor and the start of the successor',
    'op365_projectid': 'Project of the two linked nodes',
    'op365_predecessorid': 'Node that must finish first',
    'op365_successorid': 'Node that starts after the predecessor',
  },
  'op365_wbsallocation': {
    'op365_name': 'Short description of the allocation',
    'op365_hours': 'Hours planned for the resource on the node',
    'op365_wbsnodeid': 'Node the hours are planned on',
    'op365_resourceid': 'Resource whose hours are planned',
  },
  'op365_baseline': {
    'op365_name': 'Name of the baseline; Save Baseline defaults it to the date and time',
    'op365_description': 'Why the baseline was saved, e.g. contract signed',
    'op365_projectid': 'Project the baseline is a snapshot of',
  },
  'op365_baselinenode': {
    'op365_name': 'Name of the WBS node when the baseline was saved',
    'op365_code': 'Outline code of the node when the baseline was saved',
    'op365_budgethours': 'Budget hours of the node when the baseline was saved',
    'op365_budgettotal': 'Total budget of the node when the baseline was saved',
    'op365_startdate': 'Start date of the node when the baseline was saved',
    'op365_enddate': 'End date of the node when the baseline was saved',
    'op365_baselineid': 'Baseline the values belong to',
    'op365_wbsnodeid': 'Current node the saved values refer to',
  },
  'op365_timeentry': {
    'op365_name': 'Resource name and date, set automatically',
    'op365_entrydate': 'Day the hours were worked',
    'op365_hours': 'Hours worked on the day',
    'op365_notes': 'What was done',
    'op365_submittedon': 'When the hours were submitted for approval',
    'op365_decidedon': 'When the hours were approved or rejected',
    'op365_decisionnote': 'Reason given by the approver, required when rejecting',
    'op365_projectid': 'Project the hours were worked on',
    'op365_wbsnodeid': 'WBS node the hours were worked on',
    'op365_resourceid': 'Resource who worked the hours',
    'op365_decidedbyid': 'User who approved or rejected the hours',
  },
  'op365_materialusage': {
    'op365_name': 'Description of the consumed material; defaults to the item name',
    'op365_usagedate': 'Day the material was used',
    'op365_quantity': 'Quantity used',
    'op365_uom': 'Unit of measure of the quantity',
    'op365_unitcost': 'Cost per unit of the material used',
    'op365_projectid': 'Project that used the material',
    'op365_wbsnodeid': 'WBS node that used the material',
    'op365_itemid': 'Item used',
    'op365_supplierid': 'Supplier the material came from',
    'op365_goodsreceiptlineid': 'Goods receipt line the material came from',
  },
  'op365_purchaserequest': {
    'op365_number': 'Purchase request number, assigned automatically (PR-00001)',
    'op365_title': 'Short title of what is requested',
    'op365_justification': 'Why the purchase is needed',
    'op365_neededby': 'Date by which the goods or services are needed',
    'op365_submittedon': 'When the request was submitted for approval',
    'op365_managerapprovedon': 'When the project manager approved the request',
    'op365_decidedon': 'When the request was finally approved or rejected',
    'op365_decisionnote': 'Reason given by the approver, required when rejecting',
    'op365_projectid': 'Project the purchase is for',
    'op365_wbsnodeid': 'WBS node whose budget the purchase uses',
    'op365_preferredsupplierid': 'Supplier suggested by the requester',
    'op365_requesterid': 'User who asked for the purchase',
    'op365_currentapproverid': 'User who must approve the request now',
    'op365_managerapprovedbyid': 'Project manager who approved the request',
    'op365_decidedbyid': 'User who took the final decision',
  },
  'op365_purchaserequestline': {
    'op365_name': 'Description of the requested item; defaults to the item name',
    'op365_quantity': 'Requested quantity',
    'op365_uom': 'Unit of measure of the quantity',
    'op365_estimatedprice': 'Estimated unit price',
    'op365_sortorder': 'Position of the line in the request',
    'op365_notes': 'Free-text notes on the line',
    'op365_purchaserequestid': 'Purchase request the line belongs to',
    'op365_itemid': 'Requested item; empty for a service or a free-text line',
  },
  'op365_rfq': {
    'op365_number': 'Request for quotation number, assigned automatically (RFQ-00001)',
    'op365_deadline': 'Last day for suppliers to send their quote',
    'op365_notes': 'Instructions for the suppliers',
    'op365_senton': 'When the RFQ was sent to the suppliers',
    'op365_awardedon': 'When the RFQ was awarded to a supplier',
    'op365_cancelledon': 'When the RFQ was cancelled',
    'op365_projectid': 'Project the RFQ is for',
    'op365_purchaserequestid': 'Approved purchase request the RFQ comes from',
    'op365_winninginvitationid': 'Supplier invitation that won the RFQ',
    'op365_purchaseorderid': 'Purchase order created when the RFQ was awarded',
  },
  'op365_rfqinvitation': {
    'op365_name': 'Name of the invited supplier, set automatically',
    'op365_email': 'Email address the RFQ is sent to',
    'op365_invitedon': 'When the supplier was invited',
    'op365_respondedon': 'When the supplier answered',
    'op365_deliverydays': 'Delivery time quoted by the supplier, in days',
    'op365_suppliernotes': 'Notes written by the supplier with the quote',
    'op365_rfqid': 'RFQ the invitation belongs to',
    'op365_supplierid': 'Invited supplier',
  },
  'op365_rfqquote': {
    'op365_name': 'Description of the quoted item, copied from the request line',
    'op365_notes': 'Supplier notes on the quoted line',
    'op365_uom': 'Unit of measure of the quoted price',
    'op365_invitationid': 'Supplier invitation the quote belongs to',
    'op365_requestlineid': 'Purchase request line being quoted',
  },
  'op365_purchaseorder': {
    'op365_number': 'Purchase order number, assigned automatically (PO-00001)',
    'op365_orderdate': 'Date of the order',
    'op365_expecteddelivery': 'Delivery date expected from the supplier',
    'op365_deliveryplace': 'Where the goods must be delivered',
    'op365_paymentterms': 'Payment terms of the order',
    'op365_notes': 'Notes printed on the order',
    'op365_sentto': 'Email address the order was sent to',
    'op365_senton': 'When the order was sent to the supplier',
    'op365_supplierconfirmed': 'Yes when the supplier confirmed the order',
    'op365_confirmedon': 'When the supplier confirmed the order',
    'op365_receivedon': 'When all the goods were received',
    'op365_cancelledon': 'When the order was cancelled',
    'op365_projectid': 'Project the order is for',
    'op365_supplierid': 'Supplier the order is placed with',
    'op365_purchaserequestid': 'Purchase request the order comes from',
  },
  'op365_purchaseorderline': {
    'op365_name': 'Description of the ordered item',
    'op365_quantity': 'Ordered quantity',
    'op365_uom': 'Unit of measure of the quantity',
    'op365_price': 'Agreed unit price',
    'op365_sortorder': 'Position of the line in the order',
    'op365_notes': 'Free-text notes on the line',
    'op365_purchaseorderid': 'Purchase order the line belongs to',
    'op365_itemid': 'Ordered item; empty for a service or a free-text line',
    'op365_wbsnodeid': 'WBS node whose budget the line uses',
    'op365_requestlineid': 'Purchase request line the order line comes from',
  },
  'op365_goodsreceipt': {
    'op365_number': 'Goods receipt number, assigned automatically (GR-00001)',
    'op365_receiptdate': 'Date the goods arrived',
    'op365_deliverynotenumber': 'Number of the supplier delivery note (DDT)',
    'op365_deliverynotedate': 'Date of the supplier delivery note (DDT)',
    'op365_notes': 'Notes on the delivery, e.g. damaged goods',
    'op365_projectid': 'Project the goods are for',
    'op365_purchaseorderid': 'Purchase order the goods were delivered against',
  },
  'op365_goodsreceiptline': {
    'op365_name': 'Description of the received item, copied from the purchase order line',
    'op365_quantity': 'Quantity received',
    'op365_goodsreceiptid': 'Goods receipt the line belongs to',
    'op365_orderlineid': 'Purchase order line the quantity was received against',
  },
  'op365_supplierinvoice': {
    'op365_number': 'Internal number of the supplier invoice, assigned automatically (INV-00001)',
    'op365_invoicenumber': 'Number of the supplier invoice',
    'op365_invoicedate': 'Date of the supplier invoice',
    'op365_sellername': 'Seller name as written on the invoice',
    'op365_sellervatnumber': 'Seller VAT number as written on the invoice',
    'op365_deliverynoterefs': 'Delivery notes (DDT) quoted on the invoice',
    'op365_orderrefs': 'Purchase orders quoted on the invoice',
    'op365_decidedon': 'When the invoice was approved or rejected',
    'op365_decisionnote': 'Reason given by the approver, required when rejecting',
    'op365_supplierid': 'Supplier who issued the invoice',
    'op365_purchaseorderid': 'Purchase order the invoice refers to',
    'op365_projectid': 'Project the invoice is charged to',
    'op365_decidedbyid': 'User who approved or rejected the invoice',
  },
  'op365_supplierinvoiceline': {
    'op365_name': 'Description of the invoiced goods or service',
    'op365_linenumber': 'Line number on the invoice',
    'op365_code': 'Item code as written on the invoice',
    'op365_quantity': 'Invoiced quantity',
    'op365_uom': 'Unit of measure of the quantity',
    'op365_unitprice': 'Invoiced unit price',
    'op365_vatrate': 'VAT rate of the line in percent',
    'op365_supplierinvoiceid': 'Supplier invoice the line belongs to',
    'op365_orderlineid': 'Purchase order line the invoice line refers to',
  },
}


def descriptions():
    hdr = {'MSCRM.MergeLabels': 'true'}
    for table, cols in DESCRIPTIONS.items():
        for col, desc in cols.items():
            url = API + f"EntityDefinitions(LogicalName='{table}')/Attributes(LogicalName='{col}')"
            r = S.get(url)
            if r.status_code >= 300:
                ok(r, f'read {table}.{col}')
            a = r.json()
            current = ((a.get('Description') or {}).get('UserLocalizedLabel') or {}).get('Label') or ''
            if current == desc:
                print('skip', table, col); continue
            a['Description'] = L(desc)
            for k in [k for k in a if k.startswith('@odata.') and k != '@odata.type']:
                a.pop(k)
            ok(S.put(url, json=a, headers=hdr), f'description {table}.{col}')


def search_index():
    # without it the semantic model knows the tables but Copilot finds no records
    for table in DESCRIPTIONS:
        if table in NOT_INDEXED:
            continue
        url = API + f"EntityDefinitions(LogicalName='{table}')"
        e = S.get(url).json()
        if e.get('SyncToExternalSearchIndex'):
            print('skip search', table); continue
        e['SyncToExternalSearchIndex'] = True
        for k in [k for k in e if k.startswith('@odata.') and k != '@odata.type']:
            e.pop(k)
        ok(S.put(url, json=e, headers={'MSCRM.MergeLabels': 'true'}), 'search ' + table)


def copilot_on_app():
    # app setting behind "Microsoft Copilot in model-driven apps" (app designer > Settings > Features);
    # turning it on makes Dataverse index the app tables and provision the app semantic model
    definition = S.get(API + "settingdefinitions?$select=settingdefinitionid&$filter=uniquename eq 'm365copilotmodelappenabled'").json()['value']
    if not definition:
        print('skip Copilot app setting (not available in this environment)'); return
    definition = definition[0]['settingdefinitionid']
    app_id = S.get(API + f"appmodules?$select=appmoduleid&$filter=uniquename eq '{APP}'").json()['value'][0]['appmoduleid']
    current = S.get(API + f"appsettings?$select=appsettingid,value&$filter=_parentappmoduleid_value eq {app_id} "
                    f"and _settingdefinitionid_value eq {definition}").json()['value']
    if not current:
        ok(S.post(API + 'appsettings', json={
            'value': '2', 'uniquename': f'{APP}_m365copilotmodelappenabled',
            'parentappmoduleid@odata.bind': f'/appmodules({app_id})',
            'settingdefinitionid@odata.bind': f'/settingdefinitions({definition})'}), 'Copilot on the app')
    elif current[0]['value'] != '2':
        ok(S.patch(API + f"appsettings({current[0]['appsettingid']})", json={'value': '2'}), 'Copilot on the app')
    else:
        print('skip Copilot on the app')
    ok(S.post(API + 'PublishXml', json={'ParameterXml': f'<importexportxml><appmodules><appmodule>{app_id}</appmodule></appmodules></importexportxml>'}), 'publish app')


def read_skill(path):
    text = open(path, encoding='utf-8').read()
    m = re.match(r'---\n(.*?)\n---\n(.*)', text, re.S)
    meta = dict(re.findall(r'^(\w+):\s*(.+)$', m.group(1), re.M))
    return meta, m.group(2).strip()


def skills():
    folder = os.path.join(ROOT, 'copilot', 'skills')
    for f in sorted(os.listdir(folder)):
        if not f.endswith('.md'):
            continue
        meta, body = read_skill(os.path.join(folder, f))
        uname = f[:-3]
        record = {'uniquename': uname, 'name': meta['name'], 'description': meta['description'],
                  'body': body, 'ispersonal': False}
        found = S.get(API + f"skills?$select=skillid,name,description,body,ispersonal&$filter=uniquename eq '{uname}'").json()['value']
        if not found:
            ok(S.post(API + 'skills', json=record), 'skill ' + uname)
            found = S.get(API + f"skills?$select=skillid&$filter=uniquename eq '{uname}'").json()['value']
        elif any(found[0].get(k) != v for k, v in record.items() if k != 'uniquename'):
            record.pop('uniquename')
            ok(S.patch(API + f"skills({found[0]['skillid']})", json=record), 'skill ' + uname)
        else:
            print('skip skill', uname)
        # records are not added to the solution by the MSCRM.SolutionUniqueName header
        ok(S.post(API + 'AddSolutionComponent', json={'ComponentId': found[0]['skillid'], 'ComponentType': SKILL_COMPONENT,
                                                      'SolutionUniqueName': 'OpenProject365', 'AddRequiredComponents': False}),
           'skill in solution ' + uname)


def read_glossary():
    # rows of the table in copilot/glossary.md: Term | Italiano | Français | Deutsch | Definition
    text = open(os.path.join(ROOT, 'copilot', 'glossary.md'), encoding='utf-8').read()
    rows = [[c.strip() for c in line.strip().strip('|').split('|')] for line in text.splitlines() if line.startswith('|')]
    return [dict(zip(('term', 'it', 'fr', 'de', 'definition'), r)) for r in rows[2:]]


def glossary():
    # glossary entries of the app semantic model (copilotglossaryterm, lookup skill = the model);
    # the semantic model has no ALM yet, so the entries are written in every environment
    models = S.get(API + f"dvtablesearchs?$select=dvtablesearchid,name&$filter=appmoduleuniquename eq '{APP}' "
                   "and startswith(name,'M365_')").json()['value']
    if not models:
        print('skip glossary (no semantic model yet: turn on Copilot on the app and wait for the generation)'); return
    model = models[0]['dvtablesearchid']
    # glossary terms are solution components that point to this environment's model: keep them out of the
    # solution (the default MSCRM.SolutionUniqueName header would add them and deploy-dev would see drift)
    plain = {'MSCRM.SolutionUniqueName': None}
    for row in read_glossary():
        description = (f"{row['definition']} Synonyms: Italian {row['it']}; French {row['fr']}; German {row['de']}.")[:1000]
        record = {'term': row['term'], 'name': row['term'], 'description': description}
        found = S.get(API + f"copilotglossaryterms?$select=copilotglossarytermid,name,description&$filter=term eq '{row['term']}' "
                      f"and _skill_value eq {model}").json()['value']
        if not found:
            record['skill@odata.bind'] = f'/dvtablesearchs({model})'
            ok(S.post(API + 'copilotglossaryterms', json=record, headers=plain), 'glossary ' + row['term'])
        elif found[0]['description'] != description or found[0]['name'] != row['term']:
            ok(S.patch(API + f"copilotglossaryterms({found[0]['copilotglossarytermid']})", json=record, headers=plain), 'glossary ' + row['term'])
        else:
            print('skip glossary', row['term'])
    print('glossary written to', models[0]['name'], '- select Regenerate on the semantic model to use it now')


if __name__ == '__main__' and 'glossary' in sys.argv:
    glossary()
elif __name__ == '__main__':
    descriptions()
    search_index()
    ok(S.post(API + 'PublishAllXml', json={}), 'publish')
    copilot_on_app()
    skills()
    glossary()
