using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;

namespace OpenProject365.Plugins
{
    /// <summary>
    /// Data of the sourcing analysis Custom APIs (rules in <see cref="SourcingRules"/>). Everything is read with the caller's
    /// privileges (context.Service): a caller sees only the suppliers, prices and history their roles let them read.
    /// </summary>
    internal static class SourcingAnalysis
    {
        public static List<SupplierScore> ScoreSuppliers(IOrganizationService service, Entity request, out decimal estimatedAmount, out int lineCount)
        {
            var lines = Purchasing.Children(service, Model.PurchaseRequestLine, Model.PurchaseRequestId, request.Id,
                Model.ItemId, "op365_quantity", "op365_estimatedprice", "op365_amount");
            lineCount = lines.Count;
            estimatedAmount = request.GetAttributeValue<Money>("op365_estimatedamount")?.Value
                ?? lines.Sum(l => l.GetAttributeValue<Money>("op365_amount")?.Value ?? 0m);

            var candidates = new Dictionary<Guid, SupplierCandidate>();
            SupplierCandidate Candidate(Guid id)
            {
                SupplierCandidate c;
                if (!candidates.TryGetValue(id, out c)) candidates[id] = c = new SupplierCandidate { Id = id, CategoryOnly = true };
                return c;
            }

            var preferred = Purchasing.Id(request, "op365_preferredsupplierid");
            if (preferred.HasValue) Candidate(preferred.Value).Preferred = true;

            // item suppliers (price, lead time) and default suppliers of the items, line by line
            var itemIds = lines.Select(l => Purchasing.Id(l, Model.ItemId)).Where(i => i.HasValue).Select(i => i.Value).Distinct().ToArray();
            var items = new Dictionary<Guid, Entity>();
            var offers = new List<Entity>();
            if (itemIds.Length > 0)
            {
                var iq = new QueryExpression(Model.Item) { ColumnSet = new ColumnSet("op365_category", "op365_defaultsupplierid") };
                iq.Criteria.AddCondition("op365_itemid", ConditionOperator.In, itemIds.Cast<object>().ToArray());
                foreach (var i in service.RetrieveMultiple(iq).Entities) items[i.Id] = i;
                var oq = new QueryExpression("op365_itemsupplier") { ColumnSet = new ColumnSet(Model.ItemId, Model.SupplierId, "op365_price", "op365_leadtimedays") };
                oq.Criteria.AddCondition(Model.ItemId, ConditionOperator.In, itemIds.Cast<object>().ToArray());
                oq.Criteria.AddCondition("statecode", ConditionOperator.Equal, 0);
                offers = service.RetrieveMultiple(oq).Entities.ToList();
            }
            foreach (var line in lines)
            {
                var item = Purchasing.Id(line, Model.ItemId);
                if (!item.HasValue) continue;
                var qty = line.GetAttributeValue<decimal?>("op365_quantity") ?? 0m;
                var estimate = line.GetAttributeValue<Money>("op365_estimatedprice")?.Value;
                var sellers = new HashSet<Guid>();
                foreach (var offer in offers.Where(o => Purchasing.Id(o, Model.ItemId) == item))
                {
                    var supplier = Purchasing.Id(offer, Model.SupplierId);
                    if (!supplier.HasValue || !sellers.Add(supplier.Value)) continue;
                    var c = Candidate(supplier.Value);
                    c.CategoryOnly = false;
                    c.CoveredLines++;
                    var price = offer.GetAttributeValue<Money>("op365_price")?.Value;
                    if (price.HasValue && estimate.HasValue && estimate.Value > 0 && qty > 0)
                    {
                        c.QuotedAmount = (c.QuotedAmount ?? 0m) + price.Value * qty;
                        c.EstimatedAmountOfQuoted = (c.EstimatedAmountOfQuoted ?? 0m) + estimate.Value * qty;
                    }
                    var lead = offer.GetAttributeValue<int?>("op365_leadtimedays");
                    if (lead.HasValue) c.LeadTimeDays = Math.Max(c.LeadTimeDays ?? 0, lead.Value);
                }
                Entity i;
                var defaultSupplier = items.TryGetValue(item.Value, out i) ? Purchasing.Id(i, "op365_defaultsupplierid") : null;
                if (defaultSupplier.HasValue && sellers.Add(defaultSupplier.Value))
                {
                    var c = Candidate(defaultSupplier.Value);
                    c.CategoryOnly = false;
                    c.CoveredLines++;
                }
            }

            // suppliers of the same category as the items (no price on record)
            var categories = items.Values.Select(i => i.GetAttributeValue<string>("op365_category")).Where(c => !string.IsNullOrWhiteSpace(c))
                .Select(c => c.Trim()).Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
            if (categories.Length > 0)
            {
                var cq = new QueryExpression("account") { ColumnSet = new ColumnSet("accountid"), TopCount = 50 };
                cq.Criteria.AddCondition("op365_issupplier", ConditionOperator.Equal, true);
                cq.Criteria.AddCondition("statecode", ConditionOperator.Equal, 0);
                cq.Criteria.AddCondition("op365_suppliercategory", ConditionOperator.In, categories.Cast<object>().ToArray());
                foreach (var a in service.RetrieveMultiple(cq).Entities) Candidate(a.Id);
            }
            if (preferred.HasValue) candidates[preferred.Value].CategoryOnly = false;

            if (candidates.Count == 0) return new List<SupplierScore>();
            var ids = candidates.Keys.Cast<object>().ToArray();

            // supplier status and document alerts
            var aq = new QueryExpression("account")
            {
                ColumnSet = new ColumnSet("name", "statecode", "op365_issupplier", "op365_supplierstatus", "op365_expireddocs", "op365_expiringdocs")
            };
            aq.Criteria.AddCondition("accountid", ConditionOperator.In, ids);
            var seen = new HashSet<Guid>();
            foreach (var a in service.RetrieveMultiple(aq).Entities)
            {
                var c = candidates[a.Id];
                seen.Add(a.Id);
                c.Name = a.GetAttributeValue<string>("name");
                c.Active = a.GetAttributeValue<OptionSetValue>("statecode")?.Value == 0 && a.GetAttributeValue<bool>("op365_issupplier");
                c.Blocked = a.GetAttributeValue<OptionSetValue>("op365_supplierstatus")?.Value == 365000001;
                c.ExpiredDocs = a.GetAttributeValue<int?>("op365_expireddocs") ?? 0;
                c.ExpiringDocs = a.GetAttributeValue<int?>("op365_expiringdocs") ?? 0;
            }
            foreach (var missing in candidates.Keys.Where(k => !seen.Contains(k)).ToList()) candidates.Remove(missing);

            // answers to the invitations of the last 12 months
            var since = DateTime.UtcNow.AddMonths(-12);
            var today = DateTime.UtcNow.Date;
            var vq = new QueryExpression(Model.RfqInvitation) { ColumnSet = new ColumnSet(Model.SupplierId, "statuscode", "op365_deadline") };
            vq.Criteria.AddCondition(Model.SupplierId, ConditionOperator.In, candidates.Keys.Cast<object>().ToArray());
            vq.Criteria.AddCondition("createdon", ConditionOperator.OnOrAfter, since);
            vq.Criteria.AddCondition("statuscode", ConditionOperator.In, Model.InvitationInvited, Model.InvitationResponded, Model.InvitationDeclined);
            foreach (var v in service.RetrieveMultiple(vq).Entities)
            {
                var supplier = Purchasing.Id(v, Model.SupplierId);
                if (!supplier.HasValue || !candidates.ContainsKey(supplier.Value)) continue;
                var status = v.GetAttributeValue<OptionSetValue>("statuscode")?.Value ?? 0;
                var deadline = v.GetAttributeValue<DateTime?>("op365_deadline");
                var closed = status != Model.InvitationInvited || (deadline.HasValue && deadline.Value.Date < today);
                if (!closed) continue;
                candidates[supplier.Value].Asked++;
                if (status == Model.InvitationResponded) candidates[supplier.Value].Answered++;
            }

            return SourcingRules.Score(candidates.Values, lineCount);
        }

