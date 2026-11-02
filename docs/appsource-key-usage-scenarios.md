# ProjectIQ — Key usage scenarios

This document lists the key usage scenarios that ProjectIQ supports. It is uploaded to Partner Center (offer → **Supplemental content** → **Key Usage Scenario**) to help Microsoft validate the offer; it is not shown to customers. Each scenario names the user, the steps in the app and the expected result, so a reviewer can follow it in an environment where the package is installed. The full user manuals are at <https://power-builders-italia.github.io/projectiq/>.

## About the app

ProjectIQ is a project and job management model-driven app on Microsoft Dataverse for companies that work on orders: construction and installation companies, engineering firms, workshops and service companies. For every job it shows what was planned, what has been spent and what is still committed.

| Item | Value |
|---|---|
| Publisher | Power Builders Italia |
| Offer type | Dynamics 365 apps on Dataverse and Power Apps, **Get it now (Free)** |
| Package | Two managed solutions, imported in this order: `OpenProject365` (model-driven app *ProjectIQ*, plugins, PCF controls, flows) and `OpenProject365SupplierPortal` (Power Pages supplier portal) |
| Languages | English (base), Italian, French, German |
| Licences | Power Apps Premium (or equivalent) for internal users; Power Pages capacity for the supplier portal (optional) |
| Licence of the software | Apache License 2.0 |

## Before testing

