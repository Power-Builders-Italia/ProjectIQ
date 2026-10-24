using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;

namespace OpenProject365.Plugins
{
    /// <summary>Queries and totals shared by the purchasing plugins and Custom APIs.</summary>
    internal static class Purchasing
    {
        public static readonly string[] RequestApis = { "op365_SubmitPurchaseRequest", "op365_DecidePurchaseRequest", "op365_CancelPurchaseRequest",
                                                        "op365_CreateRfq", "op365_AwardRfq", "op365_CreatePurchaseOrder" };
        public static readonly string[] RfqApis = { "op365_CreateRfq", "op365_SendRfq", "op365_AwardRfq", "op365_CancelRfq" };
        public static readonly string[] OrderApis = { "op365_CreatePurchaseOrder", "op365_AwardRfq", "op365_SetPurchaseOrderStatus",
                                                      "op365_RegisterGoodsReceipt", "op365_CancelGoodsReceipt" };
        public static readonly string[] ReceiptApis = { "op365_RegisterGoodsReceipt", "op365_CancelGoodsReceipt" };

        public static int Status(Entity e) => e.GetAttributeValue<OptionSetValue>("statuscode")?.Value ?? 0;

        public static decimal Amount(Entity e, string column) => e.GetAttributeValue<Money>(column)?.Value ?? 0m;

        public static Guid? Id(Entity e, string column) => e.GetAttributeValue<EntityReference>(column)?.Id;

        public static void Fail(string message) { throw new InvalidPluginExecutionException(message); }

        public static Entity Settings(IOrganizationService system)
        {
            var query = new QueryExpression(Model.Settings)
            {
                ColumnSet = new ColumnSet("op365_purchaserequestthreshold", "op365_purchasingapproverid"),
                TopCount = 1,
            };
            return system.RetrieveMultiple(query).Entities.FirstOrDefault() ?? new Entity(Model.Settings);
        }

        /// <summary>Second-level approvers: the Purchasing Approver of Settings, else every OP365 Administrator.</summary>
        public static List<Guid> SecondLevelApprovers(IOrganizationService system)
        {
            var approver = Id(Settings(system), "op365_purchasingapproverid");
            if (approver.HasValue) return new List<Guid> { approver.Value };
            var query = new QueryExpression("systemuser") { ColumnSet = new ColumnSet(false) };
            query.Criteria.AddCondition("isdisabled", ConditionOperator.Equal, false);
            var roles = query.AddLink("systemuserroles", "systemuserid", "systemuserid").AddLink("role", "roleid", "roleid");
            roles.LinkCriteria.AddCondition("name", ConditionOperator.Equal, "OP365 Administrator");
            return system.RetrieveMultiple(query).Entities.Select(u => u.Id).Distinct().ToList();
        }

        public static bool IsSecondLevelApprover(IOrganizationService system, Guid userId)
        {
            var approver = Id(Settings(system), "op365_purchasingapproverid");
            return approver == userId || Rules.IsAdmin(system, userId);
        }

        /// <summary>Administrator or Manager of the project.</summary>
        public static void EnsureManager(IOrganizationService system, Guid projectId, Guid userId, string action)
        {
            if (!Rules.IsAdmin(system, userId) && !Rules.IsProjectManager(system, projectId, userId))
                Fail($"Only a manager of the project can {action}.");
        }

        /// <summary>Administrator, Manager or Contributor of the project.</summary>
        public static void EnsureContributor(IOrganizationService system, Guid projectId, Guid userId, string action)
        {
            if (Rules.IsAdmin(system, userId)) return;
            var query = new QueryExpression(Model.ProjectMember) { ColumnSet = new ColumnSet(false), TopCount = 1 };
            query.Criteria.AddCondition(Model.ProjectId, ConditionOperator.Equal, projectId);
            query.Criteria.AddCondition(Model.UserId, ConditionOperator.Equal, userId);
            query.Criteria.AddCondition(Model.ProjectRole, ConditionOperator.In, Model.RoleManager, Model.RoleContributor);
            if (system.RetrieveMultiple(query).Entities.Count == 0)
                Fail($"Only a manager or contributor of the project can {action}.");
        }

        public static void EnsureProjectActive(IOrganizationService system, Guid projectId)
        {
            var p = system.Retrieve(Model.Project, projectId, new ColumnSet("statecode"));
            if (p.GetAttributeValue<OptionSetValue>("statecode")?.Value != 0)
                Fail("The project is closed.");
        }

        /// <summary>Supplier account: active, flagged as supplier and not blocked.</summary>
        public static Entity EnsureSupplier(IOrganizationService system, Guid accountId)
        {
            var a = system.Retrieve("account", accountId, new ColumnSet("name", "statecode", "op365_issupplier", "op365_supplierstatus",
                "emailaddress1", "op365_vatnumber", "op365_paymentterms"));
            if (a.GetAttributeValue<OptionSetValue>("statecode")?.Value != 0 || !a.GetAttributeValue<bool>("op365_issupplier"))
                Fail($"{a.GetAttributeValue<string>("name")} is not an active supplier.");
            if (a.GetAttributeValue<OptionSetValue>("op365_supplierstatus")?.Value == 365000001)
                Fail($"{a.GetAttributeValue<string>("name")} is blocked.");
            return a;
        }

        public static List<Entity> Children(IOrganizationService system, string table, string parentColumn, Guid parentId, params string[] columns)
        {
            var query = new QueryExpression(table) { ColumnSet = new ColumnSet(columns) };
            query.Criteria.AddCondition(parentColumn, ConditionOperator.Equal, parentId);
            query.Criteria.AddCondition("statecode", ConditionOperator.Equal, 0);
            if (columns.Contains("op365_sortorder")) query.AddOrder("op365_sortorder", OrderType.Ascending);
            return system.RetrieveMultiple(query).Entities.ToList();
        }

        /// <summary>Item price for a supplier (item supplier price, else the item unit cost).</summary>
        public static Money ItemPrice(IOrganizationService system, Guid itemId, Guid? supplierId)
        {
            if (supplierId.HasValue)
            {
                var query = new QueryExpression("op365_itemsupplier") { ColumnSet = new ColumnSet("op365_price"), TopCount = 1 };
                query.Criteria.AddCondition(Model.ItemId, ConditionOperator.Equal, itemId);
                query.Criteria.AddCondition(Model.SupplierId, ConditionOperator.Equal, supplierId.Value);
                query.Criteria.AddCondition("statecode", ConditionOperator.Equal, 0);
                var price = system.RetrieveMultiple(query).Entities.FirstOrDefault()?.GetAttributeValue<Money>("op365_price");
                if (price != null) return price;
            }
            return system.Retrieve(Model.Item, itemId, new ColumnSet("op365_unitcost")).GetAttributeValue<Money>("op365_unitcost");
        }

        /// <summary>Description and unit of measure from the item when empty; price when empty.</summary>
        public static void ItemDefaults(LocalContext context, string priceColumn, Guid? supplierId)
        {
            var item = context.Get<EntityReference>(Model.ItemId);
            if (item == null || !context.Changed(Model.ItemId)) return;
            var target = context.Target;
            var i = context.SystemService.Retrieve(Model.Item, item.Id, new ColumnSet("op365_name", "op365_uom"));
            if (string.IsNullOrEmpty(context.Get<string>("op365_name"))) target["op365_name"] = i.GetAttributeValue<string>("op365_name");
            if (string.IsNullOrEmpty(context.Get<string>("op365_uom"))) target["op365_uom"] = i.GetAttributeValue<string>("op365_uom");
            if (context.Get<Money>(priceColumn) == null) target[priceColumn] = ItemPrice(context.SystemService, item.Id, supplierId);
        }

        public static OrderLineRow Row(Entity line) => new OrderLineRow
        {
            Quantity = line.GetAttributeValue<decimal?>("op365_quantity") ?? 0m,
            Received = line.GetAttributeValue<decimal?>("op365_receivedquantity") ?? 0m,
            Price = Amount(line, "op365_price"),
        };

        /// <summary>Total and received amount of a purchase order from its lines.</summary>
        public static void RecalculateOrder(IOrganizationService system, Guid orderId)
        {
            var lines = Children(system, Model.PurchaseOrderLine, Model.PurchaseOrderId, orderId, "op365_quantity", "op365_receivedquantity", "op365_price", "op365_amount");
            var total = lines.Sum(l => Amount(l, "op365_amount"));
            var received = lines.Select(Row).Sum(r => Math.Round(Math.Min(r.Received, r.Quantity) * r.Price, 2));
            var po = system.Retrieve(Model.PurchaseOrder, orderId, new ColumnSet("op365_totalamount", "op365_receivedamount"));
            if (Amount(po, "op365_totalamount") == total && Amount(po, "op365_receivedamount") == received) return;
            system.Update(new Entity(Model.PurchaseOrder, orderId) { ["op365_totalamount"] = new Money(total), ["op365_receivedamount"] = new Money(received) });
        }

