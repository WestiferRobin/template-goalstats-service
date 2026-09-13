using GoalStats.Template.Api.TestSupport;
using Xunit;

namespace GoalStats.Template.Api.UnitTests.TestSupport;

public class FixtureCleanupTests
{
    [Theory]
    [InlineData(true, false)]
    [InlineData(false, true)]
    [InlineData(true, true)]
    public async Task Cleanup_WhenStepsFail_AttemptsDatabaseCleanupAndPreservesErrors(bool hostFails, bool databaseFails)
    {
        var hostError = new InvalidOperationException("host disposal");
        var databaseError = new IOException("database cleanup");
        var calls = new List<string>();
        var error = await Record.ExceptionAsync(() => FixtureCleanup.RunAsync(
            () => { calls.Add("host"); return hostFails ? Task.FromException(hostError) : Task.CompletedTask; },
            () => { calls.Add("database"); return databaseFails ? Task.FromException(databaseError) : Task.CompletedTask; }));
        Assert.Equal(new[] { "host", "database" }, calls);
        if (hostFails && databaseFails)
            Assert.Equal(new Exception[] { hostError, databaseError }, Assert.IsType<AggregateException>(error).InnerExceptions);
        else Assert.Same(hostFails ? hostError : databaseError, error);
    }

}
