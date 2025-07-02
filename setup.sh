#!/bin/bash

set -e

echo "Updating apt and installing dependencies..."
apt-get update
apt-get install -y wget unzip curl gnupg libnss3 libxss1 libappindicator1 libindicator7 libgbm-dev fonts-liberation libasound2 xdg-utils libu2f-udev libvulkan1 xvfb unzip

echo "Installing Google Chrome..."
curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-linux-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
apt-get update
apt-get install -y google-chrome-stable

echo "Getting Chrome version..."
CHROME_VERSION=$(google-chrome-stable --version | grep -oP '[0-9.]+' | head -1)
CHROME_MAJOR=$(echo $CHROME_VERSION | cut -d. -f1)

echo "Downloading matching ChromeDriver for Chrome version $CHROME_VERSION..."
DRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_MAJOR")
wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/${DRIVER_VERSION}/chromedriver_linux64.zip
unzip /tmp/chromedriver.zip -d /usr/local/bin
chmod +x /usr/local/bin/chromedriver
rm /tmp/chromedriver.zip

echo "Setup done."
