"""Phase 1 main forms: Customer and Supplier forms on Account, main forms of the F1 tables.

Forms are generated from a compact layout description. Existing forms (matched by table + name)
are overwritten; the generated 'Information' form of each custom table is renamed and replaced.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API
from formlib import ok, section, tab, form, webresource, onload

ACCOUNT_JS = 'op365_/scripts/account.form.js'

A = 'account'
webresource(ACCOUNT_JS, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'webresources', 'account.form.js'),
            'Account form script')
ADDRESS = ['address1_line1', 'address1_city', 'address1_postalcode', 'address1_stateorprovince', 'address1_country']
form(A, 'Customer', [
    tab('Summary', [
        ('60%', [section(A, 'Customer', ['name', 'op365_iscustomer', 'op365_customertype', 'op365_vatnumber',
                                         'op365_taxcode', 'primarycontactid', 'telephone1', 'emailaddress1',
                                         'websiteurl', 'ownerid']),
                 section(A, 'Address', ADDRESS),
                 section(A, 'Billing', ['op365_paymentterms', 'op365_iban', 'op365_pec', 'op365_language'])]),
        ('40%', [section(A, 'Timeline', [('timeline',)])])]),
    tab('Contacts', [('100%', [section(A, 'Contacts', [('subgrid', 'Contacts', 'Contacts', 'contact', 'contact_customer_accounts')])])]),
], description='Account as customer (ProjectIQ)', extra=onload(ACCOUNT_JS, 'OP365.Account.onLoad'))

form(A, 'Supplier', [
    tab('Summary', [
        ('60%', [section(A, 'Supplier', ['name', 'op365_issupplier', 'op365_supplierstatus', 'op365_suppliercategory',
                                         'op365_vatnumber', 'op365_taxcode', 'primarycontactid', 'telephone1',
                                         'emailaddress1', 'ownerid']),
                 section(A, 'Address', ADDRESS),
                 section(A, 'Payment', ['op365_paymentterms', 'op365_iban', 'op365_pec', 'op365_language'])]),
        ('40%', [section(A, 'Timeline', [('timeline',)])])]),
    tab('Documents', [('100%', [
        section(A, 'Document Alerts', ['op365_expireddocs', 'op365_expiringdocs']),
        section(A, 'Documents', [('subgrid', 'Documents', 'Documents', 'op365_supplierdocument', 'op365_account_supplierdocument_supplierid')])])]),
    tab('Item Prices', [('100%', [section(A, 'Item Prices', [('subgrid', 'ItemPrices', 'Item Prices', 'op365_itemsupplier', 'op365_account_itemsupplier_supplierid')])])]),
    tab('Contacts', [('100%', [section(A, 'Contacts', [('subgrid', 'Contacts', 'Contacts', 'contact', 'contact_customer_accounts')])])]),
], description='Account as supplier (ProjectIQ)', extra=onload(ACCOUNT_JS, 'OP365.Account.onLoad'))

T = 'op365_item'
form(T, 'Item', [
    tab('General', [
        ('60%', [section(T, 'Item', ['op365_code', 'op365_name', 'op365_category', 'op365_uom', 'op365_unitcost',
                                     'op365_defaultsupplierid', 'ownerid']),
                 section(T, 'Notes', ['op365_notes'], columns=1),
                 section(T, 'Suppliers', [('subgrid', 'Suppliers', 'Suppliers', 'op365_itemsupplier', 'op365_item_itemsupplier_itemid')])]),
        ('40%', [section(T, 'Timeline', [('timeline',)])])]),
], replace='Information')

T = 'op365_itemsupplier'
form(T, 'Item Supplier', [tab('General', [('100%', [
    section(T, 'Item Supplier', ['op365_itemid', 'op365_supplierid', 'op365_name', 'op365_suppliercode',
                                 'op365_price', 'op365_leadtimedays', 'op365_minimumlot', 'ownerid']),
    section(T, 'Notes', ['op365_notes'], columns=1)])])], replace='Information')

T = 'op365_supplierdocument'
form(T, 'Supplier Document', [tab('General', [
    ('60%', [section(T, 'Document', ['op365_supplierid', 'op365_documenttype', 'op365_description', 'op365_number',
                                     'op365_issuedate', 'op365_expirydate', 'op365_externalurl', 'ownerid']),
             section(T, 'File', ['op365_file'], columns=1),
             section(T, 'Notes', ['op365_notes'], columns=1)]),
    ('40%', [section(T, 'Timeline', [('timeline',)])])])], replace='Information')

T = 'op365_resource'
form(T, 'Resource', [
    tab('General', [('100%', [
        section(T, 'Resource', ['op365_name', 'op365_role', 'op365_userid', 'ownerid']),
        section(T, 'Capacity and Cost', ['op365_weeklyhours', 'op365_hourlycost', 'op365_workingdays'])])]),
    tab('Costs', [('100%', [section(T, 'Hourly Costs', [('subgrid', 'Costs', 'Hourly Costs', 'op365_resourcecost', 'op365_resource_resourcecost_resourceid')])])]),
    tab('Absences', [('100%', [section(T, 'Absences', [('subgrid', 'Absences', 'Absences', 'op365_absence', 'op365_resource_absence_resourceid')])])]),
], replace='Information')

T = 'op365_resourcecost'
form(T, 'Resource Cost', [tab('General', [('100%', [
    section(T, 'Resource Cost', ['op365_resourceid', 'op365_validfrom', 'op365_hourlycost', 'op365_name', 'ownerid'])])])],
    replace='Information')

T = 'op365_absence'
form(T, 'Absence', [tab('General', [('100%', [
    section(T, 'Absence', ['op365_resourceid', 'op365_absencetype', 'op365_fromdate', 'op365_todate',
                           'op365_hours', 'op365_name', 'ownerid']),
    section(T, 'Notes', ['op365_notes'], columns=1)])])], replace='Information')

ok(S.post(API + 'PublishAllXml', json={}), 'publish')
