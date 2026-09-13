using System.ComponentModel.DataAnnotations;
using System.Text.Json.Serialization;
using GoalStats.Template.Api.Enums;

namespace GoalStats.Template.Api.Dtos.Action.Requests;

[JsonUnmappedMemberHandling(JsonUnmappedMemberHandling.Disallow)]
public class UpdateActionRequest
{
    [Required, StringLength(200)]
    public required string Name { get; init; }
    [EnumDataType(typeof(ActionType))]
    public required ActionType Type { get; init; }
}
