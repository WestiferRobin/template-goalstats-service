namespace GoalStats.Template.Api.Exceptions.Item;

public sealed class ItemNotFoundException : NotFoundException
{
    public Guid ItemId { get; }

    public ItemNotFoundException(Guid itemId)
        : base("The requested Item was not found.")
    {
        ItemId = itemId;
    }
}
