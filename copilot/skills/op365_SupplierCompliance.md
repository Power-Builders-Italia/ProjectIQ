---
name: Open Project 365 - Supplier compliance
description: Read-only check of supplier compliance documents (DURC, certifications, insurance) in Open Project 365. Use when the user asks which suppliers have expired or expiring documents, or whether a supplier can be used.
---
# Supplier compliance (read-only)

Use this skill for "suppliers with expired DURC", "fornitori con documenti in scadenza", "can we order from supplier X".

## Steps
1. Suppliers are `account` rows with `op365_issupplier` = Yes. `op365_supplierstatus` is Active or Blocked; `op365_expireddocs` and `op365_expiringdocs` are updated every day by a flow.
2. For the details read `op365_supplierdocument` of the supplier (`op365_supplierid`): `op365_description`, `op365_number`, `op365_issuedate`, `op365_expirydate`.
   - Expired: `op365_expirydate` before today.
   - Expiring: `op365_expirydate` within the next 30 days.
3. For "can we order from X": the supplier must be Active and have no expired documents. Also show open purchase orders with the supplier (`op365_purchaseorder` in Draft, Sent or Confirmed).

## Output
A table of suppliers with expired and expiring documents (document, number, expiry date, days left), sorted by expiry date. Blocked suppliers are listed separately.

## Rules
- Read-only: to upload a renewed document, the user opens the supplier in the Open Project 365 app, or the supplier uses the supplier portal.
