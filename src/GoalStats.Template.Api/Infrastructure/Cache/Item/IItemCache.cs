using GoalStats.Template.Api.Dtos.Item;

namespace GoalStats.Template.Api.Infrastructure.Cache.Item;

public interface IItemCache
{
    Task<ItemDto?> GetAsync(
        Guid itemId,
        CancellationToken cancellationToken = default);

    Task SetAsync(
        ItemDto item,
        CancellationToken cancellationToken = default);

    Task RemoveAsync(
        Guid itemId,
        CancellationToken cancellationToken = default);
}
