# Funda Rental Offers Telegram Bot

This is a Telegram bot built using `aiogram v3` that monitors rental offers from Funda.nl and notifies admins and specified chats of new listings based on a custom URL. The bot also provides admin controls to manage which users and chats receive these notifications.

## Features

- Fetch rental offers from Funda.nl based on a URL provided by users.
- Notify specified users and chats of new offers.
- Admin management (add and remove admins, add and remove chats).
- Easy-to-use `/start` and `/help` commands for user guidance.

## Prerequisites

Before running the bot, ensure you have the following:

- Python 3.8 or higher installed.
- A [Telegram Bot Token](https://core.telegram.org/bots#botfather).
- `aiogram v3`, `loguru`, and `selenium` Python libraries installed.
- `.env` file set up with the following variables:

```bash
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
OWNER_ID=your-telegram-user-id-here
```

The `.env` file is used to keep sensitive information like the bot token and owner ID.

### Python Libraries

Install the required Python libraries using:

```bash
pip install -r requirements.txt
```

Your `requirements.txt` should include the following dependencies:

```text
aiogram==3.x.x
loguru
selenium
python-dotenv
```

### Setup Instructions

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/TurboKach/nl-rent-scan.git
   cd nl-rent-scan
   ```

2. **Create a `.env` file**:
   Inside the root directory of the project, create a `.env` file with the following content:

   ```bash
   TELEGRAM_BOT_TOKEN=your-telegram-bot-token
   OWNER_ID=your-telegram-user-id
   ```

3. **Configure the `settings.py` file**:
   You will need to configure the `settings.py` file to include variables like `admins_ids`, `funda_url`, `funda_url_default`, `known_chats`, etc.

   Example `settings.py`:

   ```python
   class Settings:
       admins_ids = [123456789, 987654321]  # List of admin user IDs
       funda_url = "https://www.funda.nl/huur/amsterdam/"
       funda_url_default = "https://www.funda.nl/huur/"
       known_chats = []  # List of known chat IDs

   settings = Settings()
   ```

4. **Run the Bot**:
   To run the bot, execute the following command:

   ```bash
   python bot.py
   ```

   If everything is set up correctly, you should see logs indicating that the bot has started.

## How It Works

### Basic Commands

- `/start` or `/help`: Shows basic information and instructions for using the bot. Only the bot owner and admins can interact with the bot.
  
- **Admin Management**:
  - `/add_admin [user_id]`: Adds a user to the list of admins. Only the bot owner can execute this command.
  - `/remove_admin [user_id]`: Removes a user from the list of admins. Only the bot owner can execute this command.
  
- **Chat Management**:
  - `/add_chat [chat_id]`: Adds a chat where notifications will be sent.
  - `/remove_chat [chat_id]`: Removes a chat from the list of known chats.
  - `/get_chats`: Retrieves a list of known chats.
  
- **Other Commands**:
  - `/get_admins`: Retrieves a list of current admins.
  - `/get_chat_id`: Retrieves the ID of the current chat.

### Adding Admins

Admins can be added dynamically using the `/add_admin` command. Admins will have permission to interact with the bot and manage chat IDs.

You can also add an admin programmatically using the `add_admin_by_user_id` function:

```python
result = await add_admin_by_user_id(123456789)  # Replace with the actual user_id
```

### Monitoring Funda.nl

Once the bot is running, it continuously monitors the specified Funda.nl URL (`settings.funda_url`) for new rental listings. If a new offer is found, it sends the offer details to all known chats.

The `check_new_offers` function is used to scan for new offers:

```python
async def check_new_offers():
    # Logic to scan Funda.nl for new offers
    ...
```

New messages are sent to all known chats using the `check_and_send_new_messages` function, which is continuously running in the background.

## Logging

The bot uses the `loguru` library for logging. Logs are saved in a rotating file (`bot.log`) with a maximum size of 10 MB.

## Error Handling

- If the bot encounters any issues while adding admins, managing chats, or scanning for offers, it logs the error using `logger.error`.
- Invalid URLs are caught using Selenium’s `InvalidArgumentException`, and the bot reverts to the default Funda.nl URL.

## Known Issues

- Ensure that Selenium and the web driver are correctly configured for scraping.
- If the bot stops responding, check the logs for error details.
