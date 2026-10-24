using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;

namespace OpenProject365.Plugins
{
    /// <summary>
    /// Custom API op365_SendTimeReminders (unbound). Input Date (DateTime, optional: today in Europe/Rome). Output Count (int).
    /// Called by the "Daily time reminder" flow on working days: every active resource with a user who recorded fewer hours
    /// than expected on the date (weekly hours over working days, less absences) gets an in-app notification.
    /// No reminders on a company closure.
    /// </summary>
    public class SendTimeReminders : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var input = context.Execution.InputParameters;
            var date = Rules.OptionalDate(input, "Date") ?? RomeToday();
            var system = context.SystemService;

            var absences = Absences(system, date);
            var count = 0;
            if (!absences.ContainsKey(Guid.Empty))
            {
                var logged = LoggedHours(system, date);
                var url = TimesheetUrl(system);
                var query = new QueryExpression(Model.Resource) { ColumnSet = new ColumnSet("op365_userid", "op365_weeklyhours", "op365_workingdays") };
                query.Criteria.AddCondition("statecode", ConditionOperator.Equal, 0);
                query.Criteria.AddCondition("op365_userid", ConditionOperator.NotNull);
                foreach (var r in system.RetrieveMultiple(query).Entities)
                {
                    var days = (r.GetAttributeValue<OptionSetValueCollection>("op365_workingdays") ?? new OptionSetValueCollection())
                        .Select(o => TimeReminder.Day(o.Value)).ToList();
                    var absent = absences.ContainsKey(r.Id);
                    var expected = TimeReminder.ExpectedHours(r.GetAttributeValue<decimal?>("op365_weeklyhours") ?? 0m, days, date.DayOfWeek,
                        absent, absent ? absences[r.Id] : null);
                    var hours = logged.ContainsKey(r.Id) ? logged[r.Id] : 0m;
                    if (expected <= 0m || hours >= expected) continue;
                    Rules.Notify(context, r.GetAttributeValue<EntityReference>("op365_userid").Id, "Record your hours",
                        $"You have recorded {hours:0.##} of {expected:0.##} hours on {date:yyyy-MM-dd}.", "Open timesheet", url);
                    count++;
                }
            }
            context.Execution.OutputParameters["Count"] = count;
        }

        private static DateTime RomeToday()
        {
            try
            {
                return TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, TimeZoneInfo.FindSystemTimeZoneById("W. Europe Standard Time")).Date;
            }
            catch (TimeZoneNotFoundException)
            {
                return DateTime.UtcNow.Date;
            }
        }

        /// <summary>Absence hours by resource on the date (null = whole day); Guid.Empty = company closure.</summary>
        private static Dictionary<Guid, decimal?> Absences(IOrganizationService system, DateTime date)
        {
            var query = new QueryExpression("op365_absence") { ColumnSet = new ColumnSet(Model.ResourceId, "op365_hours", "op365_fromdate", "op365_todate") };
            query.Criteria.AddCondition("statecode", ConditionOperator.Equal, 0);
            query.Criteria.AddCondition("op365_fromdate", ConditionOperator.OnOrBefore, date);
            query.Criteria.AddCondition("op365_todate", ConditionOperator.OnOrAfter, date);
            var result = new Dictionary<Guid, decimal?>();
            foreach (var a in system.RetrieveMultiple(query).Entities)
            {
                var resource = a.GetAttributeValue<EntityReference>(Model.ResourceId)?.Id ?? Guid.Empty;
                var single = a.GetAttributeValue<DateTime?>("op365_fromdate")?.Date == a.GetAttributeValue<DateTime?>("op365_todate")?.Date;
                var hours = single ? a.GetAttributeValue<decimal?>("op365_hours") : null;
                if (result.ContainsKey(resource))
                    result[resource] = result[resource].HasValue && hours.HasValue ? result[resource] + hours : null;
                else
                    result[resource] = hours;
            }
            return result;
        }

        private static Dictionary<Guid, decimal> LoggedHours(IOrganizationService system, DateTime date)
        {
            var fetch = $@"<fetch aggregate='true'><entity name='{Model.TimeEntry}'>
                <attribute name='op365_hours' alias='total' aggregate='sum' />
                <attribute name='op365_resourceid' alias='resource' groupby='true' />
                <filter><condition attribute='op365_entrydate' operator='on' value='{date:yyyy-MM-dd}' />
                <condition attribute='statecode' operator='eq' value='0' /></filter></entity></fetch>";
            var result = new Dictionary<Guid, decimal>();
            foreach (var row in system.RetrieveMultiple(new FetchExpression(fetch)).Entities)
            {
                var raw = row.GetAttributeValue<AliasedValue>("resource")?.Value;
                var resource = raw is EntityReference r ? r.Id : raw is Guid g ? g : Guid.Empty;
                result[resource] = row.GetAttributeValue<AliasedValue>("total")?.Value is decimal h ? h : 0m;
            }
            return result;
        }

        private static string TimesheetUrl(IOrganizationService system)
        {
            var query = new QueryExpression("systemform") { ColumnSet = new ColumnSet("formid"), TopCount = 1 };
            query.Criteria.AddCondition("type", ConditionOperator.Equal, 0);
            query.Criteria.AddCondition("name", ConditionOperator.Equal, "Timesheet");
            var form = system.RetrieveMultiple(query).Entities.FirstOrDefault();
            return form == null ? null : $"?pagetype=dashboard&id={form.Id:D}&type=system";
        }
    }
}
