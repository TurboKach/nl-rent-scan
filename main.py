import asyncio
import json
import os

from aiogram.enums import ParseMode
from loguru import logger
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from dotenv import load_dotenv
from aiogram import F
from selenium.common.exceptions import InvalidArgumentException

from parser import parser
from settings import settings, message_queue

load_dotenv()

logger.add(f"{__name__}.log", rotation="10 MB")  # Automatically rotate too big file

# Bot init
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher()

OWNER_ID = os.getenv("OWNER_ID")


async def on_startup(dp):
    logger.info("Starting connection...")
    for chat_id in settings.known_chats:
        await bot.send_message(chat_id=chat_id, text=f"Bot started! 🔌\n\nCurrent search URL: {settings.funda_url}")


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await new_chat_remember(message)
    text = (
        "Hello! 👋\n\n"
        "This bot is scanning Funda.nl for new rental offers "
        "according to search parameters you set by url in your browser.\n\n"
        "To make this bot notify you about new offers, "
        "set up your search parameters in your browser then copy url and send it to this bot.\n\n"
        f"\nCurrent search URL: {settings.funda_url}\n\n"
        "You can change it by sending new url to this bot.\n"
    )
    await message.answer(text)


@dp.message(F.text)
async def new_url_set(message: types.Message):
    await new_chat_remember(message)
    try:
        settings.funda_url = message.text
        text = f"New url set: {settings.funda_url}"
    except Exception as e:
        logger.error(e)
        text = f"Error setting new url: {e}"
    await message.answer(text)


async def new_chat_remember(message: types.Message):
    try:
        if message.chat.id not in settings.known_chats:
            # TODO check if append is good here.
            #  Maybe it's better to set new list because of @property setter
            #  like this: settings.known_chats = settings.known_chats.append(message.chat.id)
            settings.known_chats.append(message.chat.id)
            log_msg = (
                f"New chat added: "
                f"@{message.from_user.username}, {message.chat.title or message.from_user.username} ({message.chat.id})"
            )
            logger.info(log_msg)
            await bot.send_message(chat_id=OWNER_ID, text=log_msg)
    except Exception as e:
        logger.error(e)
        await message.answer(repr(e))


async def check_new_offers():
    """
    Checks for new offers and sends them to group or chat where bot is added.
    :return:
    """
    logger.info("Checking for new offers...")
    try:
        await parser.scan_funda()
    except InvalidArgumentException:
        logger.error("Invalid URL! Default URL will be used.\n"
                     f"{settings.funda_url_default}")
        settings.funda_url = settings.funda_url_default
    # except Exception:
    #     logger.error("Trying again...")
    #     # continue


async def check_and_send_new_messages():
    while True:
        message = await message_queue.get()
        if message:
            logger.info("Sending message...")
            for chat_id in settings.known_chats:
                try:
                    await bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.HTML)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(e)


async def main():
    logger.info("Starting bot...")
    await on_startup(dp)
    await asyncio.gather(dp.start_polling(bot), check_new_offers(), check_and_send_new_messages())


if __name__ == "__main__":
    asyncio.run(main())
