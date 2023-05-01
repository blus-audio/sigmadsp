#!/bin/bash

# Load configuration for installation.
source ./templates/.env
source ./common_functions.sh

### Uninstall happens below
echo "=== Uninstall $SIGMADSP."
pipx uninstall $SIGMADSP

yes_or_no "Delete configuration folder '$CONFIGURATION_FOLDER?'" && sudo rm -rf $CONFIGURATION_FOLDER

stop_and_disable_sigmadsp_service

yes_or_no "Delete service configuration '/usr/lib/systemd/system/$SIGMADSP_BACKEND.service'?" && sudo rm /usr/lib/systemd/system/$SIGMADSP_BACKEND.service

echo "=== Uninstalled $SIGMADSP."
