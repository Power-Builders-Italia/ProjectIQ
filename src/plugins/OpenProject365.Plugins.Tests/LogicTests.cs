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
