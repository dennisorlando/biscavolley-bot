#!/bin/bash

# This script installs the biscavolley-bot

# Create the directory
mkdir -p /opt/biscavolley/

# Copy the bot script
cp biscavolley-bot.py /opt/biscavolley/

# Copy the service file
cp biscavolley-bot.service /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Enable the service
systemctl enable biscavolley-bot.service
