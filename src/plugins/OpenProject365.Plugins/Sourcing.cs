using System;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;

namespace OpenProject365.Plugins
{
    /// <summary>Queries and updates shared by the agent proposal plugins and Custom APIs (rules in <see cref="Proposals"/>).</summary>
    internal static class Sourcing
    {
        public static readonly string[] Apis = { "op365_DecideAgentProposal", "op365_RetryAgentProposal", "op365_ExpireAgentProposals", "op365_RecordProposalError" };

        private static readonly string[] Columns =
        {
            "op365_name", "op365_kind", "op365_actiontype", "statuscode", "op365_payload", "op365_decisionnote", "op365_expireson",
            Model.ProjectId, Model.PurchaseRequestId, Model.RfqId, Model.InvitationId, Model.PurchaseOrderId, Model.SupplierInvoiceId, Model.SupplierId,
        };

        /// <summary>Primary name of the lookup targets (default proposal name).</summary>
        public static string NameColumn(string table)
        {
            switch (table)
            {
                case "account": return "name";
                case Model.Project:
                case Model.RfqInvitation: return "op365_name";
                default: return "op365_number";
            }
        }

        /// <summary>Pure rules throw InvalidOperationException: the plugin boundary turns it into a translated message.</summary>
        public static T Rule<T>(Func<T> rule)
        {
            try
            {
                return rule();
            }
            catch (InvalidOperationException ex)
            {
                throw new InvalidPluginExecutionException(ex.Message, ex);
            }
        }

        /// <summary>
        /// The proposal, read after a write that locks its row: a concurrent decision, retry or expiry waits for this transaction
        /// and then reads the committed status, so a proposal is never decided twice. Error is empty on every status this
        /// lock is taken from (Pending), or is cleared/overwritten afterwards (Failed).
        /// </summary>
        public static Entity Lock(IOrganizationService system, Guid id)
        {
            system.Update(new Entity(Model.AgentProposal, id) { ["op365_error"] = null });
            return system.Retrieve(Model.AgentProposal, id, new ColumnSet(Columns));
        }

        public static int Option(Entity e, string column) => e.GetAttributeValue<OptionSetValue>(column)?.Value ?? 0;

        public static bool CanDecide(IOrganizationService system, Entity proposal, Guid userId)
        {
            var project = Purchasing.Id(proposal, Model.ProjectId);
            return Proposals.CanDecide(Option(proposal, "op365_actiontype"), Rules.IsAdmin(system, userId), Rules.IsBuyer(system, userId),
                project.HasValue && Rules.IsProjectManager(system, project.Value, userId), Purchasing.IsSecondLevelApprover(system, userId));
        }

        /// <summary>Moves the proposal to the status (statecode from the status) with the other columns given.</summary>
        public static void SetStatus(IOrganizationService system, Guid id, int status, Entity extra = null)
        {
            var update = extra ?? new Entity(Model.AgentProposal, id);
            update.LogicalName = Model.AgentProposal;
            update.Id = id;
            update["statecode"] = new OptionSetValue(Proposals.StateOf(status));
            update["statuscode"] = new OptionSetValue(status);
            system.Update(update);
        }
    }

    /// <summary>
    /// op365_agentproposal Create/Update, PreOperation (PreImage on Update). Create: the status is the initial one of the kind
    /// (Pending, Open or Done), Dedup Key from the first lookup set (request, RFQ, invitation, order, invoice, supplier,
    /// project) and the action type, no second active proposal with the same key, Expires On for proposals, default Name
    /// "{Action Type} – {target}"; the decision columns are set only by the Custom APIs. Update: the status changes only
    /// through the Custom APIs and only the Decision Note can change (owner changes and the lookups cleared by the delete of
    /// their target are let through).
    /// </summary>
    public class AgentProposalValidate : PluginBase
    {
        private static readonly string[] Decision = { "op365_decidedbyid", "op365_decidedon", "op365_decisionnote", "op365_resultid", "op365_error" };
        private static readonly string[] Owner = { "ownerid", "owninguser", "owningteam", "owningbusinessunit" };

