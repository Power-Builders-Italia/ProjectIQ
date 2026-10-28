# Semantic model glossary

Business terms of ProjectIQ for the Dataverse semantic model (Power Apps → **Semantic model** → `M365_Primary_model_op365_OpenProject365` → **Glossary** → **Add item**).
The glossary has no solution support: enter these entries in every environment, then select **Regenerate** (see [Copilot and Cowork](../docs/en/copilot.md#semantic-model-glossary)).

The app is in English and most users write in Italian, so every term lists the Italian words as synonyms.

| Term | Synonyms | Definition |
|---|---|---|
| Project | commessa, progetto, job | A customer project: a row of the Project table (op365_project). Its Code (op365_code) looks like PRJ-000123. |
| WBS node | WBS, fase, attività, task | Element of the work breakdown structure of a project (op365_wbsnode). Top-level nodes (no Parent Node) are phases. |
| Time entry | ore, ore lavorate, rapportino, timesheet, consuntivo ore | Hours of a resource on a project and WBS node on a day (op365_timeentry). Only Approved hours count in Actual Hours and Actual Cost. |
| Actual cost | consuntivo, costo consuntivo, costi sostenuti | Project or WBS node Actual Cost (op365_actualcost): approved hours x hourly cost plus material usage. |
| Committed cost | impegnato, costo impegnato | Project Committed Cost (op365_committedcost): quantity still to receive x price on the lines of open purchase orders. |
| Budget | preventivo, budget di commessa | Budget Total of the project or WBS node (op365_budgettotal): labour + materials + other. |
| Baseline | baseline, budget congelato, piano di riferimento | Snapshot of the WBS budget and dates (op365_baseline); the reference baseline has Is Reference = Yes. |
| Resource | risorsa, dipendente, tecnico | Person whose hours are planned and tracked (op365_resource), with or without a user license. |
| Company closure | chiusura aziendale, ferie collettive | Absence (op365_absence) of type Closure with no Resource: nobody works on those days. |
| Purchase request | RdA, richiesta di acquisto, PR | Request to buy for a project (op365_purchaserequest), approved by the project manager and, above the threshold, by the purchasing approver. |
| RFQ | RdO, richiesta di offerta, gara, request for quotation | Request for quotation to suppliers (op365_rfq) with invitations (op365_rfqinvitation) and quoted prices (op365_rfqquote). |
| Purchase order | OdA, ordine fornitore, ordine di acquisto, PO | Order to a supplier for a project (op365_purchaseorder). |
| Goods receipt | entrata merce, ricevimento merce, DDT, bolla | Delivery received against a purchase order (op365_goodsreceipt); Delivery Note Number is the DDT number. |
| Supplier invoice | fattura passiva, fattura fornitore, FatturaPA | Invoice received from a supplier (op365_supplierinvoice), with the XML or PDF attached; statuses To Review, Approved, Rejected. |
| Supplier document | DURC, documento fornitore, certificazione, polizza | Compliance document of a supplier with an expiry date (op365_supplierdocument). |
| Supplier | fornitore | Account with Is Supplier = Yes (op365_issupplier). Supplier Status Blocked means it must not be used. |
| Customer | cliente | Account with Is Customer = Yes (op365_iscustomer). |
| Project manager | PM, capo commessa, responsabile di commessa | User in Project Manager (op365_projectmanagerid) of the project. |
