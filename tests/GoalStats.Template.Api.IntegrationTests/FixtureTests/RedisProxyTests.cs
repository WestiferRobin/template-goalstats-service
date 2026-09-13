using GoalStats.Template.Api.IntegrationTests.Fixtures;
using StackExchange.Redis;
using Xunit;

namespace GoalStats.Template.Api.IntegrationTests.FixtureTests;

[Trait("Category", "Redis")]
public class RedisProxyTests
{
    [Fact]
    public async Task Observation_WhenRearmed_IgnoresHistoricalTrafficAndRequiresFreshMatch()
    {
        await using var proxy = new RedisProxy(Infrastructure.Cache.RedisCacheTests.Connection());
        using var redis = await ConnectionMultiplexer.ConnectAsync(proxy.Connection);
        var database = redis.GetDatabase();
        var key = $"goalstats-template-test:{Guid.NewGuid():N}:observation";
        var first = proxy.ObserveRequestsFor(key);
        await database.KeyExistsAsync(key).WaitAsync(TimeSpan.FromSeconds(5));
        await first.WaitAsync(TimeSpan.FromSeconds(5));

        var fresh = proxy.ObserveRequestsFor(key);
        // A completed unrelated round-trip is a deterministic traffic barrier, not a sleep.
        await database.KeyExistsAsync($"goalstats-template-test:{Guid.NewGuid():N}:unrelated")
            .WaitAsync(TimeSpan.FromSeconds(5));
        Assert.False(fresh.IsCompleted);
        await database.KeyExistsAsync(key).WaitAsync(TimeSpan.FromSeconds(5));
        await fresh.WaitAsync(TimeSpan.FromSeconds(5));
        // EXISTS only: this regression creates no keys to clean up.
    }

}
