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
        public const string SourcingAgentEnabledVariable = "op365_SourcingAgentEnabled";
        public const string SourcingAgentUserVariable = "op365_SourcingAgentUser";
        public const string SourcingApprovalTeamVariable = "op365_SourcingApprovalTeam";
        public const string SourcingDirectOrderLimitVariable = "op365_SourcingDirectOrderLimit";
        public const string SourcingMinQuotesVariable = "op365_SourcingMinQuotes";
        public const string SourcingReminderDaysVariable = "op365_SourcingReminderDays";
        public const string SourcingBudgetWarningPctVariable = "op365_SourcingBudgetWarningPct";
        public const string SourcingProposalExpiryDaysVariable = "op365_SourcingProposalExpiryDays";

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
        public static Guid? PurchasingApprover(IOrganizationService system) =>
            Rules.UserByName(system, Value(system, PurchasingApproverVariable));

        /// <summary>Enabled user the sourcing agent runs as; null when not set or not found.</summary>
        public static Guid? SourcingAgentUser(IOrganizationService system) =>
            Rules.UserByName(system, Value(system, SourcingAgentUserVariable));

        /// <summary>Estimated amount up to which the sourcing agent proposes a direct order; null = always a request for quotation.</summary>
        public static decimal? SourcingDirectOrderLimit(IOrganizationService system) =>
            EnvironmentValue.Number(Value(system, SourcingDirectOrderLimitVariable));

        /// <summary>Suppliers the sourcing agent invites to a request for quotation; 3 when not set.</summary>
        public static int SourcingMinQuotes(IOrganizationService system)
        {
            var n = (int)(EnvironmentValue.Number(Value(system, SourcingMinQuotesVariable)) ?? SourcingRules.DefaultMinQuotes);
            return n <= 0 ? SourcingRules.DefaultMinQuotes : n;
        }

        /// <summary>Days after which an open agent proposal expires; 5 when not set.</summary>
        public static int SourcingProposalExpiryDays(IOrganizationService system) =>
            (int)(EnvironmentValue.Number(Value(system, SourcingProposalExpiryDaysVariable)) ?? 5m);
    }
}
