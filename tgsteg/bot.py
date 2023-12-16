import asyncio
import io
import logging
from typing import cast
import typing
import pydantic_settings
from aiogram import Dispatcher, Bot
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.types import Message, PhotoSize, BufferedInputFile
from aiogram import F as Filter

from tgsteg import image_transformation, data_encoding
from tgsteg.default_strings import DefaultStrings, SqliteDefaultStringsImpl

logger = logging.getLogger(__name__)


class Settings(pydantic_settings.BaseSettings):
    token: str
    database: str = "data.sqlite"
    log_level: str = "INFO"

    model_config = pydantic_settings.SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8"
    )


dp = Dispatcher()

WELCOME = """Hello! This bot can be used to embed (currently in rather simple form) some data inside an image

Send an image with caption to write the caption into the file (but prefer smaller messages)

Send an image to check if it contains some embedded data"""


@dp.message(CommandStart())
async def respond_to_start(message: Message) -> None:
    logger.info("got start from %s", message.chat.username or message.chat.full_name)
    await message.answer(WELCOME)


def bytes_to_bytes(value: io.BytesIO) -> bytes:
    value.seek(0)
    return value.read()


def decode(image: io.BytesIO) -> typing.Optional[str]:
    try:
        image.seek(0)
        actual_image = image_transformation.extract_image(image)
        return image_transformation.unbake_string(actual_image)
    except:  # noqa: E722
        logger.error("image failed verification after baking")
        return None


@dp.message(Command("default"))
async def set_default(
    message: Message, command: CommandObject, bot: Bot, storage: DefaultStrings
) -> None:
    if message.from_user is None:
        return
    if not command.args:
        existing_value = await storage.get_value(str(message.from_user.id))
        if existing_value:
            await message.reply(f"your default value is {existing_value}")
            return

        await message.reply(
            "no default value set, use `/default value` to set it to value"
        )
        return

    if not await verify_caption(message, command.args):
        return

    await storage.update_value(str(message.from_user.id), command.args)
    await message.reply(f"updated stored data to `{command.args}`")


async def verify_caption(message: Message, caption: str) -> bool:
    try:
        data_encoding.string_to_bits(caption)
    except ValueError:
        await message.reply(
            f"provided caption contains unsupported symbols. Supported are\n\n{data_encoding.ALPHABET}"
        )
        return False

    if not data_encoding.can_fit(caption):
        await message.reply("sorry, cannot store message this big")
        return False

    return True


@dp.message(Filter.photo.as_("image_variants"), Filter.caption.as_("caption"))
async def bake_image(
    message: Message, bot: Bot, image_variants: list[PhotoSize], caption: str
) -> None:
    logger.info(
        "got bake command from %s", message.chat.username or message.chat.full_name
    )
    if not await verify_caption(message, caption):
        return

    file = await download_image(bot, image_variants)

    try:
        result = bake_and_verify(file, caption)
    except ValueError as e:
        await message.reply(f"error: {e.args[0]}")
        return

    uploaded = BufferedInputFile(result, filename=f"{message.message_id}.jpg")
    await message.reply_photo(uploaded)


def bake_and_verify(file: io.BytesIO, caption: str) -> bytes:
    file.seek(0)
    actual_image = image_transformation.extract_image(file)
    produced = image_transformation.bake_string(actual_image, caption)
    compressed = image_transformation.compress_image(produced)
    if decode(compressed) != caption:
        raise ValueError(
            "failed to decode after encode, possible reason: image is too small/big"
        )

    return bytes_to_bytes(compressed)


async def download_image(bot: Bot, image_variants: list[PhotoSize]) -> io.BytesIO:
    file = await bot.get_file(image_variants[-1].file_id)
    assert file.file_path is not None
    return cast(io.BytesIO, await bot.download_file(file.file_path))


AUTOADD_TO_EMPTY_MESSAGE = """
Incorrect magic. Most likely, image contains no embedded data.

If you want, I can add preconfigured string to image without data. See `/default` command.
"""


@dp.message(Filter.photo.as_("image_variants"))
async def unbake(
    message: Message, bot: Bot, image_variants: list[PhotoSize], storage: DefaultStrings
) -> None:
    if message.from_user is None:
        return
    logger.info(
        "got unbake command from %s", message.chat.username or message.chat.full_name
    )
    file = await download_image(bot, image_variants)
    actual_image = image_transformation.extract_image(file)
    try:
        embedded = image_transformation.unbake_string(actual_image)
    except data_encoding.StringMagicMismatch:
        default = await storage.get_value(str(message.from_user.id))
        if default is None:
            await message.reply(AUTOADD_TO_EMPTY_MESSAGE)
            return

        data = bake_and_verify(file, default)
        uploaded = BufferedInputFile(data, filename=f"{message.message_id}.jpg")
        await message.reply_photo(
            uploaded,
            caption="failed to find existing message, encoded with your default value",
        )
        return
    except ValueError as e:
        await message.reply(f"error: {e.args[0]}")
        return

    await message.reply(f"decoded: {embedded}")


async def main(settings: Settings) -> None:
    logging.basicConfig(level=settings.log_level)
    bot = Bot(settings.token)
    storage = await SqliteDefaultStringsImpl.file(settings.database)
    await dp.start_polling(bot, storage=storage)


def entrypoint() -> None:
    settings = Settings()  # type: ignore[call-arg]
    asyncio.run(main(settings))


if __name__ == "__main__":
    entrypoint()
