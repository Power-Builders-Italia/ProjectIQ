using System;
using System.Collections.Generic;
using System.Linq;
using OpenProject365.Plugins;
using Xunit;

public class SourcingTests
{
    private static readonly Guid Pr = new Guid("11111111-0000-0000-0000-000000000001");
    private static readonly DateTime Today = new DateTime(2026, 11, 3);

    private static SupplierCandidate S(string name, int covered = 2, decimal? quoted = null, decimal? estimated = null, int? lead = null,
        int answered = 0, int asked = 0, bool preferred = false, bool blocked = false, int expired = 0, bool active = true) =>
        new SupplierCandidate
        {
            Id = Guid.NewGuid(), Name = name, CoveredLines = covered, QuotedAmount = quoted, EstimatedAmountOfQuoted = estimated,
            LeadTimeDays = lead, Answered = answered, Asked = asked, Preferred = preferred, Blocked = blocked, ExpiredDocs = expired, Active = active,
        };

    [Fact]
    public void Score_ExcludesBlockedExpiredAndInactive()
    {
        var scored = SourcingRules.Score(new[] { S("Blocked", blocked: true), S("Expired", expired: 1), S("Inactive", active: false), S("Ok") }, 2);
        Assert.Equal("Ok", scored[0].Name);
        Assert.True(scored[0].Eligible);
        Assert.All(scored.Skip(1), s => { Assert.False(s.Eligible); Assert.Equal(0m, s.Score); });
        Assert.Contains("1 expired document(s).", scored.Single(s => s.Name == "Expired").Reasons);
    }

    [Fact]
    public void Score_CheaperFasterMoreReliableWins()
    {
        var scored = SourcingRules.Score(new[]
        {
            S("Dear", quoted: 120, estimated: 100, lead: 10, answered: 1, asked: 4),
            S("Cheap", quoted: 90, estimated: 100, lead: 5, answered: 4, asked: 4),
        }, 2);
        Assert.Equal(new[] { "Cheap", "Dear" }, scored.Select(s => s.Name));
        // coverage 40 + price 25 + lead 15 + answers 15
        Assert.Equal(95m, scored[0].Score);
        Assert.Equal(0.9m, scored[0].PriceIndex);
        Assert.Equal(100m, scored[0].ResponseRatePct);
    }

    [Fact]
    public void Score_MissingDataCountsHalf()
    {
        var s = SourcingRules.Score(new[] { S("NoData", covered: 1) }, 2)[0];
        // coverage 20 + price 12.5 + lead 7.5 + answers 7.5
        Assert.Equal(47.5m, s.Score);
        Assert.Equal(50m, s.CoveragePct);
        Assert.Contains("No request for quotation in the last 12 months.", s.Reasons);
    }

    [Fact]
    public void Score_PreferredBonus()
    {
        var scored = SourcingRules.Score(new[] { S("Other"), S("Preferred", preferred: true) }, 2);
        Assert.Equal("Preferred", scored[0].Name);
        Assert.Equal(scored[1].Score + SourcingRules.PreferredBonus, scored[0].Score);
    }

    [Fact]
    public void Score_DuplicateCandidatesOnce()
    {
        var a = S("A");
        Assert.Single(SourcingRules.Score(new[] { a, a }, 2));
    }

    private static RouteResult Route(decimal amount, decimal? limit, IEnumerable<SupplierCandidate> candidates, int minQuotes = 3,
        bool approved = true, bool sourced = false) =>
        SourcingRules.Route(Pr, null, approved, sourced, amount, limit, minQuotes, SourcingRules.Score(candidates, 2), Today);

    [Fact]
    public void Route_WithinLimitAndFullCoverage_DirectOrderToPreferred()
    {
        var preferred = S("Preferred", preferred: true, quoted: 110, estimated: 100);
        var r = Route(400, 500, new[] { S("Cheaper", quoted: 80, estimated: 100, lead: 1, answered: 3, asked: 3), preferred });
        Assert.Equal(SourcingRules.RouteDirect, r.Route);
        Assert.Equal(Proposals.DirectOrder, r.ActionType);
        Assert.Equal(preferred.Id.ToString("D"), r.Payload.SupplierId);
        Assert.Null(r.Payload.SupplierIds);
    }

    [Fact]
    public void Route_WithinLimitNoPreferred_DirectOrderToBest()
    {
        var best = S("Best", quoted: 80, estimated: 100);
        var r = Route(400, 500, new[] { S("Other", quoted: 100, estimated: 100), best });
        Assert.Equal(best.Id.ToString("D"), r.Payload.SupplierId);
    }

    [Fact]
    public void Route_AboveLimit_RfqToBestMinQuotes()
    {
        var r = Route(600, 500, new[] { S("A", lead: 1), S("B", lead: 2), S("C", lead: 3), S("D", lead: 4) });
        Assert.Equal(SourcingRules.RouteRfq, r.Route);
        Assert.Equal(Proposals.SourceViaRfq, r.ActionType);
        Assert.Equal(3, r.Payload.SupplierIds.Length);
        Assert.Equal("2026-11-10", r.Payload.Deadline);
        Assert.Contains("Estimated amount 600.00 above the direct order limit 500.00.", r.Reasons);
        Assert.Contains("Invite the 3 best scored supplier(s): A, B, C.", r.Reasons);
    }

