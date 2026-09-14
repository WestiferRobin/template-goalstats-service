using GoalStats.Template.Api.IntegrationTests.Fixtures;
using System.Net;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;
using Xunit;
using System.Text;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using Microsoft.AspNetCore.Http;

namespace GoalStats.Template.Api.IntegrationTests.Controllers;

public class MetaControllerTests
{
    [Theory]
    [InlineData("/health", HealthStatus.Unhealthy, 200, "Healthy")]
    [InlineData("/ready", HealthStatus.Healthy, 200, "Healthy")]
    [InlineData("/ready", HealthStatus.Degraded, 200, "Degraded")]
    [InlineData("/ready", HealthStatus.Unhealthy, 503, "Unhealthy")]
    public async Task Status_WhenChecksSelected_PreservesTransport(string path, HealthStatus status, int code, string body)
    {
        var selected = new Probe(status);
        var healthy = new Probe(HealthStatus.Healthy);
        var excluded = new Probe(HealthStatus.Unhealthy);
        using var baseline = new ApiFactory();
        using var factory = Configure(baseline, selected, healthy, excluded);
        using var client = factory.CreateClient();
        using var response = await client.GetAsync(path);
        await AssertTransport(response, code, body);
        Assert.Equal(path == "/health" ? 0 : 1, selected.Calls);
        Assert.Equal(path == "/health" ? 0 : 1, healthy.Calls);
        Assert.Equal(0, excluded.Calls);
    }

    [Theory]
    [InlineData("/health", "HEAD")]
    [InlineData("/health", "POST")]
    [InlineData("/health", "OPTIONS")]
    [InlineData("/health", "PATCH")]
    [InlineData("/ready", "HEAD")]
    [InlineData("/ready", "POST")]
    [InlineData("/ready", "OPTIONS")]
    [InlineData("/ready", "PATCH")]
    public async Task Method_WhenNotGet_PreservesUnrestrictedMapping(string path, string method)
    {
        using var baseline = new ApiFactory();
        using var factory = Configure(baseline, new Probe(HealthStatus.Healthy));
        using var client = factory.CreateClient();
        using var request = new HttpRequestMessage(new HttpMethod(method), path);
        using var response = await client.SendAsync(request);
        // TestServer exposes the middleware body even for HEAD; this assertion
        // characterizes the hosted pipeline, not Kestrel's wire-level suppression.
        await AssertTransport(response, 200, "Healthy");
    }

    [Theory]
    [InlineData("/health", "application/json")]
    [InlineData("/health", "text/html")]
    [InlineData("/ready", "application/json")]
    [InlineData("/ready", "text/html")]
    public async Task Accept_WhenAlternateRequested_PreservesPlaintext(string path, string accept)
    {
        using var baseline = new ApiFactory();
        using var factory = Configure(baseline, new Probe(HealthStatus.Degraded));
        using var client = factory.CreateClient();
        client.DefaultRequestHeaders.Accept.ParseAdd(accept);
        using var response = await client.GetAsync(path);
        await AssertTransport(response, 200, path == "/health" ? "Healthy" : "Degraded");
    }

    [Fact]
    public async Task RequestAbort_WhenReadyCheckPending_ReachesRegisteredCheck()
    {
        var probe = new Probe(HealthStatus.Healthy, pending: true);
        using var baseline = new ApiFactory();
        using var factory = Configure(baseline, probe);
        using var caller = new CancellationTokenSource();
        CancellationToken requestAbort = default;
        var request = factory.Server.SendAsync(context =>
        {
            context.Request.Method = "GET";
            context.Request.Path = "/ready";
            requestAbort = context.RequestAborted;
        }, caller.Token);
        try
        {
            var token = await probe.Started.Task.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.True(token.CanBeCanceled);
            Assert.False(token.IsCancellationRequested);
            Assert.False(requestAbort.IsCancellationRequested);
            caller.Cancel();
            await probe.Cancelled.Task.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.True(requestAbort.IsCancellationRequested);
            Assert.True(token.IsCancellationRequested);
        }
        finally
        {
            caller.Cancel();
            try { await request.WaitAsync(TimeSpan.FromSeconds(5)); }
            catch (OperationCanceledException) { }
        }
    }

    private static WebApplicationFactory<Program> Configure(ApiFactory baseline, Probe selected,
        Probe? healthy = null, Probe? excluded = null) => baseline.WithWebHostBuilder(builder =>
        builder.ConfigureTestServices(services => services.Configure<HealthCheckServiceOptions>(options =>
        {
            // Keep the real HealthCheckService and replace only provider work.
            options.Registrations.Clear();
            options.Registrations.Add(new HealthCheckRegistration("selected", selected, null, ["ready"]));
            if (healthy is not null)
                options.Registrations.Add(new HealthCheckRegistration("healthy", healthy, null, ["ready"]));
            if (excluded is not null)
            {
                options.Registrations.Add(new HealthCheckRegistration("excluded", excluded, null, ["other"]));
                options.Registrations.Add(new HealthCheckRegistration("untagged", excluded, null, []));
            }
        })));

    private static async Task AssertTransport(HttpResponseMessage response, int code, string body)
    {
        Assert.Equal(code, (int)response.StatusCode);
        Assert.Equal("text/plain", response.Content.Headers.ContentType?.ToString());
        Assert.Equal(Encoding.UTF8.GetBytes(body), await response.Content.ReadAsByteArrayAsync());
        Assert.Equal("no-store, no-cache", Assert.Single(response.Headers.GetValues("Cache-Control")));
        Assert.Equal("no-cache", Assert.Single(response.Headers.GetValues("Pragma")));
        Assert.Equal("Thu, 01 Jan 1970 00:00:00 GMT", Assert.Single(response.Content.Headers.GetValues("Expires")));
    }

    private sealed class Probe(HealthStatus status, bool pending = false) : IHealthCheck
    {
        public int Calls { get; private set; }
        public TaskCompletionSource<CancellationToken> Started { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public TaskCompletionSource<bool> Cancelled { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public async Task<HealthCheckResult> CheckHealthAsync(HealthCheckContext context, CancellationToken cancellationToken = default)
        {
            Calls++;
            Started.TrySetResult(cancellationToken);
            if (pending)
            {
                try { await Task.Delay(Timeout.Infinite, cancellationToken); }
                catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
                {
                    Cancelled.TrySetResult(true);
                    throw;
                }
            }
            return new HealthCheckResult(status, "PRIVATE_PROVIDER_DESCRIPTION", new IOException("PRIVATE_PROVIDER_ERROR"));
        }
    }

    [Theory]
    [InlineData("")]
    [InlineData("Host=127.0.0.1;Port=1;Database=unavailable;Username=test;Password=test;Timeout=1;Pooling=false")]
    public async Task Missing_or_unavailable_postgres_is_unready_but_live(string connectionString)
    {
        using var factory = new ApiFactory().WithWebHostBuilder(builder =>
            builder.ConfigureAppConfiguration((_, config) => config.AddInMemoryCollection(
                new Dictionary<string, string?> { ["ConnectionStrings:Postgres"] = connectionString, ["ConnectionStrings:Redis"] = "" })));
        using var client = factory.CreateClient();
        using var health = await client.GetAsync("/health");
        using var ready = await client.GetAsync("/ready");

        Assert.Equal(HttpStatusCode.OK, health.StatusCode);
        Assert.Equal("Healthy", await health.Content.ReadAsStringAsync());
        Assert.Equal(HttpStatusCode.ServiceUnavailable, ready.StatusCode);
        Assert.Equal("Unhealthy", await ready.Content.ReadAsStringAsync());
    }
}
