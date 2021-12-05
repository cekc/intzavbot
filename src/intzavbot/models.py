from enum import auto
from typing import AsyncGenerator

from sqlalchemy import Boolean, Column, Enum, Integer, ForeignKey, select, String
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import backref, declarative_base, deferred, foreign, relationship

from intzavbot.utils import StrEnum


Base = declarative_base()

MAX_NICKNAME_LENGTH = 64
MAX_GAME_TAG_LENGTH = 64
MAX_PROLOG_LENGTH = 300
MAX_GAME_TEXT_LENGTH = 300


class PlayerState(StrEnum):
    DEFAULT = auto()
    TYPING_NICKNAME = auto()
    TYPING_TAG_FOR_GAME_TO_CREATE = auto()
    TYPING_TAG_FOR_GAME_TO_JOIN = auto()
    WAITING_FOR_HOST_TO_APPEAR = auto()
    WAITING_FOR_HOST_TO_TYPE_PROLOG = auto()
    TYPING_PROLOG = auto()
    TYPING_GAME_TEXT = auto()
    WAITING_FOR_VOTING_FINISH = auto()
    VOTING = auto()


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    nickname = Column(String(MAX_NICKNAME_LENGTH))
    game_id = Column(Integer, ForeignKey("games.id"))
    entered_game_tag = deferred(Column(String(MAX_GAME_TAG_LENGTH)))

    is_host = Column(Boolean)
    text = deferred(Column(String(MAX_GAME_TEXT_LENGTH)))
    for_whom_votes_id = Column(Integer, ForeignKey("players.id"))

    state = Column(
        Enum(PlayerState, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=PlayerState.DEFAULT
    )

    voted_by = relationship("Player", backref=backref("for_whom_votes", remote_side=[id]))

    async def other_players(self, session: AsyncSession) -> "AsyncGenerator[Player]":
        all_players = (await session.stream(select(Player).filter_by(game_id=self.game_id))).scalars()
        async for player in all_players:
            if player.id != self.id:
                yield player


class GameKind(StrEnum):
    DICTIONARY = auto()
    POETIC = auto()


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    tag = Column(String(MAX_GAME_TAG_LENGTH), nullable=False, unique=True)
    kind = Column(Enum(GameKind), nullable=False)
    prolog = Column(String(MAX_PROLOG_LENGTH))

    players = relationship("Player", backref=backref("game"))
