using System;
using System.Linq;
using Microsoft.Crm.Sdk.Messages;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;

namespace OpenProject365.Plugins
{
    /// <summary>
    /// Project access team templates. Templates are not solution components, so they are
    /// created on first use in every environment.
    /// </summary>
    internal static class AccessTeams
    {
        // AccessRights flags: Read 1, Write 2, Append 4, AppendTo 16, Share 262144
        private static readonly (int Role, string Name, int Mask)[] Templates =
        {
            (Model.RoleManager, "OP365 Project Manager", 1 | 2 | 4 | 16 | 262144),
            (Model.RoleContributor, "OP365 Project Contributor", 1 | 4),
            (Model.RoleReader, "OP365 Project Reader", 1),
        };

        public static Guid TemplateFor(IOrganizationService system, int role)
        {
            var t = Templates.FirstOrDefault(x => x.Role == role);
            if (t.Name == null) t = Templates[2];
            var query = new QueryExpression("teamtemplate") { ColumnSet = new ColumnSet(false), TopCount = 1 };
            query.Criteria.AddCondition("teamtemplatename", ConditionOperator.Equal, t.Name);
            var found = system.RetrieveMultiple(query).Entities.FirstOrDefault();
            if (found != null) return found.Id;

            var otc = ((Microsoft.Xrm.Sdk.Messages.RetrieveEntityResponse)system.Execute(
                new Microsoft.Xrm.Sdk.Messages.RetrieveEntityRequest
                {
                    LogicalName = Model.Project,
                    EntityFilters = Microsoft.Xrm.Sdk.Metadata.EntityFilters.Entity
                })).EntityMetadata.ObjectTypeCode.Value;
            return system.Create(new Entity("teamtemplate")
            {
                ["teamtemplatename"] = t.Name,
                ["objecttypecode"] = otc,
                ["defaultaccessrightsmask"] = t.Mask,
                ["description"] = "Created by Open Project 365 for project members",
            });
        }

        public static void Add(IOrganizationService system, Guid projectId, Guid userId, int role)
        {
            system.Execute(new AddUserToRecordTeamRequest
            {
                Record = new EntityReference(Model.Project, projectId),
                SystemUserId = userId,
                TeamTemplateId = TemplateFor(system, role),
            });
        }

        public static void Remove(IOrganizationService system, Guid projectId, Guid userId, int role)
        {
            system.Execute(new RemoveUserFromRecordTeamRequest
            {
                Record = new EntityReference(Model.Project, projectId),
                SystemUserId = userId,
                TeamTemplateId = TemplateFor(system, role),
            });
        }
    }
}
