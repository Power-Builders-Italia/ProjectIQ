using System;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Text;

namespace OpenProject365.Plugins
{
    // Sourcing agent proposal rules without SDK types, covered by OpenProject365.Plugins.Tests.

    // Fields are assigned by DataContractJsonSerializer, not by code.
#pragma warning disable 0649
    [DataContract]
    internal class ProposalJson
    {
        [DataMember(Name = "supplierIds")] public string[] SupplierIds;
        [DataMember(Name = "deadline")] public string Deadline;
        [DataMember(Name = "supplierId")] public string SupplierId;
        [DataMember(Name = "contactId")] public string ContactId;
        [DataMember(Name = "note")] public string Note;
    }
#pragma warning restore 0649

    /// <summary>Parameters of a Source via RFQ proposal.</summary>
    public class SourcePayload
    {
        public Guid[] SupplierIds = new Guid[0];
        public DateTime? Deadline;
    }

    public static class Proposals
    {
        /// <summary>The Custom APIs op365_DecideAgentProposal runs for an approved proposal.</summary>
        public static readonly string[] ActionApis =
            { "op365_CreateRfq", "op365_SendRfq", "op365_CreatePurchaseOrder", "op365_AwardRfq", "op365_DecideSupplierInvoice", "op365_InviteToPortal" };

        /// <summary>
        /// True when an operation whose pipeline contains <paramref name="parentMessage"/> counts as running inside one of
        /// <paramref name="messages"/>. A Custom API that a plugin calls (op365_DecideAgentProposal running op365_SendRfq) is
        /// not in the ParentContext chain of the operations it makes: they show the calling Custom API instead. Every write made
        /// while op365_DecideAgentProposal runs an action comes from one of the ActionApis, so it stands for all of them.
        /// </summary>
        public static bool Covers(string parentMessage, string[] messages) =>
            Array.IndexOf(messages, parentMessage) >= 0
            || (parentMessage == "op365_DecideAgentProposal" && messages.Any(m => Array.IndexOf(ActionApis, m) >= 0));

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
        public const string NotAUser = "The user who decided is not a ProjectIQ user.";
        public const string DeciderRequired = "The sourcing agent must give the user who decided.";
        public const string NoteLocked = "The Decision Note cannot be changed after the proposal is decided.";
        public const string KindRequired = "Set the Kind and the Action Type of the agent proposal.";
        public const string NoInvitation = "The proposal has no invitation to award.";
        public const string NoContact = "The proposal has no contact to invite.";
        public const string NewProposalTitle = "New agent proposal";

        /// <summary>Lookups of a proposal as (column, table), in the order that picks the target of the dedup key and of the default name.</summary>
        public static readonly string[][] TargetLookups =
        {
            new[] { "op365_purchaserequestid", "op365_purchaserequest" },
            new[] { "op365_rfqid", "op365_rfq" },
            new[] { "op365_invitationid", "op365_rfqinvitation" },
            new[] { "op365_purchaseorderid", "op365_purchaseorder" },
            new[] { "op365_supplierinvoiceid", "op365_supplierinvoice" },
            new[] { "op365_supplierid", "account" },
            new[] { "op365_projectid", "op365_project" },
        };

        private static readonly string[] ActionLabels =
        {
            "Source via RFQ", "Direct Order", "Award RFQ", "Approve Invoice", "Reject Invoice", "Invite Supplier",
            "Supplier Reminder", "Compliance Alert", "Budget Alert", "Late Delivery", "Consolidation", "New Supplier Needed",
        };

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

        /// <summary>
        /// As <see cref="IsTargetValid(int, int)"/>; a Source via RFQ or Direct Order proposal is also superseded when its purchase
        /// request already has a non-cancelled RFQ or purchase order (someone sourced it meanwhile).
        /// </summary>
        public static bool IsTargetValid(int actionType, int targetStatus, bool requestHasOpenRfqOrOrder)
        {
            if ((actionType == SourceViaRfq || actionType == DirectOrder) && requestHasOpenRfqOrOrder) return false;
            return IsTargetValid(actionType, targetStatus);
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
            if (decidedBy.Value == Guid.Empty) throw new InvalidOperationException(NotAUser);
            return decidedBy.Value;
        }

