using System.Text.Json;
using System.Text.Json.Serialization;
using GoalStats.Template.Api.Enums;
namespace GoalStats.Template.Api.UnitTests.Dtos;
internal static class CacheJson
{
    public static JsonSerializerOptions Options() => new(JsonSerializerDefaults.Web)
    {
        Converters = { new JsonStringEnumConverter<ItemStatus>(JsonNamingPolicy.CamelCase, false), new JsonStringEnumConverter<ActionType>(JsonNamingPolicy.CamelCase, false) }
    };
}
