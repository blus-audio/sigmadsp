#!/bin/bash

# Load configuration for installation.
source ./templates/.env
source ./common_functions.sh

### Uninstall happens below
echo "=== Uninstall $SIGMADSP."
pipx uninstall $SIGMADSP

yes_or_no "Delete configuration folder '$CONFIGURATION_FOLDER?'" && sudo rm -rf $CONFIGURATION_FOLDER

echo "=== Stopping '$SIGMADSP_BACKEND' service."
sudo systemctl stop $SIGMADSP_BACKEND
sudo systemctl disable $SIGMADSP_BACKEND
yes_or_no "Delete service configuration '/usr/lib/systemd/system/$SIGMADSP_BACKEND.service'?" && sudo rm /usr/lib/systemd/system/$SIGMADSP_BACKEND.service

echo "=== Uninstalled $SIGMADSP."
