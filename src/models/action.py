from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from enums.action import ActionType
from models.base import Base, Timestamped


class Action(Timestamped, Base):
    __tablename__ = "actions"
    __table_args__ = (CheckConstraint("name ~ '[^[:space:]]'", name="name_not_blank"),)

    item_id: Mapped[UUID] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    action_type: Mapped[ActionType] = mapped_column(
        Enum(
            ActionType,
            values_callable=lambda values: [v.value for v in values],
            name="action_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        )
    )
