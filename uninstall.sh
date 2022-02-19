#!/bin/bash

# Load configuration for installation.
source ./templates/.env

function yes_or_no {
    while true; do
        read -p "$* [y/n]: " yn
        case $yn in
            [Yy]*) return 0  ;;  
            [Nn]*) echo "Aborted" ; return  1 ;;
        esac
    done
}

### Uninstall happens below
echo "=== Uninstall $SIGMADSP."
sudo pip3 uninstall $SIGMADSP --quiet

yes_or_no "Delete configuration folder '$CONFIGURATION_FOLDER?'" && sudo rm -rf $CONFIGURATION_FOLDER

echo "=== Stopping '$SIGMADSP_BACKEND' service."
sudo systemctl stop $SIGMADSP_BACKEND
sudo systemctl disable $SIGMADSP_BACKEND
yes_or_no "Delete service configuration '/usr/lib/systemd/system/$SIGMADSP_BACKEND.service'?" && sudo rm /usr/lib/systemd/system/$SIGMADSP_BACKEND.service

echo "=== Uninstalled $SIGMADSP."