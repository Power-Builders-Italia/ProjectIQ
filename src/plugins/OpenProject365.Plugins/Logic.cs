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
}
