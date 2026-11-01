"""Purchasing commands as classic ribbon buttons (form command bar), written into the unpacked solution.

Classic enable rules on statuscode show each button only in the statuses where its Custom API applies (modern
commands have no status-based visibility without a Power Fx component library). Run after exporting/unpacking Dev
into solutions/OpenProject365/src, then pack and import the solution into Dev:

    python tools/dataverse/ribbon.py
    pac solution pack --zipfile out/OpenProject365.zip --folder solutions/OpenProject365/src --packagetype Unmanaged
    pac solution import --path out/OpenProject365.zip --publish-changes
"""
import os
from xml.sax.saxutils import quoteattr

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'solutions', 'OpenProject365', 'src', 'Entities'))
LIBRARY = '$webresource:op365_/scripts/purchasing.js'
S = 365000000

# entity folder, logical name, buttons: (id, label, tooltip, icon, function, statuses where enabled)
COMMANDS = [
    ('op365_PurchaseRequest', 'op365_purchaserequest', [
        ('Submit', 'Submit', 'Send the request to the project manager for approval', 'Send', 'submitRequest', [1, S + 2]),
        ('Approve', 'Approve', 'Approve the request (above the threshold it goes to the purchasing approver)', 'Accept', 'approveRequest', [S]),
        ('Reject', 'Reject', 'Reject the request with a note', 'Cancel', 'rejectRequest', [S]),
        ('CreateRfq', 'Create RFQ', 'Ask suppliers for quotations', 'New', 'createRfq', [S + 1]),
        ('CreateOrder', 'Create Order', 'Create a purchase order to the preferred supplier', 'New', 'createOrder', [S + 1]),
        ('CancelRequest', 'Cancel Request', 'Cancel the request', 'Close', 'cancelRequest', [1, S, S + 1, S + 2]),
    ]),
    ('op365_Rfq', 'op365_rfq', [
        ('Send', 'Send', 'Invite the suppliers to quote', 'Send', 'sendRfq', [1, S]),
        ('CancelRfq', 'Cancel RFQ', 'Cancel the request for quotation', 'Close', 'cancelRfq', [1, S]),
    ]),
    ('op365_PurchaseOrder', 'op365_purchaseorder', [
        ('SendOrder', 'Send to Supplier', 'Mark the order as sent: its lines can no longer change', 'Send', 'sendOrder', [1]),
        ('ConfirmOrder', 'Confirm', 'Record the supplier confirmation', 'Accept', 'confirmOrder', [S]),
        ('RegisterReceipt', 'Register Receipt', 'Register the goods received and their material usage', 'Add', 'registerReceipt', [S, S + 1]),
        ('ReopenOrder', 'Back to Draft', 'Move the order back to Draft to change it', 'Edit', 'reopenOrder', [S]),
        ('CancelOrder', 'Cancel Order', 'Cancel the order', 'Close', 'cancelOrder', [1, S, S + 1]),
    ]),
    ('op365_GoodsReceipt', 'op365_goodsreceipt', [
        ('CancelReceipt', 'Cancel Receipt', 'Delete the receipt and its material usage', 'Delete', 'cancelReceipt', None),
    ]),
    ('op365_SupplierInvoice', 'op365_supplierinvoice', [
        ('ApproveInvoice', 'Approve', 'Approve the invoice', 'Accept', 'approveInvoice', [1]),
        ('RejectInvoice', 'Reject', 'Reject the invoice with a note', 'Cancel', 'rejectInvoice', [1]),
    ]),
    ('op365_SupplierDocument', 'op365_supplierdocument', [
        ('ApproveDocument', 'Approve', 'Approve the document: it becomes valid', 'Accept', 'approveDocument', [S]),
        ('RejectDocument', 'Reject', 'Reject the document with a note for the supplier', 'Cancel', 'rejectDocument', [S]),
    ]),
]


def ribbon(table, buttons):
    short = table.replace('op365_', '')
    existing = f'op365.{short}.Existing'
    actions, commands, enables, labels = [], [], [], []
    for seq, (bid, label, tip, icon, function, statuses) in enumerate(buttons):
        base = f'op365.{short}.{bid}'
        actions.append(
            f'<CustomAction Id="{base}.CustomAction" Location="Mscrm.Form.{table}.MainTab.Save.Controls._children" Sequence="{5 + seq}">'
            f'<CommandUIDefinition><Button Id="{base}.Button" Command="{base}.Command" LabelText="$LocLabels:{base}.Label" '
            f'ToolTipTitle="$LocLabels:{base}.Label" ToolTipDescription="$LocLabels:{base}.Tip" TemplateAlias="o1" ModernImage="{icon}" />'
            '</CommandUIDefinition></CustomAction>')
        enable = f'<EnableRules><EnableRule Id="{base}.Enable" /></EnableRules>' if statuses else '<EnableRules />'
        commands.append(
            f'<CommandDefinition Id="{base}.Command">{enable}<DisplayRules><DisplayRule Id="{existing}" /></DisplayRules>'
            f'<Actions><JavaScriptFunction Library="{LIBRARY}" FunctionName="OP365.Purchasing.{function}">'
            '<CrmParameter Value="PrimaryControl" /></JavaScriptFunction></Actions></CommandDefinition>')
        if statuses:
            ors = ''.join(f'<Or><ValueRule Field="statuscode" Value="{v}" /></Or>' for v in statuses)
            enables.append(f'<EnableRule Id="{base}.Enable"><OrRule>{ors}</OrRule></EnableRule>')
        for suffix, text in (('Label', label), ('Tip', tip)):
            labels.append(f'<LocLabel Id="{base}.{suffix}"><Titles><Title description={quoteattr(text)} languagecode="1033" /></Titles></LocLabel>')
    return ('<?xml version="1.0" encoding="utf-8"?>\n<RibbonDiffXml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<CustomActions>{"".join(actions)}</CustomActions>'
            '<Templates><RibbonTemplates Id="Mscrm.Templates"></RibbonTemplates></Templates>'
            f'<CommandDefinitions>{"".join(commands)}</CommandDefinitions>'
            '<RuleDefinitions><TabDisplayRules />'
            f'<DisplayRules><DisplayRule Id="{existing}"><FormStateRule State="Create" InvertResult="true" /></DisplayRule></DisplayRules>'
            f'<EnableRules>{"".join(enables)}</EnableRules></RuleDefinitions>'
            f'<LocLabels>{"".join(labels)}</LocLabels></RibbonDiffXml>\n')


for folder, table, buttons in COMMANDS:
    path = os.path.join(ROOT, folder, 'RibbonDiff.xml')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(ribbon(table, buttons))
    print('ok  ', path)
