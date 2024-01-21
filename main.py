import asyncio
import os

from aiogram.enums import ParseMode, ChatType
from aiogram.types import BotCommand
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

OWNER_ID = int(os.getenv("OWNER_ID"))


async def on_startup(dp):
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Starting connection...")
    bot_commands = [
        BotCommand(command="/start", description="Help"),
    ]
    await bot.set_my_commands(bot_commands)
    for chat_id in settings.admins_ids:
        await bot.send_message(chat_id=chat_id, text=f"Bot started! 🔌\n\nCurrent search URL: {settings.funda_url}")


@dp.message(Command("start"), Command("help"), F.chat.type == ChatType.PRIVATE)
async def cmd_start(message: types.Message):
    if message.from_user.id not in [OWNER_ID, *settings.admins_ids]:
        await message.answer("You are not allowed to use this bot. Please contact bot owner.")
        return
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


@dp.message(Command("add_admin"), F.from_user.id == OWNER_ID)
async def add_admin(message: types.Message):
    logger.debug(f"Adding admin: {message.text}")
    try:
        admin_to_add = int(message.text.split(' ', 1)[1])
        if admin_to_add not in settings.admins_ids:
            admin_ids = [*settings.admins_ids, admin_to_add]
            settings.admins_ids = admin_ids
            text = f"New admin added: {admin_to_add}"
        else:
            text = f"Admin already exists: {admin_to_add}"
    except Exception as e:
        logger.error(e)
        text = f"Error adding new admin: {e}"
    await message.answer(text)


@dp.message(Command("remove_admin"), F.from_user.id == OWNER_ID)
async def remove_admin(message: types.Message):
    logger.debug(f"Removing admin: {message.text}")
    try:
        admin_to_remove = int(message.text.split(' ', 1)[1])
        if admin_to_remove in settings.admins_ids:
            admins_ids = [*settings.admins_ids].remove(admin_to_remove)
            settings.admins_ids = admins_ids
            text = f"Admin removed: {admin_to_remove}"
        else:
            text = f"Admin doesn't exist: {admin_to_remove}"
    except Exception as e:
        logger.error(e)
        text = f"Error removing admin: {e}"
    await message.answer(text)


@dp.message(Command("add_chat"), F.from_user.id == OWNER_ID)
async def add_chat(message: types.Message):
    logger.debug(f"Adding chat: {message.text}")
    try:
        chat_to_add = int(message.text.split(' ', 1)[1])
        if chat_to_add not in settings.known_chats:
            known_chats = [*settings.known_chats, chat_to_add]
            settings.known_chats = known_chats
            text = f"New chat added: {chat_to_add}"
        else:
            text = f"Chat already exists: {chat_to_add}"
    except Exception as e:
        logger.error(e)
        text = f"Error adding new chat: {e}"
    await message.answer(text)


@dp.message(Command("remove_chat"), F.from_user.id == OWNER_ID)
async def remove_chat(message: types.Message):
    logger.debug(f"Removing chat: {message.text}")
    try:
        chat_to_remove = int(message.text.split(' ', 1)[1])
        if chat_to_remove in settings.known_chats:
            known_chats = [*settings.admins_ids].remove(chat_to_remove)
            settings.known_chats = known_chats
            text = f"Chat removed: {chat_to_remove}"
        else:
            text = f"Admin doesn't exist: {chat_to_remove}"
    except Exception as e:
        logger.error(e)
        text = f"Error removing admin: {e}"
    await message.answer(text)


@dp.message(Command("get_chats"), F.from_user.id == OWNER_ID)
async def get_chats(message: types.Message):
    logger.debug(f"Getting chats: {settings.known_chats}")
    try:
        text = f"Chats: {settings.known_chats}"
    except Exception as e:
        logger.error(e)
        text = f"Error getting chats: {e}"
    await message.answer(text)


@dp.message(Command("get_admins"), F.from_user.id == OWNER_ID)
async def get_admins(message: types.Message):
    logger.debug(f"Getting admins: {settings.admins_ids}")
    try:
        text = f"Admins: {settings.admins_ids}"
    except Exception as e:
        logger.error(e)
        text = f"Error getting admins: {e}"
    await message.answer(text)


@dp.message(Command("get_chat_id"), F.from_user.id == OWNER_ID)
async def get_chat_id(message: types.Message):
    chat_id = message.chat.id or message.from_user.id
    logger.debug(f"Getting chat id: {chat_id}")
    try:
        text = f"Chat id: {chat_id}"
    except Exception as e:
        logger.error(e)
        text = f"Error getting chat id: {e}"
    await message.answer(text)


@dp.message(F.text, F.chat.type == ChatType.PRIVATE, F.from_user.id.in_([OWNER_ID, *settings.admins_ids]))
async def new_url_set(message: types.Message):
    try:
        settings.funda_url = message.text.strip()
        text = f"New url set: {settings.funda_url}"
    except Exception as e:
        logger.error(e)
        text = f"Error setting new url: {e}"
    await message.answer(text)


async def check_new_offers():
    """
    Checks for new offers and sends them to group or chat where bot is added.
    :return:
    """
    logger.info("Checking for new offers...")
    try:
        await parser.get_google()
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
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(e)


async def main():
    logger.info("Starting bot...")
    await on_startup(dp)
    await asyncio.gather(dp.start_polling(bot), check_new_offers(), check_and_send_new_messages())


if __name__ == "__main__":
    asyncio.run(main())
