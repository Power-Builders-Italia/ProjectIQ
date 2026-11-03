using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Text;

namespace OpenProject365.Plugins
{
    // Sourcing agent analysis rules without SDK types (tasks 1-2: route a purchase request, choose the suppliers),
    // covered by OpenProject365.Plugins.Tests. The Custom APIs in SourcingAnalysis.cs read the data and call these rules.

    /// <summary>A supplier that could serve a purchase request, with the data the score needs.</summary>
    public class SupplierCandidate
    {
        public Guid Id;
        public string Name;
        public bool Active = true;
        public bool Blocked;
        public int ExpiredDocs;
        public int ExpiringDocs;
        public bool Preferred;
        /// <summary>Request lines with an item this supplier sells (item supplier row or default supplier of the item).</summary>
        public int CoveredLines;
        /// <summary>Supplier price × quantity of the covered lines that have a supplier price; null when no line has one.</summary>
        public decimal? QuotedAmount;
        /// <summary>Estimated amount of the same lines as <see cref="QuotedAmount"/>, to compare prices on the same basis.</summary>
        public decimal? EstimatedAmountOfQuoted;
        /// <summary>Longest lead time (days) of the covered items; null when unknown.</summary>
        public int? LeadTimeDays;
        /// <summary>Invitations of the last 12 months answered (Responded) and closed (Responded, Declined, or past the deadline).</summary>
        public int Answered;
        public int Asked;
        /// <summary>True when the supplier was found only through the category of the items.</summary>
        public bool CategoryOnly;
    }

    [DataContract]
    public class SupplierScore
    {
        [DataMember(Name = "supplierId", Order = 1)] public string SupplierId;
        [DataMember(Name = "name", Order = 2)] public string Name;
        [DataMember(Name = "eligible", Order = 3)] public bool Eligible;
        [DataMember(Name = "score", Order = 4)] public decimal Score;
        [DataMember(Name = "coveragePct", Order = 5)] public decimal CoveragePct;
        [DataMember(Name = "priceIndex", Order = 6, EmitDefaultValue = false)] public decimal? PriceIndex;
        [DataMember(Name = "leadTimeDays", Order = 7, EmitDefaultValue = false)] public int? LeadTimeDays;
        [DataMember(Name = "responseRatePct", Order = 8, EmitDefaultValue = false)] public decimal? ResponseRatePct;
        [DataMember(Name = "preferred", Order = 9)] public bool Preferred;
        [DataMember(Name = "reasons", Order = 10)] public string[] Reasons;
    }

    [DataContract]
    public class RoutePayload
    {
        [DataMember(Name = "supplierIds", Order = 1, EmitDefaultValue = false)] public string[] SupplierIds;
        [DataMember(Name = "deadline", Order = 2, EmitDefaultValue = false)] public string Deadline;
        [DataMember(Name = "supplierId", Order = 3, EmitDefaultValue = false)] public string SupplierId;
    }

    [DataContract]
    public class RouteResult
    {
        /// <summary>SourceViaRfq, DirectOrder, NoSupplier or NotApplicable.</summary>
        [DataMember(Name = "route", Order = 1)] public string Route;
        [DataMember(Name = "actionType", Order = 2, EmitDefaultValue = false)] public int? ActionType;
        [DataMember(Name = "purchaseRequestId", Order = 3)] public string PurchaseRequestId;
        [DataMember(Name = "projectId", Order = 4, EmitDefaultValue = false)] public string ProjectId;
        [DataMember(Name = "estimatedAmount", Order = 5)] public decimal EstimatedAmount;
        [DataMember(Name = "directOrderLimit", Order = 6, EmitDefaultValue = false)] public decimal? DirectOrderLimit;
        [DataMember(Name = "minQuotes", Order = 7)] public int MinQuotes;
        [DataMember(Name = "payload", Order = 8, EmitDefaultValue = false)] public RoutePayload Payload;
        [DataMember(Name = "reasons", Order = 9)] public string[] Reasons;
        [DataMember(Name = "suppliers", Order = 10)] public SupplierScore[] Suppliers;
    }

    public static class SourcingRules
    {
        public const string RouteRfq = "SourceViaRfq";
        public const string RouteDirect = "DirectOrder";
        public const string RouteNone = "NoSupplier";
        public const string RouteNotApplicable = "NotApplicable";

        // Score weights (total 100, plus the preferred bonus)
        public const decimal CoverageWeight = 40m;
        public const decimal PriceWeight = 25m;
        public const decimal LeadTimeWeight = 15m;
        public const decimal ResponseWeight = 15m;
        public const decimal PreferredBonus = 5m;

