using Microsoft.EntityFrameworkCore;
using GoalStats.Template.Api.Infrastructure.Database;
using GoalStats.Template.Api.Infrastructure.Database.Repositories.Action;
using GoalStats.Template.Api.Infrastructure.Database.Repositories.Item;

namespace GoalStats.Template.Api.Extensions;

public static class DatabaseExtensions
{
    public static IServiceCollection AddDatabase(
        this IServiceCollection services,
        IConfiguration configuration)
    {
        services.AddDbContext<TemplateDbContext>(options =>
            options.UseNpgsql(configuration.GetConnectionString("Postgres"),
                postgres => postgres.CommandTimeout(5)));
        services.AddScoped<IItemRepository, ItemRepository>();
        services.AddScoped<IActionRepository, ActionRepository>();
        services.AddHealthChecks()
            .AddCheck<PostgresHealthCheck>("postgres", tags: ["ready"]);

        return services;
    }
}
