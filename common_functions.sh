#!/bin/bash

if [ "$(id -u)" -eq 0 ]; then
    echo "Do not run this script as root."
    exit 1
fi

set -e

# Ask the user a yes/no question. Returns zero for yes, one for no.
function yes_or_no {
    while true; do
        read -p "$* [y/n]: " yn
        case $yn in
            [Yy]*) return 0 ;;
            [Nn]*) return 1 ;;
        esac
    done
}

# Stops and disables the sigmadsp backend service.
function stop_and_disable_sigmadsp_service {
    echo "=== Stopping and disabling existing '$SIGMADSP_BACKEND' service."
    sudo systemctl stop $SIGMADSP_BACKEND
    sudo systemctl disable $SIGMADSP_BACKEND
}
