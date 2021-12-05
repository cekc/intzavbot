from asyncio import gather
from typing import Coroutine, Dict

from aiogram import Dispatcher
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from intzavbot.models import Game, GameKind, Player, PlayerState
from intzavbot.models import MAX_GAME_TAG_LENGTH, MAX_GAME_TEXT_LENGTH, MAX_PROLOG_LENGTH, MAX_NICKNAME_LENGTH
from intzavbot.command_extractor import CommandExtractor, CommandExtractorBuilder
from intzavbot.utils import normalize_str


async def dont_understand(message: Message, player: Player, session: AsyncSession) -> None:
    await message.answer("I don't understand you")


async def init_game_creation_and_wait_for_tag(message: Message, player: Player, session: AsyncSession) -> None:
    if player.game_id is not None:
        await session.close()
        return await message.answer("You are already in game")

    player.state = PlayerState.TYPING_TAG_FOR_GAME_TO_CREATE
    await session.commit()
    await message.answer("Enter name for new game")


async def create_game(message: Message, player: Player, session: AsyncSession) -> None:
    tag = normalize_str(message.text, MAX_GAME_TAG_LENGTH)
    if len(tag) == 0:
        await session.close()
        return await message.answer("Please provide non-empty tag for game")

    player.game = Game(tag=tag, kind=GameKind.POETIC)
    player.state = PlayerState.WAITING_FOR_HOST_TO_APPEAR
    await session.commit()
    await message.answer("Successfully created!")


async def init_joining_game_and_wait_for_tag(message: Message, player: Player, session: AsyncSession) -> None:
    if player.game_id is not None:
        await session.close()
        return await message.answer("You are already in game")

    player.state = PlayerState.TYPING_TAG_FOR_GAME_TO_JOIN
    await session.commit()
    await message.answer("Enter name for the game to join")


async def join_game(message: Message, player: Player, session: AsyncSession) -> None:
    tag = normalize_str(message.text, MAX_GAME_TAG_LENGTH)
    if len(tag) == 0:
        await session.close()
        return await message.answer("Please provide non-empty alphabetic tag for game")

    game_id = (await session.execute(select(Game.id).filter_by(tag=tag))).scalar_one_or_none()
    if game_id is None:
        await session.close()
        return await message.answer("There is no game with this tag")

    player.game_id = game_id
    player.state = PlayerState.WAITING_FOR_HOST_TO_APPEAR
    await session.commit()
    await message.answer("Successfully joined!")


async def take_host(message: Message, host: Player, session: AsyncSession) -> None:
    host.is_host = True
    host.state = PlayerState.TYPING_PROLOG

    tasks = [message.bot.send_message(host.id, "You're host now! Type prolog!")]

    text = f"Host is {host.nickname} now! Wait for prolog!"

    async for player in host.other_players(session):
        if player.is_host:
            await session.close()
            return await message.answer("Host already taken")

        player.state = PlayerState.WAITING_FOR_HOST_TO_TYPE_PROLOG
        tasks.append(message.bot.send_message(player.id, text))

    await session.commit()
    await gather(*tasks)


async def enter_prolog(message: Message, host: Player, session: AsyncSession) -> None:
    if len(message.text) > MAX_PROLOG_LENGTH:
        await session.close()
        return await message.answer("Too long")

    game = await session.get(Game, host.game_id)
    game.prolog = message.text
    host.state = PlayerState.TYPING_GAME_TEXT

    tasks = [message.bot.send_message(host.id, "Thank you! Now enter right ending!")]

    async for player in host.other_players(session):
        if player.is_host:
            await session.close()
            return await message.answer("Host already taken")

        player.state = PlayerState.TYPING_GAME_TEXT
        tasks.append(message.bot.send_message(player.id, "Enter your variant!"))

    await session.commit()
    await gather(*tasks)


def prepare_command_extractor() -> Dict[PlayerState, CommandExtractor[Coroutine]]:
    builders = {state : CommandExtractorBuilder().add(dont_understand) for state in PlayerState}

    builders[PlayerState.DEFAULT] \
        .add(dont_understand) \
        .add(init_game_creation_and_wait_for_tag, "new", "create", "новая", "новую", "начать", "создать") \
        .add(init_joining_game_and_wait_for_tag, "join", "go", "присоединиться", "играть", "го")

    builders[PlayerState.TYPING_TAG_FOR_GAME_TO_CREATE].add(create_game)
    builders[PlayerState.TYPING_TAG_FOR_GAME_TO_JOIN].add(join_game)
    builders[PlayerState.WAITING_FOR_HOST_TO_APPEAR].add(take_host, "me", "take", "я", "взять")
    builders[PlayerState.TYPING_PROLOG].add(enter_prolog)

    return {state : builder.build() for state, builder in builders.items()}


def register_handlers(dispatcher: Dispatcher, session_factory: sessionmaker) -> None:
    cmd_extractor = prepare_command_extractor()

    async def meta_callback(message: Message) -> None:
        async with session_factory() as session:
            async with session.begin():
                player = await session.get(Player, message.from_user.id)

                if player is None:
                    player = Player(id=message.from_user.id)
                    session.add(player)
                    await session.commit()
                    return await message.answer("Hello, new player!")

                callback = cmd_extractor[player.state].extract(message.text)
                await callback(message, player, session)

    dispatcher.register_message_handler(meta_callback)
