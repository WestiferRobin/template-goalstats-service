from sqlalchemy import CheckConstraint, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from enums.item import ItemStatus
from models.base import Base, Timestamped


class Item(Timestamped, Base):
    __tablename__ = "items"
    __table_args__ = (CheckConstraint("name ~ '[^[:space:]]'", name="name_not_blank"),)

    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[ItemStatus] = mapped_column(
        Enum(
            ItemStatus,
            values_callable=lambda values: [v.value for v in values],
            name="item_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        default=ItemStatus.ACTIVE,
    )
