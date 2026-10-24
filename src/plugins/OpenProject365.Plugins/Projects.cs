using System;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;

namespace OpenProject365.Plugins
{
    /// <summary>
    /// op365_projectmember Create/Update/Delete, PostOperation (PreImage on Update/Delete):
    /// keeps the member in the access team that matches the project role.
    /// </summary>
    public class ProjectMemberSync : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.IsCascadeDeleteOf(Model.Project)) return;
            var system = context.SystemService;
            var pre = context.Pre;

            if (context.Message == "Delete" || context.Message == "Update")
            {
                var project = pre.GetAttributeValue<EntityReference>(Model.ProjectId);
                var user = pre.GetAttributeValue<EntityReference>(Model.UserId);
                var role = pre.GetAttributeValue<OptionSetValue>(Model.ProjectRole);
                if (project != null && user != null && role != null)
                    AccessTeams.Remove(system, project.Id, user.Id, role.Value);
            }
            if (context.Message == "Create" || context.Message == "Update")
            {
                var project = context.Get<EntityReference>(Model.ProjectId);
                var user = context.Get<EntityReference>(Model.UserId);
                var role = context.Get<OptionSetValue>(Model.ProjectRole);
                if (project != null && user != null)
                    AccessTeams.Add(system, project.Id, user.Id, role?.Value ?? Model.RoleContributor);
            }
        }
    }

    /// <summary>op365_projectmember Create, PreOperation: name = user full name.</summary>
    public class ProjectMemberName : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var target = context.Target;
            var user = target.GetAttributeValue<EntityReference>(Model.UserId);
            if (user == null || !string.IsNullOrEmpty(target.GetAttributeValue<string>("op365_name"))) return;
            target["op365_name"] = context.SystemService.Retrieve("systemuser", user.Id, new ColumnSet("fullname"))
                .GetAttributeValue<string>("fullname");
        }
    }

    /// <summary>
    /// op365_project Create/Update/Delete, PostOperation (PreImage on Update/Delete):
    /// the project manager becomes a Manager member; customer project count and contract value total.
    /// </summary>
    public class ProjectSync : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.Message != "Delete")
                EnsureManagerMember(context);

            if (context.Message == "Create" || context.Changed(Model.CustomerId) || context.Changed(Model.ContractValue)
                || context.Changed("statecode") || context.Message == "Delete")
            {
                var before = context.Pre?.GetAttributeValue<EntityReference>(Model.CustomerId);
                var after = context.Message == "Delete" ? null : context.Get<EntityReference>(Model.CustomerId);
                if (after != null) CustomerTotals(context.SystemService, after.Id, context.Message == "Delete" ? context.PrimaryId : Guid.Empty);
                if (before != null && (after == null || before.Id != after.Id))
                    CustomerTotals(context.SystemService, before.Id, context.Message == "Delete" ? context.PrimaryId : Guid.Empty);
            }
        }

        private static void EnsureManagerMember(LocalContext context)
        {
            if (!context.Changed(Model.ProjectManagerId)) return;
            var manager = context.Target.GetAttributeValue<EntityReference>(Model.ProjectManagerId);
            if (manager == null) return;

            var query = new QueryExpression(Model.ProjectMember) { ColumnSet = new ColumnSet(Model.ProjectRole), TopCount = 1 };
            query.Criteria.AddCondition(Model.ProjectId, ConditionOperator.Equal, context.PrimaryId);
            query.Criteria.AddCondition(Model.UserId, ConditionOperator.Equal, manager.Id);
            var member = context.SystemService.RetrieveMultiple(query).Entities.FirstOrDefault();
            if (member == null)
            {
                context.SystemService.Create(new Entity(Model.ProjectMember)
                {
                    [Model.ProjectId] = new EntityReference(Model.Project, context.PrimaryId),
                    [Model.UserId] = manager,
                    [Model.ProjectRole] = new OptionSetValue(Model.RoleManager),
                });
            }
            else if (member.GetAttributeValue<OptionSetValue>(Model.ProjectRole)?.Value != Model.RoleManager)
            {
                context.SystemService.Update(new Entity(Model.ProjectMember, member.Id)
                {
                    [Model.ProjectRole] = new OptionSetValue(Model.RoleManager)
                });
            }
        }

        private static void CustomerTotals(IOrganizationService system, Guid accountId, Guid excludeProject)
        {
            var query = new QueryExpression(Model.Project) { ColumnSet = new ColumnSet(Model.ContractValue) };
            query.Criteria.AddCondition(Model.CustomerId, ConditionOperator.Equal, accountId);
            if (excludeProject != Guid.Empty)
                query.Criteria.AddCondition("op365_projectid", ConditionOperator.NotEqual, excludeProject);
            var projects = system.RetrieveMultiple(query).Entities;
            system.Update(new Entity("account", accountId)
            {
                ["op365_projectcount"] = projects.Count,
                ["op365_contractvaluetotal"] = new Money(projects.Sum(p => p.GetAttributeValue<Money>(Model.ContractValue)?.Value ?? 0m)),
            });
        }
    }
}
