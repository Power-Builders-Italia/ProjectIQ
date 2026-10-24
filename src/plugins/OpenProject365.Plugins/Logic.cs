using System;
using System.Collections.Generic;
using System.Linq;

namespace OpenProject365.Plugins
{
    // Pure calculations without SDK types, covered by OpenProject365.Plugins.Tests.

    public class WbsRow
    {
        public Guid Id;
        public Guid? ParentId;
        public decimal Budget;
        public decimal Hours;
        public decimal Progress;
    }

    public static class WbsMath
    {
        /// <summary>Progress of the leaf nodes weighted by budget, then by hours, else a plain average.</summary>
        public static decimal Progress(IList<WbsRow> rows)
        {
            var parents = new HashSet<Guid>(rows.Where(r => r.ParentId.HasValue).Select(r => r.ParentId.Value));
            var leaves = rows.Where(r => !parents.Contains(r.Id)).ToList();
            if (leaves.Count == 0) return 0m;
            Func<WbsRow, decimal> weight;
            if (leaves.Sum(l => l.Budget) > 0) weight = l => l.Budget;
            else if (leaves.Sum(l => l.Hours) > 0) weight = l => l.Hours;
            else weight = l => 1m;
            var total = leaves.Sum(weight);
            return Math.Round(leaves.Sum(l => weight(l) * l.Progress) / total, 2);
        }
    }

    public static class DependencyGraph
    {
        /// <summary>True if <paramref name="to"/> can be reached from <paramref name="from"/> following predecessor → successor edges.</summary>
        public static bool Reaches(IEnumerable<Tuple<Guid, Guid>> edges, Guid from, Guid to)
        {
            var next = edges.ToLookup(e => e.Item1, e => e.Item2);
            var seen = new HashSet<Guid>();
            var stack = new Stack<Guid>();
            stack.Push(from);
            while (stack.Count > 0)
            {
                var n = stack.Pop();
                if (n == to) return true;
                if (!seen.Add(n)) continue;
                foreach (var m in next[n]) stack.Push(m);
            }
            return false;
        }
    }

    public static class TimeReminder
    {
        /// <summary>
        /// Hours a resource should record on a day: weekly hours spread over the working days, 0 on other days,
        /// less the absence hours (a whole-day absence has no hours and leaves nothing to record).
        /// </summary>
        public static decimal ExpectedHours(decimal weeklyHours, ICollection<DayOfWeek> workingDays, DayOfWeek day, bool absent, decimal? absenceHours)
        {
            if (workingDays.Count == 0 || !workingDays.Contains(day)) return 0m;
            var expected = Math.Round(weeklyHours / workingDays.Count, 2);
            if (absent) expected = absenceHours.HasValue ? Math.Max(0m, expected - absenceHours.Value) : 0m;
            return expected;
        }

        /// <summary>Working Days choice value (365000000 = Monday … 365000006 = Sunday) to a day of the week.</summary>
        public static DayOfWeek Day(int choice) => (DayOfWeek)((choice - 365000000 + 1) % 7);
    }

    public class OrderLineRow
    {
        public decimal Quantity;
        public decimal Received;
        public decimal Price;
    }

    public static class PurchaseMath
    {
        /// <summary>Above the Settings threshold (no threshold = never).</summary>
        public static bool AboveThreshold(decimal estimated, decimal? threshold) => threshold.HasValue && threshold.Value > 0m && estimated > threshold.Value;

        /// <summary>Actual + committed + the request exceed the budget (no budget = never).</summary>
        public static bool OverBudget(decimal budget, decimal actual, decimal committed, decimal estimated) => budget > 0m && actual + committed + estimated > budget;

        /// <summary>Committed cost of open order lines: quantity still to receive x price.</summary>
        public static decimal Committed(IEnumerable<OrderLineRow> lines) => lines.Sum(l => Math.Max(0m, l.Quantity - l.Received) * l.Price);

        public static bool FullyReceived(IEnumerable<OrderLineRow> lines) => lines.All(l => l.Received >= l.Quantity);

        /// <summary>"orderLineId=quantity" (invariant decimal) from the Lines input of op365_RegisterGoodsReceipt.</summary>
        public static Tuple<Guid, decimal> ReceiptLine(string value)
        {
            var parts = (value ?? "").Split('=');
            Guid id;
            decimal quantity;
            if (parts.Length != 2 || !Guid.TryParse(parts[0].Trim(), out id)
                || !decimal.TryParse(parts[1].Trim(), System.Globalization.NumberStyles.Number, System.Globalization.CultureInfo.InvariantCulture, out quantity))
                throw new ArgumentException("Receipt lines are \"orderLineId=quantity\": " + value);
            return Tuple.Create(id, quantity);
        }
    }

    public static class OrderStatus
    {
        public const int Draft = 1, Sent = 365000000, Confirmed = 365000001, Received = 365000002, Cancelled = 365000003;

        /// <summary>Error message for a purchase order status change, null when allowed. Received is set by goods receipts.</summary>
        public static string Check(int from, int to, bool hasReceipts)
        {
            if (to == Sent && from == Draft) return null;
            if (to == Confirmed && from == Sent) return null;
            if (to == Draft && from == Sent) return null;
            if (to == Cancelled && (from == Draft || from == Sent || from == Confirmed))
                return hasReceipts ? "Cancel the goods receipts before cancelling the order." : null;
            if (to == Received) return "An order becomes Received when all its lines are received.";
            return "This status change is not allowed for the purchase order.";
        }
    }
}
