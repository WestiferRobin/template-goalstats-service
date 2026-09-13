using GoalStats.Template.Api.Infrastructure.Cache;
using GoalStats.Template.Api.Infrastructure.Cache.Action;
using GoalStats.Template.Api.Infrastructure.Cache.Item;

namespace GoalStats.Template.Api.Extensions;

public static class CacheExtensions
{
    public static IServiceCollection AddCache(
        this IServiceCollection services,
        IConfiguration configuration)
    {
        services.AddOptions<CacheOptions>()
            .BindConfiguration("Cache")
            .ValidateDataAnnotations()
            .ValidateOnStart();
        services.AddStackExchangeRedisCache(options =>
        {
            // No implicit localhost/default server when the optional connection is missing.
            var connection = configuration.GetConnectionString("Redis");
            options.Configuration = string.IsNullOrWhiteSpace(connection) ? "" : connection;
        });
        services.AddSingleton<ICache, RedisCache>();
        services.AddSingleton<IItemCache, ItemCache>();
        services.AddSingleton<IActionCache, ActionCache>();
        services.AddHealthChecks()
            .AddCheck<RedisHealthCheck>("redis", tags: ["ready"]);

        return services;
    }
}
