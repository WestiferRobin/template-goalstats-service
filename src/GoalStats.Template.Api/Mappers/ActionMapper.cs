using GoalStats.Template.Api.Dtos.Action;
using GoalStats.Template.Api.Dtos.Action.Responses;

namespace GoalStats.Template.Api.Mappers;

public static class ActionMapper
{
    public static ActionResponse ToResponse(ActionDto dto) => new()
    {
        Id = dto.Id,
        ItemId = dto.ItemId,
        Name = dto.Name,
        Type = dto.Type,
        CreatedAt = dto.CreatedAt,
        UpdatedAt = dto.UpdatedAt,
    };
}
