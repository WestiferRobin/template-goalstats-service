using GoalStats.Template.Api.Dtos.Item;
using GoalStats.Template.Api.Dtos.Item.Responses;

namespace GoalStats.Template.Api.Mappers;

public static class ItemMapper
{
    public static ItemResponse ToResponse(ItemDto dto) => new()
    {
        Id = dto.Id,
        Name = dto.Name,
        Status = dto.Status,
        CreatedAt = dto.CreatedAt,
        UpdatedAt = dto.UpdatedAt,
    };
}
