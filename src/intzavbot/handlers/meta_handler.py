from aiogram import Dispatcher
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from intzavbot.models import Game, GameKind, User, UserState, MAX_GAME_TAG_LENGTH
from intzavbot.multi_pattern_extractor import MultiPatternExtractor
from intzavbot.utils import normalize_str


async def dont_understand(message: Message, user: User, session: AsyncSession) -> None:
    return await message.answer("I don't understand you")


async def init_game_creation_and_wait_for_tag(message: Message, user: User, session: AsyncSession) -> None:
    if user.game_id is not None:
        await session.close()
        return await message.answer("You are already in game")

    user.state = UserState.TYPING_TAG_FOR_GAME_TO_CREATE
    await session.commit()
    return await message.answer("Enter name for new game")


async def create_game(message: Message, user: User, session: AsyncSession) -> None:
    tag = normalize_str(message.text, MAX_GAME_TAG_LENGTH)
    if len(tag) == 0:
        await session.close()
        return await message.answer("Please provide non-zero alphabetic tag for game")

    user.game = Game(tag=tag, kind=GameKind.POETIC)

    user.state = UserState.WAITING_FOR_HOST
    await session.commit()
    return await message.answer("Successfully created!")


async def init_joining_game_and_wait_for_tag(message: Message, user: User, session: AsyncSession) -> None:
    if user.game_id is not None:
        await session.close()
        return await message.answer("You are already in game")

    user.state = UserState.TYPING_TAG_FOR_GAME_TO_JOIN
    await session.commit()
    return await message.answer("Enter name for the game to join")


async def join_game(message: Message, user: User, session: AsyncSession) -> None:
    tag = normalize_str(message.text, MAX_GAME_TAG_LENGTH)
    if len(tag) == 0:
        await session.close()
        return await message.answer("Please provide non-zero alphabetic tag for game")

    game_id = (await session.execute(select(Game.id).where(Game.tag==tag))).scalar_one_or_none()
    if game_id is None:
        await session.close()
        return await message.answer("There is no game with this tag")

    user.game_id = game_id
    user.state = UserState.WAITING_FOR_HOST
    await session.commit()
    return await message.answer("Successfully joined!")


def register_handlers(dispatcher: Dispatcher, session_factory: sessionmaker) -> None:
    dispatch_by_state = {state : MultiPatternExtractor(dont_understand) for state in UserState}

    dispatch_by_state[UserState.DEFAULT] \
        .add(dont_understand) \
        .add(init_game_creation_and_wait_for_tag, "new", "create", "новая", "новую", "начать", "создать") \
        .add(init_joining_game_and_wait_for_tag, "join", "go", "присоединиться", "играть", "го") \
        .finalize()

    dispatch_by_state[UserState.TYPING_TAG_FOR_GAME_TO_CREATE].add(create_game).finalize()
    dispatch_by_state[UserState.TYPING_TAG_FOR_GAME_TO_JOIN].add(join_game).finalize()

    async def meta_callback(message: Message) -> None:
        async with session_factory() as session:

            telegram_id = message.from_user.id
            user = (await session.execute(select(User).where(User.id==telegram_id))).scalar_one_or_none()
            if user is None:
                user = User(id=telegram_id)
                session.add(user)
                await session.commit()
                return await message.answer("Hello, new user!")

            callback = dispatch_by_state[user.state].extract(message.text.lower())

            return await callback(message, user, session)

    dispatcher.register_message_handler(meta_callback)