        /// <summary>True when the request has a request for quotation or a purchase order that is not cancelled.</summary>
        public static bool AlreadySourced(IOrganizationService service, Guid requestId)
        {
            var rq = new QueryExpression(Model.Rfq) { ColumnSet = new ColumnSet(false), TopCount = 1 };
            rq.Criteria.AddCondition(Model.PurchaseRequestId, ConditionOperator.Equal, requestId);
            rq.Criteria.AddCondition("statuscode", ConditionOperator.NotEqual, Model.RfqCancelled);
            if (service.RetrieveMultiple(rq).Entities.Count > 0) return true;
            var oq = new QueryExpression(Model.PurchaseOrder) { ColumnSet = new ColumnSet(false), TopCount = 1 };
            oq.Criteria.AddCondition(Model.PurchaseRequestId, ConditionOperator.Equal, requestId);
            oq.Criteria.AddCondition("statuscode", ConditionOperator.NotEqual, Model.PoCancelled);
            return service.RetrieveMultiple(oq).Entities.Count > 0;
        }

        /// <summary>Route of the purchase request, read with the caller's privileges (settings with the system service).</summary>
        public static RouteResult Route(LocalContext context, Guid id)
        {
            var service = context.Service;
            var request = Request(service, id);
            decimal amount; int lines;
            var scored = ScoreSuppliers(service, request, out amount, out lines);
            return SourcingRules.Route(id, Purchasing.Id(request, Model.ProjectId), Purchasing.Status(request) == Model.PrApproved,
                AlreadySourced(service, id), amount, Settings.SourcingDirectOrderLimit(context.SystemService),
                Settings.SourcingMinQuotes(context.SystemService), scored, DateTime.UtcNow);
        }

