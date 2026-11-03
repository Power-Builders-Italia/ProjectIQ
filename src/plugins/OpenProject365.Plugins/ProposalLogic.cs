using System;
using System.Globalization;
using System.IO;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Text;

namespace OpenProject365.Plugins
{
    // Sourcing agent proposal rules without SDK types, covered by OpenProject365.Plugins.Tests.

    [DataContract]
    internal class ProposalJson
    {
        [DataMember(Name = "supplierIds")] public string[] SupplierIds;
        [DataMember(Name = "deadline")] public string Deadline;
        [DataMember(Name = "supplierId")] public string SupplierId;
        [DataMember(Name = "contactId")] public string ContactId;
        [DataMember(Name = "note")] public string Note;
    }

    /// <summary>Parameters of a Source via RFQ proposal.</summary>
    public class SourcePayload
    {
        public Guid[] SupplierIds = new Guid[0];
        public DateTime? Deadline;
    }

    public static class Proposals
    {
        // Kind
        public const int Proposal = 365000000;
        public const int Insight = 365000001;
        public const int Log = 365000002;

        // Action type
        public const int SourceViaRfq = 365000000;
        public const int DirectOrder = 365000001;
        public const int AwardRfq = 365000002;
        public const int ApproveInvoice = 365000003;
        public const int RejectInvoice = 365000004;
        public const int InviteSupplier = 365000005;
        public const int SupplierReminder = 365000006;
        public const int ComplianceAlert = 365000007;
        public const int BudgetAlert = 365000008;
        public const int LateDelivery = 365000009;
        public const int Consolidation = 365000010;
        public const int NewSupplierNeeded = 365000011;

        // Status, statecode 0
        public const int Pending = 1;
        public const int Open = 365000000;
        public const int Failed = 365000001;
        // Status, statecode 1
        public const int Executed = 2;
        public const int Rejected = 365000002;
        public const int Expired = 365000003;
        public const int Superseded = 365000004;
        public const int Acknowledged = 365000005;
        public const int Done = 365000006;

        public const string AlreadyDecided = "This proposal has already been decided.";
        public const string NoteRequired = "Add a note to reject the proposal.";
        public const string OnlyFailedRetry = "Only failed proposals can be retried.";
        public const string OnlyAgentDecides = "Only the sourcing agent can decide on behalf of another user.";
        public const string CannotDecide = "You cannot decide this proposal.";
        public const string UseDecisionActions = "Use Approve, Reject, Retry or Acknowledge to change the status of an agent proposal.";
        public const string NotEditable = "An agent proposal cannot be changed after it is created.";
        public const string DuplicateOpen = "An open proposal for the same action already exists.";

        public static int StateOf(int status)
        {
            return status == Pending || status == Open || status == Failed ? 0 : 1;
        }

        public static string DedupKey(string table, Guid id, int actionType)
        {
            return table + ":" + id.ToString("D").ToLowerInvariant() + ":" + actionType.ToString(CultureInfo.InvariantCulture);
        }

        public static int InitialStatus(int kind)
        {
            return kind == Proposal ? Pending : kind == Insight ? Open : Done;
        }

        public static DateTime ExpiresOn(DateTime createdUtc, int days)
        {
            return createdUtc.Date.AddDays(days <= 0 ? 5 : days);
        }

        public static bool IsInvoiceAction(int actionType)
        {
            return actionType == ApproveInvoice || actionType == RejectInvoice;
        }

        public static bool CanDecide(int actionType, bool isAdmin, bool isBuyer, bool isProjectManager, bool isSecondLevelApprover)
        {
            if (IsInvoiceAction(actionType)) return isAdmin || isSecondLevelApprover;
            if (actionType == InviteSupplier) return isAdmin || isBuyer;
            return isAdmin || isBuyer || isProjectManager;
        }

        /// <summary>The status after the decision; Executed is the intended status, the caller turns it into Failed or Superseded when needed.</summary>
        public static int Decide(int kind, int status, bool approve, string note)
        {
            if (kind == Insight && status == Open) return Acknowledged;
            if (kind == Proposal && status == Pending)
            {
                if (approve) return Executed;
                if (string.IsNullOrWhiteSpace(note)) throw new InvalidOperationException(NoteRequired);
                return Rejected;
            }
            throw new InvalidOperationException(AlreadyDecided);
        }

        public static bool IsTargetValid(int actionType, int targetStatus)
        {
            switch (actionType)
            {
                case SourceViaRfq:
                case DirectOrder:
                    return targetStatus == Model.PrApproved;
                case AwardRfq:
                    return targetStatus == Model.RfqSent;
                case ApproveInvoice:
                case RejectInvoice:
                    return targetStatus == Model.InvoiceToReview;
                case InviteSupplier:
                    return true;
                default:
                    return false;
            }
        }

        public static SourcePayload ParseSource(string json)
        {
            var result = new SourcePayload();
            var data = Read(json);
            if (data == null) return result;
            if (data.SupplierIds != null)
            {
                var list = new System.Collections.Generic.List<Guid>();
                foreach (var s in data.SupplierIds)
                {
                    Guid g;
                    if (Guid.TryParse(s, out g)) list.Add(g);
                }
                result.SupplierIds = list.ToArray();
            }
            DateTime d;
            if (!string.IsNullOrWhiteSpace(data.Deadline)
                && DateTime.TryParseExact(data.Deadline.Trim(), "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out d))
                result.Deadline = d;
            return result;
        }

        /// <summary>A Guid property of the payload (supplierId, contactId); null when missing or invalid.</summary>
        public static Guid? ParseGuid(string json, string name)
        {
            var data = Read(json);
            if (data == null) return null;
            string value = name == "supplierId" ? data.SupplierId : name == "contactId" ? data.ContactId : null;
            Guid g;
            return Guid.TryParse(value, out g) ? (Guid?)g : null;
        }

        public static string ParseNote(string json)
        {
            var data = Read(json);
            return data == null ? null : data.Note;
        }

        public static Guid ResolveDecider(Guid callerId, Guid? agentUserId, Guid? decidedBy)
        {
            if (!decidedBy.HasValue) return callerId;
            if (!agentUserId.HasValue || agentUserId.Value != callerId) throw new InvalidOperationException(OnlyAgentDecides);
            return decidedBy.Value;
        }

        private static ProposalJson Read(string json)
        {
            if (string.IsNullOrWhiteSpace(json)) return null;
            try
            {
                var serializer = new DataContractJsonSerializer(typeof(ProposalJson));
                using (var stream = new MemoryStream(Encoding.UTF8.GetBytes(json)))
                    return (ProposalJson)serializer.ReadObject(stream);
            }
            catch (Exception)
            {
                return null;
            }
        }
    }
}
