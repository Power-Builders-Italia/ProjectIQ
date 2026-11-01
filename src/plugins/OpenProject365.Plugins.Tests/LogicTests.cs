using System;
using System.Collections.Generic;
using OpenProject365.Plugins;
using Xunit;

public class LogicTests
{
    private static readonly Guid A = Guid.NewGuid(), B = Guid.NewGuid(), C = Guid.NewGuid(), D = Guid.NewGuid();

    [Fact]
    public void Progress_IsWeightedByLeafBudget()
    {
        var rows = new List<WbsRow>
        {
            new WbsRow { Id = A, Budget = 999m, Progress = 0m },               // parent: ignored
            new WbsRow { Id = B, ParentId = A, Budget = 300m, Progress = 100m },
            new WbsRow { Id = C, ParentId = A, Budget = 100m, Progress = 0m },
        };
        Assert.Equal(75m, WbsMath.Progress(rows));
    }

    [Fact]
    public void Progress_FallsBackToHoursThenAverage()
    {
        Assert.Equal(25m, WbsMath.Progress(new List<WbsRow>
        {
            new WbsRow { Id = A, Hours = 30m, Progress = 0m },
            new WbsRow { Id = B, Hours = 10m, Progress = 100m },
        }));
        Assert.Equal(50m, WbsMath.Progress(new List<WbsRow>
        {
            new WbsRow { Id = A, Progress = 0m },
            new WbsRow { Id = B, Progress = 100m },
        }));
        Assert.Equal(0m, WbsMath.Progress(new List<WbsRow>()));
    }

    [Fact]
    public void Reaches_DetectsCycles()
    {
        var edges = new[] { Tuple.Create(A, B), Tuple.Create(B, C) };
        Assert.True(DependencyGraph.Reaches(edges, A, C));   // adding C → A would close a cycle
        Assert.False(DependencyGraph.Reaches(edges, C, A));
        Assert.False(DependencyGraph.Reaches(edges, A, D));
    }
}

public class TimeReminderTests
{
    private static readonly DayOfWeek[] Weekdays = { DayOfWeek.Monday, DayOfWeek.Tuesday, DayOfWeek.Wednesday, DayOfWeek.Thursday, DayOfWeek.Friday };

    [Fact]
    public void ExpectedHours_SpreadsWeeklyHoursOverWorkingDays()
    {
        Assert.Equal(8m, TimeReminder.ExpectedHours(40m, Weekdays, DayOfWeek.Monday, false, null));
        Assert.Equal(0m, TimeReminder.ExpectedHours(40m, Weekdays, DayOfWeek.Saturday, false, null));
        Assert.Equal(6.67m, TimeReminder.ExpectedHours(20m, new[] { DayOfWeek.Monday, DayOfWeek.Wednesday, DayOfWeek.Friday }, DayOfWeek.Friday, false, null));
        Assert.Equal(0m, TimeReminder.ExpectedHours(40m, new DayOfWeek[0], DayOfWeek.Monday, false, null));
    }

    [Fact]
    public void ExpectedHours_SubtractsAbsences()
    {
        Assert.Equal(0m, TimeReminder.ExpectedHours(40m, Weekdays, DayOfWeek.Monday, true, null));
        Assert.Equal(4m, TimeReminder.ExpectedHours(40m, Weekdays, DayOfWeek.Monday, true, 4m));
        Assert.Equal(0m, TimeReminder.ExpectedHours(40m, Weekdays, DayOfWeek.Monday, true, 10m));
    }

    [Fact]
    public void Day_MapsWorkingDaysChoices()
    {
        Assert.Equal(DayOfWeek.Monday, TimeReminder.Day(365000000));
        Assert.Equal(DayOfWeek.Saturday, TimeReminder.Day(365000005));
        Assert.Equal(DayOfWeek.Sunday, TimeReminder.Day(365000006));
    }
}

public class PurchaseMathTests
{
    [Fact]
    public void Threshold_And_Budget()
    {
        Assert.True(PurchaseMath.AboveThreshold(5001m, 5000m));
        Assert.False(PurchaseMath.AboveThreshold(5000m, 5000m));
        Assert.False(PurchaseMath.AboveThreshold(9999m, null));
        Assert.False(PurchaseMath.AboveThreshold(9999m, 0m));
        Assert.True(PurchaseMath.OverBudget(1000m, 600m, 300m, 200m));
        Assert.False(PurchaseMath.OverBudget(1000m, 600m, 300m, 100m));
        Assert.False(PurchaseMath.OverBudget(0m, 600m, 300m, 100m));
    }

    [Fact]
    public void Committed_CountsOnlyWhatIsStillToReceive()
    {
        var lines = new List<OrderLineRow>
        {
            new OrderLineRow { Quantity = 10m, Received = 4m, Price = 2m },   // 12
            new OrderLineRow { Quantity = 5m, Received = 6m, Price = 3m },    // over-received: 0
            new OrderLineRow { Quantity = 1m, Received = 0m, Price = 100m },  // 100
        };
        Assert.Equal(112m, PurchaseMath.Committed(lines));
        Assert.False(PurchaseMath.FullyReceived(lines));
        Assert.True(PurchaseMath.FullyReceived(new[] { new OrderLineRow { Quantity = 2m, Received = 2m } }));
    }

