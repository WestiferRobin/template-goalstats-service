using Microsoft.AspNetCore.Hosting;
using GoalStats.Template.Api.IntegrationTests.Fixtures;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Xunit;
using GoalStats.Template.Api.Controllers;
using Microsoft.AspNetCore.Mvc.Controllers;

namespace GoalStats.Template.Api.IntegrationTests.Controllers;

public class EndpointSurfaceTests
{
    [Fact]
    public void Production_endpoint_surface_contains_only_the_template_routes()
    {
        using var factory = new ApiFactory().WithWebHostBuilder(builder =>
            builder.UseEnvironment("Production").ConfigureAppConfiguration((_, config) => config.AddInMemoryCollection(
                new Dictionary<string, string?> { ["ConnectionStrings:Postgres"] = "", ["ConnectionStrings:Redis"] = "" })));
        using var client = factory.CreateClient();
        Assert.Equal("Production", factory.Services.GetRequiredService<IHostEnvironment>().EnvironmentName);
        var endpoints = factory.Services.GetRequiredService<EndpointDataSource>().Endpoints.OfType<RouteEndpoint>().ToArray();
        foreach (var endpoint in endpoints)
        {
            var path = endpoint.RoutePattern.RawText!.TrimStart('/');
            var action = endpoint.Metadata.GetMetadata<ControllerActionDescriptor>();
            Assert.NotNull(action);
            var owner = path is "health" or "ready" ? typeof(MetaController)
                : path.StartsWith("items", StringComparison.Ordinal) ? typeof(ItemsController) : typeof(ActionsController);
            Assert.Equal(owner, action.ControllerTypeInfo.AsType());
            if (owner == typeof(MetaController))
            {
                var methods = endpoint.Metadata.GetMetadata<HttpMethodMetadata>()?.HttpMethods;
                Assert.True(methods is null || methods.Count == 0);
                Assert.Equal(path == "health" ? nameof(MetaController.Health) : nameof(MetaController.Ready), action.ActionName);
            }
        }
        var routes = endpoints.SelectMany(endpoint =>
        {
            // MetaController preserves unrestricted operational methods; GET is documented.
            var methods = endpoint.Metadata.GetMetadata<HttpMethodMetadata>()?.HttpMethods ?? new[] { "GET" };
            return methods.Select(method => $"{method} /{endpoint.RoutePattern.RawText!.TrimStart('/')}");
        }).OrderBy(route => route).ToArray();
        var expected = new[]
        {
            "GET /items", "POST /items", "GET /items/{itemId:guid}", "PUT /items/{itemId:guid}", "DELETE /items/{itemId:guid}",
            "GET /items/{itemId:guid}/actions", "POST /items/{itemId:guid}/actions",
            "GET /actions", "POST /actions", "GET /actions/{actionId:guid}", "PUT /actions/{actionId:guid}", "DELETE /actions/{actionId:guid}",
            "GET /health", "GET /ready"
        };
        Assert.Equal(expected.OrderBy(route => route), routes);
    }
}
