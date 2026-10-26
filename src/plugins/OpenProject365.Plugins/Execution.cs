using System;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;

namespace OpenProject365.Plugins
{
    /// <summary>
    /// op365_timeentry Create/Update, PreOperation (PreImage on Update): status changes only through the Custom APIs,
    /// submitted and approved entries locked, project In Progress, WBS node of the project, resource defaulted to the
    /// caller's resource, cost (hourly cost valid on the date) and revenue (member hourly rate), name.
    /// </summary>
    public class TimeEntryValidate : PluginBase
    {
        public static readonly string[] Apis = { "op365_SubmitTimeEntries", "op365_DecideTimeEntries" };
        private static readonly string[] Inputs = { Model.ProjectId, Model.WbsNodeId, Model.ResourceId, "op365_entrydate", "op365_hours" };

        protected override void Run(LocalContext context)
        {
            var target = context.Target;
            var byApi = context.IsInside(Apis);
            if (!byApi)
            {
                var status = target.GetAttributeValue<OptionSetValue>("statuscode")?.Value;
                if (context.Message == "Create" ? status.HasValue && status != Model.TimeDraft : target.Contains("statuscode") || target.Contains("statecode"))
                    throw new InvalidPluginExecutionException("Use Submit, Approve or Reject to change the status of time entries.");
                var current = context.Pre?.GetAttributeValue<OptionSetValue>("statuscode")?.Value;
                if (current == Model.TimeSubmitted || current == Model.TimeApproved)
                    throw new InvalidPluginExecutionException("Submitted or approved time entries cannot be changed.");
            }
            if (context.Message == "Update" && !Inputs.Any(context.Changed)) return;

            var system = context.SystemService;
            if (context.Get<EntityReference>(Model.ResourceId) == null)
                target[Model.ResourceId] = CallerResource(system, context.Execution.InitiatingUserId);
            var project = context.Get<EntityReference>(Model.ProjectId);
            var resource = context.Get<EntityReference>(Model.ResourceId);
            var date = context.Get<DateTime?>("op365_entrydate") ?? DateTime.UtcNow.Date;
            var hours = context.Get<decimal?>("op365_hours") ?? 0m;
            if (!byApi) Rules.EnsureInProgress(system, project.Id);
            Rules.EnsureNodeInProject(system, context.Get<EntityReference>(Model.WbsNodeId), project.Id);

            var res = system.Retrieve(Model.Resource, resource.Id, new ColumnSet("op365_name", "op365_userid"));
            target["op365_cost"] = new Money(Math.Round(hours * Rules.HourlyCostAt(system, resource.Id, date), 2));
            target["op365_revenue"] = new Money(Math.Round(hours * MemberRate(system, project.Id, res.GetAttributeValue<EntityReference>("op365_userid")), 2));
            var name = res.GetAttributeValue<string>("op365_name") + " " + date.ToString("yyyy-MM-dd");
            target["op365_name"] = name.Length > 200 ? name.Substring(0, 200) : name;
        }

        private static EntityReference CallerResource(IOrganizationService system, Guid userId)
        {
            var query = new QueryExpression(Model.Resource) { ColumnSet = new ColumnSet(false), TopCount = 1 };
            query.Criteria.AddCondition("op365_userid", ConditionOperator.Equal, userId);
            query.Criteria.AddCondition("statecode", ConditionOperator.Equal, 0);
            var found = system.RetrieveMultiple(query).Entities.FirstOrDefault();
            if (found == null)
                throw new InvalidPluginExecutionException("Your user is not linked to a resource. Ask an administrator to set User on your Resource.");
            return found.ToEntityReference();
        }

        private static decimal MemberRate(IOrganizationService system, Guid projectId, EntityReference user)
        {
            if (user == null) return 0m;
            var query = new QueryExpression(Model.ProjectMember) { ColumnSet = new ColumnSet("op365_hourlyrate"), TopCount = 1 };
            query.Criteria.AddCondition(Model.ProjectId, ConditionOperator.Equal, projectId);
            query.Criteria.AddCondition(Model.UserId, ConditionOperator.Equal, user.Id);
            return system.RetrieveMultiple(query).Entities.FirstOrDefault()?.GetAttributeValue<Money>("op365_hourlyrate")?.Value ?? 0m;
        }
    }

