from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.item import Item


class ItemRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Item]:
        return list(self.session.scalars(select(Item).order_by(Item.created_at, Item.id)))

    def get_by_id(self, item_id: UUID, *, for_update: bool = False) -> Item | None:
        statement = select(Item).where(Item.id == item_id)
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def add(self, item: Item) -> None:
        self.session.add(item)
        self.session.flush()

    def flush(self) -> None:
        self.session.flush()

    def delete(self, item: Item) -> None:
        self.session.delete(item)
        self.session.flush()
