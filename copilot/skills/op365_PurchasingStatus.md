---
name: ProjectIQ - Purchasing status
description: Read-only view of the purchasing cycle in ProjectIQ (purchase requests, RFQs, purchase orders, goods receipts, supplier invoices). Use when the user asks where a purchase is, what is waiting for approval, late deliveries, or invoices to review.
---
# Purchasing status (read-only)

The cycle is: purchase request (RdA) > RFQ (RdO, optional) > purchase order (OdA) > goods receipt (entrata merce, DDT) > supplier invoice (fattura passiva).
Copilot cannot submit, approve, send, award, receive or cancel anything: these steps run only from the buttons of the ProjectIQ app.

## Status values
| Table | Status reasons (`statuscode`) |
|---|---|
| `op365_purchaserequest` | 1 Draft, 365000000 Submitted, 365000001 Approved, 365000002 Rejected, 365000003 Cancelled, 365000004 Ordered |
| `op365_rfq` | 1 Draft, 365000000 Sent, 365000001 Awarded, 365000002 Cancelled |
| `op365_rfqinvitation` | 1 To Invite, 365000000 Invited, 365000001 Responded, 365000002 Declined |
| `op365_purchaseorder` | 1 Draft, 365000000 Sent, 365000001 Confirmed, 365000002 Received, 365000003 Cancelled |
| `op365_supplierinvoice` | 1 To Review, 365000000 Approved, 365000001 Rejected |

## Typical questions and how to answer
1. **Where is purchase X?** Find the purchase request by `op365_title` or project, then follow the links: RFQ (`op365_rfq.op365_purchaserequestid`), purchase order (`op365_purchaseorder.op365_purchaserequestid`), goods receipts (`op365_goodsreceipt.op365_purchaseorderid`), invoices (`op365_supplierinvoice.op365_purchaseorderid`). Show the chain with the status of each step.
2. **What is waiting for my approval?** Purchase requests in Submitted with `op365_currentapproverid` = the user. Show `op365_estimatedamount`, `op365_overbudget`, `op365_abovethreshold`, `op365_neededby`.
3. **Late deliveries?** Purchase orders in Sent or Confirmed with `op365_expecteddelivery` before today. Show supplier, `op365_totalamount`, `op365_receivedamount`.
4. **RFQs to close?** RFQs in Sent whose `op365_deadline` is past: show `op365_responsecount` and the quoted amount of each invitation (`op365_quotedamount`).
5. **Invoices to review?** Supplier invoices in To Review: show supplier, `op365_invoicenumber`, `op365_invoicedate`, `op365_totalamount`, and whether the linked order is Received.

## Rules
- Over Budget means actual + committed + this request exceed the budget; Above Threshold means the request needs the purchasing approver (environment variable `op365_PurchasingApprover`).
- Amounts protected by column security (Spend) may be empty for the user: say so.