        protected override void Run(LocalContext context)
        {
            if (context.IsInside(Sourcing.Apis)) return;
            var target = context.Target;
            if (target == null) return;
            if (context.Message == "Update")
            {
                if (context.Changed("statuscode") || context.Changed("statecode")) Purchasing.Fail(Proposals.UseDecisionActions);
                if (context.ChangesOnly(new[] { "op365_decisionnote" }.Concat(Owner).ToArray())) return;
                // a deleted record clears the lookups that point to it (referential, remove link)
                if (context.IsInside("Delete") && context.ChangesOnly(Proposals.TargetLookups.Select(l => l[0]).ToArray())) return;
                Purchasing.Fail(Proposals.NotEditable);
            }

            var system = context.SystemService;
            var kind = target.GetAttributeValue<OptionSetValue>("op365_kind")?.Value;
            var action = target.GetAttributeValue<OptionSetValue>("op365_actiontype")?.Value;
            if (!kind.HasValue || !action.HasValue) Purchasing.Fail(Proposals.KindRequired);
            var status = Proposals.InitialStatus(kind.Value);
            // the platform may already have put the default status (Pending, active) in the target
            var given = target.GetAttributeValue<OptionSetValue>("statuscode")?.Value;
            var givenState = target.GetAttributeValue<OptionSetValue>("statecode")?.Value;
            if ((given.HasValue && given != Proposals.Pending && given != status) || (givenState.HasValue && givenState != 0 && givenState != Proposals.StateOf(status)))
                Purchasing.Fail(Proposals.UseDecisionActions);
            foreach (var c in Decision) target.Attributes.Remove(c);
            target["statecode"] = new OptionSetValue(Proposals.StateOf(status));
            target["statuscode"] = new OptionSetValue(status);

            var first = Proposals.TargetLookups.Select(l => new { Table = l[1], Ref = target.GetAttributeValue<EntityReference>(l[0]) })
                .FirstOrDefault(l => l.Ref != null);
            var key = target.GetAttributeValue<string>("op365_dedupkey");
            if (string.IsNullOrWhiteSpace(key) && first != null)
                target["op365_dedupkey"] = key = Proposals.DedupKey(first.Table, first.Ref.Id, action.Value);
            if (!string.IsNullOrWhiteSpace(key))
            {
                var query = new QueryExpression(Model.AgentProposal) { ColumnSet = new ColumnSet(false), TopCount = 1 };
                query.Criteria.AddCondition("op365_dedupkey", ConditionOperator.Equal, key);
                query.Criteria.AddCondition("statecode", ConditionOperator.Equal, 0);
                if (system.RetrieveMultiple(query).Entities.Count > 0) Purchasing.Fail(Proposals.DuplicateOpen);
            }

            if (kind == Proposals.Proposal)
                target["op365_expireson"] = Proposals.ExpiresOn(DateTime.UtcNow, Settings.SourcingProposalExpiryDays(system));
            else
                target.Attributes.Remove("op365_expireson");

            if (string.IsNullOrWhiteSpace(target.GetAttributeValue<string>("op365_name")))
            {
                string name = null;
                if (first != null)
                {
                    var column = Sourcing.NameColumn(first.Table);
                    name = system.Retrieve(first.Table, first.Ref.Id, new ColumnSet(column)).GetAttributeValue<string>(column);
                }
                target["op365_name"] = Proposals.DefaultName(action.Value, name);
            }
        }
    }

