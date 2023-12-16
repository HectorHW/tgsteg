import asyncio
import io
import logging
from typing import cast
import typing
import pydantic_settings
from aiogram import Dispatcher, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, PhotoSize, BufferedInputFile
from aiogram import F as Filter

from tgsteg import image_transformation

logger = logging.getLogger(__name__)


class Settings(pydantic_settings.BaseSettings):
    token: str
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


@dp.message(Filter.photo.as_("image_variants"), Filter.caption.as_("caption"))
async def bake_image(
    message: Message, bot: Bot, image_variants: list[PhotoSize], caption: str
) -> None:
    logger.info(
        "got bake command from %s", message.chat.username or message.chat.full_name
    )
    file = await download_image(bot, image_variants)
    actual_image = image_transformation.extract_image(file)
    try:
        produced = image_transformation.bake_string_v2(actual_image, caption)
    except ValueError as e:
        await message.reply(f"error: {e.args[0]}")
        return

    compressed = image_transformation.compress_image(produced)

    if decode(compressed) != caption:
        await message.reply(
            "failed to decode after encode, possible reason: image is too small/big"
        )
        return

    uploaded = BufferedInputFile(
        bytes_to_bytes(compressed), filename=f"{message.message_id}.jpg"
    )
    await message.reply_photo(uploaded)


async def download_image(bot: Bot, image_variants: list[PhotoSize]) -> io.BytesIO:
    file = await bot.get_file(image_variants[-1].file_id)
    assert file.file_path is not None
    return cast(io.BytesIO, await bot.download_file(file.file_path))


@dp.message(Filter.photo.as_("image_variants"))
async def unbake(message: Message, bot: Bot, image_variants: list[PhotoSize]) -> None:
    logger.info(
        "got unbake command from %s", message.chat.username or message.chat.full_name
    )
    file = await download_image(bot, image_variants)
    actual_image = image_transformation.extract_image(file)
    try:
        embedded = image_transformation.unbake_string(actual_image)
    except image_transformation.IncorrectMagic:
        await message.reply(
            "incorrect magic. Most likely, image contains no embedded data"
        )
        return
    except ValueError as e:
        await message.reply(f"error: {e.args[0]}")
        return

    await message.reply(f"decoded: {embedded}")


async def main(settings: Settings) -> None:
    logging.basicConfig(level=settings.log_level)
    bot = Bot(settings.token)
    await dp.start_polling(bot)


def entrypoint() -> None:
    settings = Settings()  # type: ignore[call-arg]
    asyncio.run(main(settings))


if __name__ == "__main__":
    entrypoint()
