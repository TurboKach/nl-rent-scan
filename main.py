import asyncio
import json
import os

from loguru import logger
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from dotenv import load_dotenv
from aiogram import F
from selenium.common.exceptions import InvalidArgumentException

from parser import scan_funda, message_queue

load_dotenv()

logger.add(f"{__name__}.log", rotation="10 MB")  # Automatically rotate too big file

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher()

OWNER_ID = os.getenv("OWNER_ID")

# init settings
with open("settings.json", "r") as f:
    settings = json.load(f)

funda_url = settings.get("funda_url")
known_chats = settings.get("known_chats")
last_valid_url = settings.get("last_valid_url")
restart_scan = False


async def on_startup(dp):
    logger.info("Starting connection...")
    for chat_id in known_chats:
        await bot.send_message(chat_id=chat_id, text="Bot started!")


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await new_chat_remember(message)
    text = (
        "Hello! 👋\n\n"
        "This bot is scanning Funda.nl for new rental offers "
        "according to search parameters you set by url in your browser.\n\n"
        "To make this bot notify you about new offers, "
        "set up your search parameters in your browser then copy url and send it to this bot.\n\n"
    )
    if funda_url:
        text += (
            f"\nCurrent search URL: {funda_url}\n\n"
            "You can change it by sending new url to this bot.\n"
        )
    else:
        text += "\nSend new Funda.nl search url from your browser to update search parameters."
    await message.answer(text)


@dp.message(F.text)
async def new_url_set(message: types.Message):
    await new_chat_remember(message)
    global funda_url
    try:
        await url_update(message.text)
        text = f"New url set: {funda_url}"
    except Exception as e:
        logger.error(e)
        text = f"Error: {e}"
    await message.answer(text)


async def url_update(new_url: str):
    global restart_scan
    global funda_url
    funda_url = new_url
    settings["funda_url"] = funda_url
    with open("settings.json", "w") as f:
        json.dump(settings, f)
    restart_scan = True


async def new_chat_remember(message: types.Message):
    text = ''
    try:
        global known_chats
        new_chat = message.chat.id
        if new_chat not in known_chats:
            known_chats.append(new_chat)
            settings["known_chats"] = known_chats
            with open("settings.json", "w") as f:
                json.dump(settings, f)
            log_msg = f"New chat added: @{message.from_user.username}, {message.from_user.username or message.chat.title}({new_chat})"
            logger.info(log_msg)
            await bot.send_message(chat_id=OWNER_ID, text=log_msg)
    except Exception as e:
        logger.error(e)
        text = f"Error: {e}"
    if text:
        await message.answer(text)


async def check_new_offers():
    """
    Checks for new offers and sends them to group or chat where bot is added.
    :return:
    """
    logger.info("Checking for new offers...")
    global restart_scan
    global funda_url
    while not restart_scan:
        try:
            await scan_funda(funda_url)
            message = await message_queue.get()
            if message:
                for chat_id in known_chats:
                    await bot.send_message(chat_id=chat_id, text=message)
        except InvalidArgumentException:
            logger.error("Invalid URL! Default URL will be used.\n"
                         "https://www.funda.nl/en/zoeken/huur?selected_area=[%22amsterdam%22]")
            funda_url = "https://www.funda.nl/en/zoeken/huur?selected_area=[%22amsterdam%22]"
            await url_update(funda_url)
        # except Exception:
        #     logger.error("Trying again...")
        #     # continue

    logger.info("Restarting the scanner with new url...")
    await asyncio.sleep(1)
    restart_scan = False
    asyncio.create_task(check_new_offers())  # Restart the loop


async def main():
    logger.info("Starting bot...")
    await on_startup(dp)
    await asyncio.gather(dp.start_polling(bot), check_new_offers())


if __name__ == "__main__":
    asyncio.run(main())
