namespace OpenProject365.Plugins
{
    /// <summary>Logical names used by the plugins.</summary>
    internal static class Model
    {
        public const string Project = "op365_project";
        public const string ProjectMember = "op365_projectmember";
        public const string WbsNode = "op365_wbsnode";
        public const string WbsDependency = "op365_wbsdependency";
        public const string Baseline = "op365_baseline";
        public const string BaselineNode = "op365_baselinenode";
        public const string Resource = "op365_resource";
        public const string ResourceCost = "op365_resourcecost";

        public const string ProjectId = "op365_projectid";
        public const string CustomerId = "op365_customerid";
        public const string ProjectManagerId = "op365_projectmanagerid";
        public const string ContractValue = "op365_contractvalue";
        public const string BudgetTotal = "op365_budgettotal";
        public const string BudgetHours = "op365_budgethours";
        public const string ProgressPct = "op365_progresspct";
        public const string UserId = "op365_userid";
        public const string ProjectRole = "op365_projectrole";
        public const string ParentId = "op365_parentid";

        public const int RoleManager = 365000000;
        public const int RoleContributor = 365000001;
        public const int RoleReader = 365000002;
    }
}
