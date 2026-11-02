using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;

namespace OpenProject365.Plugins
{
    /// <summary>
    /// Project suppliers (op365_projectsupplier): the suppliers that work on a project and the WBS nodes of their scope
    /// (N:N op365_projectsupplier_wbsnode), which the supplier portal shows. A selected node always brings its branch.
    /// </summary>
    internal static class ProjectSuppliers
    {
        public const string Table = "op365_projectsupplier";
        public const string Scope = "op365_projectsupplier_wbsnode";
        public const string Id = "op365_projectsupplierid";
        public const string CanUpdateProgress = "op365_canupdateprogress";
        public const string ProgressVariable = "op365_SupplierProgressUpdates";
        public const int Active = 1;
        public const int Invited = 365000000;

        /// <summary>Supplier Progress Updates environment variable; off when not set.</summary>
        public static bool ProgressUpdates(IOrganizationService system) =>
            EnvironmentValue.Bool(Settings.Value(system, ProgressVariable), false);

        /// <summary>
        /// Project supplier row of the project and supplier, created when missing (Invited, or Active when active is true).
        /// With active, an Invited or inactive row becomes Active. Returns the row id.
        /// </summary>
        public static Guid Ensure(IOrganizationService system, Guid projectId, Guid supplierId, bool active)
        {
            var query = new QueryExpression(Table) { ColumnSet = new ColumnSet("statecode", "statuscode"), TopCount = 1 };
            query.Criteria.AddCondition(Model.ProjectId, ConditionOperator.Equal, projectId);
            query.Criteria.AddCondition(Model.SupplierId, ConditionOperator.Equal, supplierId);
            var row = system.RetrieveMultiple(query).Entities.FirstOrDefault();
            if (row == null)
                return system.Create(new Entity(Table)
                {
                    [Model.ProjectId] = new EntityReference(Model.Project, projectId),
                    [Model.SupplierId] = new EntityReference("account", supplierId),
                    ["statuscode"] = new OptionSetValue(active ? Active : Invited),
                });
            if (active && Purchasing.Status(row) != Active)
                system.Update(new Entity(Table, row.Id) { ["statecode"] = new OptionSetValue(0), ["statuscode"] = new OptionSetValue(Active) });
            return row.Id;
        }

        /// <summary>Active WBS nodes of a project as rows (id and parent).</summary>
        public static List<WbsRow> Nodes(IOrganizationService system, Guid projectId)
        {
            var query = new QueryExpression(Model.WbsNode) { ColumnSet = new ColumnSet(Model.ParentId) };
            query.Criteria.AddCondition(Model.ProjectId, ConditionOperator.Equal, projectId);
            query.Criteria.AddCondition("statecode", ConditionOperator.Equal, 0);
            return system.RetrieveMultiple(query).Entities
                .Select(n => new WbsRow { Id = n.Id, ParentId = n.GetAttributeValue<EntityReference>(Model.ParentId)?.Id }).ToList();
        }

        /// <summary>WBS nodes already in the scope of a project supplier.</summary>
        public static HashSet<Guid> ScopeOf(IOrganizationService system, Guid projectSupplierId)
        {
            var query = new QueryExpression(Scope) { ColumnSet = new ColumnSet(Model.WbsNodeId) };
            query.Criteria.AddCondition(Id, ConditionOperator.Equal, projectSupplierId);
            return new HashSet<Guid>(system.RetrieveMultiple(query).Entities.Select(e => e.GetAttributeValue<Guid>(Model.WbsNodeId)));
        }

        /// <summary>Project suppliers whose scope contains the node.</summary>
        public static List<Guid> HoldersOf(IOrganizationService system, Guid nodeId)
        {
            var query = new QueryExpression(Scope) { ColumnSet = new ColumnSet(Id) };
            query.Criteria.AddCondition(Model.WbsNodeId, ConditionOperator.Equal, nodeId);
            return system.RetrieveMultiple(query).Entities.Select(e => e.GetAttributeValue<Guid>(Id)).Distinct().ToList();
        }

