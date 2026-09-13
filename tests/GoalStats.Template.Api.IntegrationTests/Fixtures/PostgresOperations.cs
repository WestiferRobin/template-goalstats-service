using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Npgsql;
using GoalStats.Template.Api.Infrastructure.Database;
namespace GoalStats.Template.Api.IntegrationTests.Fixtures;
internal static class PostgresOperations
{
    public static string Connection(PostgresFixture fixture)
    {
        using var scope = fixture.Factory.Services.CreateScope();
        return scope.ServiceProvider.GetRequiredService<TemplateDbContext>().Database.GetConnectionString()!;
    }
    public static TemplateDbContext Context(string connection, string? application = null)
    {
        var settings = new NpgsqlConnectionStringBuilder(connection) { Pooling = false };
        if (application is not null) settings.ApplicationName = application;
        return new TemplateDbContext(new DbContextOptionsBuilder<TemplateDbContext>().UseNpgsql(settings.ConnectionString, options => options.CommandTimeout(10)).Options);
    }
    public static async Task WaitForLockAsync(string connection, string application)
    {
        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(8));
        await using var observer = new NpgsqlConnection(connection);
        await observer.OpenAsync(deadline.Token);
        while (true)
        {
            await using var command = new NpgsqlCommand("SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE application_name = @app AND wait_event_type = 'Lock')", observer) { CommandTimeout = 2 };
            command.Parameters.AddWithValue("app", application);
            if ((bool)(await command.ExecuteScalarAsync(deadline.Token))!) return;
            await Task.Delay(20, deadline.Token);
        }
    }
}
