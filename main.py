import asyncio
import os
import traceback

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode, ChatType
from aiogram.filters import Command
from aiogram.types import BotCommand
from dotenv import load_dotenv
from loguru import logger
from selenium.common.exceptions import InvalidArgumentException

from parser import FundaParser
from settings import settings, message_queue

# Load environment variables
load_dotenv()

OWNER_ID = int(os.getenv("OWNER_ID"))
MAX_MESSAGE_LENGTH = 4092

# Set up logging
logger.add(f"{__name__}.log", rotation="10 MB")  # Automatically rotate large log files

# Bot initialization
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher(storage=None)  # No persistence for storage

# Initialize the parser instance
parser = FundaParser()


async def send_critical_error_message(error_msg):
    """
    Sends a simplified critical error message to the bot owner on Telegram.
    """
    try:
        # Compose the error message to be sent (only using the exception type and message)
        message = (
            f"⚠️ Critical Error:\n\n"
            f"Exception: {type(error_msg).__name__}\n"
            f"Message: {str(error_msg)}"
        )

        # Ensure the message is within Telegram's character limit
        if len(message) > MAX_MESSAGE_LENGTH:
            message = message[:MAX_MESSAGE_LENGTH] + '...'  # Truncate if too long

        # Send the simplified message to the bot owner
        await bot.send_message(OWNER_ID, message)
    except Exception as e:
        logger.error(f"Failed to send critical error message: {e}")



async def add_admin_by_user_id(user_id: int) -> str:
    """
    Adds a new admin by user_id if they don't already exist in the list.
    :param user_id: The user ID of the admin to add.
    :return: A message indicating the result of the operation.
    """
    try:
        if user_id not in settings.admins_ids:
            settings.admins_ids.append(user_id)
            text = f"New admin added: {user_id}"
        else:
            text = f"Admin already exists: {user_id}"
    except Exception as e:
        logger.error(f"Error adding new admin: {e}")
        text = f"Error adding new admin: {e}"

    return text


async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Starting connection...")

    bot_commands = [
        BotCommand(command="/start", description="Help"),
    ]
    await bot.set_my_commands(bot_commands)

    if OWNER_ID not in settings.admins_ids:
        await add_admin_by_user_id(OWNER_ID)

    for chat_id in settings.admins_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=f"Bot started! 🔌\n\nCurrent search URL: {settings.funda_url}")
        except Exception as e:
            logger.error(f"Failed to send startup message to {chat_id}: {e}")


@dp.message(Command(commands=["start", "help"]))
async def cmd_start(message: types.Message):
    if message.from_user.id not in [OWNER_ID, *settings.admins_ids]:
        await message.answer("You are not allowed to use this bot. Please contact the bot owner.")
        return

    text = (
        "Hello! 👋\n\n"
        "This bot scans Funda.nl for new rental offers "
        "based on the search parameters set by the URL you provide.\n\n"
        "To start receiving notifications for new offers, "
        "set up your search in your browser, copy the URL, and send it to this bot.\n\n"
        f"Current search URL:\n{settings.funda_url}\n\n"
        "You can update it by sending a new URL."
    )
    await message.answer(text)


@dp.message(Command("add_admin"), F.from_user.id == OWNER_ID)
async def add_admin(message: types.Message):
    logger.debug(f"Adding admin: {message.text}")
    try:
        admin_to_add = int(message.text.split(' ', 1)[1])
        result = await add_admin_by_user_id(admin_to_add)
    except Exception as e:
        logger.error(e)
        result = f"Error adding new admin: {e}"

    await message.answer(result)


@dp.message(Command("remove_admin"), F.from_user.id == OWNER_ID)
async def remove_admin(message: types.Message):
    logger.debug(f"Removing admin: {message.text}")
    try:
        admin_to_remove = int(message.text.split(' ', 1)[1])
        if admin_to_remove in settings.admins_ids:
            settings.admins_ids.remove(admin_to_remove)
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
            settings.known_chats.append(chat_to_add)
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
            settings.known_chats.remove(chat_to_remove)
            text = f"Chat removed: {chat_to_remove}"
        else:
            text = f"Chat doesn't exist: {chat_to_remove}"
    except Exception as e:
        logger.error(e)
        text = f"Error removing chat: {e}"

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
        text = f"New URL set:\n{settings.funda_url}"
    except Exception as e:
        logger.error(e)
        text = f"Error setting new URL: {e}"

    await message.answer(text)

    for chat in settings.known_chats:
        await bot.send_message(chat_id=chat, text=text)


async def check_new_offers():
    """
    Checks for new offers and sends them to the group or chat where the bot is added.
    """
    logger.info("Checking for new offers...")
    try:
        await parser.scan_funda()
    except InvalidArgumentException:
        logger.error(f"Invalid URL! Default URL will be used.\n{settings.funda_url_default}")
        settings.funda_url = settings.funda_url_default


async def check_and_send_new_messages():
    """
    Continuously checks for new messages in the message queue and sends them to known chats.
    """
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
    try:
        logger.info("Starting bot...")
        await on_startup()
        await asyncio.gather(dp.start_polling(bot), check_new_offers(), check_and_send_new_messages())
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        logger.critical(f"Bot crashed: {error_msg}")
        await send_critical_error_message(error_msg)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