        public static Entity Request(IOrganizationService service, Guid id) =>
            service.Retrieve(Model.PurchaseRequest, id, new ColumnSet("statuscode", Model.ProjectId, "op365_preferredsupplierid", "op365_estimatedamount"));
    }

    /// <summary>
    /// Custom API op365_SourcingSuggestSuppliers (bound to op365_purchaserequest, read-only). Output Result: JSON array of the
    /// candidate suppliers, best first, with score, coverage, price index, lead time, answer rate and reasons; suppliers that are
    /// inactive, blocked or with expired documents are listed last as not eligible.
    /// </summary>
    public class SourcingSuggestSuppliers : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var request = SourcingAnalysis.Request(context.Service, context.TargetReference.Id);
            decimal amount; int lines;
            var scored = SourcingAnalysis.ScoreSuppliers(context.Service, request, out amount, out lines);
            context.Execution.OutputParameters["Result"] = SourcingRules.Json(scored.ToArray());
        }
    }

    /// <summary>
    /// Custom API op365_SourcingRouteRequest (bound to op365_purchaserequest, read-only). Outputs Route (SourceViaRfq, DirectOrder,
    /// NoSupplier, NotApplicable), ActionType (the agent proposal action type, 0 when none), Payload (JSON for the proposal:
    /// supplierIds and deadline, or supplierId) and Result (the whole analysis as JSON, for the proposal Evidence).
    /// </summary>
    public class SourcingRouteRequest : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var route = SourcingAnalysis.Route(context, context.TargetReference.Id);
            var output = context.Execution.OutputParameters;
            output["Route"] = route.Route;
            output["ActionType"] = route.ActionType ?? 0;
            output["Payload"] = route.Payload == null ? "" : SourcingRules.Json(route.Payload);
            output["Result"] = SourcingRules.Json(route);
        }
    }

    /// <summary>
    /// Custom API op365_SourcingProposeRoute (bound to op365_purchaserequest), the only write tool of the sourcing agent for tasks
    /// 1 and 2. Input Rationale (the agent's explanation). Recomputes the route (the agent never passes numbers) and creates, with
    /// the caller's privileges, the agent proposal Source via RFQ or Direct Order (payload, evidence, amount, project, request,
    /// supplier), or the insight New Supplier Needed when no supplier is eligible; nothing when the route is NotApplicable.
    /// Refused while op365_SourcingAgentEnabled is off. Outputs Route and ProposalId (empty when nothing was created).
    /// </summary>
    public class SourcingProposeRoute : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (!Settings.SourcingAgentEnabled(context.SystemService)) Purchasing.Fail(SourcingRules.AgentOff);
            var rationale = Sourcing.Rule(() => SourcingRules.Rationale(context.Execution.InputParameters.Contains("Rationale")
                ? context.Execution.InputParameters["Rationale"] as string : null));
            var id = context.TargetReference.Id;
            var route = SourcingAnalysis.Route(context, id);
            var output = context.Execution.OutputParameters;
            output["Route"] = route.Route;
            output["ProposalId"] = "";
            var proposal = SourcingRules.Proposal(route);
            if (proposal == null) return;

            var row = new Entity(Model.AgentProposal)
            {
                ["op365_kind"] = new OptionSetValue(proposal.Kind),
                ["op365_actiontype"] = new OptionSetValue(proposal.ActionType),
                ["op365_rationale"] = rationale,
                ["op365_evidence"] = SourcingRules.Json(route),
                ["op365_amount"] = new Money(route.EstimatedAmount),
                [Model.PurchaseRequestId] = new EntityReference(Model.PurchaseRequest, id),
            };
            if (proposal.Payload != null) row["op365_payload"] = proposal.Payload;
            if (!string.IsNullOrEmpty(route.ProjectId)) row[Model.ProjectId] = new EntityReference(Model.Project, Guid.Parse(route.ProjectId));
            if (proposal.SupplierId.HasValue) row[Model.SupplierId] = new EntityReference("account", proposal.SupplierId.Value);
            output["ProposalId"] = context.Service.Create(row).ToString("D");
        }
    }
}
