# Supplier portal

> **Language:** English · [Italiano](../it/supplier-portal.md) · [Français](../fr/supplier-portal.md) · [Deutsch](../de/supplier-portal.md)
> **Manual index:** [README](../../README.md#user-manuals)

The **supplier portal** is a website, built with Microsoft Power Pages on the same Dataverse database as ProjectIQ, where your suppliers can work with you without emails and spreadsheets going back and forth. On the portal a supplier:

- finds on a **dashboard** what you are waiting for: RFQs to quote, orders to confirm, documents to renew;
- sees the **requests for quotation** (RFQs) you sent them, types **unit prices**, **delivery days** and **notes**, and sends the quote — or declines;
- sees the **purchase orders** you sent them, with lines and amounts, and **confirms** them;
- sees how much of each order has already been **received**, the **projects** of its orders and the status of its **invoices**;
- uploads its **company documents** (DURC, certifications, insurance), which your buyer approves, and is warned when they expire.

Everything the supplier does is immediately visible in ProjectIQ: quotes appear in the Quote Comparison of the RFQ, confirmations change the order status, uploaded documents wait for your review.

This manual has two parts: **Part 1 for suppliers** (you can send it to them) and **Part 2 for your internal staff**, who give suppliers access and follow their answers.

```mermaid
sequenceDiagram
    participant B as Buyer (ProjectIQ)
    participant DV as Dataverse
    participant S as Supplier (portal)
    B->>DV: Send RFQ (invitation + empty quote lines)
    S->>DV: Requests for quotation → Open → prices, delivery days → Send quote
    DV-->>B: Invitation Responded, Quote Comparison updated
    B->>DV: Award → purchase order → Send to Supplier
    S->>DV: Purchase orders → Open → Confirm order
    DV-->>B: Order Confirmed
    B->>DV: Register Receipt
    S->>DV: Sees Received quantities
    S->>DV: Documents → Upload document (DURC...)
    B->>DV: Approve or Reject
    DV-->>S: Expiry e-mail and alert on the Dashboard
```

## Part 1 — Guide for suppliers

### Signing in

Your customer gives you access to its supplier portal. You receive the portal address (for example `https://<customer>-suppliers.powerappsportals.com`) and the instructions to create or activate your account. Use the email address your customer registered for you.

1. Open the portal address and click **Sign in**.
2. Sign in with your account.
3. Open **Dashboard**. On the left, the sidebar shows the modules: **Dashboard**, **Projects**, **Requests for quotation**, **Purchase orders**, **Invoices** and **Documents**. A blue counter shows the RFQs to quote and the orders to confirm; an orange counter shows the documents to renew or correct. At the bottom you find your company, your name and **Sign out**.

If a page says "This area is reserved to suppliers. Sign in with the account your customer invited.", you are not signed in, or your account has not been enabled as supplier yet: contact your customer.

You see only the data **of your company**. Colleagues of your company with their own account see the same data.

### The dashboard

The **Dashboard** is the start page:

| Part | What it shows |
|---|---|
| Counters | **Requests to quote**, **Orders to confirm**, the amount **Ordered** in the current year (confirmed and received orders) and the **Invoices under review** |
| **Document compliance** | A ring with the share of your approved documents that are valid (green), expiring within 30 days (orange) and expired (red), plus how many wait for review or were rejected |
| **To do** | One line per thing your customer is waiting for: expired documents to renew, rejected documents to correct, RFQs to quote (with the deadline), orders to confirm, documents expiring soon. Click a line to open the page where you do it |
| **Your projects** | The first project cards (see below), with **All projects** for the complete list |

### Projects

**Projects** shows one card for each project of your purchase orders: code and name, **Project progress**, **Your deliveries** (the share of your ordered amount already received), the number of **Orders**, the **Ordered** amount and the **End date** of the project. A project with an order to confirm has an orange border. **See orders** opens the purchase orders.

### Answering a request for quotation

1. Click **Requests for quotation**. Each RFQ is a card with the invitation date, the number, the subject, the **Quoted** amount once you have answered and a bar showing how much time is left before the **Deadline** (it turns orange and then red as the deadline gets close). The buttons at the top filter the cards: **All**, **To quote**, **Quoted**, **Closed**.

| Card badge | Meaning |
|---|---|
| **To quote** | Waiting for your quote (orange border) |
| **Quoted** | You sent a quote (you can still change it until the deadline) |
| **Declined** / **Closed** | You declined, or the deadline has passed |

2. Click **Quote now** (or **Change quote**, **Open**) on the card. You see the RFQ number, the deadline, your customer's notes and the list of items with quantity and unit.
3. For each line type the **Unit price** and, if needed, **Notes** (brand, alternative product, conditions...).
4. Type the **Delivery days** (how many days after the order you can deliver) and any **Notes for the buyer**.
5. Click **Send quote**. A green message confirms: "Your quote has been sent. You can change it until the deadline."

Good to know:

- You can leave a line without price if you do not supply that item: "Lines without a price are not quoted." Quoting every line gives you a better chance, because the best total is calculated only among suppliers who quoted all the lines.
- You can come back and **change prices until the deadline**. After the deadline (or after declining) the fields are read-only.
- If you cannot quote, click **Decline** and confirm. The RFQ is marked Declined.
- The **Quoted** amount in the list is quantity × unit price over all your lines.

### Confirming a purchase order

1. Click **Purchase orders**. Each order is a card with project, order date, number and total. Orders waiting for your confirmation are marked **To confirm** and show expected delivery, payment terms and delivery place; the others show a **Received** bar. The buttons at the top filter the cards: **All**, **To confirm**, **Confirmed**, **Received**.
2. Click **Review and confirm** (or **Open**). You see order date, expected delivery, **Delivery place**, **Payment terms**, status, and the lines with quantity, unit price, amount and the quantity already **Received**.
3. Check the order and click **Confirm order**, then confirm. The status becomes **Confirmed** with the confirmation date.

| Status shown | Meaning |
|---|---|
| **To confirm** | The order has been sent to you and waits for your confirmation |
| **Confirmed** | You (or the buyer on your behalf) confirmed it |
| **Received** | All the goods have been received by your customer |

If something in the order is wrong (price, quantity, date), do not confirm it: contact the buyer, who will correct the order and send it again.

### Invoices

**Invoices** shows the invoices your customer received from you: totals **Under review**, **Approved** in the current year and **Rejected**, then one card per invoice with order and project, number, amount, document type and dates. The steps **Received → Reviewed → Approved** (or **Rejected**, in red) show where the invoice is; a rejected invoice shows the **Reason**. The buttons at the top filter the cards. The portal does not receive invoices: send them as usual.

### Company documents

**Documents** lists the documents your customer needs from your company (DURC, company report, certifications, insurance, contracts) with **Number**, **Issued**, **Expires**, and two badges:

| Column | Badges |
|---|---|
| **Expiry** | **Valid**, **Expiring** (within 30 days), **Expired**, **Replaced** (a newer document of the same type was approved), **No expiry** |
| **Review** | **Pending review** (the buyer has not checked it yet), **Approved**, **Rejected** (with the reason) |

To upload a document:

1. Click **Upload document** (or scroll to the form at the bottom of the page).
2. Choose the **Type**, type a **Description** and, if any, **Number**, **Issue date**, **Expiry date** and **Notes**.
3. Choose the **File** (PDF or image, up to 32 MB) and click **Upload document**.

The document is **Pending review** until the buyer approves it. While it is pending or rejected you can click **Edit** (change the data or the file, then **Save changes**) or **Delete**. Correcting a rejected document sends it back to review. Once **Approved** a document can only be viewed: to renew it, upload a new document of the same type; when the buyer approves it, the old one becomes **Replaced**.

You receive an e-mail when an approved document is about to expire (30 days before) and when it expires; the Dashboard shows the same alerts.

### Errors

If an action fails, a red message explains why. Common cases: "Session expired: sign in again." (sign in and repeat), "The deadline of the request for quotation has passed." (contact the buyer to extend it), "The request for quotation is closed." (it was awarded or cancelled), "Approved documents cannot be changed." or "Approved documents cannot be deleted." (upload a new document instead), "Choose the file of the document." (a new document needs its file).

## Part 2 — Guide for internal staff

### What the portal exposes

The portal is deliberately narrow. Suppliers can read only their own records and can write only a few fields:

| Data | Supplier can read | Supplier can change |
|---|---|---|
| RFQ invitations of their company | Number, deadline, notes, status, quoted amount | **Delivery days**, **supplier notes**, **status** (only to Responded or Declined) |
| Quote lines of those invitations | Item, quantity, unit, price, notes | **Unit price**, **notes** |
| Purchase orders of their company (Sent, Confirmed, Received) | Header and amounts | **Supplier confirmed** (which confirms the order) |
| Lines of those orders | Item, quantity, price, amount, received quantity | Nothing |
| Projects of those orders | Code, name, progress, end date | Nothing |
| Supplier invoices of their company | Number, dates, amount, status, decision note | Nothing |
| Supplier documents of their company | All fields, including the review note | Type, description, number, dates, notes, file; can create and delete, only while the document is not approved |

Draft and cancelled orders and RFQs not yet sent are never shown. Prices of other suppliers are never visible.

### Giving a supplier access

A supplier user is a **contact** whose **company** is the supplier account, with the **Supplier** web role.

1. In ProjectIQ make sure the supplier account is **Is Supplier**, **Active** and not **Blocked**, and has a valid **Email**.
2. Create (or open) the **contact** of the person, with **Company Name** = the supplier and their email.
3. In **Power Pages Management** (or the portal studio, *Set up → Web roles*) assign the web role **Supplier** to the contact.
4. Let the person sign in with the method configured on your site (for example send an **invitation** from Power Pages Management → *Invitations*, or let them register with the email you recorded).
5. Send the person the address of the portal and [Part 1](#part-1--guide-for-suppliers) of this manual.

To remove access, remove the Supplier web role from the contact or deactivate the contact.

### Reviewing the documents

A document uploaded on the portal is **Pending Review** and the owner of the supplier account receives the notification "Supplier document to review". Open it from the notification, or from the view **Supplier Documents to Review**, check the file and click **Approve** or **Reject** (with a note the supplier will read). See [Master data](master-data.md#review). Expiry e-mails to suppliers need the setup described in [Administration](administration.md#daily-document-expiry).

### Following the answers

- In the RFQ, the **Invitations** list shows each supplier's status, **Responded On**, **Quoted Amount** and **Delivery Days**; the **Responses** counter shows how many answered.
- The **Quote Comparison** tab shows the portal quotes next to the ones you typed yourself. Award as described in [Purchasing](purchasing.md#comparing-and-awarding).
- When a supplier confirms an order on the portal, the order becomes **Confirmed** and *Supplier Confirmed* / *Confirmed On* are filled in, exactly as if you had clicked **Confirm**.

### Remember

- An RFQ appears on the portal only after **Send**; an order only after **Send to Supplier**.
- Neither action sends an email by itself: tell the supplier that a new RFQ or order is waiting (your usual email, or an automation your administrator may add).
- If you move an order **Back to Draft**, it disappears from the portal until you send it again.
- After the deadline the supplier can no longer change the quote: extend the **Deadline** and **Send** again if you want more answers.

### For administrators

The portal is shipped as a separate solution, **OpenProject365SupplierPortal**, which depends on the main solution. The look of the portal (sidebar, cards, compliance ring) is plain Liquid and CSS in the web templates **OP365 Supplier Style**, **OP365 Supplier Nav** and **OP365 Supplier Project Cards**. Setup, the table permissions, the Web API settings and the deployment steps are documented in [Development environment setup](../dev-environment.md#supplier-portal-power-pages). After every deployment of the portal, clear the site cache (`/_services/about` → *Clear cache*, Administrators web role) and sign in again. In a new environment, an imported site must be reactivated (Power Pages → *Inactive sites*) before use.
