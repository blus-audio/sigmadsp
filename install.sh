#!/bin/bash

# Load configuration for installation.
source ./templates/.env
source ./common_functions.sh

echo "=== Install '$SIGMADSP_EXECUTABLE'."

# Creates a new sigmadsp configuration file. This overwrites an old file with the same name.
function create_new_config_file {
    echo "> Create new configuration for '$SIGMADSP_EXECUTABLE' in '$SIGMADSP_CONFIGURATION_FOLDER/$SIGMADSP_CONFIGURATION_FILE'."
    sudo mkdir -p $SIGMADSP_CONFIGURATION_FOLDER

    envsubst < ./templates/config.yaml.template > $SIGMADSP_TEMP_FOLDER/$SIGMADSP_CONFIGURATION_FILE
    sudo mv $SIGMADSP_TEMP_FOLDER/$SIGMADSP_CONFIGURATION_FILE $SIGMADSP_CONFIGURATION_FOLDER/$SIGMADSP_CONFIGURATION_FILE
}

# Install pipx with Python, for later installing the sigmadsp package.
function install_pipx_python {
    echo "=== Installing pipx."
    {
        sudo apt install -y pipx
        pipx ensurepath
    } || {
        echo "! Falling back to installation via pip."
        # Install the prerequisite pip3.
        sudo apt-get install -y python3-pip python3-venv

        # Install pipx for running sigmadsp in a virtual environment.
        python3 -m pip install --user pipx
        python3 -m pipx ensurepath
    }
}

### Installation starts below. ###
echo "=== Install required packages."
sudo apt-get update

# Required for gpiod
sudo apt-get install python3-dev

install_pipx_python

# Use updated paths in current shell.
source ~/.bashrc

# Install the package itself, along with its executable scripts.
pipx install $SIGMADSP_EXECUTABLE

# Optional: stop and disable any old existing service.
stop_and_disable_sigmadsp_service || true

if [ -f "$SIGMADSP_CONFIGURATION_FOLDER/$SIGMADSP_CONFIGURATION_FILE" ]
then
    echo "=== Existing configuration found for '$SIGMADSP_EXECUTABLE' in '$SIGMADSP_CONFIGURATION_FOLDER/$SIGMADSP_CONFIGURATION_FILE'."
    if [ "$(yes_or_no "Backup and overwrite existing configuration?")" -eq "0" ]
    then
        sudo mv $SIGMADSP_CONFIGURATION_FOLDER/$SIGMADSP_CONFIGURATION_FILE $SIGMADSP_CONFIGURATION_FOLDER/$SIGMADSP_CONFIGURATION_FILE.bak
        create_new_config_file
    else
        echo "> Keep existing configuration."
    fi
else
    create_new_config_file
fi

# Discover service.
source ~/.bashrc

echo "=== Setup '$SIGMADSP_BACKEND' service."
# Create systemd config for the service.
# This location looks for the service executable, which was previously installed with the Python package.
SIGMADSP_SERVICE_LOCATION=`which $SIGMADSP_BACKEND`

echo "> Found service executable at '$SIGMADSP_SERVICE_LOCATION'."
export SIGMADSP_SERVICE_LOCATION

envsubst < ./templates/backend.service.template > $SIGMADSP_TEMP_FOLDER/$SIGMADSP_BACKEND.service
sudo mv $SIGMADSP_TEMP_FOLDER/$SIGMADSP_BACKEND.service /usr/lib/systemd/system/$SIGMADSP_BACKEND.service

sudo systemctl daemon-reload
sudo systemctl start $SIGMADSP_BACKEND
sudo systemctl enable $SIGMADSP_BACKEND

echo "=== Finished installation of '$SIGMADSP_EXECUTABLE' and its backend service '$SIGMADSP_BACKEND'."
