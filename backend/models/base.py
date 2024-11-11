from pydantic import ConfigDict, BaseModel
from sqlalchemy import Column, DateTime, UUID

from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import as_declarative, declared_attr

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import enum
from sqlalchemy.orm import DeclarativeBase,registry


def lenient_constructor(self, **kwargs):
        cls_ = type(self)
        for k in kwargs:
            if not hasattr(cls_, k):
                print(f'Skipping invalid attr {k!r}')
                continue
            setattr(self, k, kwargs[k])
registry = registry(constructor=lenient_constructor)


class Base(DeclarativeBase):
    registry = registry
# @as_declarative()
# class Base(DeclarativeBase):
    id = Column(UUID, primary_key=True, index=True, default=func.uuid_generate_v4())
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    __name__: str

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

