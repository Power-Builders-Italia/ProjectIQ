using System;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;

namespace OpenProject365.Plugins
{
    /// <summary>op365_resource Create, PreOperation: default 40 weekly hours, Monday-Friday.</summary>
    public class ResourceDefaults : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var target = context.Target;
            if (target.GetAttributeValue<decimal?>("op365_weeklyhours") == null)
                target["op365_weeklyhours"] = 40m;
            if (target.GetAttributeValue<OptionSetValueCollection>("op365_workingdays") == null)
                target["op365_workingdays"] = new OptionSetValueCollection(
                    Enumerable.Range(0, 5).Select(i => new OptionSetValue(365000000 + i)).ToList());
        }
    }

    /// <summary>
    /// op365_resourcecost Create/Update/Delete, PostOperation (PreImage on Update/Delete):
    /// the resource hourly cost is the cost valid today (latest Valid From not in the future).
    /// </summary>
    public class ResourceCostSync : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.IsCascadeDeleteOf(Model.Resource)) return;
            var resource = context.Get<EntityReference>("op365_resourceid");
            if (resource == null) return;

            var query = new QueryExpression(Model.ResourceCost)
            {
                ColumnSet = new ColumnSet("op365_hourlycost"),
                TopCount = 1,
                Criteria =
                {
                    Conditions =
                    {
                        new ConditionExpression("op365_resourceid", ConditionOperator.Equal, resource.Id),
                        new ConditionExpression("op365_validfrom", ConditionOperator.OnOrBefore, DateTime.UtcNow.Date),
                        new ConditionExpression("statecode", ConditionOperator.Equal, 0),
                    }
                },
                Orders = { new OrderExpression("op365_validfrom", OrderType.Descending) }
            };
            var current = context.SystemService.RetrieveMultiple(query).Entities.FirstOrDefault();
            var update = new Entity(Model.Resource, resource.Id)
            {
                ["op365_hourlycost"] = current?.GetAttributeValue<Money>("op365_hourlycost")
            };
            context.SystemService.Update(update);
        }
    }
}