1. Open the app **ProjectIQ** from [make.powerapps.com](https://make.powerapps.com) → **Apps**.
2. Give the test users the **Basic User** and **OP365 User** security roles; give the administrator **OP365 Administrator**.
3. Link each user who records hours to a **Resource** record (**Master Data → Resources**).
4. Optional: set the environment variables of **Settings** (time approval, purchase request threshold, purchasing approver) and turn on the *Daily time reminder* flow, as described in the Administration manual.

The app has four areas, chosen with the area switcher at the bottom of the left navigation: **Projects**, **Purchasing**, **Master Data** and **Settings**.

## Scenarios at a glance

| # | Scenario | Main user | Area |
|---|---|---|---|
| 1 | Set up master data | Administrator | Master Data |
| 2 | Create a project and its team | Project manager | Projects |
| 3 | Build the WBS, budget and plan; save a baseline | Project manager | Projects |
| 4 | Allocate resources and check the resource load | Project manager | Projects |
| 5 | Record and approve hours | Team member, project manager | Projects |
| 6 | Record material usage | Team member | Projects |
| 7 | Purchase: request, quotation, order, receipt, invoice | Team member, buyer, approver | Purchasing |
| 8 | Supplier answers an RFQ and confirms an order on the portal | Supplier | Supplier portal |
| 9 | Follow costs and margin of a job | Project manager, management | Projects |

## 1. Set up master data

**User:** administrator.

1. **Master Data → Customers → + New**: create a customer.
2. **Master Data → Suppliers → + New**: create two suppliers.
3. **Master Data → Items → + New**: create an item with a unit cost; in its suppliers section add the suppliers that sell it, with their price.
4. **Master Data → Resources → + New**: create a resource for each person, with weekly capacity, hourly cost and the linked user.

**Result:** customers, suppliers, items and resources are available in the lookups of projects, timesheets and purchasing documents.

## 2. Create a project and its team

**User:** project manager.

1. **Projects → Work → Projects → + New**.
2. Fill in name, customer, project manager, start and end date, contract value; save.
3. In the project team, add members with a role: **Manager**, **Contributor** or **Reader**.

**Result:** the project is created; only its members (and administrators) see it.

## 3. Build the WBS, budget and plan; save a baseline

**User:** project manager.

1. On the project, open the **WBS** tab (WBS Tree Grid) and add phases, work packages and tasks, with budget hours, budget amount and dates; edit them inline.
2. Add **dependencies** (finish-to-start, with lag days) between tasks.
3. Open the **Gantt** tab: bars, dependencies and the **critical path** are shown.
4. Click **Save Baseline** in the command bar and confirm.

**Result:** budget and progress roll up from tasks to the project. A baseline named "Baseline yyyy-mm-dd hh:mm UTC" becomes the reference, and the Gantt compares the current plan with it.

## 4. Allocate resources and check the resource load

**User:** project manager / planner.

1. On a WBS node, open the **Allocations** tab and click **+ New WBS Allocation**: resource and hours.
2. Open **Projects → Planning → Resource Load**.

**Result:** the dashboard is a heat map that shows, per resource and week, the hours allocated across all projects against capacity (net of company closures and absences), with colour bands that highlight overloads.

## 5. Record and approve hours

**Users:** team member (linked to a resource), project manager.

1. Team member: **Projects → Time → Timesheet**. Add a line for a project and task, type hours on the days of the week, click **Submit**.
2. Project manager: receives the notification "N time entries submitted on <project>"; opens **Projects → Time → Approvals**, selects the entries and clicks **Approve** (or **Reject** with a reason).

**Result:** approved entries become actual hours and actual cost of the task and of the project, valued at the hourly cost valid on the day worked. The team member is notified. Rejected entries return editable with the reason. A daily reminder tells users who forgot to record their hours.

## 6. Record material usage

**User:** team member.

1. **Projects → Work → Material Usage → + New** (or from the project).
2. Choose project, WBS node, item, quantity and date; the unit cost is proposed from the supplier price or the item cost; save.

**Result:** the amount becomes actual material cost of the WBS node and of the project.

## 7. Purchase: request, quotation, order, receipt, invoice

**Users:** team member, project manager, buyer, purchasing approver.

1. Team member: **Purchasing → Procurement → Purchase Requests → + New**, with project, WBS node, lines and preferred supplier; click **Submit**.
2. Project manager: clicks **Approve**. Above the purchase request threshold, the request moves to the purchasing approver, who approves it too. The request shows whether it is above the threshold and over budget.
3. Buyer: on the approved request clicks **Create RFQ**; invites suppliers and clicks **Send**.
4. Quotes arrive from the supplier portal (scenario 8) or are typed by the buyer. The **Quote Comparison** tab shows lines × suppliers, the best price per line and the best total; the buyer clicks **Award** under a supplier.
5. A draft purchase order is created with the quoted lines and prices; the buyer clicks **Send to Supplier**; the supplier confirms it.
6. When goods arrive: **Register Receipt** on the order, with the received quantities.
7. **Purchasing → Procurement → Supplier Invoices → + New**, linked to the order; the purchasing approver clicks **Approve**.

**Result:** sending the order adds **committed cost** to the project; the goods receipt turns it into **actual cost** (material usage). The **Spend** dashboard shows spend by supplier and item. Numbers are assigned automatically (PR-, RFQ-, PO-, GR-, INV-#####).

## 8. Supplier answers an RFQ and confirms an order on the portal

**Users:** buyer (in the app), supplier (on the portal).

1. Buyer: on a contact whose **Company Name** is the supplier, clicks **Invite to Portal**. The supplier receives an e-mail with an invitation and creates the account.
2. Supplier: on the portal dashboard opens **Requests for quotation** → the RFQ, types unit prices, delivery days and notes, clicks **Send quote**.
3. Buyer: the quote appears in the **Quote Comparison** of the RFQ; awards and sends the order (scenario 7).
4. Supplier: opens **Purchase orders** → the order and clicks **Confirm order**.

**Result:** the order becomes **Confirmed** in ProjectIQ. The supplier sees received quantities, its projects and the status of its invoices, and can upload company documents (certifications, insurance) for the buyer to approve; expiring documents are reported automatically.

## 9. Follow costs and margin of a job

**User:** project manager / management.

1. Open a project with approved hours, material usage and purchase orders.
2. Open the **Costs** tab (Cost Summary).

**Result:** contract value, budget, actual cost (labour / materials), committed cost, estimate at completion and expected margin are shown, with budget vs actual for each WBS branch. Hourly and material cost columns are visible only to users with the **OP365 Cost Visibility** column security profile.

## Support

Support requests: <https://github.com/Power-Builders-Italia/ProjectIQ/issues>. User manuals: <https://power-builders-italia.github.io/projectiq/>.