    /// <summary>op365_agentproposal Create, PostOperation: a new proposal notifies the managers of its project (FYI, in-app).</summary>
    public class AgentProposalNotify : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.Get<OptionSetValue>("op365_kind")?.Value != Proposals.Proposal) return;
            var project = context.Get<EntityReference>(Model.ProjectId);
            if (project == null) return;
            var name = context.Get<string>("op365_name");
            if (string.IsNullOrWhiteSpace(name))
                name = context.SystemService.Retrieve(Model.AgentProposal, context.PrimaryId, new ColumnSet("op365_name")).GetAttributeValue<string>("op365_name");
            foreach (var user in Rules.ProjectManagers(context.SystemService, project.Id))
                Rules.Notify(context, user, Proposals.NewProposalTitle, name);
        }
    }

    /// <summary>
    /// Custom API op365_DecideAgentProposal (bound). Inputs Approve (bool), Note (string; required to reject), DecidedBy (string,
    /// User Name or e-mail; accepted only from op365_SourcingAgentUser). Outputs Status (int), ResultId (string).
    /// Insight → Acknowledged. Proposal: Reject → Rejected; Approve → Superseded when the target is no longer in the expected
    /// status, else the action runs as the decider (CreateRfq + SendRfq, CreatePurchaseOrder, AwardRfq, DecideSupplierInvoice,
    /// InviteToPortal) → Executed with the id of the result. A failing action fails the whole call (nothing is kept): the
    /// caller records it with op365_RecordProposalError.
    /// </summary>
    public class DecideAgentProposal : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var input = context.Execution.InputParameters;
            var approve = input.Contains("Approve") && input["Approve"] is bool a && a;
            var note = input.Contains("Note") ? input["Note"] as string : null;
            var decidedBy = input.Contains("DecidedBy") ? input["DecidedBy"] as string : null;
            var system = context.SystemService;
            var id = context.TargetReference.Id;

            var decider = Sourcing.Rule(() => Proposals.ResolveDecider(context.CallerId, Settings.SourcingAgentUser(system), decidedBy,
                name => Rules.UserByName(system, name)));
            var proposal = Sourcing.Lock(system, id);
            var kind = Sourcing.Option(proposal, "op365_kind");
            var action = Sourcing.Option(proposal, "op365_actiontype");
            var status = Sourcing.Rule(() => Proposals.Decide(kind, Sourcing.Option(proposal, "statuscode"), approve, note));
            if (!Sourcing.CanDecide(system, proposal, decider)) Purchasing.Fail(Proposals.CannotDecide);

            var decision = new Entity(Model.AgentProposal, id)
            {
                ["op365_decidedbyid"] = new EntityReference("systemuser", decider),
                ["op365_decidedon"] = DateTime.UtcNow,
            };
            if (!string.IsNullOrWhiteSpace(note)) decision["op365_decisionnote"] = note;

            string resultId = null;
            if (status == Proposals.Executed)
            {
                var targetStatus = TargetStatus(system, proposal, action);
                if (!targetStatus.HasValue || !Proposals.IsTargetValid(action, targetStatus.Value))
                {
                    status = Proposals.Superseded;
                }
                else
                {
                    var service = context.Factory.CreateOrganizationService(decider);
                    try
                    {
                        resultId = Run(service, proposal, action, note).ToString("D");
                    }
                    catch (Exception ex) when (!(ex is InvalidPluginExecutionException))
                    {
                        // fault of the inner Custom API: its message (already in the user's language) without the class prefix
                        context.Trace(ex.ToString());
                        throw new InvalidPluginExecutionException(ex.Message, ex);
                    }
                    decision["op365_resultid"] = resultId;
                }
            }
            Sourcing.SetStatus(system, id, status, decision);
            context.Execution.OutputParameters["Status"] = status;
            context.Execution.OutputParameters["ResultId"] = resultId;
        }

        /// <summary>Status reason of the record the action works on; null when the proposal has no such record.</summary>
        private static int? TargetStatus(IOrganizationService system, Entity proposal, int action)
        {
            string column, table;
            switch (action)
            {
                case Proposals.SourceViaRfq:
                case Proposals.DirectOrder: column = Model.PurchaseRequestId; table = Model.PurchaseRequest; break;
                case Proposals.AwardRfq: column = Model.RfqId; table = Model.Rfq; break;
                case Proposals.ApproveInvoice:
                case Proposals.RejectInvoice: column = Model.SupplierInvoiceId; table = Model.SupplierInvoice; break;
                case Proposals.InviteSupplier: return 0;   // no status to check: InviteToPortal checks the contact
                default: return null;
            }
            var id = Purchasing.Id(proposal, column);
            return id.HasValue ? Purchasing.Status(system.Retrieve(table, id.Value, new ColumnSet("statuscode"))) : (int?)null;
        }

        /// <summary>Runs the approved action with the decider's service; returns the id of the record it produced.</summary>
        private static Guid Run(IOrganizationService service, Entity proposal, int action, string note)
        {
            var payload = proposal.GetAttributeValue<string>("op365_payload");
            switch (action)
            {
                case Proposals.SourceViaRfq:
                {
                    var source = Proposals.ParseSource(payload);
                    var create = new OrganizationRequest("op365_CreateRfq") { ["Target"] = new EntityReference(Model.PurchaseRequest, Purchasing.Id(proposal, Model.PurchaseRequestId).Value) };
                    if (source.SupplierIds.Length > 0) create["SupplierIds"] = source.SupplierIds.Select(g => g.ToString("D")).ToArray();
                    if (source.Deadline.HasValue) create["Deadline"] = source.Deadline.Value;
                    var rfqId = (Guid)service.Execute(create).Results["RfqId"];
                    service.Execute(new OrganizationRequest("op365_SendRfq") { ["Target"] = new EntityReference(Model.Rfq, rfqId) });
                    return rfqId;
                }
                case Proposals.DirectOrder:
                {
                    var order = new OrganizationRequest("op365_CreatePurchaseOrder") { ["Target"] = new EntityReference(Model.PurchaseRequest, Purchasing.Id(proposal, Model.PurchaseRequestId).Value) };
                    var supplier = Proposals.ParseGuid(payload, "supplierId") ?? Purchasing.Id(proposal, Model.SupplierId);
                    if (supplier.HasValue) order["SupplierId"] = supplier.Value;
                    return (Guid)service.Execute(order).Results["PurchaseOrderId"];
                }
                case Proposals.AwardRfq:
                {
                    var invitation = Purchasing.Id(proposal, Model.InvitationId);
                    if (!invitation.HasValue) Purchasing.Fail(Proposals.NoInvitation);
                    return (Guid)service.Execute(new OrganizationRequest("op365_AwardRfq")
                    {
                        ["Target"] = new EntityReference(Model.Rfq, Purchasing.Id(proposal, Model.RfqId).Value),
                        ["InvitationId"] = invitation.Value,
                    }).Results["PurchaseOrderId"];
                }
                case Proposals.ApproveInvoice:
                case Proposals.RejectInvoice:
                {
                    var invoice = Purchasing.Id(proposal, Model.SupplierInvoiceId).Value;
                    var decide = new OrganizationRequest("op365_DecideSupplierInvoice")
                    {
                        ["Target"] = new EntityReference(Model.SupplierInvoice, invoice),
                        ["Approve"] = action == Proposals.ApproveInvoice,
                    };
                    var invoiceNote = Proposals.InvoiceNote(note, proposal.GetAttributeValue<string>("op365_decisionnote"), payload);
                    if (!string.IsNullOrWhiteSpace(invoiceNote)) decide["Note"] = invoiceNote;
                    service.Execute(decide);
                    return invoice;   // DecideSupplierInvoice has no output: the result is the decided invoice
                }
                case Proposals.InviteSupplier:
                {
                    var contact = Proposals.ParseGuid(payload, "contactId");
                    if (!contact.HasValue) Purchasing.Fail(Proposals.NoContact);
                    return (Guid)service.Execute(new OrganizationRequest("op365_InviteToPortal") { ["Target"] = new EntityReference("contact", contact.Value) })
                        .Results["InvitationId"];
                }
                default:
                    throw new InvalidPluginExecutionException(Proposals.CannotDecide);
            }
        }
    }

    /// <summary>Custom API op365_RetryAgentProposal (bound): Failed → Pending and Error cleared, for a user who can decide the proposal.</summary>
    public class RetryAgentProposal : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var system = context.SystemService;
            var id = context.TargetReference.Id;
            var proposal = Sourcing.Lock(system, id);
            var status = Sourcing.Rule(() => Proposals.Retry(Sourcing.Option(proposal, "statuscode")));
            if (!Sourcing.CanDecide(system, proposal, context.CallerId)) Purchasing.Fail(Proposals.CannotDecide);
            Sourcing.SetStatus(system, id, status, new Entity(Model.AgentProposal, id) { ["op365_error"] = null });
        }
    }

    /// <summary>
    /// Custom API op365_ExpireAgentProposals (unbound). Output Count (int). Pending proposals whose Expires On is before today
    /// (Europe/Rome) → Expired. Called every day by the "Daily agent proposal expiry" flow.
    /// </summary>
    public class ExpireAgentProposals : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var system = context.SystemService;
            var today = SupplierDocuments.RomeToday();
            var query = new QueryExpression(Model.AgentProposal) { ColumnSet = new ColumnSet(false) };
            query.Criteria.AddCondition("statuscode", ConditionOperator.Equal, Proposals.Pending);
            query.Criteria.AddCondition("op365_expireson", ConditionOperator.LessThan, today);
            var count = 0;
            foreach (var row in system.RetrieveMultiple(query).Entities)
            {
                // re-read under the row lock: a decision taken meanwhile wins
                var proposal = Sourcing.Lock(system, row.Id);
                if (Sourcing.Option(proposal, "statuscode") != Proposals.Pending) continue;
                if (!(proposal.GetAttributeValue<DateTime?>("op365_expireson")?.Date < today)) continue;
                Sourcing.SetStatus(system, row.Id, Proposals.Expired);
                count++;
            }
            context.Execution.OutputParameters["Count"] = count;
        }
    }

    /// <summary>
    /// Custom API op365_RecordProposalError (unbound). Inputs ProposalId (Guid), Error (string). A Pending (or Failed) proposal
    /// → Failed with the error of the approved action, which rolled back DecideAgentProposal. Called by the card flow and the
    /// app command after a failed decision; allowed to administrators, the sourcing agent user and the users who can decide
    /// the proposal.
    /// </summary>
    public class RecordProposalError : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var input = context.Execution.InputParameters;
            var id = input.Contains("ProposalId") && input["ProposalId"] is Guid g ? g : Guid.Empty;
            var error = input.Contains("Error") ? input["Error"] as string : null;
            var system = context.SystemService;
            var caller = context.CallerId;
            var proposal = Sourcing.Lock(system, id);
            if (Settings.SourcingAgentUser(system) != caller && !Sourcing.CanDecide(system, proposal, caller))
                Purchasing.Fail(Proposals.CannotDecide);
            var status = Sourcing.Rule(() => Proposals.RecordError(Sourcing.Option(proposal, "statuscode")));
            Sourcing.SetStatus(system, id, status, new Entity(Model.AgentProposal, id) { ["op365_error"] = Proposals.ErrorText(error) });
        }
    }
}
