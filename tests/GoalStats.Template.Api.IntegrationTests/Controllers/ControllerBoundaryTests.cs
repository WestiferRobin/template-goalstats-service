using System.Net;
using System.Net.Http.Json;
using System.Text;
using GoalStats.Template.Api.Dtos.Action;
using GoalStats.Template.Api.Dtos.Action.Requests;
using GoalStats.Template.Api.Dtos.Item;
using GoalStats.Template.Api.Dtos.Item.Requests;
using GoalStats.Template.Api.IntegrationTests.Fixtures;
using GoalStats.Template.Api.Services;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Xunit;

namespace GoalStats.Template.Api.IntegrationTests.Controllers;

public class ControllerBoundaryTests
{
    private static readonly Guid Parent = Guid.Parse("11111111-1111-4111-8111-111111111111");

    [Theory]
    [InlineData("item")]
    [InlineData("action")]
    [InlineData("nested-action")]
    public async Task RequestAbort_WhenServicePending_CancelsThroughProductionRoute(string route)
    {
        var probe = new ServiceProbe(fail: false);
        using var baseline = new ApiFactory();
        using var factory = baseline.WithWebHostBuilder(builder => builder.ConfigureTestServices(services => Register(services, probe)));
        using var caller = new CancellationTokenSource();
        using var body = new MemoryStream(Encoding.UTF8.GetBytes(Body(route)));
        var request = factory.Server.SendAsync(context =>
        {
            context.Request.Method = "POST";
            context.Request.Path = Path(route);
            context.Request.ContentType = "application/json";
            context.Request.ContentLength = body.Length;
            context.Request.Body = body;
        }, caller.Token);
        try
        {
            var observed = await probe.Started.Task.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Equal(observed.RequestAbort, observed.ServiceToken);
            Assert.True(observed.ServiceToken.CanBeCanceled);
            Assert.False(observed.ServiceToken.IsCancellationRequested);
            AssertOwner(route, observed.Owner);
            Assert.False(probe.Cancelled.Task.IsCompleted);
            caller.Cancel();
            await probe.Cancelled.Task.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.True(observed.ServiceToken.IsCancellationRequested);
        }
        finally
        {
            caller.Cancel();
            // A disconnected caller has no promised HTTP response/status contract.
            try { await request.WaitAsync(TimeSpan.FromSeconds(5)); }
            catch (OperationCanceledException) { }
        }
    }

    [Theory]
    [InlineData("item")]
    [InlineData("action")]
    [InlineData("nested-action")]
    public async Task ServiceFailure_WhenProductionRouteInvoked_ReturnsSafeProblemDetails(string route)
    {
        var probe = new ServiceProbe(fail: true);
        using var baseline = new ApiFactory();
        using var factory = baseline.WithWebHostBuilder(builder => builder.ConfigureTestServices(services => Register(services, probe)));
        using var client = factory.CreateClient();
        using var response = await client.PostAsync(Path(route), new StringContent(Body(route), Encoding.UTF8, "application/json"));
        var observed = await probe.Started.Task.WaitAsync(TimeSpan.FromSeconds(5));
        AssertOwner(route, observed.Owner);
        Assert.Equal(HttpStatusCode.InternalServerError, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        var problem = await response.Content.ReadFromJsonAsync<ProblemDetails>();
        Assert.NotNull(problem);
        Assert.Equal(500, problem.Status);
        Assert.Equal("Internal Server Error", problem.Title);
        Assert.Equal("An unexpected error occurred.", problem.Detail);
        var json = await response.Content.ReadAsStringAsync();
        Assert.DoesNotContain("PRIVATE_SERVICE_FAILURE", json);
        Assert.DoesNotContain("InvalidOperationException", json);
    }

    private static string Path(string route) => route switch
    {
        "item" => "/items", "action" => "/actions", _ => $"/items/{Parent}/actions"
    };
    private static string Body(string route) => route switch
    {
        "item" => "{\"name\":\"Boundary\"}",
        "action" => $"{{\"name\":\"Boundary\",\"type\":\"create\",\"itemId\":\"{Parent}\"}}",
        _ => "{\"name\":\"Boundary\",\"type\":\"create\"}"
    };
    private static void AssertOwner(string route, Guid? owner)
    {
        if (route == "item") Assert.Null(owner);
        else Assert.Equal(Parent, owner);
    }
    private static void Register(IServiceCollection services, ServiceProbe probe)
    {
        services.AddHttpContextAccessor();
        services.RemoveAll<IItemService>(); services.RemoveAll<IActionService>();
        services.AddSingleton<IItemService>(provider => new ItemBoundaryService(probe, provider.GetRequiredService<IHttpContextAccessor>()));
        services.AddSingleton<IActionService>(provider => new ActionBoundaryService(probe, provider.GetRequiredService<IHttpContextAccessor>()));
    }
    private sealed record Observation(CancellationToken ServiceToken, CancellationToken RequestAbort, Guid? Owner);
    private sealed class ServiceProbe(bool fail)
    {
        public TaskCompletionSource<Observation> Started { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public TaskCompletionSource<bool> Cancelled { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public async Task<T> Invoke<T>(IHttpContextAccessor accessor, CancellationToken token, Guid? owner = null)
        {
            Started.TrySetResult(new(token, accessor.HttpContext!.RequestAborted, owner));
            if (fail) throw new InvalidOperationException("PRIVATE_SERVICE_FAILURE");
            try { await Task.Delay(Timeout.Infinite, token); }
            catch (OperationCanceledException) when (token.IsCancellationRequested)
            {
                Cancelled.TrySetResult(true);
                throw;
            }
            throw new InvalidOperationException("The pending service must be cancelled.");
        }
    }
    // Only the creation routes participate; unexpected service operations fail loudly.
    private sealed class ItemBoundaryService(ServiceProbe probe, IHttpContextAccessor accessor) : IItemService
    {
        public Task<ItemDto> CreateAsync(CreateItemRequest request, CancellationToken cancellationToken = default) => probe.Invoke<ItemDto>(accessor, cancellationToken);
        public Task<ItemDto> GetAsync(Guid id, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        public Task<IReadOnlyList<ItemDto>> ListAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        public Task<ItemDto> UpdateAsync(Guid id, UpdateItemRequest request, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        public Task DeleteAsync(Guid id, CancellationToken cancellationToken = default) => throw new NotSupportedException();
    }
    private sealed class ActionBoundaryService(ServiceProbe probe, IHttpContextAccessor accessor) : IActionService
    {
        public Task<ActionDto> CreateAsync(CreateActionRequest request, CancellationToken cancellationToken = default) => probe.Invoke<ActionDto>(accessor, cancellationToken, request.ItemId);
        public Task<ActionDto> GetAsync(Guid id, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        public Task<IReadOnlyList<ActionDto>> ListAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        public Task<IReadOnlyList<ActionDto>> ListByItemAsync(Guid id, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        public Task<ActionDto> UpdateAsync(Guid id, UpdateActionRequest request, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        public Task DeleteAsync(Guid id, CancellationToken cancellationToken = default) => throw new NotSupportedException();
    }
}
