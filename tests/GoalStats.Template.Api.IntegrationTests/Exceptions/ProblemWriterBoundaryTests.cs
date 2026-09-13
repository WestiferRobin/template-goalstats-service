using GoalStats.Template.Api.Exceptions;
using GoalStats.Template.Api.Extensions;
using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace GoalStats.Template.Api.IntegrationTests.Exceptions;

// Exercise the configured DI -> handler -> real ProblemDetailsService -> writer/JSON
// boundary. Hosted tests in ApiExceptionHandlerTests own public exception responses.
public class ProblemWriterBoundaryTests
{
    [Fact]
    public async Task WriterFailure_WhenSelectedByRealProblemService_PropagatesWithoutFallbackBody()
    {
        var services = Services();
        // First supported writer wins; the real ProblemDetailsService dispatches it.
        services.Insert(0, ServiceDescriptor.Singleton<IProblemDetailsWriter>(new FailingWriter()));
        using var provider = services.BuildServiceProvider();
        var context = new DefaultHttpContext { RequestServices = provider };
        using var body = new MemoryStream(); context.Response.Body = body;
        var handler = provider.GetServices<IExceptionHandler>().OfType<ApiExceptionHandler>().Single();

        await Assert.ThrowsAsync<IOException>(async () =>
            await handler.TryHandleAsync(context, new NotFoundException("Missing"), default));
        Assert.Equal(0, body.Length);
    }

    [Fact]
    public async Task Fallback_WhenRealWritersRejectAccept_HonorsResponseCancellation()
    {
        using var provider = Services().BuildServiceProvider();
        using var caller = new CancellationTokenSource(); caller.Cancel();
        var context = new DefaultHttpContext { RequestServices = provider, RequestAborted = caller.Token };
        context.Request.Headers.Accept = "text/html";
        using var body = new MemoryStream(); context.Response.Body = body;
        var handler = provider.GetServices<IExceptionHandler>().OfType<ApiExceptionHandler>().Single();

        var error = await Assert.ThrowsAnyAsync<OperationCanceledException>(async () =>
            await handler.TryHandleAsync(context, new NotFoundException("Missing"), context.RequestAborted));
        Assert.Equal(caller.Token, error.CancellationToken);
        Assert.Equal("application/problem+json", context.Response.ContentType);
        Assert.Equal(0, body.Length);
    }

    private static IServiceCollection Services()
    {
        var services = new ServiceCollection();
        services.AddLogging();
        services.AddApi();
        return services;
    }
    private sealed class FailingWriter : IProblemDetailsWriter
    {
        public bool CanWrite(ProblemDetailsContext context) => true;
        public ValueTask WriteAsync(ProblemDetailsContext context) => ValueTask.FromException(new IOException("Writer unavailable"));
    }
}