        /// <summary>Adds the nodes and their descendants to the scope of the project supplier (only the missing ones).</summary>
        public static void AddScope(IOrganizationService system, Guid projectSupplierId, Guid projectId, IEnumerable<Guid> nodes)
        {
            var wanted = WbsScope.Expand(Nodes(system, projectId), nodes);
            wanted.ExceptWith(ScopeOf(system, projectSupplierId));
            if (wanted.Count == 0) return;
            var refs = new EntityReferenceCollection(wanted.Select(n => new EntityReference(Model.WbsNode, n)).ToList());
            system.Associate(Table, projectSupplierId, new Relationship(Scope), refs);
        }

        public static Guid ProjectOf(IOrganizationService system, Guid projectSupplierId) =>
            system.Retrieve(Table, projectSupplierId, new ColumnSet(Model.ProjectId)).GetAttributeValue<EntityReference>(Model.ProjectId).Id;
    }

    /// <summary>op365_projectsupplier Create/Update, PreOperation: name "Project - Supplier".</summary>
    public class ProjectSupplierName : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.Message == "Update" && !context.Changed(Model.ProjectId) && !context.Changed(Model.SupplierId)) return;
            var system = context.SystemService;
            var project = context.Get<EntityReference>(Model.ProjectId);
            var supplier = context.Get<EntityReference>(Model.SupplierId);
            if (project == null || supplier == null) return;
            Purchasing.EnsureSupplier(system, supplier.Id);
            var name = system.Retrieve(Model.Project, project.Id, new ColumnSet("op365_name")).GetAttributeValue<string>("op365_name")
                       + " - " + system.Retrieve("account", supplier.Id, new ColumnSet("name")).GetAttributeValue<string>("name");
            context.Target["op365_name"] = name.Length > 400 ? name.Substring(0, 400) : name;
        }
    }

    /// <summary>
    /// op365_projectsupplier Retrieve/RetrieveMultiple, PostOperation: Can Update Progress = the environment variable
    /// Supplier Progress Updates (the supplier portal reads it with the row; Liquid cannot read environment variables).
    /// </summary>
    public class ProjectSupplierFlags : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var output = context.Execution.OutputParameters;
            var rows = new List<Entity>();
            if (output.Contains("BusinessEntityCollection") && output["BusinessEntityCollection"] is EntityCollection collection)
                rows.AddRange(collection.Entities);
            if (output.Contains("BusinessEntity") && output["BusinessEntity"] is Entity one)
                rows.Add(one);
            if (rows.Count == 0) return;
            var flag = ProjectSuppliers.ProgressUpdates(context.SystemService);
            foreach (var row in rows) row[ProjectSuppliers.CanUpdateProgress] = flag;
        }
    }

    /// <summary>
    /// op365_rfqinvitation Create/Update (status), PostOperation: an invited supplier becomes a project supplier (Invited)
    /// of the project of the request for quotation.
    /// </summary>
    public class RfqInvitationProjectSupplier : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var system = context.SystemService;
            var inv = system.Retrieve(Model.RfqInvitation, context.PrimaryId, new ColumnSet(Model.RfqId, Model.SupplierId, "statuscode"));
            if (Purchasing.Status(inv) != Model.InvitationInvited) return;
            var rfq = Purchasing.Id(inv, Model.RfqId);
            var supplier = Purchasing.Id(inv, Model.SupplierId);
            if (!rfq.HasValue || !supplier.HasValue) return;
            var project = Purchasing.Id(system.Retrieve(Model.Rfq, rfq.Value, new ColumnSet(Model.ProjectId)), Model.ProjectId);
            if (project.HasValue) ProjectSuppliers.Ensure(system, project.Value, supplier.Value, false);
        }
    }

    /// <summary>
    /// op365_purchaseorder Update (status), PostOperation: a Sent, Confirmed or Received order makes its supplier an Active
    /// project supplier and adds the WBS nodes of its lines (with their branches) to the scope. Cancelling keeps the scope.
    /// </summary>
    public class PurchaseOrderProjectSupplier : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var status = context.Target.GetAttributeValue<OptionSetValue>("statuscode")?.Value;
            if (status != Model.PoSent && status != Model.PoConfirmed && status != Model.PoReceived) return;
            var system = context.SystemService;
            var po = system.Retrieve(Model.PurchaseOrder, context.PrimaryId, new ColumnSet(Model.ProjectId, Model.SupplierId));
            var project = Purchasing.Id(po, Model.ProjectId);
            var supplier = Purchasing.Id(po, Model.SupplierId);
            if (!project.HasValue || !supplier.HasValue) return;
            var row = ProjectSuppliers.Ensure(system, project.Value, supplier.Value, true);
            var nodes = Purchasing.Children(system, Model.PurchaseOrderLine, Model.PurchaseOrderId, po.Id, Model.WbsNodeId)
                .Select(l => Purchasing.Id(l, Model.WbsNodeId)).Where(n => n.HasValue).Select(n => n.Value).Distinct().ToList();
            if (nodes.Count > 0) ProjectSuppliers.AddScope(system, row, project.Value, nodes);
        }
    }

    /// <summary>
    /// Associate of op365_projectsupplier_wbsnode, PostOperation: the descendants of the added nodes join the scope too.
    /// The step is registered for all tables (Associate has no table filter) and ignores the other relationships.
    /// </summary>
    public class ProjectSupplierScope : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var input = context.Execution.InputParameters;
            if (!(input.Contains("Relationship") && input["Relationship"] is Relationship rel) || rel.SchemaName != ProjectSuppliers.Scope) return;
            var target = context.TargetReference;
            var related = input.Contains("RelatedEntities") ? input["RelatedEntities"] as EntityReferenceCollection : null;
            if (target == null || related == null) return;
            var all = related.Concat(new[] { target }).ToList();
            var holders = all.Where(r => r.LogicalName == ProjectSuppliers.Table).Select(r => r.Id).Distinct().ToList();
            var nodes = all.Where(r => r.LogicalName == Model.WbsNode).Select(r => r.Id).Distinct().ToList();
            var system = context.SystemService;
            foreach (var holder in holders)
                ProjectSuppliers.AddScope(system, holder, ProjectSuppliers.ProjectOf(system, holder), nodes);
        }
    }

    /// <summary>
    /// op365_wbsnode Create/Update (parent), PostOperation: a node added under a node of a supplier scope joins that scope
    /// (with its branch when it is moved).
    /// </summary>
    public class WbsNodeSupplierScope : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var parent = context.Target.GetAttributeValue<EntityReference>(Model.ParentId);
            var project = context.Get<EntityReference>(Model.ProjectId);
            if (parent == null || project == null) return;
            var system = context.SystemService;
            foreach (var holder in ProjectSuppliers.HoldersOf(system, parent.Id))
                ProjectSuppliers.AddScope(system, holder, project.Id, new[] { context.PrimaryId });
        }
    }

    /// <summary>
    /// op365_wbsnode Update, PreOperation: the supplier portal can change only the progress % of a WBS node without child
    /// nodes, between 0 and 100, and only when the environment variable Supplier Progress Updates is yes. The table
    /// permissions of the portal limit the nodes to the supplier's scope.
    /// </summary>
    public class WbsNodePortalGuard : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var system = context.SystemService;
            if (!SupplierDocuments.IsPortal(system, context.Execution.InitiatingUserId)) return;
            if (!ProjectSuppliers.ProgressUpdates(system)) SupplierDocuments.Fail("Progress updates from the supplier portal are disabled.");
            if (!context.ChangesOnly(Model.ProgressPct)) SupplierDocuments.Fail("On the supplier portal only the progress of a WBS node can be changed.");
            var progress = context.Target.GetAttributeValue<decimal?>(Model.ProgressPct);
            if (progress < 0m || progress > 100m) SupplierDocuments.Fail("Progress must be between 0 and 100.");
            var query = new QueryExpression(Model.WbsNode) { ColumnSet = new ColumnSet(false), TopCount = 1 };
            query.Criteria.AddCondition(Model.ParentId, ConditionOperator.Equal, context.PrimaryId);
            query.Criteria.AddCondition("statecode", ConditionOperator.Equal, 0);
            if (system.RetrieveMultiple(query).Entities.Count > 0)
                SupplierDocuments.Fail("Only the progress of WBS nodes without child nodes can be updated: the others are calculated.");
        }
    }
}