        public const int DefaultMinQuotes = 3;
        public const int RfqDeadlineDays = 7;

        public const string NotApproved = "Only approved purchase requests can be sourced.";

        /// <summary>
        /// Scores every candidate, best first. Not eligible (score 0, listed last): inactive, blocked, or with expired documents.
        /// Score: coverage of the request lines 40, price 25 (cheapest priced candidate / this one; no price: half), lead time 15
        /// (shortest / this one; unknown: half), answers to past invitations 15 (rate; no history: half), preferred supplier +5.
        /// </summary>
        public static List<SupplierScore> Score(IEnumerable<SupplierCandidate> candidates, int requestLines)
        {
            var list = candidates.GroupBy(c => c.Id).Select(g => g.First()).ToList();
            var eligible = list.Where(IsEligible).ToList();
            var bestPrice = eligible.Select(PriceIndex).Where(p => p.HasValue && p.Value > 0).Select(p => p.Value).DefaultIfEmpty(0m).Min();
            var bestLead = eligible.Where(c => c.LeadTimeDays.HasValue).Select(c => Math.Max(1, c.LeadTimeDays.Value)).DefaultIfEmpty(0).Min();

            var result = new List<SupplierScore>();
            foreach (var c in list)
            {
                var ok = IsEligible(c);
                var coverage = requestLines <= 0 ? 0m : Math.Min(1m, (decimal)c.CoveredLines / requestLines);
                var price = PriceIndex(c);
                var rate = c.Asked > 0 ? (decimal?)Math.Min(1m, (decimal)c.Answered / c.Asked) : null;
                decimal score = 0m;
                if (ok)
                {
                    score += CoverageWeight * coverage;
                    score += price.HasValue && price.Value > 0 && bestPrice > 0 ? PriceWeight * bestPrice / price.Value : PriceWeight / 2;
                    score += c.LeadTimeDays.HasValue && bestLead > 0 ? LeadTimeWeight * bestLead / Math.Max(1, c.LeadTimeDays.Value) : LeadTimeWeight / 2;
                    score += rate.HasValue ? ResponseWeight * rate.Value : ResponseWeight / 2;
                    if (c.Preferred) score += PreferredBonus;
                }
                result.Add(new SupplierScore
                {
                    SupplierId = c.Id.ToString("D"),
                    Name = c.Name,
                    Eligible = ok,
                    Score = Math.Round(score, 1),
                    CoveragePct = Math.Round(coverage * 100m, 0),
                    PriceIndex = price.HasValue ? (decimal?)Math.Round(price.Value, 3) : null,
                    LeadTimeDays = c.LeadTimeDays,
                    ResponseRatePct = rate.HasValue ? (decimal?)Math.Round(rate.Value * 100m, 0) : null,
                    Preferred = c.Preferred,
                    Reasons = Reasons(c, coverage, requestLines).ToArray(),
                });
            }
            return result.OrderByDescending(s => s.Eligible).ThenByDescending(s => s.Score).ThenBy(s => s.Name, StringComparer.OrdinalIgnoreCase).ToList();
        }

        public static bool IsEligible(SupplierCandidate c) => c.Active && !c.Blocked && c.ExpiredDocs <= 0;

        /// <summary>Supplier price / estimated price on the lines that have a supplier price (1 = as estimated, 0.9 = 10% cheaper).</summary>
        public static decimal? PriceIndex(SupplierCandidate c)
        {
            if (!c.QuotedAmount.HasValue || !c.EstimatedAmountOfQuoted.HasValue || c.EstimatedAmountOfQuoted.Value <= 0) return null;
            return c.QuotedAmount.Value / c.EstimatedAmountOfQuoted.Value;
        }

        private static IEnumerable<string> Reasons(SupplierCandidate c, decimal coverage, int lines)
        {
            if (!c.Active) yield return "Not an active supplier.";
            if (c.Blocked) yield return "Blocked.";
            if (c.ExpiredDocs > 0) yield return $"{c.ExpiredDocs} expired document(s).";
            if (c.ExpiringDocs > 0) yield return $"{c.ExpiringDocs} document(s) expiring soon.";
            if (c.Preferred) yield return "Preferred supplier of the request.";
            if (c.CategoryOnly) yield return "Found through the item category; no item price on record.";
            else if (lines > 0) yield return $"Sells {c.CoveredLines} of {lines} line(s).";
            var price = PriceIndex(c);
            if (price.HasValue) yield return $"Price {Percent(price.Value - 1m)} against the estimate.";
            if (c.LeadTimeDays.HasValue) yield return $"Lead time {c.LeadTimeDays.Value} day(s).";
            if (c.Asked > 0) yield return $"Answered {c.Answered} of {c.Asked} request(s) for quotation in the last 12 months.";
            else yield return "No request for quotation in the last 12 months.";
        }

