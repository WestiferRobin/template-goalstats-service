using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using Microsoft.Extensions.Options;

namespace GoalStats.Template.Api.Controllers;

[ApiController]
[ApiExplorerSettings(IgnoreApi = true)]
public sealed class MetaController : ControllerBase
{
    private readonly HealthCheckMiddleware liveness;
    private readonly HealthCheckMiddleware readiness;

    public MetaController(HealthCheckService healthChecks)
    {
        liveness = new HealthCheckMiddleware(_ => Task.CompletedTask,
            Options.Create(new HealthCheckOptions { Predicate = _ => false }), healthChecks);
        readiness = new HealthCheckMiddleware(_ => Task.CompletedTask,
            Options.Create(new HealthCheckOptions { Predicate = registration => registration.Tags.Contains("ready") }),
            healthChecks);
    }

    // GET is documented; route-only attributes preserve MapHealthChecks' unrestricted methods.
    // The framework owns aggregation, response bytes/headers and request cancellation.
    [Route("/health")]
    public Task Health() => liveness.InvokeAsync(HttpContext);

    [Route("/ready")]
    public Task Ready() => readiness.InvokeAsync(HttpContext);
}
