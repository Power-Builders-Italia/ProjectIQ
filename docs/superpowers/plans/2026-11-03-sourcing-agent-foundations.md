# Sourcing Agent — PR 0 Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Everything the sourcing agent needs before its first task: the Agent Proposal table, the OP365 Buyer and OP365 Sourcing Agent roles, the decision Custom APIs that run the existing purchasing APIs with the identity of the person who approved, the Teams card and expiry flows, the settings and the documentation. No Copilot Studio agent yet: proposals are created by hand to test the chain end to end.

**Architecture:** Pure rules in `ProposalLogic.cs` (unit-tested, linked into the test project like `InvoiceLogic.cs`); Dataverse plumbing in `Sourcing.cs`; schema, roles and settings through idempotent scripts in `tools/dataverse`; commands on the proposal form through `ribbon.py` and `purchasing.js`; flows in `flow_definitions.py`.

**Tech Stack:** C# net462 plugins (Microsoft.CrmSdk.CoreAssemblies 9.0.2.60), xunit tests on net10.0, Python 3 Web API scripts, Power Automate (Dataverse + Teams connectors), Markdown + Mermaid.

**Spec:** `docs/superpowers/specs/2026-11-03-sourcing-agent-design.md` (sections 3, 4, 5, 6 and 8; the Foundations box of section 7).

## Global Constraints

- Solution `OpenProject365`, publisher prefix `op365`, choice values from 365000000 (`S` below = 365000000).
- Plugin messages are English in the code and get a German, French and Italian row in `Text.cs` (order: English, German, French, Italian).
- Every status change of a proposal goes through a Custom API; direct status updates fail.
- Every environment variable lives in `OpenProject365` (`settings_env.py`).
- Manuals: English first, then `it`, `fr`, `de`, structurally identical, UI labels in English; `python3 tools/docs/check_docs.py` → 0 errors.
- CI must stay green: `dotnet build src/plugins/OpenProject365.Plugins -c Release` and `dotnet test src/plugins/OpenProject365.Plugins.Tests`.

## Review Focus

1. **Impersonated caller seen by the existing APIs.** A service created with `CreateOrganizationService(deciderId)` runs the nested Custom API with `UserId = decider` but `InitiatingUserId = original caller` (the agent application user on the Teams path). Every role check reached from a proposal must read `UserId`. Pinned by Task 2 (switch to `context.CallerId`) and by the Teams-path case of the smoke test (Task 8).
2. **A forged `DecidedBy`.** Any user except `op365_SourcingAgentUser` passing `DecidedBy` must fail with "Only the sourcing agent can decide on behalf of another user." Pinned in Task 1 (`ResolveDecider`) and Task 8.
3. **Double decision** (Teams card clicked after the app decision, or two buyers at once). The second call must fail with "This proposal has already been decided." and change nothing. Pinned in Task 1 (`Decide` on a non-pending status).
4. **Target changed since the proposal** (RFQ already awarded by hand, invoice already decided, request no longer Approved). The proposal must become Superseded, not Failed, and run nothing. Pinned in Task 1 (`IsTargetValid`) and Task 8.
5. **Action fails inside the chain** (e.g. `SendRfq` fails after `CreateRfq`). The whole chain must roll back (single transaction) and the proposal end Failed with the error text. Pinned in Task 4 by catching the error *outside* the transaction (see Step 4.4) and in Task 8.

---

## File structure

| File | Responsibility |
|---|---|
| `src/plugins/OpenProject365.Plugins/ProposalLogic.cs` (new) | Choice values, dedup key, status transitions, who may decide, target validity, payload parsing. No Dataverse calls |
| `src/plugins/OpenProject365.Plugins/Sourcing.cs` (new) | `AgentProposalValidate`, `DecideAgentProposal`, `RetryAgentProposal`, `ExpireAgentProposals`, the action runner |
| `src/plugins/OpenProject365.Plugins/PluginBase.cs` | `LocalContext.CallerId` |
| `src/plugins/OpenProject365.Plugins/Shared.cs` | `Rules.IsBuyer`, `Rules.UserByName` |
| `src/plugins/OpenProject365.Plugins/Purchasing.cs` | `EnsureManager` accepts buyers; `CallerId` instead of `InitiatingUserId` |
| `src/plugins/OpenProject365.Plugins/Settings.cs` | Sourcing variables |
| `src/plugins/OpenProject365.Plugins/Model.cs` | `AgentProposal` names |
| `src/plugins/OpenProject365.Plugins/Text.cs` | New and changed messages |
| `src/plugins/OpenProject365.Plugins.Tests/ProposalTests.cs` (new) + csproj link | Unit tests |
| `tools/dataverse/sourcing_agent.py` (new) | Table, lookups, columns, status reasons, secured Evidence, roles, views, form |
| `tools/dataverse/settings_env.py` | Eight sourcing variables |
| `tools/dataverse/plugins.py` | Steps and Custom APIs |
| `tools/dataverse/ribbon.py`, `src/webresources/purchasing.js` | Approve / Reject / Retry / Acknowledge |
| `tools/dataverse/flow_definitions.py`, `tools/dataverse/flows.py` | Teams card flow, daily expiry flow, Teams connection reference |
| `tools/dataverse/translations.json` | IT/FR/DE labels of the new table, columns, choices, views, roles |
| `tools/dataverse/sourcing_smoke.py` (new) | End-to-end check in Dev |
| Docs (Task 9) | ADR 0003, manual skeleton ×4, purchasing, administration, data model, dev environment, README, mkdocs |

