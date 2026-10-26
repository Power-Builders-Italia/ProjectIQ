using System;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;

namespace OpenProject365.Plugins
{
    /// <summary>Company settings, kept in the op365_ environment variables of the solution.</summary>
    internal static class Settings
    {
        public const string TimeApprovalEnabledVariable = "op365_TimeApprovalEnabled";
        public const string PurchaseRequestThresholdVariable = "op365_PurchaseRequestThreshold";
        public const string PurchasingApproverVariable = "op365_PurchasingApprover";

        /// <summary>Current value of the environment variable, else its default value; null when neither is set.</summary>
        public static string Value(IOrganizationService system, string schemaName)
        {
            var query = new QueryExpression("environmentvariabledefinition") { ColumnSet = new ColumnSet("defaultvalue"), TopCount = 1 };
            query.Criteria.AddCondition("schemaname", ConditionOperator.Equal, schemaName);
            var value = query.AddLink("environmentvariablevalue", "environmentvariabledefinitionid", "environmentvariabledefinitionid", JoinOperator.LeftOuter);
            value.EntityAlias = "v";
            value.Columns = new ColumnSet("value");
            var row = system.RetrieveMultiple(query).Entities.FirstOrDefault();
            if (row == null) return null;
            return EnvironmentValue.Effective(row.GetAttributeValue<AliasedValue>("v.value")?.Value as string, row.GetAttributeValue<string>("defaultvalue"));
        }

        /// <summary>Time approval switch; on when the variable has no value.</summary>
        public static bool TimeApprovalEnabled(IOrganizationService system) =>
            EnvironmentValue.Bool(Value(system, TimeApprovalEnabledVariable), true);

        /// <summary>Amount above which a purchase request needs second-level approval; null = never.</summary>
        public static decimal? PurchaseRequestThreshold(IOrganizationService system) =>
            EnvironmentValue.Number(Value(system, PurchaseRequestThresholdVariable));

        /// <summary>Enabled user whose User Name or primary email is the Purchasing Approver variable; null when not set or not found.</summary>
        public static Guid? PurchasingApprover(IOrganizationService system)
        {
            var name = Value(system, PurchasingApproverVariable);
            if (name == null) return null;
            var query = new QueryExpression("systemuser") { ColumnSet = new ColumnSet(false), TopCount = 1 };
            query.Criteria.AddCondition("isdisabled", ConditionOperator.Equal, false);
            var who = query.Criteria.AddFilter(LogicalOperator.Or);
            who.AddCondition("domainname", ConditionOperator.Equal, name);
            who.AddCondition("internalemailaddress", ConditionOperator.Equal, name);
            return system.RetrieveMultiple(query).Entities.FirstOrDefault()?.Id;
        }
    }
}
