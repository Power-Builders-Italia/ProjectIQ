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