    [Fact]
    public void Route_NoLimit_RfqAndWarnsFewSuppliers()
    {
        var r = Route(100, null, new[] { S("A") });
        Assert.Equal(SourcingRules.RouteRfq, r.Route);
        Assert.Contains("No direct order limit is set.", r.Reasons);
        Assert.Contains("Fewer suppliers than the 3 quotes wanted.", r.Reasons);
    }

    [Fact]
    public void Route_WithinLimitButNoFullCoverage_Rfq()
    {
        var r = Route(100, 500, new[] { S("Half", covered: 1) });
        Assert.Equal(SourcingRules.RouteRfq, r.Route);
        Assert.Contains("No compliant supplier sells every line.", r.Reasons);
    }

    [Fact]
    public void Route_RfqSkipsNotEligible()
    {
        var ok = S("Ok");
        var r = Route(100, null, new[] { S("Blocked", blocked: true), ok });
        Assert.Equal(new[] { ok.Id.ToString("D") }, r.Payload.SupplierIds);
    }

    [Fact]
    public void Route_NoEligible_NoSupplier()
    {
        var r = Route(100, 500, new[] { S("Blocked", blocked: true) });
        Assert.Equal(SourcingRules.RouteNone, r.Route);
        Assert.Null(r.ActionType);
        Assert.Null(r.Payload);
    }

    [Fact] public void Route_NotApproved_NotApplicable() => Assert.Equal(SourcingRules.RouteNotApplicable, Route(100, 500, new[] { S("A") }, approved: false).Route);
    [Fact] public void Route_AlreadySourced_NotApplicable() => Assert.Equal(SourcingRules.RouteNotApplicable, Route(100, 500, new[] { S("A") }, sourced: true).Route);
    [Fact] public void Route_MinQuotesZero_UsesDefault() => Assert.Equal(SourcingRules.DefaultMinQuotes, Route(100, null, new[] { S("A") }, minQuotes: 0).MinQuotes);

    [Fact]
    public void Payload_IsReadByDecideAgentProposal()
    {
        var a = S("A"); var b = S("B", lead: 1);
        var r = Route(100, null, new[] { a, b });
        var parsed = Proposals.ParseSource(SourcingRules.Json(r.Payload));
        Assert.Equal(r.Payload.SupplierIds.Select(Guid.Parse), parsed.SupplierIds);
        Assert.Equal(new DateTime(2026, 11, 10), parsed.Deadline);

        var d = Route(100, 500, new[] { a });
        Assert.Equal(a.Id, Proposals.ParseGuid(SourcingRules.Json(d.Payload), "supplierId"));
    }

    [Fact]
    public void Json_HasNamedFields()
    {
        var json = SourcingRules.Json(Route(100, 500, new[] { S("A") }));
        Assert.Contains("\"route\":\"DirectOrder\"", json);
        Assert.Contains("\"suppliers\":[", json);
    }

    [Fact]
    public void Proposal_Rfq_PayloadOfTheRoute()
    {
        var r = Route(600, 500, new[] { S("A"), S("B") });
        var p = SourcingRules.Proposal(r);
        Assert.Equal(Proposals.Proposal, p.Kind);
        Assert.Equal(Proposals.SourceViaRfq, p.ActionType);
        Assert.Equal(SourcingRules.Json(r.Payload), p.Payload);
        Assert.Null(p.SupplierId);
    }

    [Fact]
    public void Proposal_DirectOrder_HasSupplier()
    {
        var a = S("A");
        var p = SourcingRules.Proposal(Route(100, 500, new[] { a }));
        Assert.Equal(Proposals.DirectOrder, p.ActionType);
        Assert.Equal(a.Id, p.SupplierId);
    }

    [Fact]
    public void Proposal_NoSupplier_Insight()
    {
        var p = SourcingRules.Proposal(Route(100, 500, new[] { S("Blocked", blocked: true) }));
        Assert.Equal(Proposals.Insight, p.Kind);
        Assert.Equal(Proposals.NewSupplierNeeded, p.ActionType);
        Assert.Null(p.Payload);
    }

    [Fact] public void Proposal_NotApplicable_Nothing() => Assert.Null(SourcingRules.Proposal(Route(100, 500, new[] { S("A") }, approved: false)));

    [Fact]
    public void Rationale_TrimmedCutAndRequired()
    {
        Assert.Equal("Why", SourcingRules.Rationale("  Why "));
        Assert.Equal(SourcingRules.RationaleMax, SourcingRules.Rationale(new string('x', 5000)).Length);
        Assert.Equal(SourcingRules.RationaleRequired, Assert.Throws<InvalidOperationException>(() => SourcingRules.Rationale(" ")).Message);
    }
}