        /// <summary>
        /// The user a decision runs as: the caller, or the user named by DecidedBy (User Name or e-mail) when the caller is the
        /// sourcing agent. The caller is checked before the name is looked up, so other callers learn nothing about user names.
        /// The agent itself never decides: without DecidedBy its call is refused.
        /// </summary>
        public static Guid ResolveDecider(Guid callerId, Guid? agentUserId, string decidedBy, Func<string, Guid?> findUser)
        {
            var isAgent = agentUserId.HasValue && agentUserId.Value == callerId;
            if (string.IsNullOrWhiteSpace(decidedBy))
            {
                if (isAgent) throw new InvalidOperationException(DeciderRequired);
                return callerId;
            }
            if (!agentUserId.HasValue || agentUserId.Value != callerId) throw new InvalidOperationException(OnlyAgentDecides);
            return ResolveDecider(callerId, agentUserId, findUser(decidedBy.Trim()) ?? Guid.Empty);
        }

        /// <summary>Retry: Failed goes back to Pending; any other status throws.</summary>
        public static int Retry(int status)
        {
            if (status != Failed) throw new InvalidOperationException(OnlyFailedRetry);
            return Pending;
        }

        /// <summary>Error of an approved action: a Pending (or already Failed) proposal becomes Failed; a decided one throws.</summary>
        public static int RecordError(int status)
        {
            if (status != Pending && status != Failed) throw new InvalidOperationException(AlreadyDecided);
            return Failed;
        }

        /// <summary>As <see cref="RecordError(int)"/>, for a decider who must be allowed to decide the proposal (also when the caller is the agent).</summary>
        public static int RecordError(int status, bool deciderCanDecide)
        {
            if (!deciderCanDecide) throw new InvalidOperationException(CannotDecide);
            return RecordError(status);
        }

        /// <summary>Error text as stored (Error column, 2000 characters).</summary>
        public static string ErrorText(string error)
        {
            error = string.IsNullOrWhiteSpace(error) ? "Unknown error." : error.Trim();
            return error.Length > 2000 ? error.Substring(0, 2000) : error;
        }

        /// <summary>The Decision Note can be edited only while the proposal is active (Pending, Open or Failed).</summary>
        public static bool NoteEditable(int status)
        {
            return StateOf(status) == 0;
        }

        /// <summary>Decision note as stored (Decision Note column, 2000 characters).</summary>
        public static string NoteText(string note)
        {
            return note != null && note.Length > 2000 ? note.Substring(0, 2000) : note;
        }

        /// <summary>Note for the supplier invoice decision: the decision note, else the stored one, else the note of the payload.</summary>
        public static string InvoiceNote(string decisionNote, string storedNote, string payload)
        {
            if (!string.IsNullOrWhiteSpace(decisionNote)) return decisionNote;
            if (!string.IsNullOrWhiteSpace(storedNote)) return storedNote;
            return ParseNote(payload);
        }

        /// <summary>English label of the action type (as the choice); empty for unknown values.</summary>
        public static string ActionLabel(int actionType)
        {
            var i = actionType - SourceViaRfq;
            return i >= 0 && i < ActionLabels.Length ? ActionLabels[i] : "";
        }

        /// <summary>Default name "{Action Type} – {target}", within the 400 characters of the column.</summary>
        public static string DefaultName(int actionType, string target)
        {
            var label = ActionLabel(actionType);
            var name = string.IsNullOrWhiteSpace(target) ? label : string.IsNullOrEmpty(label) ? target.Trim() : label + " \u2013 " + target.Trim();
            if (string.IsNullOrEmpty(name)) name = "Agent proposal";
            return name.Length > 400 ? name.Substring(0, 400) : name;
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
