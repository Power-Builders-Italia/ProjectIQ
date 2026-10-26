using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;

namespace OpenProject365.Plugins
{
    /// <summary>Rules shared by time entries, material usage and the Custom APIs.</summary>
    internal static class Rules
    {
        public static void EnsureInProgress(IOrganizationService service, Guid projectId)
        {
            var p = service.Retrieve(Model.Project, projectId, new ColumnSet("statecode", "statuscode"));
            if (p.GetAttributeValue<OptionSetValue>("statecode")?.Value != 0
                || p.GetAttributeValue<OptionSetValue>("statuscode")?.Value != Model.ProjectInProgress)
                throw new InvalidPluginExecutionException("Hours and materials can be recorded only on projects In Progress.");
        }

        public static void EnsureNodeInProject(IOrganizationService service, EntityReference node, Guid projectId)
        {
            if (node == null) return;
            var project = service.Retrieve(Model.WbsNode, node.Id, new ColumnSet(Model.ProjectId)).GetAttributeValue<EntityReference>(Model.ProjectId);
            if (project?.Id != projectId)
                throw new InvalidPluginExecutionException("The WBS node belongs to another project.");
        }

        /// <summary>Hourly cost valid on the date: latest Resource Cost not after it, else the resource's current cost.</summary>
        public static decimal HourlyCostAt(IOrganizationService service, Guid resourceId, DateTime date)
        {
            var query = new QueryExpression(Model.ResourceCost) { ColumnSet = new ColumnSet("op365_hourlycost"), TopCount = 1 };
            query.Criteria.AddCondition(Model.ResourceId, ConditionOperator.Equal, resourceId);
            query.Criteria.AddCondition("op365_validfrom", ConditionOperator.OnOrBefore, date.Date);
            query.Criteria.AddCondition("statecode", ConditionOperator.Equal, 0);
            query.AddOrder("op365_validfrom", OrderType.Descending);
            var cost = service.RetrieveMultiple(query).Entities.FirstOrDefault()?.GetAttributeValue<Money>("op365_hourlycost");
            if (cost != null) return cost.Value;
            return service.Retrieve(Model.Resource, resourceId, new ColumnSet("op365_hourlycost"))
                .GetAttributeValue<Money>("op365_hourlycost")?.Value ?? 0m;
        }

        /// <summary>System Administrator or OP365 Administrator.</summary>
        public static bool IsAdmin(IOrganizationService system, Guid userId)
        {
            var query = new QueryExpression("role") { ColumnSet = new ColumnSet(false), TopCount = 1 };
            query.Criteria.AddCondition("name", ConditionOperator.In, "System Administrator", "OP365 Administrator");
            var link = query.AddLink("systemuserroles", "roleid", "roleid");
            link.LinkCriteria.AddCondition("systemuserid", ConditionOperator.Equal, userId);
            return system.RetrieveMultiple(query).Entities.Count > 0;
        }

        public static bool IsProjectManager(IOrganizationService system, Guid projectId, Guid userId)
        {
            var query = new QueryExpression(Model.ProjectMember) { ColumnSet = new ColumnSet(false), TopCount = 1 };
            query.Criteria.AddCondition(Model.ProjectId, ConditionOperator.Equal, projectId);
            query.Criteria.AddCondition(Model.UserId, ConditionOperator.Equal, userId);
            query.Criteria.AddCondition(Model.ProjectRole, ConditionOperator.Equal, Model.RoleManager);
            return system.RetrieveMultiple(query).Entities.Count > 0;
        }

        public static IEnumerable<Guid> ProjectManagers(IOrganizationService system, Guid projectId)
        {
            var query = new QueryExpression(Model.ProjectMember) { ColumnSet = new ColumnSet(Model.UserId) };
            query.Criteria.AddCondition(Model.ProjectId, ConditionOperator.Equal, projectId);
            query.Criteria.AddCondition(Model.ProjectRole, ConditionOperator.Equal, Model.RoleManager);
            return system.RetrieveMultiple(query).Entities
                .Select(m => m.GetAttributeValue<EntityReference>(Model.UserId)?.Id ?? Guid.Empty)
                .Where(id => id != Guid.Empty).Distinct().ToList();
        }

