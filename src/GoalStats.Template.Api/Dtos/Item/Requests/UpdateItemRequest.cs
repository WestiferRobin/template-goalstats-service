using System.ComponentModel.DataAnnotations;
using GoalStats.Template.Api.Enums;

namespace GoalStats.Template.Api.Dtos.Item.Requests;

public class UpdateItemRequest
{
    [Required, StringLength(200)]
    public required string Name { get; init; }

    [EnumDataType(typeof(ItemStatus))]
    public required ItemStatus Status { get; init; }
}
