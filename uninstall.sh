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

# Notify the user about the user deletion
echo "The user 'biscavolley' was not deleted automatically. Consider removing it manually, if needed."