    [Fact]
    public void ReceiptLine_ParsesInvariantQuantities()
    {
        var id = Guid.NewGuid();
        var line = PurchaseMath.ReceiptLine(id + "=2.5");
        Assert.Equal(id, line.Item1);
        Assert.Equal(2.5m, line.Item2);
        Assert.Throws<ArgumentException>(() => PurchaseMath.ReceiptLine("nope"));
        Assert.Throws<ArgumentException>(() => PurchaseMath.ReceiptLine(id + "=x"));
    }

    [Fact]
    public void OrderStatus_Transitions()
    {
        Assert.Null(OrderStatus.Check(OrderStatus.Draft, OrderStatus.Sent, false));
        Assert.Null(OrderStatus.Check(OrderStatus.Sent, OrderStatus.Confirmed, false));
        Assert.Null(OrderStatus.Check(OrderStatus.Confirmed, OrderStatus.Cancelled, false));
        Assert.NotNull(OrderStatus.Check(OrderStatus.Confirmed, OrderStatus.Cancelled, true));
        Assert.NotNull(OrderStatus.Check(OrderStatus.Draft, OrderStatus.Confirmed, false));
        Assert.NotNull(OrderStatus.Check(OrderStatus.Confirmed, OrderStatus.Received, false));
        Assert.NotNull(OrderStatus.Check(OrderStatus.Received, OrderStatus.Cancelled, false));
    }
}

public class DocumentExpiryTests
{
    private static readonly Guid A = Guid.NewGuid(), B = Guid.NewGuid(), C = Guid.NewGuid();

    [Fact]
    public void DocumentExpiry_StatusFromDate()
    {
        var today = new DateTime(2026, 11, 1);
        Assert.Null(DocumentExpiry.Status(null, today, false));
        Assert.Equal(Model.ExpiryExpired, DocumentExpiry.Status(today.AddDays(-1), today, false));
        Assert.Equal(Model.ExpiryExpiring, DocumentExpiry.Status(today, today, false));
        Assert.Equal(Model.ExpiryExpiring, DocumentExpiry.Status(today.AddDays(30), today, false));
        Assert.Equal(Model.ExpiryValid, DocumentExpiry.Status(today.AddDays(31), today, false));
        Assert.Equal(Model.ExpiryReplaced, DocumentExpiry.Status(today.AddDays(-10), today, true));
    }

    [Fact]
    public void DocumentExpiry_ApprovedRenewalReplacesOlderDocument()
    {
        var today = new DateTime(2026, 11, 1);
        var old = new DocumentRow { Id = A, Type = 1, Expiry = today.AddDays(-5), Approved = true };
        var pending = new DocumentRow { Id = B, Type = 1, Expiry = today.AddDays(120), Approved = false };
        var other = new DocumentRow { Id = C, Type = 2, Expiry = today.AddDays(10), Approved = true };
        var docs = new List<DocumentRow> { old, pending, other };
        var statuses = DocumentExpiry.Statuses(docs, today);
        Assert.Equal(Model.ExpiryExpired, statuses[A]);          // the renewal is not approved yet
        Assert.Equal(Model.ExpiryValid, statuses[B]);
        Assert.Equal(Model.ExpiryExpiring, statuses[C]);
        Assert.Equal(Tuple.Create(1, 1), DocumentExpiry.Counters(docs, statuses));

        pending.Approved = true;
        statuses = DocumentExpiry.Statuses(docs, today);
        Assert.Equal(Model.ExpiryReplaced, statuses[A]);
        Assert.Equal(Tuple.Create(0, 1), DocumentExpiry.Counters(docs, statuses));
    }

    [Fact]
    public void DocumentExpiry_NoticeOncePerStep()
    {
        Assert.Equal(Model.NoticeExpiring, DocumentExpiry.Notice(true, Model.ExpiryExpiring, null));
        Assert.Null(DocumentExpiry.Notice(true, Model.ExpiryExpiring, Model.NoticeExpiring));
        Assert.Equal(Model.NoticeExpired, DocumentExpiry.Notice(true, Model.ExpiryExpired, null));
        Assert.Equal(Model.NoticeExpired, DocumentExpiry.Notice(true, Model.ExpiryExpired, Model.NoticeExpiring));
        Assert.Null(DocumentExpiry.Notice(true, Model.ExpiryExpired, Model.NoticeExpired));
        Assert.Null(DocumentExpiry.Notice(true, Model.ExpiryReplaced, null));
        Assert.Null(DocumentExpiry.Notice(true, Model.ExpiryValid, null));
        Assert.Null(DocumentExpiry.Notice(false, Model.ExpiryExpired, null));
    }

    [Fact]
    public void EmailTemplates_PickByLanguageThenDefault()
    {
        const string json = "{\"DocumentExpiring\":{\"Italian\":\"Documento in scadenza\",\"English\":\"Document expiring\",\"default\":\"English\"}}";
        Assert.Equal("Documento in scadenza", EmailTemplates.Pick(json, "DocumentExpiring", "Italian"));
        Assert.Equal("Document expiring", EmailTemplates.Pick(json, "DocumentExpiring", "German"));
        Assert.Equal("Document expiring", EmailTemplates.Pick(json, "DocumentExpiring", null));
        Assert.Null(EmailTemplates.Pick(json, "DocumentExpired", "Italian"));
        Assert.Null(EmailTemplates.Pick("not json", "DocumentExpiring", "Italian"));
        Assert.Null(EmailTemplates.Pick(null, "DocumentExpiring", "Italian"));
    }
}