        /// <summary>In-app notification (model-driven app bell). Never fails the calling operation.</summary>
        public static void Notify(LocalContext context, Guid userId, string title, string body, string actionTitle = null, string actionUrl = null)
        {
            try
            {
                var notification = new Entity("appnotification")
                {
                    ["title"] = title,
                    ["body"] = body,
                    ["ownerid"] = new EntityReference("systemuser", userId),
                    ["icontype"] = new OptionSetValue(100000000),   // info
                    ["toasttype"] = new OptionSetValue(200000000),  // timed
                };
                if (actionUrl != null)
                    notification["data"] = "{\"actions\":[{\"title\":\"" + actionTitle + "\",\"data\":{\"url\":\"" + actionUrl + "\"}}]}";
                context.SystemService.Create(notification);
            }
            catch (Exception ex)
            {
                context.Trace("notification skipped: {0}", ex.Message);
            }
        }

        /// <summary>Optional DateTime input of a Custom API (an omitted one arrives as DateTime.MinValue).</summary>
        public static DateTime? OptionalDate(ParameterCollection input, string name) =>
            input.Contains(name) && input[name] is DateTime d && d.Year > 1900 ? d.Date : (DateTime?)null;

        /// <summary>Guids from a Custom API StringArray input.</summary>
        public static List<Guid> Ids(ParameterCollection input, string name)
        {
            var values = input.Contains(name) ? input[name] as string[] : null;
            var ids = new List<Guid>();
            foreach (var v in values ?? new string[0])
            {
                Guid id;
                if (Guid.TryParse(v, out id)) ids.Add(id);
            }
            if (ids.Count == 0) throw new InvalidPluginExecutionException("Select at least one time entry.");
            return ids.Distinct().ToList();
        }
    }

    /// <summary>Actual hours and costs of a project and its WBS nodes, from approved hours and all material usage.</summary>
    internal static class Actuals
    {
        public static void Recalculate(IOrganizationService system, Guid projectId)
        {
            var hours = Sum(system, Model.TimeEntry, projectId, "op365_hours", Model.TimeApproved);
            var labour = Sum(system, Model.TimeEntry, projectId, "op365_cost", Model.TimeApproved);
            var materials = Sum(system, Model.MaterialUsage, projectId, "op365_totalcost", null);

            var query = new QueryExpression(Model.WbsNode) { ColumnSet = new ColumnSet(Model.ActualHours, Model.ActualCost) };
            query.Criteria.AddCondition(Model.ProjectId, ConditionOperator.Equal, projectId);
            foreach (var n in system.RetrieveMultiple(query).Entities)
            {
                var h = hours.ContainsKey(n.Id) ? hours[n.Id] : 0m;
                var c = (labour.ContainsKey(n.Id) ? labour[n.Id] : 0m) + (materials.ContainsKey(n.Id) ? materials[n.Id] : 0m);
                if (n.GetAttributeValue<decimal?>(Model.ActualHours) == h && n.GetAttributeValue<Money>(Model.ActualCost)?.Value == c) continue;
                system.Update(new Entity(Model.WbsNode, n.Id) { [Model.ActualHours] = h, [Model.ActualCost] = new Money(c) });
            }
            system.Update(new Entity(Model.Project, projectId)
            {
                [Model.ActualHours] = hours.Values.Sum(),
                [Model.ActualCost] = new Money(labour.Values.Sum() + materials.Values.Sum()),
            });
        }

        /// <summary>Sum of a column by WBS node (Guid.Empty = no node).</summary>
        private static Dictionary<Guid, decimal> Sum(IOrganizationService system, string table, Guid projectId, string column, int? status)
        {
            var fetch = $@"<fetch aggregate='true'><entity name='{table}'>
                <attribute name='{column}' alias='total' aggregate='sum' />
                <attribute name='op365_wbsnodeid' alias='node' groupby='true' />
                <filter><condition attribute='op365_projectid' operator='eq' value='{projectId}' />
                <condition attribute='statecode' operator='eq' value='0' />"
                + (status.HasValue ? $"<condition attribute='statuscode' operator='eq' value='{status.Value}' />" : "")
                + "</filter></entity></fetch>";
            var result = new Dictionary<Guid, decimal>();
            foreach (var row in system.RetrieveMultiple(new FetchExpression(fetch)).Entities)
            {
                var raw = row.GetAttributeValue<AliasedValue>("node")?.Value;
                var node = raw is EntityReference r ? r.Id : raw is Guid g ? g : Guid.Empty;
                var value = row.GetAttributeValue<AliasedValue>("total")?.Value;
                var amount = value is Money m ? m.Value : value is decimal d ? d : 0m;
                result[node] = (result.ContainsKey(node) ? result[node] : 0m) + amount;
            }
            return result;
        }
    }
}
