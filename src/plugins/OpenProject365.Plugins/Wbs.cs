using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;

namespace OpenProject365.Plugins
{
    /// <summary>op365_wbsnode Create/Update, PreOperation (PreImage on Update): budget total = labour + materials + other.</summary>
    public class WbsNodeBudget : PluginBase
    {
        private static readonly string[] Parts = { "op365_budgetlabour", "op365_budgetmaterials", "op365_budgetother" };

        protected override void Run(LocalContext context)
        {
            if (context.Message == "Update" && !Parts.Any(context.Changed)) return;
            var total = Parts.Sum(p => context.Get<Money>(p)?.Value ?? 0m);
            context.Target[Model.BudgetTotal] = new Money(total);
        }
    }

    /// <summary>
    /// op365_wbsnode Create/Update/Delete, PostOperation (PreImage on Update/Delete):
    /// project budget total and budget-weighted progress of the leaf nodes.
    /// </summary>
    public class WbsNodeRollup : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.IsCascadeDeleteOf(Model.Project)) return;
            if (context.Message == "Update" && !new[] { Model.BudgetTotal, Model.ProgressPct, Model.BudgetHours, Model.ParentId, "statecode" }
                    .Any(context.Changed)) return;
            var project = context.Get<EntityReference>(Model.ProjectId);
            if (project != null) Recalculate(context.SystemService, project.Id);
        }

        public static void Recalculate(IOrganizationService system, Guid projectId)
        {
            var query = new QueryExpression(Model.WbsNode)
            {
                ColumnSet = new ColumnSet(Model.ParentId, Model.BudgetTotal, Model.BudgetHours, Model.ProgressPct)
            };
            query.Criteria.AddCondition(Model.ProjectId, ConditionOperator.Equal, projectId);
            query.Criteria.AddCondition("statecode", ConditionOperator.Equal, 0);
            var nodes = system.RetrieveMultiple(query).Entities;

            var rows = nodes.Select(n => new WbsRow
            {
                Id = n.Id,
                ParentId = n.GetAttributeValue<EntityReference>(Model.ParentId)?.Id,
                Budget = n.GetAttributeValue<Money>(Model.BudgetTotal)?.Value ?? 0m,
                Hours = n.GetAttributeValue<decimal?>(Model.BudgetHours) ?? 0m,
                Progress = n.GetAttributeValue<decimal?>(Model.ProgressPct) ?? 0m,
            }).ToList();

            system.Update(new Entity(Model.Project, projectId)
            {
                [Model.BudgetTotal] = new Money(rows.Sum(r => r.Budget)),
                [Model.ProgressPct] = WbsMath.Progress(rows),
            });
        }
    }

    /// <summary>
    /// op365_wbsnode Delete, PreValidation: deletes the dependencies and the child nodes
    /// (lookups only remove the link, a table can have one cascading parent).
    /// </summary>
    public class WbsNodeDelete : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.IsCascadeDeleteOf(Model.Project)) return;
            var id = context.PrimaryId;
            var deps = new QueryExpression(Model.WbsDependency) { ColumnSet = new ColumnSet(false) };
            deps.Criteria.FilterOperator = LogicalOperator.Or;
            deps.Criteria.AddCondition("op365_predecessorid", ConditionOperator.Equal, id);
            deps.Criteria.AddCondition("op365_successorid", ConditionOperator.Equal, id);
            foreach (var d in context.Service.RetrieveMultiple(deps).Entities)
                context.Service.Delete(Model.WbsDependency, d.Id);

            var children = new QueryExpression(Model.WbsNode) { ColumnSet = new ColumnSet(false) };
            children.Criteria.AddCondition(Model.ParentId, ConditionOperator.Equal, id);
            foreach (var c in context.Service.RetrieveMultiple(children).Entities)
                context.Service.Delete(Model.WbsNode, c.Id);
        }
    }

    /// <summary>
    /// op365_wbsdependency Create/Update, PreOperation (PreImage on Update): project from the predecessor,
    /// both nodes in the same project, no self link and no cycles; name "pred → succ".
    /// </summary>
    public class WbsDependencyValidate : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var pred = context.Get<EntityReference>("op365_predecessorid");
            var succ = context.Get<EntityReference>("op365_successorid");
            if (pred == null || succ == null) return;
            if (pred.Id == succ.Id)
                throw new InvalidPluginExecutionException("A WBS node cannot depend on itself.");

            var cols = new ColumnSet(Model.ProjectId, "op365_name", "op365_code");
            var p = context.Service.Retrieve(Model.WbsNode, pred.Id, cols);
            var s = context.Service.Retrieve(Model.WbsNode, succ.Id, cols);
            var project = p.GetAttributeValue<EntityReference>(Model.ProjectId);
            if (project?.Id != s.GetAttributeValue<EntityReference>(Model.ProjectId)?.Id)
                throw new InvalidPluginExecutionException("Predecessor and successor must belong to the same project.");

            var links = new QueryExpression(Model.WbsDependency) { ColumnSet = new ColumnSet("op365_predecessorid", "op365_successorid") };
            links.Criteria.AddCondition(Model.ProjectId, ConditionOperator.Equal, project.Id);
            var edges = context.Service.RetrieveMultiple(links).Entities
                .Where(e => e.Id != context.PrimaryId)
                .Select(e => Tuple.Create(e.GetAttributeValue<EntityReference>("op365_predecessorid")?.Id ?? Guid.Empty,
                                          e.GetAttributeValue<EntityReference>("op365_successorid")?.Id ?? Guid.Empty))
                .ToList();
            if (DependencyGraph.Reaches(edges, succ.Id, pred.Id))
                throw new InvalidPluginExecutionException("This dependency would create a cycle in the plan.");

            context.Target[Model.ProjectId] = project;
            context.Target["op365_name"] = Label(p) + " → " + Label(s);
        }

        private static string Label(Entity node)
        {
            var code = node.GetAttributeValue<string>("op365_code");
            var name = node.GetAttributeValue<string>("op365_name");
            var text = string.IsNullOrEmpty(code) ? name : code + " " + name;
            return text.Length > 95 ? text.Substring(0, 95) : text;
        }
    }
}
