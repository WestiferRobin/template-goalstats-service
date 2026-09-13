using System.Runtime.ExceptionServices;

namespace GoalStats.Template.Api.TestSupport;

internal static class FixtureCleanup
{
    // Keep both failures when necessary, and never let host disposal skip database cleanup.
    internal static async Task RunAsync(Func<Task> disposeHost, Func<Task> dropDatabase)
    {
        Exception? hostError = null;
        try { await disposeHost(); }
        catch (Exception error) { hostError = error; }
        try { await dropDatabase(); }
        catch (Exception databaseError)
        {
            if (hostError is not null)
                throw new AggregateException("Host disposal and owned database cleanup failed.", hostError, databaseError);
            throw;
        }
        if (hostError is not null) ExceptionDispatchInfo.Capture(hostError).Throw();
    }

}
