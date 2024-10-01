# Funda Rental Offers Telegram Bot

A Telegram bot built using `aiogram` that monitors rental offers from Funda.nl and notifies admins and chats of new listings based on a custom URL. The bot includes admin controls for managing who receives notifications.

## Features

- Fetches rental offers from Funda.nl based on a provided URL.
- Notifies users and chats of new offers.
- Admin commands to manage users and chats.
- Simple `/start` and `/help` commands.

## Prerequisites

- Python 3.8+
- A [Telegram Bot Token](https://core.telegram.org/bots#botfather)
- `.env` file with:

```bash
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
OWNER_ID=your-telegram-user-id
```

### Install Dependencies

Install the required Python libraries:

```bash
pip install -r requirements.txt
```

Example `requirements.txt`:

```text
aiogram
loguru
seleniumbase
beautifulsoup4
python-dotenv
```

## Setup Instructions

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/TurboKach/nl-rent-scan.git
   cd nl-rent-scan
   ```

2. **Create a `.env` File**:

   Inside the root directory, create a `.env` file with the following content:

   ```bash
   TELEGRAM_BOT_TOKEN=your-telegram-bot-token
   OWNER_ID=your-telegram-user-id
   ```

3. **Run the Bot**:

   ```bash
   python bot.py
   ```

## Running the Bot on a Remote Server with Docker

To deploy this bot on a remote server using Docker:

1. Ensure the `Dockerfile` is present in the project.

2. **Build the Docker image**:

   ```bash
   docker build -t funda_parser_bot .
   ```

3. **Run the Docker container** locally or on your remote server:

   - **Locally**:

     ```bash
     docker run --env-file .env funda_parser_bot
     ```

   - **On a remote server**:
     1. Copy your project to the remote server.
     2. Build the Docker image or pull it from a Docker registry.
     3. Run the container using the `.env` file:

     ```bash
     docker run --env-file .env funda_parser_bot
     ```

## Setting Up Chrome on a Remote Server

The bot uses Selenium to automate Chrome for web scraping. If you're running the bot on a remote server, you'll need to install Google Chrome and ChromeDriver.

### 1. Install Google Chrome

To install Google Chrome on a remote server (e.g., Ubuntu):

```bash
# Update the package lists
sudo apt update

# Install necessary dependencies
sudo apt install -y wget gnupg2 software-properties-common

# Download Google's signing key and add it to the system
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -

# Set up the stable repository for Chrome
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list

# Update the package lists and install Google Chrome
sudo apt update
sudo apt install -y google-chrome-stable
```

### 2. Verify Chrome Installation

You can verify both installations with:

```bash
google-chrome --version  # Should return the installed Chrome version
```

Now, your server is ready to run the bot using Selenium with Chrome.

## Key Commands

- `/start` or `/help`: Shows basic instructions.
- `/add_admin [user_id]`, `/remove_admin [user_id]`: Manage admins (owner only).
- `/add_chat [chat_id]`, `/remove_chat [chat_id]`: Manage chats (owner only).
- `/get_admins`, `/get_chats`, `/get_chat_id`: Retrieve the current admins or chats.

## Monitoring Funda.nl

The bot monitors a Funda.nl URL for new rental listings and notifies all specified chats when new offers are found.

## Logging and Error Handling

- Uses `loguru` for logging. Logs are saved in a rotating file (`bot.log`).
- Handles invalid URLs and other Selenium exceptions, reverting to a default Funda.nl URL if needed.