    /// <summary>op365_timeentry Delete, PreOperation (PreImage): submitted and approved entries cannot be deleted.</summary>
    public class TimeEntryDelete : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.IsCascadeDeleteOf(Model.Project)) return;
            var status = context.Pre?.GetAttributeValue<OptionSetValue>("statuscode")?.Value;
            if (status == Model.TimeSubmitted || status == Model.TimeApproved)
                throw new InvalidPluginExecutionException("Submitted or approved time entries cannot be deleted.");
        }
    }

    /// <summary>
    /// op365_materialusage Create/Update, PreOperation (PreImage on Update): project In Progress, WBS node of the project,
    /// description, unit of measure and unit cost from the item (supplier price first), total cost.
    /// </summary>
    public class MaterialUsageValidate : PluginBase
    {
        private static readonly string[] Inputs = { Model.ProjectId, Model.WbsNodeId, "op365_itemid", "op365_supplierid", "op365_quantity", "op365_unitcost" };

        protected override void Run(LocalContext context)
        {
            if (context.Message == "Update" && !Inputs.Any(context.Changed)) return;
            var system = context.SystemService;
            var target = context.Target;
            var project = context.Get<EntityReference>(Model.ProjectId);
            if (!context.IsInside("op365_RegisterGoodsReceipt")) Rules.EnsureInProgress(system, project.Id);
            Rules.EnsureNodeInProject(system, context.Get<EntityReference>(Model.WbsNodeId), project.Id);

            var item = context.Get<EntityReference>("op365_itemid");
            if (item != null && context.Changed("op365_itemid"))
            {
                var i = system.Retrieve(Model.Item, item.Id, new ColumnSet("op365_name", "op365_uom", "op365_unitcost"));
                if (string.IsNullOrEmpty(context.Get<string>("op365_name"))) target["op365_name"] = i.GetAttributeValue<string>("op365_name");
                if (string.IsNullOrEmpty(context.Get<string>("op365_uom"))) target["op365_uom"] = i.GetAttributeValue<string>("op365_uom");
                if (context.Get<Money>("op365_unitcost") == null)
                    target["op365_unitcost"] = SupplierPrice(system, item.Id, context.Get<EntityReference>("op365_supplierid")) ?? i.GetAttributeValue<Money>("op365_unitcost");
            }
            var quantity = context.Get<decimal?>("op365_quantity") ?? 0m;
            var unit = (target.Contains("op365_unitcost") ? target.GetAttributeValue<Money>("op365_unitcost") : context.Get<Money>("op365_unitcost"))?.Value ?? 0m;
            target["op365_totalcost"] = new Money(Math.Round(quantity * unit, 2));
        }

        private static Money SupplierPrice(IOrganizationService system, Guid itemId, EntityReference supplier)
        {
            if (supplier == null) return null;
            var query = new QueryExpression("op365_itemsupplier") { ColumnSet = new ColumnSet("op365_price"), TopCount = 1 };
            query.Criteria.AddCondition("op365_itemid", ConditionOperator.Equal, itemId);
            query.Criteria.AddCondition("op365_supplierid", ConditionOperator.Equal, supplier.Id);
            query.Criteria.AddCondition("statecode", ConditionOperator.Equal, 0);
            return system.RetrieveMultiple(query).Entities.FirstOrDefault()?.GetAttributeValue<Money>("op365_price");
        }
    }

    /// <summary>
    /// op365_timeentry and op365_materialusage Create/Update/Delete, PostOperation (PreImage on Update/Delete):
    /// actual hours and costs of the WBS nodes and the project.
    /// </summary>
    public class ActualsRollup : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.IsCascadeDeleteOf(Model.Project)) return;
            var before = context.Pre?.GetAttributeValue<EntityReference>(Model.ProjectId);
            var after = context.Message == "Delete" ? null : context.Get<EntityReference>(Model.ProjectId);
            if (after != null) Actuals.Recalculate(context.SystemService, after.Id);
            if (before != null && (after == null || before.Id != after.Id)) Actuals.Recalculate(context.SystemService, before.Id);
        }
    }

    /// <summary>
    /// Custom API op365_SubmitTimeEntries (unbound). Input TimeEntryIds (string array). Output Count (int).
    /// Draft or Rejected entries of the caller (or any entry for an administrator) become Submitted, or Approved
    /// directly when the time approval environment variable is off. Project managers get an in-app notification.
    /// </summary>
    public class SubmitTimeEntries : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var system = context.SystemService;
            var caller = context.Execution.InitiatingUserId;
            var admin = Rules.IsAdmin(system, caller);
            var approval = Settings.TimeApprovalEnabled(system);
            var now = DateTime.UtcNow;
            var projects = new System.Collections.Generic.Dictionary<Guid, int>();
            foreach (var id in Rules.Ids(context.Execution.InputParameters, "TimeEntryIds"))
            {
                var e = context.Service.Retrieve(Model.TimeEntry, id, new ColumnSet("statuscode", Model.ProjectId, Model.ResourceId));
                var status = e.GetAttributeValue<OptionSetValue>("statuscode")?.Value;
                if (status != Model.TimeDraft && status != Model.TimeRejected)
                    throw new InvalidPluginExecutionException("Only draft or rejected time entries can be submitted.");
                var user = system.Retrieve(Model.Resource, e.GetAttributeValue<EntityReference>(Model.ResourceId).Id, new ColumnSet("op365_userid"))
                    .GetAttributeValue<EntityReference>("op365_userid");
                if (!admin && user?.Id != caller)
                    throw new InvalidPluginExecutionException("You can submit only your own time entries.");
                var update = new Entity(Model.TimeEntry, id)
                {
                    ["statuscode"] = new OptionSetValue(approval ? Model.TimeSubmitted : Model.TimeApproved),
                    ["op365_submittedon"] = now,
                };
                if (!approval)
                {
                    update["op365_decidedon"] = now;
                    update["op365_decidedbyid"] = new EntityReference("systemuser", caller);
                }
                system.Update(update);
                var project = e.GetAttributeValue<EntityReference>(Model.ProjectId).Id;
                projects[project] = (projects.ContainsKey(project) ? projects[project] : 0) + 1;
            }
            if (approval)
            {
                foreach (var p in projects)
                {
                    var name = system.Retrieve(Model.Project, p.Key, new ColumnSet("op365_name")).GetAttributeValue<string>("op365_name");
                    foreach (var manager in Rules.ProjectManagers(system, p.Key).Where(m => m != caller))
                        Rules.Notify(context, manager, "Time entries to approve", $"{p.Value} time entries submitted on {name}.");
                }
            }
            context.Execution.OutputParameters["Count"] = projects.Values.Sum();
        }
    }

    /// <summary>
    /// Custom API op365_DecideTimeEntries (unbound). Inputs TimeEntryIds (string array), Approve (bool), Note (string).
    /// Output Count (int). Submitted entries become Approved or Rejected; only a Manager of the project or an
    /// administrator can decide. The resource's user gets an in-app notification.
    /// </summary>
    public class DecideTimeEntries : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var input = context.Execution.InputParameters;
            var approve = input.Contains("Approve") && input["Approve"] is bool a && a;
            var note = input.Contains("Note") ? input["Note"] as string : null;
            if (!approve && string.IsNullOrWhiteSpace(note))
                throw new InvalidPluginExecutionException("Add a note to reject time entries.");
            var system = context.SystemService;
            var caller = context.Execution.InitiatingUserId;
            var admin = Rules.IsAdmin(system, caller);
            var now = DateTime.UtcNow;
            var count = 0;
            var notify = new System.Collections.Generic.Dictionary<Guid, int>();
            foreach (var id in Rules.Ids(input, "TimeEntryIds"))
            {
                var e = system.Retrieve(Model.TimeEntry, id, new ColumnSet("statuscode", Model.ProjectId, Model.ResourceId));
                if (e.GetAttributeValue<OptionSetValue>("statuscode")?.Value != Model.TimeSubmitted)
                    throw new InvalidPluginExecutionException("Only submitted time entries can be approved or rejected.");
                if (!admin && !Rules.IsProjectManager(system, e.GetAttributeValue<EntityReference>(Model.ProjectId).Id, caller))
                    throw new InvalidPluginExecutionException("Only a manager of the project can approve or reject its time entries.");
                system.Update(new Entity(Model.TimeEntry, id)
                {
                    ["statuscode"] = new OptionSetValue(approve ? Model.TimeApproved : Model.TimeRejected),
                    ["op365_decidedon"] = now,
                    ["op365_decidedbyid"] = new EntityReference("systemuser", caller),
                    ["op365_decisionnote"] = note,
                });
                count++;
                var user = system.Retrieve(Model.Resource, e.GetAttributeValue<EntityReference>(Model.ResourceId).Id, new ColumnSet("op365_userid"))
                    .GetAttributeValue<EntityReference>("op365_userid");
                if (user != null && user.Id != caller) notify[user.Id] = (notify.ContainsKey(user.Id) ? notify[user.Id] : 0) + 1;
            }
            foreach (var n in notify)
                Rules.Notify(context, n.Key, approve ? "Time entries approved" : "Time entries rejected",
                    $"{n.Value} of your time entries were {(approve ? "approved" : "rejected")}." + (string.IsNullOrWhiteSpace(note) ? "" : " Note: " + note));
            context.Execution.OutputParameters["Count"] = count;
        }
    }

    /// <summary>
    /// Custom API op365_GetLabourCost (unbound function). Inputs ResourceId (Guid), Date (DateTime). Output HourlyCost (decimal).
    /// Read with the caller's privileges, so column security on hourly costs applies (0 without the Cost Visibility profile).
    /// </summary>
    public class GetLabourCost : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var input = context.Execution.InputParameters;
            var resource = (Guid)input["ResourceId"];
            var date = input.Contains("Date") && input["Date"] is DateTime d ? d : DateTime.UtcNow;
            context.Execution.OutputParameters["HourlyCost"] = Rules.HourlyCostAt(context.Service, resource, date);
        }
    }
}
