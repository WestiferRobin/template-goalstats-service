using GoalStats.Template.Api.Enums;

namespace GoalStats.Template.Api.Dtos.Item.Responses;

public class ItemResponse
{
    public Guid Id { get; init; }
    public string Name { get; init; } = string.Empty;
    public ItemStatus Status { get; init; }
    public DateTime CreatedAt { get; init; }
    public DateTime UpdatedAt { get; init; }
}
