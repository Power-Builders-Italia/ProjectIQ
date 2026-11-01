using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using Microsoft.Crm.Sdk.Messages;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;

namespace OpenProject365.Plugins
{
    /// <summary>Supplier documents: review (Pending Review, Approved, Rejected), expiry status and supplier alert counters.</summary>
    internal static class SupplierDocuments
    {
        public static readonly string[] Apis = { "op365_DecideSupplierDocument", "op365_UpdateDocumentExpiry" };
        public const string ExpiryStatus = "op365_expirystatus";
        public const string ExpiryNotice = "op365_expirynotice";

        /// <summary>
        /// True when the caller is the application user of a Power Pages site ("# Portals-&lt;site&gt;"): the supplier portal
        /// writes through the Web API as that user.
        /// </summary>
        public static bool IsPortal(IOrganizationService system, Guid userId)
        {
            var user = system.Retrieve("systemuser", userId, new ColumnSet("fullname", "applicationid"));
            return user.GetAttributeValue<Guid?>("applicationid").HasValue
                   && (user.GetAttributeValue<string>("fullname") ?? "").StartsWith("# Portals-", StringComparison.Ordinal);
        }

        public static DateTime RomeToday()
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

        public static List<Entity> Documents(IOrganizationService system, Guid? supplierId, params string[] extra)
        {
            var columns = new[] { Model.SupplierId, "statuscode", "op365_documenttype", "op365_expirydate", ExpiryStatus, ExpiryNotice }.Concat(extra).ToArray();
            var query = new QueryExpression(Model.SupplierDocument) { ColumnSet = new ColumnSet(columns) };
            query.Criteria.AddCondition("statecode", ConditionOperator.Equal, 0);
            if (supplierId.HasValue) query.Criteria.AddCondition(Model.SupplierId, ConditionOperator.Equal, supplierId.Value);
            else query.Criteria.AddCondition(Model.SupplierId, ConditionOperator.NotNull);
            var result = new List<Entity>();
            query.PageInfo = new PagingInfo { Count = 5000, PageNumber = 1 };
            while (true)
            {
                var page = system.RetrieveMultiple(query);
                result.AddRange(page.Entities);
                if (!page.MoreRecords) break;
                query.PageInfo.PageNumber++;
                query.PageInfo.PagingCookie = page.PagingCookie;
            }
            return result;
        }

        public static DocumentRow Row(Entity d) => new DocumentRow
        {
            Id = d.Id,
            Type = d.GetAttributeValue<OptionSetValue>("op365_documenttype")?.Value ?? 0,
            Expiry = d.GetAttributeValue<DateTime?>("op365_expirydate"),
            Approved = d.GetAttributeValue<OptionSetValue>("statuscode")?.Value == Model.DocumentApproved,
            ExpiryStatus = d.GetAttributeValue<OptionSetValue>(ExpiryStatus)?.Value,
            Notice = d.GetAttributeValue<OptionSetValue>(ExpiryNotice)?.Value,
        };

        /// <summary>
        /// Recomputes the expiry status of the active documents of one supplier and its Expired/Expiring Documents counters.
        /// Returns the number of documents whose status changed.
        /// </summary>
        public static int Refresh(IOrganizationService system, Guid supplierId, IList<Entity> docs, DateTime today)
        {
            var rows = docs.Select(Row).ToList();
            var statuses = DocumentExpiry.Statuses(rows, today);
            var changed = 0;
            foreach (var row in rows.Where(r => r.ExpiryStatus != statuses[r.Id]))
            {
                system.Update(new Entity(Model.SupplierDocument, row.Id) { [ExpiryStatus] = Option(statuses[row.Id]) });
                changed++;
            }
            var counters = DocumentExpiry.Counters(rows, statuses);
            var account = system.Retrieve("account", supplierId, new ColumnSet("op365_expireddocs", "op365_expiringdocs"));
            if (account.GetAttributeValue<int?>("op365_expireddocs") != counters.Item1 || account.GetAttributeValue<int?>("op365_expiringdocs") != counters.Item2)
                system.Update(new Entity("account", supplierId) { ["op365_expireddocs"] = counters.Item1, ["op365_expiringdocs"] = counters.Item2 });
            return changed;
        }

        public static OptionSetValue Option(int? value) => value.HasValue ? new OptionSetValue(value.Value) : null;

        public static void Fail(string message) => throw new InvalidPluginExecutionException(message);
    }

