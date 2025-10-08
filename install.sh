#!/bin/bash

# This script installs the biscavolley-bot

# Create the user
useradd -r -s /bin/false biscavolley

# Ask for the bot token
read -s -p "Enter the bot token: " BOT_TOKEN

# Create the environment file directory
mkdir -p /etc/biscavolley/

# Write the bot token to the environment file
echo "BOT_TOKEN=$BOT_TOKEN" >/etc/biscavolley/environment

# Set the owner of the environment file to the user running the script
chown biscavolley /etc/biscavolley/environment

# Set the permissions of the environment file to be read-only by the user
chmod 400 /etc/biscavolley/environment

# Create the directory
mkdir -p /opt/biscavolley/

# Create a virtual environment
python3 -m venv /opt/biscavolley/venv

# Install the dependencies
/opt/biscavolley/venv/bin/pip install -r requirements.txt

# Copy the bot script
cp biscavolley-bot.py /opt/biscavolley/

# Set the owner of the directory
chown -R biscavolley:biscavolley /opt/biscavolley

# Copy the service file
cp biscavolley-bot.service /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Enable the service
systemctl enable --now biscavolley-bot.service