---

### Task 1: Proposal rules (pure logic)

**Files:**
- Create: `src/plugins/OpenProject365.Plugins/ProposalLogic.cs`
- Create: `src/plugins/OpenProject365.Plugins.Tests/ProposalTests.cs`
- Modify: `src/plugins/OpenProject365.Plugins.Tests/OpenProject365.Plugins.Tests.csproj` (link `ProposalLogic.cs`)

**Interfaces:**
- Produces (namespace `OpenProject365.Plugins`, `public static class Proposals`):
  - Kind: `Proposal = S`, `Insight = S+1`, `Log = S+2`.
  - ActionType: `SourceViaRfq = S`, `DirectOrder = S+1`, `AwardRfq = S+2`, `ApproveInvoice = S+3`, `RejectInvoice = S+4`, `InviteSupplier = S+5`, `SupplierReminder = S+6`, `ComplianceAlert = S+7`, `BudgetAlert = S+8`, `LateDelivery = S+9`, `Consolidation = S+10`, `NewSupplierNeeded = S+11`.
  - Status (statecode 0): `Pending = 1`, `Open = S`, `Failed = S+1`; (statecode 1): `Executed = 2`, `Rejected = S+2`, `Expired = S+3`, `Superseded = S+4`, `Acknowledged = S+5`, `Done = S+6`. `int StateOf(int status)` → 0 or 1.
  - `string DedupKey(string table, Guid id, int actionType)` → `"{table}:{id:D}:{actionType}"` (lower-case guid).
  - `int InitialStatus(int kind)` → Pending / Open / Done.
  - `DateTime ExpiresOn(DateTime createdUtc, int days)` → `createdUtc.Date.AddDays(days)`; `days <= 0` → 5.
  - `bool IsInvoiceAction(int actionType)` → Approve/Reject Invoice.
  - `bool CanDecide(int actionType, bool isAdmin, bool isBuyer, bool isProjectManager, bool isSecondLevelApprover)`: invoice actions → `isAdmin || isSecondLevelApprover`; Invite Supplier → `isAdmin || isBuyer`; other proposals → `isAdmin || isBuyer || isProjectManager`.
  - `int Decide(int kind, int status, bool approve, string note)` → the new status; throws `InvalidOperationException` with the exact messages below.
  - `bool IsTargetValid(int actionType, int targetStatus)`: Source via RFQ / Direct Order → request `PrApproved`; Award RFQ → RFQ `RfqSent`; invoice actions → invoice `InvoiceToReview`; Invite Supplier → always true.
  - `SourcePayload ParseSource(string json)` with `Guid[] SupplierIds`, `DateTime? Deadline`; `Guid? ParseGuid(string json, string name)`; `string ParseNote(string json)`. JSON via `DataContractJsonSerializer` (as in `Logic.cs`), names `supplierIds`, `deadline` (`yyyy-MM-dd`), `supplierId`, `contactId`, `note`. Blank or invalid JSON → empty payload, never an exception.
  - `Guid ResolveDecider(Guid callerId, Guid? agentUserId, Guid? decidedBy)`: no `decidedBy` → caller; `decidedBy` with caller ≠ agent user (or agent user not set) → throws.

