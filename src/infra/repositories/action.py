from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from models.action import Action


class ActionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, item_id: UUID | None = None) -> list[Action]:
        statement = select(Action).order_by(Action.created_at, Action.id)
        if item_id is not None:
            statement = statement.where(Action.item_id == item_id)
        return list(self.session.scalars(statement))

    def get_by_id(self, action_id: UUID, *, for_update: bool = False) -> Action | None:
        statement = select(Action).where(Action.id == action_id)
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def exists(self, action_id: UUID) -> bool:
        return bool(self.session.scalar(select(exists().where(Action.id == action_id))))

    def add(self, action: Action) -> None:
        self.session.add(action)
        self.session.flush()

    def flush(self) -> None:
        self.session.flush()

    def delete(self, action: Action) -> None:
        self.session.delete(action)
        self.session.flush()
