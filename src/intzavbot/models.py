from enum import auto

from sqlalchemy import Boolean, Column, Enum, Integer, ForeignKey, String
from sqlalchemy.orm import backref, declarative_base, deferred, relationship

from intzavbot.utils import StrEnum


Base = declarative_base()

MAX_NICKNAME_LENGTH = 64
MAX_GAME_TAG_LENGTH = 64
MAX_PROLOG_LENGTH = 300
MAX_GAME_TEXT_LENGTH = 300


class UserState(StrEnum):
    DEFAULT = auto()
    TYPING_TAG_FOR_GAME_TO_CREATE = auto()
    TYPING_TAG_FOR_GAME_TO_JOIN = auto()
    TYPING_NICKNAME = auto()
    WAITING_FOR_HOST = auto()
    TYPING_GAME_TEXT = auto()
    VOTING = auto()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    nickname = Column(String(MAX_NICKNAME_LENGTH))
    game_id = Column(Integer, ForeignKey("games.id"))
    entered_game_tag = deferred(Column(String(MAX_GAME_TAG_LENGTH)))

    is_host = Column(Boolean)
    text = deferred(Column(String(MAX_GAME_TEXT_LENGTH)))
    for_whom_votes_id = Column(Integer, ForeignKey("users.id"))

    state = Column(
        Enum(UserState, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserState.DEFAULT
    )

    voted_by = relationship("User", backref=backref("for_whom_votes", remote_side=[id]))


class GameKind(StrEnum):
    DICTIONARY = auto()
    POETIC = auto()


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    tag = Column(String(MAX_GAME_TAG_LENGTH), nullable=False, unique=True)
    kind = Column(Enum(GameKind), nullable=False)
    prolog = Column(String(MAX_PROLOG_LENGTH))

    users = relationship("User", backref=backref("game"))