Exact messages (also used in Task 2's `Text.cs` rows):
- "This proposal has already been decided."
- "Add a note to reject the proposal."
- "Only failed proposals can be retried."
- "Only the sourcing agent can decide on behalf of another user."
- "You cannot decide this proposal." (used by Task 4 when `CanDecide` is false)
- "Use Approve, Reject, Retry or Acknowledge to change the status of an agent proposal."
- "An agent proposal cannot be changed after it is created."
- "An open proposal for the same action already exists."

`Decide` rules: kind Insight and status Open → Acknowledged (approve and note ignored); kind Proposal and status Pending → approve ? Executed : (note blank → throw "Add a note…" : Rejected); any other combination → throw "This proposal has already been decided.". (Executed here is the *intended* status; Task 4 turns it into Failed or Superseded when needed.)

- [ ] **Step 1: Write the failing tests** in `ProposalTests.cs` (xunit, same style as `InvoiceTests.cs`):

```csharp
[Fact] public void DedupKey_IsTableIdAction() =>
    Assert.Equal("op365_rfq:0f8fad5b-d9cb-469f-a165-70867728950e:365000002",
        Proposals.DedupKey("op365_rfq", new Guid("0F8FAD5B-D9CB-469F-A165-70867728950E"), Proposals.AwardRfq));
[Fact] public void Decide_PendingApprove_IsExecuted() => Assert.Equal(Proposals.Executed, Proposals.Decide(Proposals.Proposal, Proposals.Pending, true, null));
[Fact] public void Decide_RejectWithoutNote_Throws() =>
    Assert.Equal("Add a note to reject the proposal.", Assert.Throws<InvalidOperationException>(() => Proposals.Decide(Proposals.Proposal, Proposals.Pending, false, " ")).Message);
[Fact] public void Decide_AlreadyDecided_Throws() =>
    Assert.Equal("This proposal has already been decided.", Assert.Throws<InvalidOperationException>(() => Proposals.Decide(Proposals.Proposal, Proposals.Executed, true, null)).Message);
[Fact] public void Decide_InsightOpen_IsAcknowledged() => Assert.Equal(Proposals.Acknowledged, Proposals.Decide(Proposals.Insight, Proposals.Open, false, null));
[Fact] public void CanDecide_InvoiceNeedsSecondLevel() {
    Assert.False(Proposals.CanDecide(Proposals.ApproveInvoice, false, true, true, false));
    Assert.True(Proposals.CanDecide(Proposals.RejectInvoice, false, false, false, true)); }
[Fact] public void CanDecide_RfqAllowsBuyerOrManager() {
    Assert.True(Proposals.CanDecide(Proposals.AwardRfq, false, true, false, false));
    Assert.True(Proposals.CanDecide(Proposals.SourceViaRfq, false, false, true, false));
    Assert.False(Proposals.CanDecide(Proposals.InviteSupplier, false, false, true, false)); }
[Fact] public void IsTargetValid_AwardNeedsSentRfq() {
    Assert.True(Proposals.IsTargetValid(Proposals.AwardRfq, Model.RfqSent));
    Assert.False(Proposals.IsTargetValid(Proposals.AwardRfq, Model.RfqAwarded)); }
[Fact] public void ResolveDecider_ForgedDecidedBy_Throws() =>
    Assert.Equal("Only the sourcing agent can decide on behalf of another user.",
        Assert.Throws<InvalidOperationException>(() => Proposals.ResolveDecider(A, B, C)).Message);   // caller A, agent B, decidedBy C
[Fact] public void ResolveDecider_AgentPassesDecidedBy() => Assert.Equal(C, Proposals.ResolveDecider(B, B, C));
[Fact] public void ResolveDecider_NoDecidedBy_IsCaller() => Assert.Equal(A, Proposals.ResolveDecider(A, null, null));
[Fact] public void ParseSource_ReadsSuppliersAndDeadline() {
    var p = Proposals.ParseSource("{\"supplierIds\":[\"0f8fad5b-d9cb-469f-a165-70867728950e\"],\"deadline\":\"2026-11-20\"}");
    Assert.Single(p.SupplierIds); Assert.Equal(new DateTime(2026, 11, 20), p.Deadline); }
[Fact] public void ParseSource_InvalidJson_IsEmpty() => Assert.Empty(Proposals.ParseSource("not json").SupplierIds);
[Fact] public void ExpiresOn_DefaultsToFiveDays() => Assert.Equal(new DateTime(2026, 11, 8), Proposals.ExpiresOn(new DateTime(2026, 11, 3, 15, 0, 0), 0));
```
(`A`, `B`, `C` are three fixed `Guid` fields of the test class.)

- [ ] **Step 2: Run** `dotnet test src/plugins/OpenProject365.Plugins.Tests --filter ProposalTests` → build FAIL (`Proposals` not defined).
- [ ] **Step 3: Implement** `ProposalLogic.cs` per the Interfaces block; add `<Compile Include="../OpenProject365.Plugins/ProposalLogic.cs" Link="ProposalLogic.cs" />` to the test csproj.
- [ ] **Step 4: Run** `dotnet test src/plugins/OpenProject365.Plugins.Tests` → all PASS (existing tests included).
- [ ] **Step 5: Commit** `git commit -m "Sourcing agent: proposal rules"`.

---

### Task 2: Caller identity and the OP365 Buyer in the purchasing checks

**Files:**
- Modify: `src/plugins/OpenProject365.Plugins/PluginBase.cs` (`LocalContext`)
- Modify: `src/plugins/OpenProject365.Plugins/Shared.cs` (`Rules`)
- Modify: `src/plugins/OpenProject365.Plugins/Purchasing.cs` (`EnsureManager` and every `context.Execution.InitiatingUserId`)
- Modify: `src/plugins/OpenProject365.Plugins/Settings.cs`
- Modify: `src/plugins/OpenProject365.Plugins/Text.cs`
- Test: `src/plugins/OpenProject365.Plugins.Tests/TextTests.cs`

**Interfaces:**
- Produces: `Guid LocalContext.CallerId => Execution.UserId` (doc comment: "the user the operation runs for; equals the initiating user except when a plugin impersonates, as DecideAgentProposal does").
- Produces: `bool Rules.IsBuyer(IOrganizationService system, Guid userId)` — role named `OP365 Buyer`, same query as `IsAdmin`.
- Produces: `Guid? Rules.UserByName(IOrganizationService system, string name)` — enabled user by `domainname` or `internalemailaddress`; `Settings.PurchasingApprover` is rewritten to use it.
- Produces in `Settings`: constants `SourcingAgentEnabledVariable = "op365_SourcingAgentEnabled"`, `SourcingAgentUserVariable = "op365_SourcingAgentUser"`, `SourcingApprovalTeamVariable = "op365_SourcingApprovalTeam"`, `SourcingDirectOrderLimitVariable = "op365_SourcingDirectOrderLimit"`, `SourcingMinQuotesVariable = "op365_SourcingMinQuotes"`, `SourcingReminderDaysVariable = "op365_SourcingReminderDays"`, `SourcingBudgetWarningPctVariable = "op365_SourcingBudgetWarningPct"`, `SourcingProposalExpiryDaysVariable = "op365_SourcingProposalExpiryDays"`; accessors `Guid? SourcingAgentUser(system)` (via `UserByName`) and `int SourcingProposalExpiryDays(system)` (`EnvironmentValue.Number`, default 5). The other variables get accessors in the PRs that read them.

- [ ] **Step 1: Write the failing test** in `TextTests.cs`:

```csharp
[Fact] public void ManagerOrBuyerMessage_IsTranslated() =>
    Assert.Equal("Solo un capo commessa della commessa o un buyer può creare una richiesta di offerta.",
        Text.Translate("Only a manager of the project or a buyer can create a request for quotation.", Text.Column(1040)));
[Fact] public void ProposalMessages_AreTranslated() =>
    Assert.NotEqual("This proposal has already been decided.", Text.Translate("This proposal has already been decided.", Text.Column(1040)));
```
Also update the existing `Translate_PlaceholderValuesAreTranslatedToo`: its first assertion becomes `"Seul un chef de projet du projet ou un acheteur peut créer une commande d'achat."` for `"Only a manager of the project or a buyer can create a purchase order."` (the old message no longer exists).

- [ ] **Step 2: Run** `dotnet test src/plugins/OpenProject365.Plugins.Tests --filter TextTests` → FAIL.
- [ ] **Step 3: Implement.** `EnsureManager`: allow `IsAdmin || IsProjectManager || IsBuyer`; message "Only a manager of the project or a buyer can {0}." (replace the old template row in `Text.cs` with this one in four languages; keep the two specific time-entry and purchase-request rows unchanged). Replace every `context.Execution.InitiatingUserId` in `Purchasing.cs` with `context.CallerId`. Add `Text.cs` rows for the eight Task 1 messages. Add the `Settings` and `Rules` members.
- [ ] **Step 4: Run** `dotnet build src/plugins/OpenProject365.Plugins -c Release && dotnet test src/plugins/OpenProject365.Plugins.Tests` → PASS.
- [ ] **Step 5: Commit** `git commit -m "Purchasing: OP365 Buyer in the manager checks; caller is the effective user"`.

---

### Task 3: Schema, roles and settings in Dev

**Files:**
- Create: `tools/dataverse/sourcing_agent.py`
- Modify: `tools/dataverse/settings_env.py`, `tools/dataverse/translations.json`

**Interfaces:**
- Consumes: the choice values of Task 1 (option order of `col('choice', …, options=[...])` gives S, S+1, …).
- Produces: table `op365_agentproposal` with the columns below; roles `OP365 Buyer`, `OP365 Sourcing Agent`.

Script content, following `project_suppliers.py` and `supplier_invoices.py`:
1. `create_tables([('AgentProposal', 'Agent Proposal', 'Agent Proposals', 'Decision, insight or log written by the sourcing agent', ('Name', 'Name', 400, False))])`.
2. `create_lookups`: `ProjectId` → `op365_project` **parental**; `PurchaseRequestId`, `RfqId`, `InvitationId` (`op365_rfqinvitation`), `PurchaseOrderId`, `SupplierInvoiceId`, `SupplierId` (`account`), `DecidedById` (`systemuser`) → referential.
3. `create_columns`: `Kind` and `ActionType` (choices in the Task 1 order), `Rationale` memo 4000, `Evidence` memo 100000 **secured**, `Payload` memo 4000, `Amount` and `EstimatedSaving` currency, `DedupKey` text 200, `ExpiresOn` date, `DecidedOn` date-time, `DecisionNote` memo 2000, `ResultId` text 100, `Error` memo 2000. Descriptions from spec section 4.
4. `status_reasons`: active `(S, 0, 'Open')`, `(S+1, 0, 'Failed')`; inactive `(S+2, 1, 'Rejected')` … `(S+6, 1, 'Done')`; rename default 1 → Pending, 2 → Executed.
5. `Evidence` into the `OP365 Cost Visibility` profile (read only), as in `phase3_security.py`.
6. `grant_roles`: `OP365 Administrator` all on the table (Global); `OP365 User` Read (Basic); `OP365 Buyer` Read/Write/Append/AppendTo on the table (Global) plus, per spec section 6, Read (Global) on project and WBS tables, full (Global) on `op365_purchaserequest`, `op365_purchaserequestline`, `op365_rfq`, `op365_rfqinvitation`, `op365_rfqquote`, `op365_purchaseorder`, `op365_purchaseorderline`, `op365_goodsreceipt`, `op365_goodsreceiptline`, `account`, `contact`, Read/AppendTo (Global) on `op365_supplierinvoice` and lines; `OP365 Sourcing Agent` Read (Global) on master data, project and purchasing tables and Create/Read/Append (Global) on the proposal table.
7. Views: **Open Agent Proposals** (default; Kind = Proposal, active; columns Name, ActionType, ProjectId, SupplierId, Amount, ExpiresOn, statuscode), **Agent Insights** (Kind = Insight, Open), **Agent Log** (all, newest first), **My Agent Decisions** (DecidedById = current user).
8. Form **Agent Proposal**: General (Name, Kind, ActionType, lookups, Amount, EstimatedSaving, ExpiresOn, statuscode), Rationale, Evidence, Decision (DecidedById, DecidedOn, DecisionNote, ResultId, Error); all read-only except DecisionNote.
9. Subgrid **Agent Proposals** on the Project form (Purchasing tab) with the `add_section` helper of `project_suppliers.py`.
10. `settings_env.py`: eight rows (spec section 4 table, exact defaults: Enabled `no`, MinQuotes `3`, ReminderDays `2`, BudgetWarningPct `90`, ProposalExpiryDays `5`, the others none); `op365_SourcingApprovalTeam` description "Teams team id and channel id separated by |".

- [ ] **Step 1: Run** `python3 tools/dataverse/sourcing_agent.py` against Dev → each line `ok` or `skip`; run it again → only `skip` (idempotent).
- [ ] **Step 2: Run** `python3 tools/dataverse/settings_env.py` → eight new definitions; `python3 tools/dataverse/translations.py` → labels applied.
- [ ] **Step 3: Check** in the maker portal that the table, its views, the form and both roles exist, and that a user with only OP365 User sees a proposal only when it is linked to a project of their access team.
- [ ] **Step 4: Commit** `git commit -m "Sourcing agent: Agent Proposal table, roles and settings"`.

---

### Task 4: Proposal plugins and Custom APIs

**Files:**
- Create: `src/plugins/OpenProject365.Plugins/Sourcing.cs`
- Modify: `src/plugins/OpenProject365.Plugins/Model.cs`, `tools/dataverse/plugins.py`

**Interfaces:**
- Consumes: `Proposals.*` (Task 1), `CallerId`, `IsBuyer`, `UserByName`, `Settings.SourcingAgentUser`, `Settings.SourcingProposalExpiryDays` (Task 2).
- Produces Custom APIs (register in `APIS` of `plugins.py`):
  - `op365_DecideAgentProposal` bound `op365_agentproposal`; request `Approve` (0, required), `Note` (10, optional), `DecidedBy` (10, optional, "User Name or e-mail of the person who decided; accepted only from the sourcing agent"); response `Status` (7), `ResultId` (10).
  - `op365_RetryAgentProposal` bound `op365_agentproposal`; no parameters.
  - `op365_ExpireAgentProposals` unbound; response `Count` (7).
- Produces steps (`STEPS`): `AgentProposalValidate` on Create and Update, PreOperation, PreImage `op365_kind,op365_actiontype,statuscode,op365_dedupkey`.

Behaviour:
1. `AgentProposalValidate`. Skip when `context.IsInside("op365_DecideAgentProposal", "op365_RetryAgentProposal", "op365_ExpireAgentProposals")`. Create: status must be empty (set `Proposals.InitialStatus(kind)`); fill `DedupKey` from the first set lookup in the order request, RFQ, invitation, order, invoice, supplier, project (+ ActionType) when empty; fail "An open proposal for the same action already exists." when an active row has the same key; set `ExpiresOn` for kind Proposal; default Name "{ActionType label} – {target name}". Update: fail "Use Approve, …" on `statuscode`/`statecode`; fail "An agent proposal cannot be changed after it is created." unless `context.ChangesOnly("op365_decisionnote")`.
2. `DecideAgentProposal`:
   - `decider = Proposals.ResolveDecider(context.CallerId, Settings.SourcingAgentUser(system), Rules.UserByName(system, DecidedBy))`; a `DecidedBy` that resolves to no user fails "The user who decided is not a ProjectIQ user.".
   - `Proposals.Decide(...)` on the current row; insight → update to Acknowledged and stop.
   - `CanDecide` with `IsAdmin`, `IsBuyer`, `IsProjectManager(projectId)`, `Purchasing.IsSecondLevelApprover` of the decider; false → "You cannot decide this proposal.".
   - Reject → Rejected with DecidedBy/On/Note, stop.
   - Approve: read the target's status; `!IsTargetValid` → Superseded, stop.
   - Run the action with `var service = factory.CreateOrganizationService(decider)` (expose the factory on `LocalContext`) by `OrganizationRequest`s: Source via RFQ → `op365_CreateRfq` (Target request, `SupplierIds` as string array, `Deadline`) then `op365_SendRfq` (Target the new RFQ); Direct Order → `op365_CreatePurchaseOrder` (`SupplierId`); Award RFQ → `op365_AwardRfq` (`InvitationId`); Approve/Reject Invoice → `op365_DecideSupplierInvoice` (`Approve` true/false, `Note` = DecisionNote if not blank, else payload note); Invite Supplier → `op365_InviteToPortal` on the payload `contactId`.
   - Success → Executed, `ResultId` = the id the last API returned.
3. **Failure handling (Review Focus 5).** A failing inner request aborts the whole Dataverse transaction, so the proposal cannot be marked Failed in the same call. `DecideAgentProposal` therefore lets the error propagate (the caller sees it, nothing is half-done), and the *callers* record it: the card flow (Task 6) calls `DecideAgentProposal`, and on failure calls `op365_RecordProposalError` (unbound, request `ProposalId` 12, `Error` 10; allowed to admins and to `op365_SourcingAgentUser`) which sets Failed + Error. The app command (Task 5) does the same from `purchasing.js`. Add this fourth Custom API to the `APIS` table.
4. `RetryAgentProposal`: Failed → Pending, clears Error, needs `CanDecide` for the caller; other statuses fail "Only failed proposals can be retried.".
5. `ExpireAgentProposals`: Pending with `ExpiresOn` < today (Europe/Rome, as `UpdateDocumentExpiry`) → Expired; `Count` output.

- [ ] **Step 1: Build** `dotnet build src/plugins/OpenProject365.Plugins -c Release` → PASS (no new unit tests: the rules are covered in Task 1; this task is verified by the smoke test in Task 8).
- [ ] **Step 2: Register** `python3 tools/dataverse/plugins.py` against Dev → new types, steps and four Custom APIs created; second run → `skip`.
- [ ] **Step 3: Commit** `git commit -m "Sourcing agent: decide, retry, expire and record error of agent proposals"`.

---

### Task 5: Commands on the Agent Proposal form

**Files:**
- Modify: `tools/dataverse/ribbon.py`, `src/webresources/purchasing.js`

**Interfaces:**
- Consumes: the four Custom APIs of Task 4; existing `run`, `reject` helpers and `decision.html` of `purchasing.js`.
- Produces: buttons on `op365_agentproposal` — **Approve** (`approveProposal`, statuses `[1]`), **Reject** (`rejectProposal`, `[1]`, note required via `decision.html`), **Retry** (`retryProposal`, `[S+1]`), **Acknowledge** (`acknowledgeProposal`, `[S]`).

- [ ] **Step 1: Implement** the four functions with the existing `run` helper (confirm texts: "Approve this proposal? The agent's action runs with your identity.", "Retry this proposal?"); on a failed `op365_DecideAgentProposal` call `op365_RecordProposalError` with the error message, then refresh.
- [ ] **Step 2: Run** `python3 tools/dataverse/ribbon.py`, pack and import into Dev as in its docstring; upload `purchasing.js` (the `phase4_forms.py` upload step); `python3 tools/alm/compare_solution.py --check-webresources src/webresources solutions/OpenProject365/src/WebResources` → PASS after export.
- [ ] **Step 3: Check** in Dev that each button shows only in its statuses.
- [ ] **Step 4: Commit** `git commit -m "Sourcing agent: Approve, Reject, Retry and Acknowledge commands"`.

---

### Task 6: Flows — Teams card and daily expiry

**Files:**
- Modify: `tools/dataverse/flow_definitions.py`, `tools/dataverse/flows.py`

**Interfaces:**
- Consumes: `op365_DecideAgentProposal`, `op365_RecordProposalError`, `op365_ExpireAgentProposals`; variables `op365_SourcingApprovalTeam`, `op365_SourcingAgentEnabled`.
- Produces: connection reference `op365_teams` ("ProjectIQ Teams", connector `shared_teams`); flows **Agent proposal approval** and **Daily agent proposal expiry**.

1. **Agent proposal approval**: Dataverse trigger "When a row is added" on `op365_agentproposal`, filter `op365_kind eq 365000000`; Teams "Post adaptive card in a chat or channel and wait for a response" to the team and channel of the variable (split on `|`); the card shows Name, ActionType, project, supplier, Amount, Rationale, a link to the record and the buttons Approve / Reject with a note input; on response call `op365_DecideAgentProposal` with `Approve`, `Note`, `DecidedBy` = responder e-mail; on failure call `op365_RecordProposalError`; then update the card with the outcome. The Dataverse connection of this flow must belong to the application user named in `op365_SourcingAgentUser`. In-app notification (FYI) to the project managers: `Rules.Notify` from `AgentProposalValidate` on Create is simpler and works without the flow — add it there (title "New agent proposal", body = Name).
2. **Daily agent proposal expiry**: recurrence 06:30 Europe/Rome, calls `op365_ExpireAgentProposals` (pattern of the existing daily document expiry flow).

- [ ] **Step 1: Run** `python3 tools/dataverse/flows.py` → two flows and one connection reference created (flows off).
- [ ] **Step 2: Turn on** both flows in Dev with the connections (Dataverse as the application user, Teams as a service account member of the team).
- [ ] **Step 3: Commit** `git commit -m "Sourcing agent: Teams approval card and daily proposal expiry flows"`.

---

### Task 7: Application user setup in Dev

**Files:** none (environment setup, recorded in Task 9's Administration manual).

- [ ] **Step 1:** Create the application user *ProjectIQ Sourcing Agent* (app registration with a client secret in the Dev key vault), assign **Basic User**, **OP365 Sourcing Agent** and the **OP365 Cost Visibility** profile.
- [ ] **Step 2:** Set `op365_SourcingAgentUser` to its User Name and `op365_SourcingApprovalTeam` to the Dev test team and channel.
- [ ] **Step 3:** Assign **OP365 Buyer** to a test buyer user.

---

### Task 8: End-to-end smoke test in Dev

**Files:**
- Create: `tools/dataverse/sourcing_smoke.py` (pattern of `phase4_smoke.py`; reads `PAC_*` and, for the agent path, `SOURCING_AGENT_CLIENT_ID` / `SOURCING_AGENT_CLIENT_SECRET`)

Each case prints `PASS`/`FAIL` and the script exits 1 on any failure.

| Case | Setup | Expect |
|---|---|---|
| Approve Source via RFQ (app path, as the test buyer) | Approved purchase request of `seed_test.py`; proposal created by the agent client with payload of two supplier ids | Proposal Executed, `ResultId` = an RFQ in Sent with two invitations; RFQ `createdby` = the buyer |
| Teams path (as the agent client with `DecidedBy` = buyer e-mail) | Second approved request | Executed; the RFQ is created by the buyer, not by the agent (Review Focus 1) |
| Forged DecidedBy (as the buyer with `DecidedBy` = another user) | Pending proposal | Error "Only the sourcing agent can decide on behalf of another user."; still Pending (Review Focus 2) |
| Double decision | Proposal from case 1 | Error "This proposal has already been decided." (Review Focus 3) |
| Superseded | Award RFQ proposal on an RFQ then awarded by hand | Superseded, no new order (Review Focus 4) |
| Failure rolls back | Source via RFQ whose payload deadline is in the past (SendRfq fails) | Error returned, no RFQ left; after `RecordProposalError` the proposal is Failed with the error; Retry → Pending (Review Focus 5) |
| Invoice by buyer | Approve Invoice proposal decided by the buyer (not Purchasing Approver) | Error "You cannot decide this proposal." |
| Duplicate | Second proposal with the same target and action | Error "An open proposal for the same action already exists." |
| Expiry | Pending proposal with ExpiresOn yesterday, then `op365_ExpireAgentProposals` | Expired, Count ≥ 1 |

- [ ] **Step 1: Run** `python3 tools/dataverse/sourcing_smoke.py` → every case PASS.
- [ ] **Step 2:** Approve one proposal from the Teams card by hand and check the card update.
- [ ] **Step 3: Export** Dev with the `export-dev` workflow (or by hand), review the diff, commit the unpacked solution: `git commit -m "Dev: agent proposal table, roles, flows and commands"`.
- [ ] **Step 4: Commit** the smoke script `git commit -m "Sourcing agent: smoke test"`.

---

### Task 9: Documentation

**Files:**
- Create: `docs/adr/0003-sourcing-agent-proposals.md`
- Create: `docs/en/sourcing-agent.md`, then `docs/it/`, `docs/fr/`, `docs/de/` with the same structure
- Modify: `docs/*/purchasing.md` ("Who does what"), `docs/*/administration.md` (Security roles, Company settings, First setup checklist, Licences, Background automations), `docs/data-model.md` (new section "Sourcing agent"), `docs/dev-environment.md` (Teams connection reference, application user, smoke test), `README.md` (User manuals row), `mkdocs.yml` (menu entry in four languages)

Content:
- ADR 0003: context (ADR 0001 is read-only; the agent needs to act), decision (proposals, decision by a person, impersonation, trust in `DecidedBy` only from `op365_SourcingAgentUser`, failure recorded by the caller), consequences; status accepted with today's date.
- Manual skeleton for this PR: sections *What the agent does* (the ten tasks table, marked "coming" except the proposal mechanics), *Who does what*, *Agent proposals* (fields, life-cycle diagram), *Deciding a proposal* (from Teams, from the app, Retry), *Insights and log*, *Views*, *Messages you may see* (the Task 1 and Task 4 messages in English). Later PRs fill *What suppliers receive* and each task.
- Every statement checked against Tasks 1-6 code.

- [ ] **Step 1: Write** the English files, then the three translations.
- [ ] **Step 2: Run** `python3 tools/docs/check_docs.py` → `0 errors`.
- [ ] **Step 3: Commit** `git commit -m "Sourcing agent: ADR 0003, manual and administration docs"`.

---

### Task 10: Pull request

- [ ] **Step 1: Run** the CI checks locally: `python3 tools/docs/check_docs.py`, `python3 -m unittest discover -s tools/alm -v`, `dotnet build src/plugins/OpenProject365.Plugins -c Release`, `dotnet test src/plugins/OpenProject365.Plugins.Tests` → all PASS.
- [ ] **Step 2:** Push the branch and open a draft pull request with the repository template (Documentation boxes: manuals in four languages, README, data model and dev environment checked; Test: unit tests and the smoke output).