        /// <summary>Open order lines (orders Sent or Confirmed) of a project, optionally of one WBS node.</summary>
        public static List<OrderLineRow> OpenLines(IOrganizationService system, Guid projectId, Guid? nodeId = null)
        {
            var query = new QueryExpression(Model.PurchaseOrderLine) { ColumnSet = new ColumnSet("op365_quantity", "op365_receivedquantity", "op365_price") };
            query.Criteria.AddCondition("statecode", ConditionOperator.Equal, 0);
            if (nodeId.HasValue) query.Criteria.AddCondition(Model.WbsNodeId, ConditionOperator.Equal, nodeId.Value);
            var po = query.AddLink(Model.PurchaseOrder, Model.PurchaseOrderId, "op365_purchaseorderid");
            po.LinkCriteria.AddCondition(Model.ProjectId, ConditionOperator.Equal, projectId);
            po.LinkCriteria.AddCondition("statuscode", ConditionOperator.In, Model.PoSent, Model.PoConfirmed);
            return system.RetrieveMultiple(query).Entities.Select(Row).ToList();
        }

        public static void ProjectCommitted(IOrganizationService system, Guid projectId)
        {
            var committed = Math.Round(PurchaseMath.Committed(OpenLines(system, projectId)), 2);
            var p = system.Retrieve(Model.Project, projectId, new ColumnSet(Model.CommittedCost));
            if (Amount(p, Model.CommittedCost) == committed && p.Contains(Model.CommittedCost)) return;
            system.Update(new Entity(Model.Project, projectId) { [Model.CommittedCost] = new Money(committed) });
        }

        /// <summary>Supplier spend: purchase orders not cancelled.</summary>
        public static void SupplierSpend(IOrganizationService system, Guid accountId)
        {
            var fetch = $@"<fetch aggregate='true'><entity name='{Model.PurchaseOrder}'>
                <attribute name='op365_totalamount' alias='total' aggregate='sum' />
                <filter><condition attribute='op365_supplierid' operator='eq' value='{accountId}' />
                <condition attribute='statecode' operator='eq' value='0' />
                <condition attribute='statuscode' operator='ne' value='{Model.PoCancelled}' /></filter></entity></fetch>";
            var value = system.RetrieveMultiple(new FetchExpression(fetch)).Entities.FirstOrDefault()?.GetAttributeValue<AliasedValue>("total")?.Value;
            var spend = value is Money m ? m.Value : 0m;
            system.Update(new Entity("account", accountId) { ["op365_spend"] = new Money(spend) });
        }

        /// <summary>Item usage: number and amount of purchase order lines not cancelled.</summary>
        public static void ItemTotals(IOrganizationService system, Guid itemId)
        {
            var query = new QueryExpression(Model.PurchaseOrderLine) { ColumnSet = new ColumnSet("op365_amount") };
            query.Criteria.AddCondition(Model.ItemId, ConditionOperator.Equal, itemId);
            query.Criteria.AddCondition("statecode", ConditionOperator.Equal, 0);
            query.AddLink(Model.PurchaseOrder, Model.PurchaseOrderId, "op365_purchaseorderid")
                .LinkCriteria.AddCondition("statuscode", ConditionOperator.NotEqual, Model.PoCancelled);
            var lines = system.RetrieveMultiple(query).Entities;
            system.Update(new Entity(Model.Item, itemId)
            {
                ["op365_usagecount"] = lines.Count,
                ["op365_spend"] = new Money(lines.Sum(l => Amount(l, "op365_amount"))),
            });
        }

        public static string ProjectName(IOrganizationService system, Guid projectId) =>
            system.Retrieve(Model.Project, projectId, new ColumnSet("op365_name")).GetAttributeValue<string>("op365_name");
    }

    // ---------------------------------------------------------------- purchase requests

    /// <summary>
    /// op365_purchaserequest Create/Update, PreOperation (PreImage on Update): status only through the Custom APIs,
    /// content editable only in Draft or Rejected, open project, WBS node of the project, requester defaulted to the caller.
    /// </summary>
    public class PurchaseRequestValidate : PluginBase
    {
        private static readonly string[] Free = { "op365_justification", "op365_estimatedamount" };

        protected override void Run(LocalContext context)
        {
            var target = context.Target;
            if (context.IsInside(Purchasing.RequestApis)) return;
            if (context.Message == "Create")
            {
                var status = target.GetAttributeValue<OptionSetValue>("statuscode")?.Value;
                if (status.HasValue && status != Model.PrDraft) Purchasing.Fail("Use Submit to send a purchase request for approval.");
                if (!target.Contains("op365_requesterid")) target["op365_requesterid"] = new EntityReference("systemuser", context.Execution.InitiatingUserId);
            }
            else
            {
                if (target.Contains("statuscode") || target.Contains("statecode"))
                    Purchasing.Fail("Use Submit, Approve, Reject or Cancel to change the status of a purchase request.");
                var current = Purchasing.Status(context.Pre);
                if (current != Model.PrDraft && current != Model.PrRejected && !context.ChangesOnly(Free))
                    Purchasing.Fail("A purchase request can be changed only while it is Draft or Rejected.");
            }
            var project = context.Get<EntityReference>(Model.ProjectId);
            if (project == null) return;
            if (context.Message == "Create" || context.Changed(Model.ProjectId)) Purchasing.EnsureProjectActive(context.SystemService, project.Id);
            Rules.EnsureNodeInProject(context.SystemService, context.Get<EntityReference>(Model.WbsNodeId), project.Id);
        }
    }

