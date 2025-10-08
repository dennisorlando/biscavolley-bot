#!/bin/bash

# This script uninstalls the biscavolley-bot

# Disable the service
systemctl disable biscavolley-bot.service

# Remove the service file
rm /etc/systemd/system/biscavolley-bot.service

# Reload systemd
systemctl daemon-reload

# Remove the directory
rm -rf /opt/biscavolley/

# Remove the environment file
rm -rf /etc/biscavolley/
