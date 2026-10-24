using System;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;

namespace OpenProject365.Plugins
{
    /// <summary>op365_baseline Create/Update, PostOperation: only one reference baseline per project.</summary>
    public class BaselineReference : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (!context.Changed("op365_isreference") || !context.Target.GetAttributeValue<bool>("op365_isreference")) return;
            var project = context.Get<EntityReference>(Model.ProjectId)
                ?? context.Service.Retrieve(Model.Baseline, context.PrimaryId, new ColumnSet(Model.ProjectId))
                       .GetAttributeValue<EntityReference>(Model.ProjectId);
            if (project == null) return;
            var others = new QueryExpression(Model.Baseline) { ColumnSet = new ColumnSet(false) };
            others.Criteria.AddCondition(Model.ProjectId, ConditionOperator.Equal, project.Id);
            others.Criteria.AddCondition("op365_isreference", ConditionOperator.Equal, true);
            others.Criteria.AddCondition("op365_baselineid", ConditionOperator.NotEqual, context.PrimaryId);
            foreach (var b in context.Service.RetrieveMultiple(others).Entities)
                context.Service.Update(new Entity(Model.Baseline, b.Id) { ["op365_isreference"] = false });
        }
    }

    /// <summary>
    /// Custom API op365_SaveBaseline, bound to op365_project.
    /// Inputs: Name (string, optional), KeepReference (bool, optional: true keeps the current reference baseline). Output: BaselineId (Guid).
    /// Copies budget and dates of every active WBS node into a new baseline.
    /// </summary>
    public class SaveBaseline : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var input = context.Execution.InputParameters;
            var project = (EntityReference)input["Target"];
            var name = input.Contains("Name") ? input["Name"] as string : null;
            if (string.IsNullOrWhiteSpace(name))
                name = "Baseline " + DateTime.UtcNow.ToString("yyyy-MM-dd HH:mm") + " UTC";
            var keepReference = input.Contains("KeepReference") && input["KeepReference"] is bool keep && keep;

            var service = context.Service;
            var baselineId = service.Create(new Entity(Model.Baseline)
            {
                ["op365_name"] = name.Length > 200 ? name.Substring(0, 200) : name,
                [Model.ProjectId] = project,
                ["op365_isreference"] = !keepReference,
            });

            var query = new QueryExpression(Model.WbsNode)
            {
                ColumnSet = new ColumnSet("op365_name", "op365_code", Model.BudgetHours, Model.BudgetTotal, "op365_startdate", "op365_enddate")
            };
            query.Criteria.AddCondition(Model.ProjectId, ConditionOperator.Equal, project.Id);
            query.Criteria.AddCondition("statecode", ConditionOperator.Equal, 0);
            foreach (var n in service.RetrieveMultiple(query).Entities)
            {
                service.Create(new Entity(Model.BaselineNode)
                {
                    ["op365_name"] = n.GetAttributeValue<string>("op365_name"),
                    ["op365_baselineid"] = new EntityReference(Model.Baseline, baselineId),
                    ["op365_wbsnodeid"] = n.ToEntityReference(),
                    ["op365_code"] = n.GetAttributeValue<string>("op365_code"),
                    [Model.BudgetHours] = n.GetAttributeValue<decimal?>(Model.BudgetHours),
                    [Model.BudgetTotal] = n.GetAttributeValue<Money>(Model.BudgetTotal),
                    ["op365_startdate"] = n.GetAttributeValue<DateTime?>("op365_startdate"),
                    ["op365_enddate"] = n.GetAttributeValue<DateTime?>("op365_enddate"),
                });
            }
            context.Execution.OutputParameters["BaselineId"] = baselineId;
        }
    }
}
