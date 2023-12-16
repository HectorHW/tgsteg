import abc
from typing import Optional
import typing

from sqlalchemy import select
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


class DefaultStrings(abc.ABC):
    @abc.abstractmethod
    async def get_value(self, user: str) -> Optional[str]:
        ...

    @abc.abstractmethod
    async def update_value(self, user: str, value: str) -> None:
        ...


class Base(DeclarativeBase):
    pass


class DefaultStringsTable(Base):
    __tablename__ = "default_strings"
    user_id: Mapped[int] = mapped_column(primary_key=True)
    stored_value: Mapped[str]


class SqliteDefaultStringsImpl(DefaultStrings):
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self.sessionmaker = sessionmaker

    @classmethod
    async def file(cls, path: str) -> typing.Self:
        engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)
        return cls(async_sessionmaker(engine))

    async def get_value(self, user: str) -> str | None:
        async with self.sessionmaker() as session:
            qeuery_result = await session.scalars(
                select(DefaultStringsTable).where(DefaultStringsTable.user_id == user)
            )
            if entry := qeuery_result.one_or_none():
                return entry.stored_value
            return None

    async def update_value(self, user: str, value: str) -> None:
        async with self.sessionmaker() as session:
            session.add(DefaultStringsTable(user_id=user, stored_value=value))
            await session.commit()
