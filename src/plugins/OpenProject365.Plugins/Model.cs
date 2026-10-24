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
        public const string TimeEntry = "op365_timeentry";
        public const string MaterialUsage = "op365_materialusage";
        public const string Settings = "op365_settings";
        public const string Item = "op365_item";

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
        public const string WbsNodeId = "op365_wbsnodeid";
        public const string ResourceId = "op365_resourceid";
        public const string ActualCost = "op365_actualcost";
        public const string ActualHours = "op365_actualhours";

        public const int RoleManager = 365000000;
        public const int RoleContributor = 365000001;
        public const int RoleReader = 365000002;

        // project status reasons
        public const int ProjectInProgress = 1;

        // time entry status reasons
        public const int TimeDraft = 1;
        public const int TimeSubmitted = 365000000;
        public const int TimeApproved = 365000001;
        public const int TimeRejected = 365000002;
    }
}
