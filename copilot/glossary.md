# Semantic model glossary

Business terms of ProjectIQ for the Dataverse semantic model (Power Apps → **Semantic model** → `M365_Primary_model_op365_OpenProject365` → **Glossary**).
The semantic model has no ALM support yet: `python3 tools/dataverse/workiq.py glossary` writes this table into the semantic model of each environment (one entry per row, synonyms in the definition), then select **Regenerate** (see [Copilot and Cowork](../docs/en/copilot.md#semantic-model-glossary)). Keep the column order: the script reads it.

Users ask Copilot in their own language, so every term lists as synonyms the words used in Italian, French and German: first the name the app shows in that language, then the everyday business words.

| Term | Italiano | Français | Deutsch | Definition |
|---|---|---|---|---|
| Project | commessa, progetto, job | projet, affaire | Projekt, Auftrag | A customer project: a row of the Project table (op365_project). Its Code (op365_code) looks like PRJ-000123. |
| WBS node | nodo WBS, WBS, fase, attività, task | nœud WBS, WBS, phase, activité, tâche | PSP-Element, PSP, Phase, Vorgang, Aufgabe | Element of the work breakdown structure of a project (op365_wbsnode). Top-level nodes (no Parent Node) are phases. |
| Time entry | registrazione ore, ore, ore lavorate, rapportino, timesheet, consuntivo ore | saisie de temps, heures, feuille de temps | Zeiteintrag, Stunden, Stundenzettel, Zeiterfassung | Hours of a resource on a project and WBS node on a day (op365_timeentry). Only Approved hours count in Actual Hours and Actual Cost. |
| Actual cost | costo effettivo, consuntivo, costo consuntivo, costi sostenuti | coût réel, coûts engagés réalisés | Istkosten, tatsächliche Kosten | Project or WBS node Actual Cost (op365_actualcost): approved hours x hourly cost plus material usage. |
| Committed cost | impegnato, costo impegnato | coût engagé, engagements | Obligo, gebundene Kosten | Project Committed Cost (op365_committedcost): quantity still to receive x price on the lines of open purchase orders. |
| Budget | preventivo, budget di commessa | budget, budget du projet | Budget, Projektbudget | Budget Total of the project or WBS node (op365_budgettotal): labour + materials + other. |
| Baseline | baseline, budget congelato, piano di riferimento | planning de référence, référence | Basisplan, Baseline | Snapshot of the WBS budget and dates (op365_baseline); the reference baseline has Is Reference = Yes. |
| Resource | risorsa, dipendente, tecnico | ressource, salarié, technicien | Ressource, Mitarbeiter, Techniker | Person whose hours are planned and tracked (op365_resource), with or without a user license. |
| Company closure | chiusura aziendale, ferie collettive | fermeture de l'entreprise, congés collectifs | Betriebsschließung, Betriebsferien | Absence (op365_absence) of type Closure with no Resource: nobody works on those days. |
| Purchase request | richiesta di acquisto, RdA, RDA, PR | demande d'achat, DA | Bestellanforderung, BANF | Request to buy for a project (op365_purchaserequest), approved by the project manager and, above the threshold, by the purchasing approver. |
| RFQ | richiesta di offerta, RdO, gara, request for quotation | demande de prix, appel d'offres, consultation | Angebotsanfrage, Ausschreibung, Anfrage | Request for quotation to suppliers (op365_rfq) with invitations (op365_rfqinvitation) and quoted prices (op365_rfqquote). |
| Purchase order | ordine di acquisto, OdA, ordine fornitore, PO | commande d'achat, bon de commande | Bestellung, Einkaufsbestellung | Order to a supplier for a project (op365_purchaseorder). |
| Goods receipt | ricevimento merci, entrata merce, DDT, bolla | réception de marchandises, bon de livraison, BL | Wareneingang, Lieferschein | Delivery received against a purchase order (op365_goodsreceipt); Delivery Note Number is the DDT number. |
| Supplier invoice | fattura fornitore, fattura passiva, FatturaPA | facture fournisseur, facture d'achat | Lieferantenrechnung, Eingangsrechnung | Invoice received from a supplier (op365_supplierinvoice), with the XML or PDF attached; statuses To Review, Approved, Rejected. |
| Supplier document | documento fornitore, DURC, certificazione, polizza | document fournisseur, attestation, certificat, assurance | Lieferantendokument, Nachweis, Zertifikat, Versicherung | Compliance document of a supplier with an expiry date (op365_supplierdocument). |
| Supplier | fornitore | fournisseur | Lieferant | Account with Is Supplier = Yes (op365_issupplier). Supplier Status Blocked means it must not be used. |
| Customer | cliente | client | Kunde | Account with Is Customer = Yes (op365_iscustomer). |
| Project manager | capo commessa, PM, responsabile di commessa | chef de projet | Projektleiter | User in Project Manager (op365_projectmanagerid) of the project. |
| Project member | membro commessa, team di commessa | membre du projet, équipe projet | Projektmitglied, Projektteam | User working on a project (op365_projectmember), with the role Manager, Contributor or Reader; the role decides the access to the project records. |
| WBS allocation | allocazione WBS, ore pianificate, pianificazione | affectation WBS, heures planifiées | PSP-Zuordnung, Planstunden | Planned hours of a resource on a WBS node (op365_wbsallocation); used for resource load. |
| Absence | assenza, ferie, permesso, malattia | absence, congé, maladie | Abwesenheit, Urlaub, Krankheit | Absence of a resource (op365_absence): Vacation, Leave or Sickness; with type Closure and no Resource it is a company closure. |
| Item | articolo, materiale, codice articolo | article, matériel, code article | Artikel, Material, Artikelnummer | Purchased or consumed article (op365_item), identified by its Code (op365_code). |
| Material usage | consumi materiale, scarico materiale, materiale consumato | consommation de matériel, sortie de matériel | Materialverbrauch, Materialentnahme | Material consumed by a project (op365_materialusage); its cost counts in Actual Cost. |