    /// <summary>op365_purchaserequest Delete, PreOperation (PreImage): only Draft, Rejected or Cancelled requests.</summary>
    public class PurchaseRequestDelete : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.IsCascadeDeleteOf(Model.Project)) return;
            var status = Purchasing.Status(context.Pre);
            if (status != Model.PrDraft && status != Model.PrRejected && status != Model.PrCancelled)
                Purchasing.Fail("Only draft, rejected or cancelled purchase requests can be deleted.");
        }
    }

    /// <summary>
    /// op365_purchaserequestline Create/Update/Delete, PreOperation (PreImage on Update/Delete): the request must be
    /// Draft or Rejected; description, unit and estimated price from the item; amount.
    /// </summary>
    public class PurchaseRequestLineValidate : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.IsCascadeDeleteOf(Model.PurchaseRequest) || context.IsCascadeDeleteOf(Model.Project)) return;
            var system = context.SystemService;
            var request = context.Message == "Delete" ? context.Pre?.GetAttributeValue<EntityReference>(Model.PurchaseRequestId)
                                                      : context.Get<EntityReference>(Model.PurchaseRequestId);
            if (request == null) return;
            var pr = system.Retrieve(Model.PurchaseRequest, request.Id, new ColumnSet("statuscode", "op365_preferredsupplierid"));
            var status = Purchasing.Status(pr);
            if (status != Model.PrDraft && status != Model.PrRejected && !context.IsInside(Purchasing.RequestApis))
                Purchasing.Fail("Lines can be changed only while the purchase request is Draft or Rejected.");
            if (context.Message == "Delete") return;
            Purchasing.ItemDefaults(context, "op365_estimatedprice", Purchasing.Id(pr, "op365_preferredsupplierid"));
            var target = context.Target;
            var quantity = context.Get<decimal?>("op365_quantity") ?? 0m;
            var price = (target.Contains("op365_estimatedprice") ? target.GetAttributeValue<Money>("op365_estimatedprice") : context.Get<Money>("op365_estimatedprice"))?.Value ?? 0m;
            target["op365_amount"] = new Money(Math.Round(quantity * price, 2));
        }
    }

    /// <summary>op365_purchaserequestline Create/Update/Delete, PostOperation (PreImage on Update/Delete): request estimated amount.</summary>
    public class PurchaseRequestTotals : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.IsCascadeDeleteOf(Model.PurchaseRequest) || context.IsCascadeDeleteOf(Model.Project)) return;
            var request = (context.Message == "Delete" ? null : context.Get<EntityReference>(Model.PurchaseRequestId))
                          ?? context.Pre?.GetAttributeValue<EntityReference>(Model.PurchaseRequestId);
            if (request == null) return;
            var system = context.SystemService;
            var total = Purchasing.Children(system, Model.PurchaseRequestLine, Model.PurchaseRequestId, request.Id, "op365_amount")
                .Sum(l => Purchasing.Amount(l, "op365_amount"));
            system.Update(new Entity(Model.PurchaseRequest, request.Id) { ["op365_estimatedamount"] = new Money(total) });
        }
    }

    /// <summary>
    /// Custom API op365_SubmitPurchaseRequest (bound to op365_purchaserequest). Draft or Rejected → Submitted.
    /// Sets OverBudget (actual + committed + request above the WBS node or project budget), AboveThreshold (Settings),
    /// ApprovalLevel Manager and the project manager as current approver, then notifies the approver.
    /// </summary>
    public class SubmitPurchaseRequest : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var system = context.SystemService;
            var id = context.TargetReference.Id;
            var caller = context.Execution.InitiatingUserId;
            var pr = system.Retrieve(Model.PurchaseRequest, id, new ColumnSet("statuscode", "op365_number", "op365_title", Model.ProjectId,
                Model.WbsNodeId, "op365_requesterid", "op365_estimatedamount"));
            var status = Purchasing.Status(pr);
            if (status != Model.PrDraft && status != Model.PrRejected) Purchasing.Fail("Only draft or rejected purchase requests can be submitted.");
            var projectId = Purchasing.Id(pr, Model.ProjectId) ?? Guid.Empty;
            if (Purchasing.Id(pr, "op365_requesterid") != caller && !Rules.IsAdmin(system, caller) && !Rules.IsProjectManager(system, projectId, caller))
                Purchasing.Fail("Only the requester or a manager of the project can submit the purchase request.");
            if (Purchasing.Children(system, Model.PurchaseRequestLine, Model.PurchaseRequestId, id, "op365_amount").Count == 0)
                Purchasing.Fail("Add at least one line before submitting.");

            var estimated = Purchasing.Amount(pr, "op365_estimatedamount");
            var node = Purchasing.Id(pr, Model.WbsNodeId);
            decimal budget, actual, committed;
            if (node.HasValue)
            {
                var n = system.Retrieve(Model.WbsNode, node.Value, new ColumnSet(Model.BudgetTotal, Model.ActualCost));
                budget = Purchasing.Amount(n, Model.BudgetTotal);
                actual = Purchasing.Amount(n, Model.ActualCost);
                committed = PurchaseMath.Committed(Purchasing.OpenLines(system, projectId, node));
            }
            else
            {
                var p = system.Retrieve(Model.Project, projectId, new ColumnSet(Model.BudgetTotal, Model.ActualCost, Model.CommittedCost));
                budget = Purchasing.Amount(p, Model.BudgetTotal);
                actual = Purchasing.Amount(p, Model.ActualCost);
                committed = Purchasing.Amount(p, Model.CommittedCost);
            }
            var threshold = Purchasing.Settings(system).GetAttributeValue<Money>("op365_purchaserequestthreshold")?.Value;
            var project = system.Retrieve(Model.Project, projectId, new ColumnSet(Model.ProjectManagerId, "op365_name"));
            var approver = Purchasing.Id(project, Model.ProjectManagerId);
            var update = new Entity(Model.PurchaseRequest, id)
            {
                ["statuscode"] = new OptionSetValue(Model.PrSubmitted),
                ["op365_submittedon"] = DateTime.UtcNow,
                ["op365_overbudget"] = PurchaseMath.OverBudget(budget, actual, committed, estimated),
                ["op365_abovethreshold"] = PurchaseMath.AboveThreshold(estimated, threshold),
                ["op365_approvallevel"] = new OptionSetValue(Model.LevelManager),
                ["op365_currentapproverid"] = approver.HasValue ? new EntityReference("systemuser", approver.Value) : null,
                ["op365_managerapprovedbyid"] = null,
                ["op365_managerapprovedon"] = null,
                ["op365_decidedbyid"] = null,
                ["op365_decidedon"] = null,
                ["op365_decisionnote"] = null,
            };
            system.Update(update);
            if (approver.HasValue && approver.Value != caller)
                Rules.Notify(context, approver.Value, "Purchase request to approve",
                    $"{pr.GetAttributeValue<string>("op365_number")} {pr.GetAttributeValue<string>("op365_title")} on {project.GetAttributeValue<string>("op365_name")}: {estimated:N2}.");
        }
    }

    /// <summary>
    /// Custom API op365_DecidePurchaseRequest (bound). Inputs Approve (bool), Note (string; required to reject).
    /// Level Manager: a manager of the project (or the current approver, or an administrator) decides; an approval above
    /// the threshold moves the request to level Administrator. Level Administrator: the Purchasing Approver of Settings or an
    /// administrator decides. The requester (or the next approver) is notified.
    /// </summary>
    public class DecidePurchaseRequest : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var input = context.Execution.InputParameters;
            var approve = input.Contains("Approve") && input["Approve"] is bool a && a;
            var note = input.Contains("Note") ? input["Note"] as string : null;
            if (!approve && string.IsNullOrWhiteSpace(note)) Purchasing.Fail("Add a note to reject the purchase request.");
            var system = context.SystemService;
            var id = context.TargetReference.Id;
            var caller = context.Execution.InitiatingUserId;
            var pr = system.Retrieve(Model.PurchaseRequest, id, new ColumnSet("statuscode", "op365_number", "op365_title", Model.ProjectId,
                "op365_requesterid", "op365_currentapproverid", "op365_approvallevel", "op365_abovethreshold", "op365_estimatedamount"));
            if (Purchasing.Status(pr) != Model.PrSubmitted) Purchasing.Fail("Only submitted purchase requests can be approved or rejected.");
            var projectId = Purchasing.Id(pr, Model.ProjectId) ?? Guid.Empty;
            var level = pr.GetAttributeValue<OptionSetValue>("op365_approvallevel")?.Value ?? Model.LevelManager;
            var now = DateTime.UtcNow;
            var title = $"{pr.GetAttributeValue<string>("op365_number")} {pr.GetAttributeValue<string>("op365_title")}";
            var requester = Purchasing.Id(pr, "op365_requesterid");

            if (level == Model.LevelManager)
            {
                if (Purchasing.Id(pr, "op365_currentapproverid") != caller && !Rules.IsAdmin(system, caller) && !Rules.IsProjectManager(system, projectId, caller))
                    Purchasing.Fail("Only a manager of the project can decide this purchase request.");
                if (approve && pr.GetAttributeValue<bool>("op365_abovethreshold") && !Purchasing.IsSecondLevelApprover(system, caller))
                {
                    var approvers = Purchasing.SecondLevelApprovers(system);
                    system.Update(new Entity(Model.PurchaseRequest, id)
                    {
                        ["op365_approvallevel"] = new OptionSetValue(Model.LevelAdministrator),
                        ["op365_managerapprovedbyid"] = new EntityReference("systemuser", caller),
                        ["op365_managerapprovedon"] = now,
                        ["op365_currentapproverid"] = approvers.Count == 1 ? new EntityReference("systemuser", approvers[0]) : null,
                    });
                    foreach (var user in approvers.Where(u => u != caller))
                        Rules.Notify(context, user, "Purchase request to approve", $"{title} is above the approval threshold and needs your approval.");
                    return;
                }
            }
            else if (!Purchasing.IsSecondLevelApprover(system, caller))
            {
                Purchasing.Fail("This purchase request is above the threshold: only the purchasing approver or an administrator can decide it.");
            }

            system.Update(new Entity(Model.PurchaseRequest, id)
            {
                ["statuscode"] = new OptionSetValue(approve ? Model.PrApproved : Model.PrRejected),
                ["op365_decidedbyid"] = new EntityReference("systemuser", caller),
                ["op365_decidedon"] = now,
                ["op365_decisionnote"] = note,
                ["op365_currentapproverid"] = null,
            });
            if (requester.HasValue && requester.Value != caller)
                Rules.Notify(context, requester.Value, approve ? "Purchase request approved" : "Purchase request rejected",
                    $"{title} was {(approve ? "approved" : "rejected")}." + (string.IsNullOrWhiteSpace(note) ? "" : " Note: " + note));
        }
    }

    /// <summary>Custom API op365_CancelPurchaseRequest (bound): any status but Ordered or Cancelled → Cancelled (requester, managers, administrators).</summary>
    public class CancelPurchaseRequest : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var system = context.SystemService;
            var id = context.TargetReference.Id;
            var caller = context.Execution.InitiatingUserId;
            var pr = system.Retrieve(Model.PurchaseRequest, id, new ColumnSet("statuscode", Model.ProjectId, "op365_requesterid"));
            var status = Purchasing.Status(pr);
            if (status == Model.PrOrdered || status == Model.PrCancelled) Purchasing.Fail("Ordered or cancelled purchase requests cannot be cancelled.");
            if (Purchasing.Id(pr, "op365_requesterid") != caller)
                Purchasing.EnsureManager(system, Purchasing.Id(pr, Model.ProjectId) ?? Guid.Empty, caller, "cancel the purchase request");
            system.Update(new Entity(Model.PurchaseRequest, id) { ["statuscode"] = new OptionSetValue(Model.PrCancelled), ["op365_currentapproverid"] = null });
        }
    }

    // ---------------------------------------------------------------- RFQs

    /// <summary>
    /// Custom API op365_CreateRfq (bound to an approved op365_purchaserequest). Inputs Deadline (DateTime, default in 7 days),
    /// SupplierIds (string array, default the preferred supplier and the default suppliers of the items). Output RfqId.
    /// </summary>
    public class CreateRfq : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var system = context.SystemService;
            var input = context.Execution.InputParameters;
            var id = context.TargetReference.Id;
            var pr = system.Retrieve(Model.PurchaseRequest, id, new ColumnSet("statuscode", Model.ProjectId, "op365_preferredsupplierid", "op365_title"));
            if (Purchasing.Status(pr) != Model.PrApproved) Purchasing.Fail("Only approved purchase requests can go to a request for quotation.");
            var projectId = Purchasing.Id(pr, Model.ProjectId) ?? Guid.Empty;
            Purchasing.EnsureManager(system, projectId, context.Execution.InitiatingUserId, "create a request for quotation");
            var deadline = Rules.OptionalDate(input, "Deadline") ?? DateTime.UtcNow.Date.AddDays(7);
            if (deadline < DateTime.UtcNow.Date) Purchasing.Fail("The deadline must be today or later.");

            var suppliers = new List<Guid>();
            var given = input.Contains("SupplierIds") ? input["SupplierIds"] as string[] : null;
            foreach (var s in given ?? new string[0])
            {
                Guid g;
                if (Guid.TryParse(s, out g)) suppliers.Add(g);
            }
            if (suppliers.Count == 0)
            {
                var preferred = Purchasing.Id(pr, "op365_preferredsupplierid");
                if (preferred.HasValue) suppliers.Add(preferred.Value);
                foreach (var line in Purchasing.Children(system, Model.PurchaseRequestLine, Model.PurchaseRequestId, id, Model.ItemId))
                {
                    var item = Purchasing.Id(line, Model.ItemId);
                    if (!item.HasValue) continue;
                    var supplier = Purchasing.Id(system.Retrieve(Model.Item, item.Value, new ColumnSet("op365_defaultsupplierid")), "op365_defaultsupplierid");
                    if (supplier.HasValue) suppliers.Add(supplier.Value);
                }
            }
            var rfqId = system.Create(new Entity(Model.Rfq)
            {
                [Model.ProjectId] = new EntityReference(Model.Project, projectId),
                [Model.PurchaseRequestId] = new EntityReference(Model.PurchaseRequest, id),
                ["op365_deadline"] = deadline,
                ["op365_notes"] = pr.GetAttributeValue<string>("op365_title"),
            });
            foreach (var supplier in suppliers.Distinct())
                system.Create(new Entity(Model.RfqInvitation)
                {
                    [Model.RfqId] = new EntityReference(Model.Rfq, rfqId),
                    [Model.SupplierId] = new EntityReference("account", supplier),
                });
            context.Execution.OutputParameters["RfqId"] = rfqId;
        }
    }

    /// <summary>Custom API op365_SendRfq (bound to a draft op365_rfq): RFQ → Sent, invitations To Invite → Invited. Output Count.</summary>
    public class SendRfq : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var system = context.SystemService;
            var id = context.TargetReference.Id;
            var rfq = system.Retrieve(Model.Rfq, id, new ColumnSet("statuscode", Model.ProjectId, "op365_deadline"));
            var status = Purchasing.Status(rfq);
            if (status != Model.RfqDraft && status != Model.RfqSent) Purchasing.Fail("Only draft or sent requests for quotation can be sent.");
            Purchasing.EnsureManager(system, Purchasing.Id(rfq, Model.ProjectId) ?? Guid.Empty, context.Execution.InitiatingUserId, "send the request for quotation");
            if (rfq.GetAttributeValue<DateTime?>("op365_deadline")?.Date < DateTime.UtcNow.Date) Purchasing.Fail("The deadline has passed: move it before sending.");
            var now = DateTime.UtcNow;
            var count = 0;
            var invitations = Purchasing.Children(system, Model.RfqInvitation, Model.RfqId, id, "statuscode");
            if (invitations.Count == 0) Purchasing.Fail("Invite at least one supplier.");
            foreach (var inv in invitations.Where(i => Purchasing.Status(i) == Model.InvitationToInvite))
            {
                system.Update(new Entity(Model.RfqInvitation, inv.Id) { ["statuscode"] = new OptionSetValue(Model.InvitationInvited), ["op365_invitedon"] = now });
                count++;
            }
            if (status == Model.RfqDraft)
                system.Update(new Entity(Model.Rfq, id) { ["statuscode"] = new OptionSetValue(Model.RfqSent), ["op365_senton"] = now });
            context.Execution.OutputParameters["Count"] = count;
        }
    }

    /// <summary>
    /// Custom API op365_AwardRfq (bound to a sent op365_rfq). Input InvitationId (Guid). Output PurchaseOrderId.
    /// Creates a draft purchase order to the winning supplier with the quoted lines; RFQ → Awarded, request → Ordered.
    /// </summary>
    public class AwardRfq : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var system = context.SystemService;
            var id = context.TargetReference.Id;
            var invitationId = (Guid)context.Execution.InputParameters["InvitationId"];
            var rfq = system.Retrieve(Model.Rfq, id, new ColumnSet("statuscode", Model.ProjectId, Model.PurchaseRequestId));
            if (Purchasing.Status(rfq) != Model.RfqSent) Purchasing.Fail("Only sent requests for quotation can be awarded.");
            var projectId = Purchasing.Id(rfq, Model.ProjectId) ?? Guid.Empty;
            Purchasing.EnsureManager(system, projectId, context.Execution.InitiatingUserId, "award the request for quotation");
            var inv = system.Retrieve(Model.RfqInvitation, invitationId, new ColumnSet(Model.RfqId, Model.SupplierId, "statuscode", "op365_deliverydays"));
            if (Purchasing.Id(inv, Model.RfqId) != id) Purchasing.Fail("The invitation belongs to another request for quotation.");
            if (Purchasing.Status(inv) != Model.InvitationResponded) Purchasing.Fail("Award a supplier who sent a quote.");

            var quotes = Purchasing.Children(system, Model.RfqQuote, Model.InvitationId, invitationId, Model.RequestLineId, "op365_price", "op365_notes")
                .Where(q => Purchasing.Id(q, Model.RequestLineId).HasValue).ToList();
            if (quotes.Count == 0) Purchasing.Fail("The supplier quoted no lines.");
            var requestId = Purchasing.Id(rfq, Model.PurchaseRequestId);
            var pr = requestId.HasValue ? system.Retrieve(Model.PurchaseRequest, requestId.Value, new ColumnSet(Model.WbsNodeId)) : null;
            var days = inv.GetAttributeValue<int?>("op365_deliverydays");
            var orderId = OrderBuilder.Create(system, projectId, Purchasing.Id(inv, Model.SupplierId) ?? Guid.Empty, requestId,
                days.HasValue ? DateTime.UtcNow.Date.AddDays(days.Value) : (DateTime?)null);
            var sort = 0;
            foreach (var q in quotes)
            {
                var line = system.Retrieve(Model.PurchaseRequestLine, Purchasing.Id(q, Model.RequestLineId).Value,
                    new ColumnSet("op365_name", Model.ItemId, "op365_quantity", "op365_uom", "op365_sortorder"));
                OrderBuilder.AddLine(system, orderId, line, q.GetAttributeValue<Money>("op365_price"), pr == null ? null : Purchasing.Id(pr, Model.WbsNodeId), ++sort);
            }
            var now = DateTime.UtcNow;
            system.Update(new Entity(Model.Rfq, id)
            {
                ["statuscode"] = new OptionSetValue(Model.RfqAwarded),
                ["op365_awardedon"] = now,
                ["op365_winninginvitationid"] = new EntityReference(Model.RfqInvitation, invitationId),
                [Model.PurchaseOrderId] = new EntityReference(Model.PurchaseOrder, orderId),
            });
            if (requestId.HasValue) system.Update(new Entity(Model.PurchaseRequest, requestId.Value) { ["statuscode"] = new OptionSetValue(Model.PrOrdered) });
            context.Execution.OutputParameters["PurchaseOrderId"] = orderId;
        }
    }

    /// <summary>Custom API op365_CancelRfq (bound): Draft or Sent → Cancelled.</summary>
    public class CancelRfq : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var system = context.SystemService;
            var id = context.TargetReference.Id;
            var rfq = system.Retrieve(Model.Rfq, id, new ColumnSet("statuscode", Model.ProjectId));
            var status = Purchasing.Status(rfq);
            if (status != Model.RfqDraft && status != Model.RfqSent) Purchasing.Fail("Only draft or sent requests for quotation can be cancelled.");
            Purchasing.EnsureManager(system, Purchasing.Id(rfq, Model.ProjectId) ?? Guid.Empty, context.Execution.InitiatingUserId, "cancel the request for quotation");
            system.Update(new Entity(Model.Rfq, id) { ["statuscode"] = new OptionSetValue(Model.RfqCancelled), ["op365_cancelledon"] = DateTime.UtcNow });
        }
    }

    /// <summary>
    /// op365_rfqinvitation Create/Update, PreOperation (PreImage on Update): active supplier, RFQ open with a future deadline,
    /// name and email from the supplier. Outside the Custom APIs the status can only move from Invited to Responded or Declined
    /// (supplier portal).
    /// </summary>
    public class RfqInvitationValidate : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var system = context.SystemService;
            var target = context.Target;
            var rfqRef = context.Get<EntityReference>(Model.RfqId);
            var rfq = system.Retrieve(Model.Rfq, rfqRef.Id, new ColumnSet("statuscode", "op365_deadline"));
            var byApi = context.IsInside(Purchasing.RfqApis);
            if (!byApi)
            {
                var rfqStatus = Purchasing.Status(rfq);
                if (rfqStatus != Model.RfqDraft && rfqStatus != Model.RfqSent) Purchasing.Fail("The request for quotation is closed.");
                if (rfq.GetAttributeValue<DateTime?>("op365_deadline")?.Date < DateTime.UtcNow.Date) Purchasing.Fail("The deadline of the request for quotation has passed.");
                if (target.Contains("statuscode"))
                {
                    var to = Purchasing.Status(target);
                    var from = context.Message == "Create" ? Model.InvitationToInvite : Purchasing.Status(context.Pre);
                    var portalAnswer = (from == Model.InvitationInvited || from == Model.InvitationToInvite)
                                       && (to == Model.InvitationResponded || to == Model.InvitationDeclined);
                    if (to != from && !portalAnswer && !(context.Message == "Create" && to == Model.InvitationToInvite))
                        Purchasing.Fail("Use Send on the request for quotation to invite suppliers.");
                    if (to == Model.InvitationResponded || to == Model.InvitationDeclined) target["op365_respondedon"] = DateTime.UtcNow;
                }
            }
            if (context.Message == "Create" || context.Changed(Model.SupplierId))
            {
                var supplier = Purchasing.EnsureSupplier(system, context.Get<EntityReference>(Model.SupplierId).Id);
                target["op365_name"] = supplier.GetAttributeValue<string>("name");
                if (string.IsNullOrEmpty(context.Get<string>("op365_email"))) target["op365_email"] = supplier.GetAttributeValue<string>("emailaddress1");
            }
        }
    }

    /// <summary>op365_rfqinvitation Create/Update/Delete, PostOperation (PreImage on Update/Delete): RFQ responses.</summary>
    public class RfqResponses : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.IsCascadeDeleteOf(Model.Rfq) || context.IsCascadeDeleteOf(Model.Project)) return;
            var rfq = (context.Message == "Delete" ? null : context.Get<EntityReference>(Model.RfqId)) ?? context.Pre?.GetAttributeValue<EntityReference>(Model.RfqId);
            if (rfq == null) return;
            var system = context.SystemService;
            var count = Purchasing.Children(system, Model.RfqInvitation, Model.RfqId, rfq.Id, "statuscode").Count(i => Purchasing.Status(i) == Model.InvitationResponded);
            system.Update(new Entity(Model.Rfq, rfq.Id) { ["op365_responsecount"] = count });
        }
    }

    /// <summary>
    /// op365_rfqquote Create/Update/Delete, PreOperation (PreImage on Update/Delete): RFQ open, deadline not passed (unless by
    /// a manager after it), request line of the RFQ's purchase request; name from the line. Creating a quote marks the
    /// invitation Responded.
    /// </summary>
    public class RfqQuoteValidate : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.IsCascadeDeleteOf(Model.RfqInvitation) || context.IsCascadeDeleteOf(Model.Rfq) || context.IsCascadeDeleteOf(Model.Project)) return;
            var system = context.SystemService;
            var invRef = context.Message == "Delete" ? context.Pre.GetAttributeValue<EntityReference>(Model.InvitationId) : context.Get<EntityReference>(Model.InvitationId);
            var inv = system.Retrieve(Model.RfqInvitation, invRef.Id, new ColumnSet(Model.RfqId, "statuscode"));
            var rfq = system.Retrieve(Model.Rfq, Purchasing.Id(inv, Model.RfqId).Value, new ColumnSet("statuscode", Model.PurchaseRequestId));
            var status = Purchasing.Status(rfq);
            if (status != Model.RfqDraft && status != Model.RfqSent) Purchasing.Fail("The request for quotation is closed.");
            if (context.Message == "Delete") return;
            var target = context.Target;
            var line = context.Get<EntityReference>(Model.RequestLineId);
            if (line != null && context.Changed(Model.RequestLineId))
            {
                var l = system.Retrieve(Model.PurchaseRequestLine, line.Id, new ColumnSet(Model.PurchaseRequestId, "op365_name"));
                if (Purchasing.Id(l, Model.PurchaseRequestId) != Purchasing.Id(rfq, Model.PurchaseRequestId))
                    Purchasing.Fail("The line belongs to another purchase request.");
                target["op365_name"] = l.GetAttributeValue<string>("op365_name");
            }
            if (context.Message == "Create" && Purchasing.Status(inv) != Model.InvitationResponded)
                system.Update(new Entity(Model.RfqInvitation, inv.Id) { ["statuscode"] = new OptionSetValue(Model.InvitationResponded), ["op365_respondedon"] = DateTime.UtcNow });
        }
    }

    /// <summary>op365_rfqquote Create/Update/Delete, PostOperation (PreImage on Update/Delete): invitation quoted amount.</summary>
    public class RfqQuoteTotals : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.IsCascadeDeleteOf(Model.RfqInvitation) || context.IsCascadeDeleteOf(Model.Rfq) || context.IsCascadeDeleteOf(Model.Project)) return;
            var inv = (context.Message == "Delete" ? null : context.Get<EntityReference>(Model.InvitationId)) ?? context.Pre?.GetAttributeValue<EntityReference>(Model.InvitationId);
            if (inv == null) return;
            var system = context.SystemService;
            var total = 0m;
            foreach (var q in Purchasing.Children(system, Model.RfqQuote, Model.InvitationId, inv.Id, Model.RequestLineId, "op365_price"))
            {
                var line = Purchasing.Id(q, Model.RequestLineId);
                var quantity = line.HasValue ? system.Retrieve(Model.PurchaseRequestLine, line.Value, new ColumnSet("op365_quantity")).GetAttributeValue<decimal?>("op365_quantity") ?? 0m : 0m;
                total += Math.Round(quantity * Purchasing.Amount(q, "op365_price"), 2);
            }
            system.Update(new Entity(Model.RfqInvitation, inv.Id) { ["op365_quotedamount"] = new Money(total) });
        }
    }

    // ---------------------------------------------------------------- purchase orders

    internal static class OrderBuilder
    {
        public static Guid Create(IOrganizationService system, Guid projectId, Guid supplierId, Guid? requestId, DateTime? expected)
        {
            var supplier = Purchasing.EnsureSupplier(system, supplierId);
            var project = system.Retrieve(Model.Project, projectId, new ColumnSet("statuscode"));
            if (Purchasing.Status(project) != Model.ProjectInProgress) Purchasing.Fail("Purchase orders can be created only on projects In Progress.");
            var po = new Entity(Model.PurchaseOrder)
            {
                [Model.ProjectId] = new EntityReference(Model.Project, projectId),
                [Model.SupplierId] = new EntityReference("account", supplierId),
                ["op365_orderdate"] = DateTime.UtcNow.Date,
                ["op365_paymentterms"] = supplier.GetAttributeValue<string>("op365_paymentterms"),
            };
            if (requestId.HasValue) po[Model.PurchaseRequestId] = new EntityReference(Model.PurchaseRequest, requestId.Value);
            if (expected.HasValue) po["op365_expecteddelivery"] = expected.Value;
            return system.Create(po);
        }

        public static void AddLine(IOrganizationService system, Guid orderId, Entity requestLine, Money price, Guid? nodeId, int sort)
        {
            var line = new Entity(Model.PurchaseOrderLine)
            {
                [Model.PurchaseOrderId] = new EntityReference(Model.PurchaseOrder, orderId),
                [Model.RequestLineId] = requestLine.ToEntityReference(),
                ["op365_name"] = requestLine.GetAttributeValue<string>("op365_name"),
                ["op365_quantity"] = requestLine.GetAttributeValue<decimal?>("op365_quantity") ?? 0m,
                ["op365_uom"] = requestLine.GetAttributeValue<string>("op365_uom"),
                ["op365_sortorder"] = sort,
            };
            if (price != null) line["op365_price"] = price;
            var item = Purchasing.Id(requestLine, Model.ItemId);
            if (item.HasValue) line[Model.ItemId] = new EntityReference(Model.Item, item.Value);
            if (nodeId.HasValue) line[Model.WbsNodeId] = new EntityReference(Model.WbsNode, nodeId.Value);
            system.Create(line);
        }
    }

    /// <summary>
    /// Custom API op365_CreatePurchaseOrder (bound to an approved op365_purchaserequest). Input SupplierId (Guid, default the
    /// preferred supplier). Output PurchaseOrderId. Draft order with the request lines at the estimated (or supplier) price;
    /// request → Ordered.
    /// </summary>
    public class CreatePurchaseOrder : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var system = context.SystemService;
            var input = context.Execution.InputParameters;
            var id = context.TargetReference.Id;
            var pr = system.Retrieve(Model.PurchaseRequest, id, new ColumnSet("statuscode", Model.ProjectId, Model.WbsNodeId, "op365_preferredsupplierid"));
            if (Purchasing.Status(pr) != Model.PrApproved) Purchasing.Fail("Only approved purchase requests can be ordered.");
            var projectId = Purchasing.Id(pr, Model.ProjectId) ?? Guid.Empty;
            Purchasing.EnsureManager(system, projectId, context.Execution.InitiatingUserId, "create a purchase order");
            var supplier = input.Contains("SupplierId") && input["SupplierId"] is Guid g && g != Guid.Empty ? g : Purchasing.Id(pr, "op365_preferredsupplierid");
            if (!supplier.HasValue) Purchasing.Fail("Choose the supplier: set Preferred Supplier on the request.");
            var lines = Purchasing.Children(system, Model.PurchaseRequestLine, Model.PurchaseRequestId, id,
                "op365_name", Model.ItemId, "op365_quantity", "op365_uom", "op365_estimatedprice", "op365_sortorder");
            if (lines.Count == 0) Purchasing.Fail("The purchase request has no lines.");
            var orderId = OrderBuilder.Create(system, projectId, supplier.Value, id, null);
            var sort = 0;
            foreach (var line in lines)
            {
                var item = Purchasing.Id(line, Model.ItemId);
                var price = item.HasValue ? Purchasing.ItemPrice(system, item.Value, supplier) : null;
                OrderBuilder.AddLine(system, orderId, line, price ?? line.GetAttributeValue<Money>("op365_estimatedprice"), Purchasing.Id(pr, Model.WbsNodeId), ++sort);
            }
            system.Update(new Entity(Model.PurchaseRequest, id) { ["statuscode"] = new OptionSetValue(Model.PrOrdered) });
            context.Execution.OutputParameters["PurchaseOrderId"] = orderId;
        }
    }

    /// <summary>
    /// op365_purchaseorder Create/Update, PreOperation (PreImage on Update): status only through the Custom APIs (or a Sent order
    /// confirmed by the supplier: Supplier Confirmed = yes → Confirmed), content editable only in Draft, project In Progress,
    /// active supplier, order date and payment terms defaulted.
    /// </summary>
    public class PurchaseOrderValidate : PluginBase
    {
        private static readonly string[] Free = { "op365_notes", "op365_expecteddelivery", "op365_deliveryplace", "op365_totalamount", "op365_receivedamount", "modifiedon" };

        protected override void Run(LocalContext context)
        {
            var system = context.SystemService;
            var target = context.Target;
            if (context.IsInside(Purchasing.OrderApis)) return;
            if (context.Message == "Create")
            {
                var status = target.GetAttributeValue<OptionSetValue>("statuscode")?.Value;
                if (status.HasValue && status != Model.PoDraft) Purchasing.Fail("New purchase orders start as Draft.");
                if (!target.Contains("op365_orderdate")) target["op365_orderdate"] = DateTime.UtcNow.Date;
            }
            else
            {
                if (target.Contains("statuscode") || target.Contains("statecode"))
                    Purchasing.Fail("Use Send, Confirm or Cancel to change the status of a purchase order.");
                var current = Purchasing.Status(context.Pre);
                if (target.GetAttributeValue<bool>("op365_supplierconfirmed") && current == Model.PoSent)
                {
                    target["statuscode"] = new OptionSetValue(Model.PoConfirmed);
                    target["op365_confirmedon"] = DateTime.UtcNow;
                    return;
                }
                if (current != Model.PoDraft && !context.ChangesOnly(Free))
                    Purchasing.Fail("A purchase order can be changed only while it is Draft.");
            }
            var project = context.Get<EntityReference>(Model.ProjectId);
            if (context.Message == "Create" || context.Changed(Model.ProjectId))
            {
                var p = system.Retrieve(Model.Project, project.Id, new ColumnSet("statecode", "statuscode"));
                if (p.GetAttributeValue<OptionSetValue>("statuscode")?.Value != Model.ProjectInProgress)
                    Purchasing.Fail("Purchase orders can be created only on projects In Progress.");
            }
            if (context.Message == "Create" || context.Changed(Model.SupplierId))
            {
                var supplier = Purchasing.EnsureSupplier(system, context.Get<EntityReference>(Model.SupplierId).Id);
                if (string.IsNullOrEmpty(context.Get<string>("op365_paymentterms"))) target["op365_paymentterms"] = supplier.GetAttributeValue<string>("op365_paymentterms");
            }
        }
    }

    /// <summary>op365_purchaseorder Delete, PreOperation (PreImage): only Draft or Cancelled orders.</summary>
    public class PurchaseOrderDelete : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.IsCascadeDeleteOf(Model.Project)) return;
            var status = Purchasing.Status(context.Pre);
            if (status != Model.PoDraft && status != Model.PoCancelled) Purchasing.Fail("Only draft or cancelled purchase orders can be deleted.");
        }
    }

    /// <summary>
    /// op365_purchaseorderline Create/Update/Delete, PreOperation (PreImage on Update/Delete): order Draft (received quantities
    /// change only through goods receipts), WBS node of the order's project, item defaults with the supplier price, amount.
    /// </summary>
    public class PurchaseOrderLineValidate : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.IsCascadeDeleteOf(Model.PurchaseOrder) || context.IsCascadeDeleteOf(Model.Project)) return;
            var system = context.SystemService;
            var target = context.Target;
            if (target != null && target.Contains("op365_receivedquantity") && !context.IsInside(Purchasing.ReceiptApis))
                Purchasing.Fail("Received quantities come from goods receipts.");
            if (context.IsInside(Purchasing.ReceiptApis)) return;   // they change only received quantities
            var orderRef = context.Message == "Delete" ? context.Pre?.GetAttributeValue<EntityReference>(Model.PurchaseOrderId) : context.Get<EntityReference>(Model.PurchaseOrderId);
            var po = system.Retrieve(Model.PurchaseOrder, orderRef.Id, new ColumnSet("statuscode", Model.ProjectId, Model.SupplierId));
            var receiptOnly = context.Message == "Update" && context.ChangesOnly("op365_receivedquantity");
            if (Purchasing.Status(po) != Model.PoDraft && !receiptOnly && !context.IsInside("op365_CreatePurchaseOrder", "op365_AwardRfq"))
                Purchasing.Fail("Lines can be changed only while the purchase order is Draft.");
            if (context.Message == "Delete" || receiptOnly) return;
            Rules.EnsureNodeInProject(system, context.Get<EntityReference>(Model.WbsNodeId), Purchasing.Id(po, Model.ProjectId) ?? Guid.Empty);
            Purchasing.ItemDefaults(context, "op365_price", Purchasing.Id(po, Model.SupplierId));
            var quantity = context.Get<decimal?>("op365_quantity") ?? 0m;
            var price = (target.Contains("op365_price") ? target.GetAttributeValue<Money>("op365_price") : context.Get<Money>("op365_price"))?.Value ?? 0m;
            target["op365_amount"] = new Money(Math.Round(quantity * price, 2));
        }
    }

    /// <summary>
    /// op365_purchaseorderline Create/Update/Delete and op365_purchaseorder Update/Delete, PostOperation (PreImage on
    /// Update/Delete): order total and received amount, project committed cost, supplier spend, item usage and spend.
    /// </summary>
    public class PurchaseTotals : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var system = context.SystemService;
            var projectDelete = context.IsCascadeDeleteOf(Model.Project);
            if (context.Execution.PrimaryEntityName == Model.PurchaseOrderLine)
            {
                var order = (context.Message == "Delete" ? null : context.Get<EntityReference>(Model.PurchaseOrderId)) ?? context.Pre?.GetAttributeValue<EntityReference>(Model.PurchaseOrderId);
                var items = new[] { context.Message == "Delete" ? null : context.Get<EntityReference>(Model.ItemId), context.Pre?.GetAttributeValue<EntityReference>(Model.ItemId) }
                    .Where(i => i != null).Select(i => i.Id).Distinct();
                foreach (var item in items) Purchasing.ItemTotals(system, item);
                if (order == null || projectDelete || context.IsCascadeDeleteOf(Model.PurchaseOrder)) return;
                Purchasing.RecalculateOrder(system, order.Id);
                var po = system.Retrieve(Model.PurchaseOrder, order.Id, new ColumnSet(Model.ProjectId, Model.SupplierId));
                Purchasing.ProjectCommitted(system, Purchasing.Id(po, Model.ProjectId).Value);
                Purchasing.SupplierSpend(system, Purchasing.Id(po, Model.SupplierId).Value);
                return;
            }

            // purchase order: status, project or supplier changed, or deleted
            var after = context.Message == "Delete" ? null : context.Target;
            var projects = new[] { after == null ? null : context.Get<EntityReference>(Model.ProjectId), context.Pre?.GetAttributeValue<EntityReference>(Model.ProjectId) }
                .Where(r => r != null).Select(r => r.Id).ToList();
            var suppliers = new[] { after == null ? null : context.Get<EntityReference>(Model.SupplierId), context.Pre?.GetAttributeValue<EntityReference>(Model.SupplierId) }
                .Where(r => r != null).Select(r => r.Id).ToList();
            if (!projectDelete)
                foreach (var p in projects.Distinct()) Purchasing.ProjectCommitted(system, p);
            foreach (var s in suppliers.Distinct()) Purchasing.SupplierSpend(system, s);
            if (context.Message == "Update" && context.Changed("statuscode"))
                foreach (var item in Purchasing.Children(system, Model.PurchaseOrderLine, Model.PurchaseOrderId, context.PrimaryId, Model.ItemId)
                             .Select(l => Purchasing.Id(l, Model.ItemId)).Where(i => i.HasValue).Select(i => i.Value).Distinct())
                    Purchasing.ItemTotals(system, item);
        }
    }

    /// <summary>
    /// Custom API op365_SetPurchaseOrderStatus (bound). Input Status (string: Sent, Confirmed, Draft, Cancelled).
    /// Draft → Sent (sent to the supplier email) → Confirmed; Sent → Draft to change it; Cancelled without receipts.
    /// </summary>
    public class SetPurchaseOrderStatus : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var system = context.SystemService;
            var id = context.TargetReference.Id;
            var name = (context.Execution.InputParameters["Status"] as string ?? "").Trim();
            var map = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase)
            {
                ["Draft"] = Model.PoDraft, ["Sent"] = Model.PoSent, ["Confirmed"] = Model.PoConfirmed, ["Cancelled"] = Model.PoCancelled, ["Received"] = Model.PoReceived,
            };
            if (!map.ContainsKey(name)) Purchasing.Fail("Status must be Draft, Sent, Confirmed or Cancelled.");
            var to = map[name];
            var po = system.Retrieve(Model.PurchaseOrder, id, new ColumnSet("statuscode", Model.ProjectId, Model.SupplierId));
            var from = Purchasing.Status(po);
            Purchasing.EnsureManager(system, Purchasing.Id(po, Model.ProjectId) ?? Guid.Empty, context.Execution.InitiatingUserId, "change the status of the purchase order");
            var receipts = Purchasing.Children(system, Model.GoodsReceipt, Model.PurchaseOrderId, id).Count > 0;
            var error = OrderStatus.Check(from, to, receipts);
            if (error != null) Purchasing.Fail(error);
            var now = DateTime.UtcNow;
            var update = new Entity(Model.PurchaseOrder, id) { ["statuscode"] = new OptionSetValue(to) };
            if (to == Model.PoSent)
            {
                if (Purchasing.Children(system, Model.PurchaseOrderLine, Model.PurchaseOrderId, id).Count == 0) Purchasing.Fail("Add at least one line before sending.");
                var supplier = system.Retrieve("account", Purchasing.Id(po, Model.SupplierId).Value, new ColumnSet("emailaddress1"));
                update["op365_senton"] = now;
                update["op365_sentto"] = supplier.GetAttributeValue<string>("emailaddress1");
                update["op365_supplierconfirmed"] = false;
            }
            if (to == Model.PoConfirmed) { update["op365_confirmedon"] = now; update["op365_supplierconfirmed"] = true; }
            if (to == Model.PoCancelled) update["op365_cancelledon"] = now;
            system.Update(update);
        }
    }

    // ---------------------------------------------------------------- goods receipts

    /// <summary>
    /// Custom API op365_RegisterGoodsReceipt (bound to a Sent or Confirmed op365_purchaseorder). Inputs ReceiptDate (DateTime,
    /// default today), DeliveryNoteNumber (string), DeliveryNoteDate (DateTime), Lines (string array "orderLineId=quantity";
    /// default everything still to receive). Output GoodsReceiptId. Creates the receipt and its lines, one Material Usage per
    /// line at the order price, updates received quantities and marks the order Received when complete.
    /// </summary>
    public class RegisterGoodsReceipt : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var system = context.SystemService;
            var input = context.Execution.InputParameters;
            var id = context.TargetReference.Id;
            var po = system.Retrieve(Model.PurchaseOrder, id, new ColumnSet("statuscode", Model.ProjectId, Model.SupplierId, "op365_number"));
            var status = Purchasing.Status(po);
            if (status != Model.PoSent && status != Model.PoConfirmed) Purchasing.Fail("Goods can be received only on sent or confirmed purchase orders.");
            var projectId = Purchasing.Id(po, Model.ProjectId).Value;
            Purchasing.EnsureContributor(system, projectId, context.Execution.InitiatingUserId, "register goods receipts");
            Rules.EnsureInProgress(system, projectId);

            var lines = Purchasing.Children(system, Model.PurchaseOrderLine, Model.PurchaseOrderId, id,
                "op365_name", "op365_quantity", "op365_receivedquantity", "op365_price", "op365_uom", Model.ItemId, Model.WbsNodeId, "op365_sortorder")
                .ToDictionary(l => l.Id);
            var wanted = new Dictionary<Guid, decimal>();
            var given = input.Contains("Lines") ? input["Lines"] as string[] : null;
            if (given != null && given.Length > 0)
            {
                foreach (var value in given)
                {
                    Tuple<Guid, decimal> line;
                    try { line = PurchaseMath.ReceiptLine(value); }
                    catch (ArgumentException ex) { throw new InvalidPluginExecutionException(ex.Message); }
                    if (!lines.ContainsKey(line.Item1)) Purchasing.Fail("A receipt line belongs to another purchase order.");
                    if (line.Item2 <= 0m) continue;
                    wanted[line.Item1] = (wanted.ContainsKey(line.Item1) ? wanted[line.Item1] : 0m) + line.Item2;
                }
            }
            else
            {
                foreach (var l in lines.Values)
                {
                    var r = Purchasing.Row(l);
                    if (r.Quantity > r.Received) wanted[l.Id] = r.Quantity - r.Received;
                }
            }
            if (wanted.Count == 0) Purchasing.Fail("Nothing to receive.");
            foreach (var w in wanted)
            {
                var r = Purchasing.Row(lines[w.Key]);
                if (w.Value > r.Quantity - r.Received)
                    Purchasing.Fail($"{lines[w.Key].GetAttributeValue<string>("op365_name")}: only {r.Quantity - r.Received:0.###} still to receive.");
            }

            var date = Rules.OptionalDate(input, "ReceiptDate") ?? DateTime.UtcNow.Date;
            var receipt = new Entity(Model.GoodsReceipt)
            {
                [Model.PurchaseOrderId] = new EntityReference(Model.PurchaseOrder, id),
                [Model.ProjectId] = new EntityReference(Model.Project, projectId),
                ["op365_receiptdate"] = date,
            };
            if (input.Contains("DeliveryNoteNumber")) receipt["op365_deliverynotenumber"] = input["DeliveryNoteNumber"] as string;
            var noteDate = Rules.OptionalDate(input, "DeliveryNoteDate");
            if (noteDate.HasValue) receipt["op365_deliverynotedate"] = noteDate.Value;
            var receiptId = system.Create(receipt);

            foreach (var w in wanted.OrderBy(x => lines[x.Key].GetAttributeValue<int?>("op365_sortorder") ?? 0))
            {
                var l = lines[w.Key];
                var lineId = system.Create(new Entity(Model.GoodsReceiptLine)
                {
                    [Model.GoodsReceiptId] = new EntityReference(Model.GoodsReceipt, receiptId),
                    [Model.OrderLineId] = new EntityReference(Model.PurchaseOrderLine, l.Id),
                    ["op365_name"] = l.GetAttributeValue<string>("op365_name"),
                    ["op365_quantity"] = w.Value,
                });
                var usage = new Entity(Model.MaterialUsage)
                {
                    [Model.ProjectId] = new EntityReference(Model.Project, projectId),
                    ["op365_goodsreceiptlineid"] = new EntityReference(Model.GoodsReceiptLine, lineId),
                    [Model.SupplierId] = po.GetAttributeValue<EntityReference>(Model.SupplierId),
                    ["op365_name"] = l.GetAttributeValue<string>("op365_name"),
                    ["op365_uom"] = l.GetAttributeValue<string>("op365_uom"),
                    ["op365_quantity"] = w.Value,
                    ["op365_unitcost"] = new Money(Purchasing.Amount(l, "op365_price")),
                    ["op365_usagedate"] = date,
                };
                if (l.Contains(Model.ItemId)) usage[Model.ItemId] = l[Model.ItemId];
                if (l.Contains(Model.WbsNodeId)) usage[Model.WbsNodeId] = l[Model.WbsNodeId];
                system.Create(usage);
                var received = (l.GetAttributeValue<decimal?>("op365_receivedquantity") ?? 0m) + w.Value;
                system.Update(new Entity(Model.PurchaseOrderLine, l.Id) { ["op365_receivedquantity"] = received });
                l["op365_receivedquantity"] = received;
            }
            if (PurchaseMath.FullyReceived(lines.Values.Select(Purchasing.Row)))
                system.Update(new Entity(Model.PurchaseOrder, id) { ["statuscode"] = new OptionSetValue(Model.PoReceived), ["op365_receivedon"] = DateTime.UtcNow });
            context.Execution.OutputParameters["GoodsReceiptId"] = receiptId;
        }
    }

    /// <summary>
    /// Custom API op365_CancelGoodsReceipt (bound to op365_goodsreceipt): deletes its material usage, lines and the receipt,
    /// restores the received quantities and moves a Received order back to Confirmed.
    /// </summary>
    public class CancelGoodsReceipt : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var system = context.SystemService;
            var id = context.TargetReference.Id;
            var gr = system.Retrieve(Model.GoodsReceipt, id, new ColumnSet(Model.PurchaseOrderId, Model.ProjectId));
            var projectId = Purchasing.Id(gr, Model.ProjectId).Value;
            Purchasing.EnsureManager(system, projectId, context.Execution.InitiatingUserId, "cancel goods receipts");
            foreach (var line in Purchasing.Children(system, Model.GoodsReceiptLine, Model.GoodsReceiptId, id, Model.OrderLineId, "op365_quantity"))
            {
                var usages = new QueryExpression(Model.MaterialUsage) { ColumnSet = new ColumnSet(false) };
                usages.Criteria.AddCondition("op365_goodsreceiptlineid", ConditionOperator.Equal, line.Id);
                foreach (var u in system.RetrieveMultiple(usages).Entities) system.Delete(Model.MaterialUsage, u.Id);
                var orderLine = Purchasing.Id(line, Model.OrderLineId);
                if (orderLine.HasValue)
                {
                    var ol = system.Retrieve(Model.PurchaseOrderLine, orderLine.Value, new ColumnSet("op365_receivedquantity"));
                    var received = Math.Max(0m, (ol.GetAttributeValue<decimal?>("op365_receivedquantity") ?? 0m) - (line.GetAttributeValue<decimal?>("op365_quantity") ?? 0m));
                    system.Update(new Entity(Model.PurchaseOrderLine, orderLine.Value) { ["op365_receivedquantity"] = received });
                }
                system.Delete(Model.GoodsReceiptLine, line.Id);
            }
            system.Delete(Model.GoodsReceipt, id);
            var order = Purchasing.Id(gr, Model.PurchaseOrderId);
            if (order.HasValue && Purchasing.Status(system.Retrieve(Model.PurchaseOrder, order.Value, new ColumnSet("statuscode"))) == Model.PoReceived)
                system.Update(new Entity(Model.PurchaseOrder, order.Value) { ["statuscode"] = new OptionSetValue(Model.PoConfirmed), ["op365_receivedon"] = null });
        }
    }

    /// <summary>
    /// op365_goodsreceipt and op365_goodsreceiptline Create/Update/Delete, PreOperation: receipts are created and cancelled
    /// only with Register Receipt and Cancel Receipt; afterwards only the delivery note and notes can change.
    /// </summary>
    public class GoodsReceiptGuard : PluginBase
    {
        private static readonly string[] Free = { "op365_deliverynotenumber", "op365_deliverynotedate", "op365_notes", "modifiedon" };

        protected override void Run(LocalContext context)
        {
            if (context.IsInside(Purchasing.ReceiptApis) || context.IsCascadeDeleteOf(Model.Project) || context.IsCascadeDeleteOf(Model.GoodsReceipt)) return;
            if (context.Message == "Update" && context.Execution.PrimaryEntityName == Model.GoodsReceipt && context.ChangesOnly(Free)) return;
            Purchasing.Fail("Use Register Receipt on the purchase order to receive goods, and Cancel Receipt to undo a receipt.");
        }
    }

    /// <summary>op365_materialusage Update/Delete, PreOperation (PreImage): usage created by a goods receipt changes only with the receipt.</summary>
    public class MaterialUsageReceiptGuard : PluginBase
    {
        private static readonly string[] Free = { "op365_wbsnodeid", "modifiedon" };

        protected override void Run(LocalContext context)
        {
            if (context.Pre?.GetAttributeValue<EntityReference>("op365_goodsreceiptlineid") == null) return;
            if (context.IsInside(Purchasing.ReceiptApis) || context.IsCascadeDeleteOf(Model.Project)) return;
            if (context.Message == "Update" && context.ChangesOnly(Free)) return;
            Purchasing.Fail("This material usage comes from a goods receipt: cancel the receipt to change it.");
        }
    }

    // ---------------------------------------------------------------- supplier invoices

    /// <summary>
    /// op365_supplierinvoice Create/Update, PreOperation (PreImage on Update): status only through Approve/Reject, decided invoices
    /// locked; seller name and VAT number from the supplier, project from the purchase order.
    /// </summary>
    public class SupplierInvoiceValidate : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var system = context.SystemService;
            var target = context.Target;
            if (context.IsInside("op365_DecideSupplierInvoice")) return;
            if (context.Message == "Create")
            {
                var status = target.GetAttributeValue<OptionSetValue>("statuscode")?.Value;
                if (status.HasValue && status != Model.InvoiceToReview) Purchasing.Fail("Use Approve or Reject to decide a supplier invoice.");
            }
            else
            {
                if (target.Contains("statuscode") || target.Contains("statecode")) Purchasing.Fail("Use Approve or Reject to decide a supplier invoice.");
                if (Purchasing.Status(context.Pre) != Model.InvoiceToReview)
                    Purchasing.Fail("Approved or rejected invoices cannot be changed.");
            }
            var supplier = context.Get<EntityReference>(Model.SupplierId);
            if (supplier != null && context.Changed(Model.SupplierId))
            {
                var a = system.Retrieve("account", supplier.Id, new ColumnSet("name", "op365_vatnumber"));
                if (string.IsNullOrEmpty(context.Get<string>("op365_sellername"))) target["op365_sellername"] = a.GetAttributeValue<string>("name");
                if (string.IsNullOrEmpty(context.Get<string>("op365_sellervatnumber"))) target["op365_sellervatnumber"] = a.GetAttributeValue<string>("op365_vatnumber");
            }
            var order = context.Get<EntityReference>(Model.PurchaseOrderId);
            if (order != null && context.Changed(Model.PurchaseOrderId) && context.Get<EntityReference>(Model.ProjectId) == null)
                target[Model.ProjectId] = system.Retrieve(Model.PurchaseOrder, order.Id, new ColumnSet(Model.ProjectId)).GetAttributeValue<EntityReference>(Model.ProjectId);
        }
    }

    /// <summary>
    /// op365_supplierinvoiceline Create/Update/Delete, PreOperation (PreImage on Update/Delete): invoice To Review;
    /// total price = quantity x unit price when empty.
    /// </summary>
    public class SupplierInvoiceLineValidate : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.IsCascadeDeleteOf(Model.SupplierInvoice)) return;
            var invoice = context.Message == "Delete" ? context.Pre?.GetAttributeValue<EntityReference>(Model.SupplierInvoiceId) : context.Get<EntityReference>(Model.SupplierInvoiceId);
            if (Purchasing.Status(context.SystemService.Retrieve(Model.SupplierInvoice, invoice.Id, new ColumnSet("statuscode"))) != Model.InvoiceToReview)
                Purchasing.Fail("Lines of approved or rejected invoices cannot be changed.");
            if (context.Message == "Delete") return;
            var target = context.Target;
            if (!target.Contains("op365_totalprice") && (context.Changed("op365_quantity") || context.Changed("op365_unitprice")))
            {
                var quantity = context.Get<decimal?>("op365_quantity");
                var unit = context.Get<Money>("op365_unitprice");
                if (quantity.HasValue && unit != null) target["op365_totalprice"] = new Money(Math.Round(quantity.Value * unit.Value, 2));
            }
        }
    }

    /// <summary>op365_supplierinvoiceline Create/Update/Delete, PostOperation (PreImage on Update/Delete): invoice taxable, VAT and total from the lines.</summary>
    public class SupplierInvoiceTotals : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.IsCascadeDeleteOf(Model.SupplierInvoice)) return;
            var invoice = (context.Message == "Delete" ? null : context.Get<EntityReference>(Model.SupplierInvoiceId)) ?? context.Pre?.GetAttributeValue<EntityReference>(Model.SupplierInvoiceId);
            if (invoice == null) return;
            var system = context.SystemService;
            var lines = Purchasing.Children(system, Model.SupplierInvoiceLine, Model.SupplierInvoiceId, invoice.Id, "op365_totalprice", "op365_vatrate");
            var taxable = lines.Sum(l => Purchasing.Amount(l, "op365_totalprice"));
            var vat = lines.Sum(l => Math.Round(Purchasing.Amount(l, "op365_totalprice") * (l.GetAttributeValue<decimal?>("op365_vatrate") ?? 0m) / 100m, 2));
            system.Update(new Entity(Model.SupplierInvoice, invoice.Id)
            {
                ["op365_taxableamount"] = new Money(taxable),
                ["op365_vatamount"] = new Money(vat),
                ["op365_totalamount"] = new Money(taxable + vat),
            });
        }
    }

    /// <summary>
    /// Custom API op365_DecideSupplierInvoice (bound). Inputs Approve (bool), Note (string; required to reject).
    /// To Review → Approved or Rejected; the Purchasing Approver of Settings or an administrator decides.
    /// </summary>
    public class DecideSupplierInvoice : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var input = context.Execution.InputParameters;
            var approve = input.Contains("Approve") && input["Approve"] is bool a && a;
            var note = input.Contains("Note") ? input["Note"] as string : null;
            if (!approve && string.IsNullOrWhiteSpace(note)) Purchasing.Fail("Add a note to reject the invoice.");
            var system = context.SystemService;
            var caller = context.Execution.InitiatingUserId;
            var id = context.TargetReference.Id;
            if (Purchasing.Status(system.Retrieve(Model.SupplierInvoice, id, new ColumnSet("statuscode"))) != Model.InvoiceToReview)
                Purchasing.Fail("Only invoices to review can be approved or rejected.");
            if (!Purchasing.IsSecondLevelApprover(system, caller)) Purchasing.Fail("Only the purchasing approver or an administrator can decide supplier invoices.");
            system.Update(new Entity(Model.SupplierInvoice, id)
            {
                ["statuscode"] = new OptionSetValue(approve ? Model.InvoiceApproved : Model.InvoiceRejected),
                ["op365_decidedbyid"] = new EntityReference("systemuser", caller),
                ["op365_decidedon"] = DateTime.UtcNow,
                ["op365_decisionnote"] = note,
            });
        }
    }

    /// <summary>contact Create/Update/Delete, PostOperation (PreImage on Update/Delete): account contact count.</summary>
    public class ContactCount : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.IsCascadeDeleteOf("account")) return;
            var accounts = new[] { context.Message == "Delete" ? null : context.Get<EntityReference>("parentcustomerid"), context.Pre?.GetAttributeValue<EntityReference>("parentcustomerid") }
                .Where(r => r != null && r.LogicalName == "account").Select(r => r.Id).Distinct();
            var system = context.SystemService;
            foreach (var account in accounts)
            {
                var query = new QueryExpression("contact") { ColumnSet = new ColumnSet(false) };
                query.Criteria.AddCondition("parentcustomerid", ConditionOperator.Equal, account);
                query.Criteria.AddCondition("statecode", ConditionOperator.Equal, 0);
                system.Update(new Entity("account", account) { ["op365_contactcount"] = system.RetrieveMultiple(query).Entities.Count });
            }
        }
    }
}