        private static string Percent(decimal delta) =>
            (delta > 0 ? "+" : "") + Math.Round(delta * 100m, 0).ToString(CultureInfo.InvariantCulture) + "%";

        /// <summary>
        /// Route of an approved purchase request. Direct order when a limit is set, the estimated amount is within it and an eligible
        /// supplier sells every line (the preferred one when it does, else the best scored); otherwise a request for quotation to the
        /// best <paramref name="minQuotes"/> eligible suppliers; no eligible supplier: NoSupplier.
        /// </summary>
        public static RouteResult Route(Guid requestId, Guid? projectId, bool approved, bool alreadySourced, decimal estimatedAmount,
            decimal? directOrderLimit, int minQuotes, List<SupplierScore> scored, DateTime todayUtc)
        {
            if (minQuotes <= 0) minQuotes = DefaultMinQuotes;
            var result = new RouteResult
            {
                PurchaseRequestId = requestId.ToString("D"),
                ProjectId = projectId?.ToString("D"),
                EstimatedAmount = estimatedAmount,
                DirectOrderLimit = directOrderLimit,
                MinQuotes = minQuotes,
                Suppliers = scored.ToArray(),
            };
            var reasons = new List<string>();
            if (!approved)
            {
                result.Route = RouteNotApplicable;
                result.Reasons = new[] { "The purchase request is not approved." };
                return result;
            }
            if (alreadySourced)
            {
                result.Route = RouteNotApplicable;
                result.Reasons = new[] { "The purchase request already has a request for quotation or a purchase order." };
                return result;
            }
            var eligible = scored.Where(s => s.Eligible).ToList();
            if (eligible.Count == 0)
            {
                result.Route = RouteNone;
                result.Reasons = new[] { "No active, compliant supplier sells these items." };
                return result;
            }

            var full = eligible.Where(s => s.CoveragePct >= 100m).ToList();
            var withinLimit = directOrderLimit.HasValue && estimatedAmount <= directOrderLimit.Value;
            if (withinLimit && full.Count > 0)
            {
                var pick = full.FirstOrDefault(s => s.Preferred) ?? full[0];
                result.Route = RouteDirect;
                result.ActionType = Proposals.DirectOrder;
                result.Payload = new RoutePayload { SupplierId = pick.SupplierId };
                reasons.Add($"Estimated amount {Amount(estimatedAmount)} within the direct order limit {Amount(directOrderLimit.Value)}.");
                reasons.Add($"{pick.Name} sells every line" + (pick.Preferred ? " and is the preferred supplier." : " and has the best score."));
                result.Reasons = reasons.ToArray();
                return result;
            }

            var invite = eligible.Take(minQuotes).ToList();
            result.Route = RouteRfq;
            result.ActionType = Proposals.SourceViaRfq;
            result.Payload = new RoutePayload
            {
                SupplierIds = invite.Select(s => s.SupplierId).ToArray(),
                Deadline = todayUtc.Date.AddDays(RfqDeadlineDays).ToString("yyyy-MM-dd", CultureInfo.InvariantCulture),
            };
            if (!directOrderLimit.HasValue) reasons.Add("No direct order limit is set.");
            else if (!withinLimit) reasons.Add($"Estimated amount {Amount(estimatedAmount)} above the direct order limit {Amount(directOrderLimit.Value)}.");
            else reasons.Add("No compliant supplier sells every line.");
            reasons.Add($"Invite the {invite.Count} best scored supplier(s): " + string.Join(", ", invite.Select(s => s.Name)) + ".");
            if (invite.Count < minQuotes) reasons.Add($"Fewer suppliers than the {minQuotes} quotes wanted.");
            result.Reasons = reasons.ToArray();
            return result;
        }

        private static string Amount(decimal value) => value.ToString("0.00", CultureInfo.InvariantCulture);

        public static string Json<T>(T value)
        {
            var serializer = new DataContractJsonSerializer(typeof(T));
            using (var stream = new MemoryStream())
            {
                serializer.WriteObject(stream, value);
                return Encoding.UTF8.GetString(stream.ToArray());
            }
        }
    }
}
