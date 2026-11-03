using System;
using OpenProject365.Plugins;
using Xunit;

public class ProposalTests
{
    private static readonly Guid A = new Guid("aaaaaaaa-0000-0000-0000-000000000001");
    private static readonly Guid B = new Guid("bbbbbbbb-0000-0000-0000-000000000002");
    private static readonly Guid C = new Guid("cccccccc-0000-0000-0000-000000000003");

    [Fact] public void DedupKey_IsTableIdAction() =>
        Assert.Equal("op365_rfq:0f8fad5b-d9cb-469f-a165-70867728950e:365000002",
            Proposals.DedupKey("op365_rfq", new Guid("0F8FAD5B-D9CB-469F-A165-70867728950E"), Proposals.AwardRfq));
    [Fact] public void Decide_PendingApprove_IsExecuted() => Assert.Equal(Proposals.Executed, Proposals.Decide(Proposals.Proposal, Proposals.Pending, true, null));
    [Fact] public void Decide_RejectWithoutNote_Throws() =>
        Assert.Equal("Add a note to reject the proposal.", Assert.Throws<InvalidOperationException>(() => Proposals.Decide(Proposals.Proposal, Proposals.Pending, false, " ")).Message);
    [Fact] public void Decide_RejectWithNote_IsRejected() => Assert.Equal(Proposals.Rejected, Proposals.Decide(Proposals.Proposal, Proposals.Pending, false, "no"));
    [Fact] public void Decide_AlreadyDecided_Throws() =>
        Assert.Equal("This proposal has already been decided.", Assert.Throws<InvalidOperationException>(() => Proposals.Decide(Proposals.Proposal, Proposals.Executed, true, null)).Message);
    [Fact] public void Decide_InsightOpen_IsAcknowledged() => Assert.Equal(Proposals.Acknowledged, Proposals.Decide(Proposals.Insight, Proposals.Open, false, null));
    [Fact] public void CanDecide_InvoiceNeedsSecondLevel() {
        Assert.False(Proposals.CanDecide(Proposals.ApproveInvoice, false, true, true, false));
        Assert.True(Proposals.CanDecide(Proposals.RejectInvoice, false, false, false, true)); }
    [Fact] public void CanDecide_RfqAllowsBuyerOrManager() {
        Assert.True(Proposals.CanDecide(Proposals.AwardRfq, false, true, false, false));
        Assert.True(Proposals.CanDecide(Proposals.SourceViaRfq, false, false, true, false));
        Assert.False(Proposals.CanDecide(Proposals.InviteSupplier, false, false, true, false)); }
    [Fact] public void IsTargetValid_AwardNeedsSentRfq() {
        Assert.True(Proposals.IsTargetValid(Proposals.AwardRfq, Model.RfqSent));
        Assert.False(Proposals.IsTargetValid(Proposals.AwardRfq, Model.RfqAwarded)); }
    [Fact] public void ResolveDecider_ForgedDecidedBy_Throws() =>
        Assert.Equal("Only the sourcing agent can decide on behalf of another user.",
            Assert.Throws<InvalidOperationException>(() => Proposals.ResolveDecider(A, B, C)).Message);
    [Fact] public void ResolveDecider_AgentPassesDecidedBy() => Assert.Equal(C, Proposals.ResolveDecider(B, B, C));
    [Fact] public void ResolveDecider_NoDecidedBy_IsCaller() => Assert.Equal(A, Proposals.ResolveDecider(A, null, null));
    [Fact] public void ParseSource_ReadsSuppliersAndDeadline() {
        var p = Proposals.ParseSource("{\"supplierIds\":[\"0f8fad5b-d9cb-469f-a165-70867728950e\"],\"deadline\":\"2026-11-20\"}");
        Assert.Single(p.SupplierIds); Assert.Equal(new DateTime(2026, 11, 20), p.Deadline); }
    [Fact] public void ParseSource_InvalidJson_IsEmpty() => Assert.Empty(Proposals.ParseSource("not json").SupplierIds);
    [Fact] public void ParseGuidAndNote_ReadFields() {
        var json = "{\"supplierId\":\"0f8fad5b-d9cb-469f-a165-70867728950e\",\"note\":\"hi\"}";
        Assert.Equal(new Guid("0f8fad5b-d9cb-469f-a165-70867728950e"), Proposals.ParseGuid(json, "supplierId"));
        Assert.Null(Proposals.ParseGuid(json, "contactId"));
        Assert.Null(Proposals.ParseGuid("", "supplierId"));
        Assert.Equal("hi", Proposals.ParseNote(json)); }
    [Fact] public void ExpiresOn_DefaultsToFiveDays() => Assert.Equal(new DateTime(2026, 11, 8), Proposals.ExpiresOn(new DateTime(2026, 11, 3, 15, 0, 0), 0));
    [Fact] public void StateAndInitialStatus() {
        Assert.Equal(0, Proposals.StateOf(Proposals.Failed));
        Assert.Equal(1, Proposals.StateOf(Proposals.Executed));
        Assert.Equal(Proposals.Pending, Proposals.InitialStatus(Proposals.Proposal));
        Assert.Equal(Proposals.Open, Proposals.InitialStatus(Proposals.Insight));
        Assert.Equal(Proposals.Done, Proposals.InitialStatus(Proposals.Log)); }
}
