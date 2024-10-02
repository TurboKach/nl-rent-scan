#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status

# Update package lists and install core packages
echo "Updating package lists..."
apt-get update

# Install basic dependencies
echo "Installing basic dependencies..."
apt-get install -y --no-install-recommends \
    wget \
    gpgv \
    curl \
    ca-certificates \
    apt-transport-https \
    gnupg \
    unzip

# Add Google Chrome's signing key
echo "Adding Google Chrome signing key..."
curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | apt-key add -

# Add Chrome's stable repository
echo "Adding Google Chrome stable repository..."
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# Update package lists for Chrome
echo "Updating package lists for Chrome..."
apt-get update

# Install Google Chrome
echo "Installing Google Chrome..."
apt-get install -y --no-install-recommends google-chrome-stable

# Download ChromeDriver
echo "Downloading ChromeDriver..."
CHROME_VERSION=$(google-chrome --version | grep -oP "\d+\.\d+\.\d+")
CHROMEDRIVER_VERSION=$(curl -s https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION)
wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip

# Unzip ChromeDriver
echo "Unzipping ChromeDriver..."
unzip /tmp/chromedriver.zip -d /usr/local/bin/
chmod +x /usr/local/bin/chromedriver

# Cleanup
echo "Cleaning up..."
rm -rf /var/lib/apt/lists/* /tmp/chromedriver.zip

# Run the main application
echo "Starting the application..."
exec "$@"