    /// <summary>
    /// op365_supplierdocument Create/Update, PreOperation (PreImage on Update): the review status changes only through
    /// Approve/Reject. A document created by the supplier portal is Pending Review; one created in the app is Approved.
    /// The portal cannot change an approved document, and a rejected one it changes goes back to Pending Review.
    /// Expiry status from the expiry date; a new expiry date clears the expiry notice.
    /// </summary>
    public class SupplierDocumentValidate : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.IsInside(SupplierDocuments.Apis)) return;
            if (context.Message == "Update" && context.ChangesOnly(SupplierDocuments.ExpiryStatus, SupplierDocuments.ExpiryNotice)) return;
            var system = context.SystemService;
            var target = context.Target;
            var caller = context.Execution.InitiatingUserId;
            var portal = SupplierDocuments.IsPortal(system, caller);
            if (context.Message == "Create")
            {
                if (portal)
                {
                    target["statuscode"] = new OptionSetValue(Model.DocumentPendingReview);
                    target["op365_fromportal"] = true;
                    foreach (var c in new[] { "op365_reviewedbyid", "op365_reviewedon", "op365_reviewnote" }) target.Attributes.Remove(c);
                }
                else
                {
                    var status = target.GetAttributeValue<OptionSetValue>("statuscode")?.Value;
                    if (status.HasValue && status != Model.DocumentApproved) SupplierDocuments.Fail("Use Approve or Reject to review a supplier document.");
                    target["op365_reviewedbyid"] = new EntityReference("systemuser", caller);
                    target["op365_reviewedon"] = DateTime.UtcNow;
                }
            }
            else
            {
                if (target.Contains("statuscode") && !target.Contains("statecode")) SupplierDocuments.Fail("Use Approve or Reject to review a supplier document.");
                var current = context.Pre?.GetAttributeValue<OptionSetValue>("statuscode")?.Value;
                if (portal)
                {
                    if (current == Model.DocumentApproved) SupplierDocuments.Fail("Approved documents cannot be changed.");
                    if (current == Model.DocumentRejected) target["statuscode"] = new OptionSetValue(Model.DocumentPendingReview);
                }
            }
            if (context.Message == "Create" || context.Changed("op365_expirydate"))
            {
                target[SupplierDocuments.ExpiryStatus] = SupplierDocuments.Option(DocumentExpiry.Status(context.Get<DateTime?>("op365_expirydate"), SupplierDocuments.RomeToday(), false));
                target[SupplierDocuments.ExpiryNotice] = null;
            }
        }
    }

    /// <summary>op365_supplierdocument Delete, PreOperation (PreImage): the supplier portal cannot delete an approved document.</summary>
    public class SupplierDocumentDelete : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.IsCascadeDeleteOf("account")) return;
            if (context.Pre?.GetAttributeValue<OptionSetValue>("statuscode")?.Value == Model.DocumentApproved
                && SupplierDocuments.IsPortal(context.SystemService, context.Execution.InitiatingUserId))
                SupplierDocuments.Fail("Approved documents cannot be deleted.");
        }
    }

    /// <summary>
    /// op365_supplierdocument Create/Update/Delete, PostOperation (PreImage on Update/Delete): expiry status of the supplier's
    /// documents (a renewal replaces the older one) and its document alert counters; a document sent by the portal for review
    /// notifies the owner of the supplier.
    /// </summary>
    public class SupplierDocumentAlerts : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.IsCascadeDeleteOf("account")) return;
            var system = context.SystemService;
            var suppliers = new[] { context.Message == "Delete" ? null : context.Get<EntityReference>(Model.SupplierId), context.Pre?.GetAttributeValue<EntityReference>(Model.SupplierId) }
                .Where(r => r != null).Select(r => r.Id).Distinct().ToList();
            var today = SupplierDocuments.RomeToday();
            foreach (var supplier in suppliers)
                SupplierDocuments.Refresh(system, supplier, SupplierDocuments.Documents(system, supplier), today);

            if (context.Message == "Delete" || context.IsInside(SupplierDocuments.Apis)) return;
            var status = context.Get<OptionSetValue>("statuscode")?.Value;
            var before = context.Pre?.GetAttributeValue<OptionSetValue>("statuscode")?.Value;
            if (status != Model.DocumentPendingReview || suppliers.Count == 0) return;
            if (context.Message == "Update" && before == Model.DocumentPendingReview) return;
            var account = system.Retrieve("account", suppliers[0], new ColumnSet("name", "ownerid"));
            var owner = account.GetAttributeValue<EntityReference>("ownerid");
            if (owner == null || owner.LogicalName != "systemuser") return;
            Rules.Notify(context, owner.Id, "Supplier document to review",
                $"{account.GetAttributeValue<string>("name")} sent a document to review: {context.Get<string>("op365_description")}.");
        }
    }

    /// <summary>
    /// Custom API op365_DecideSupplierDocument (bound). Inputs Approve (bool), Note (string; required to reject).
    /// Pending Review → Approved or Rejected, with the caller's privileges on supplier documents.
    /// </summary>
    public class DecideSupplierDocument : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var input = context.Execution.InputParameters;
            var approve = input.Contains("Approve") && input["Approve"] is bool a && a;
            var note = input.Contains("Note") ? input["Note"] as string : null;
            if (!approve && string.IsNullOrWhiteSpace(note)) SupplierDocuments.Fail("Add a note to reject the supplier document.");
            var id = context.TargetReference.Id;
            var doc = context.SystemService.Retrieve(Model.SupplierDocument, id, new ColumnSet("statuscode"));
            if (doc.GetAttributeValue<OptionSetValue>("statuscode")?.Value != Model.DocumentPendingReview)
                SupplierDocuments.Fail("Only supplier documents pending review can be approved or rejected.");
            context.Service.Update(new Entity(Model.SupplierDocument, id)
            {
                ["statuscode"] = new OptionSetValue(approve ? Model.DocumentApproved : Model.DocumentRejected),
                ["op365_reviewedbyid"] = new EntityReference("systemuser", context.Execution.InitiatingUserId),
                ["op365_reviewedon"] = DateTime.UtcNow,
                ["op365_reviewnote"] = note,
            });
        }
    }

    /// <summary>
    /// Custom API op365_UpdateDocumentExpiry (unbound). Input Date (DateTime, optional: today in Europe/Rome). Outputs Count (int:
    /// documents whose expiry status changed) and Sent (int: e-mails sent). Called every day by the "Daily document expiry" flow:
    /// refreshes the expiry status and the alert counters of every supplier, then e-mails the supplier once when an approved
    /// document starts expiring and once when it expires. The e-mail comes from the Dataverse e-mail template (Account type)
    /// that the op365_SupplierEmailTemplates environment variable names for the message and the supplier's Language, is sent
    /// from the queue of op365_SupplierEmailSender and is regarding the document; the notice is recorded after sending.
    /// No sender or no template: statuses and counters are still updated, no e-mail.
    /// </summary>
    public class UpdateDocumentExpiry : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var date = Rules.OptionalDate(context.Execution.InputParameters, "Date") ?? SupplierDocuments.RomeToday();
            var system = context.SystemService;
            var docs = SupplierDocuments.Documents(system, null, "op365_description", "op365_number", "op365_issuedate");
            var mailer = new SupplierMailer(context);
            var count = 0;
            var sent = 0;
            foreach (var group in docs.GroupBy(d => d.GetAttributeValue<EntityReference>(Model.SupplierId).Id))
            {
                var list = group.ToList();
                count += SupplierDocuments.Refresh(system, group.Key, list, date);
                var statuses = DocumentExpiry.Statuses(list.Select(SupplierDocuments.Row).ToList(), date);
                foreach (var d in list)
                {
                    var row = SupplierDocuments.Row(d);
                    var notice = DocumentExpiry.Notice(row.Approved, statuses[d.Id], row.Notice);
                    if (notice == null) continue;
                    var message = notice == Model.NoticeExpired ? "DocumentExpired" : "DocumentExpiring";
                    if (!mailer.Send(message, group.Key, d.ToEntityReference(), Tokens(d))) continue;
                    system.Update(new Entity(Model.SupplierDocument, d.Id) { [SupplierDocuments.ExpiryNotice] = new OptionSetValue(notice.Value) });
                    sent++;
                }
            }
            context.Execution.OutputParameters["Count"] = count;
            context.Execution.OutputParameters["Sent"] = sent;
        }

        /// <summary>Document fields for the {placeholders} of the template (Account templates cannot read the document).</summary>
        private static Dictionary<string, string> Tokens(Entity d) => new Dictionary<string, string>
        {
            ["{Document}"] = d.GetAttributeValue<string>("op365_description") ?? "",
            ["{DocumentType}"] = d.FormattedValues.Contains("op365_documenttype") ? d.FormattedValues["op365_documenttype"] : "",
            ["{Number}"] = d.GetAttributeValue<string>("op365_number") ?? "",
            ["{IssueDate}"] = d.GetAttributeValue<DateTime?>("op365_issuedate")?.ToString("dd/MM/yyyy") ?? "",
            ["{ExpiryDate}"] = d.GetAttributeValue<DateTime?>("op365_expirydate")?.ToString("dd/MM/yyyy") ?? "",
        };
    }

    /// <summary>
    /// E-mails to suppliers from Dataverse e-mail templates: op365_SupplierEmailTemplates (JSON, message → language → template
    /// title, see <see cref="EmailTemplates"/>) and op365_SupplierEmailSender (name or e-mail address of the sending queue).
    /// </summary>
    internal sealed class SupplierMailer
    {
        public const string TemplatesVariable = "op365_SupplierEmailTemplates";
        public const string SenderVariable = "op365_SupplierEmailSender";
        private static readonly string[] Languages = { "Italian", "English", "German", "French" };
        private readonly LocalContext context;
        private readonly string config;
        private readonly Guid? queue;
        private readonly Dictionary<string, Guid?> templates = new Dictionary<string, Guid?>();

        public SupplierMailer(LocalContext context)
        {
            this.context = context;
            var system = context.SystemService;
            config = Settings.Value(system, TemplatesVariable);
            var sender = Settings.Value(system, SenderVariable);
            if (sender == null) return;
            var query = new QueryExpression("queue") { ColumnSet = new ColumnSet(false), TopCount = 1 };
            var who = query.Criteria.AddFilter(LogicalOperator.Or);
            who.AddCondition("name", ConditionOperator.Equal, sender);
            who.AddCondition("emailaddress", ConditionOperator.Equal, sender);
            queue = system.RetrieveMultiple(query).Entities.FirstOrDefault()?.Id;
            if (queue == null) context.Trace("queue {0} not found: no e-mails", sender);
        }

        /// <summary>
        /// Sends the message in the supplier's language to the supplier (its e-mail address) or to <paramref name="to"/>
        /// (a contact), regarding the record; false when nothing was sent.
        /// </summary>
        public bool Send(string message, Guid supplierId, EntityReference regarding, IDictionary<string, string> tokens, EntityReference to = null)
        {
            if (queue == null || config == null) return false;
            var system = context.SystemService;
            try
            {
                var account = system.Retrieve("account", supplierId, new ColumnSet("emailaddress1", "op365_language"));
                if (to == null && string.IsNullOrWhiteSpace(account.GetAttributeValue<string>("emailaddress1"))) return false;
                var value = account.GetAttributeValue<OptionSetValue>("op365_language")?.Value;
                var language = value.HasValue && value >= 365000000 && value < 365000004 ? Languages[value.Value - 365000000] : null;
                var title = EmailTemplates.Pick(config, message, language);
                var template = title == null ? null : Template(title);
                if (template == null)
                {
                    context.Trace("no template for {0} ({1})", message, language);
                    return false;
                }
                var instantiated = (InstantiateTemplateResponse)system.Execute(new InstantiateTemplateRequest
                {
                    TemplateId = template.Value, ObjectType = "account", ObjectId = supplierId,
                });
                var draft = instantiated.EntityCollection.Entities[0];
                var email = new Entity("email")
                {
                    ["subject"] = Fill(draft.GetAttributeValue<string>("subject"), tokens),
                    ["description"] = Fill(draft.GetAttributeValue<string>("description"), tokens),
                    ["regardingobjectid"] = regarding,
                    ["from"] = new EntityCollection(new List<Entity> { new Entity("activityparty") { ["partyid"] = new EntityReference("queue", queue.Value) } }),
                    ["to"] = new EntityCollection(new List<Entity> { new Entity("activityparty") { ["partyid"] = to ?? new EntityReference("account", supplierId) } }),
                };
                var id = system.Create(email);
                system.Execute(new SendEmailRequest { EmailId = id, IssueSend = true, TrackingToken = "" });
                return true;
            }
            catch (Exception ex)
            {
                context.Trace("e-mail {0} to {1} not sent: {2}", message, supplierId, ex.Message);
                return false;
            }
        }

        private Guid? Template(string title)
        {
            if (templates.ContainsKey(title)) return templates[title];
            var query = new QueryExpression("template") { ColumnSet = new ColumnSet(false), TopCount = 1 };
            query.Criteria.AddCondition("title", ConditionOperator.Equal, title);
            query.Criteria.AddCondition("templatetypecode", ConditionOperator.Equal, "account");
            return templates[title] = context.SystemService.RetrieveMultiple(query).Entities.FirstOrDefault()?.Id;
        }

        private static string Fill(string text, IDictionary<string, string> tokens)
        {
            if (string.IsNullOrEmpty(text)) return text;
            foreach (var t in tokens) text = text.Replace(t.Key, WebUtility.HtmlEncode(t.Value));
            return text;
        }
    }
}
