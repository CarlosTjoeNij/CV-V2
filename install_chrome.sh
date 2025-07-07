#!/bin/bash
set -e

echo "Updating package lists..."
apt-get update

echo "Installing dependencies for Chrome..."
apt-get install -y libappindicator3-1 fonts-liberation

echo "Downloading Google Chrome..."
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

echo "Installing Google Chrome..."
dpkg -i google-chrome-stable_current_amd64.deb || apt-get install -f -y

echo "Cleaning up..."
rm google-chrome-stable_current_amd64.deb
