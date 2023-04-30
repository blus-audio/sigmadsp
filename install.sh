#!/bin/bash

# Load configuration for installation.
source ./templates/.env

### Installation starts below. ###
echo "=== Install required packages."
sudo apt-get -qq update

# Install the prerequisite pip3.
sudo apt-get -qq install -y python3-pip python3-venv

# Install pipx for running sigmadsp in a virtual environment.
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install the package itself, along with its executable scripts.
pipx install $SIGMADSP

echo "=== Stopping existing '$SIGMADSP_BACKEND' service."
sudo systemctl stop $SIGMADSP_BACKEND
sudo systemctl disable $SIGMADSP_BACKEND

echo "=== Generate new configuration for '$SIGMADSP' in '$CONFIGURATION_FOLDER/$CONFIGURATION_FILE'."
sudo mkdir -p $CONFIGURATION_FOLDER

envsubst < ./templates/config.yaml.template > $TEMP_FOLDER/$CONFIGURATION_FILE
sudo mv $TEMP_FOLDER/$CONFIGURATION_FILE $CONFIGURATION_FOLDER/$CONFIGURATION_FILE

# Create systemd config for the service.
# This location looks for the service executable, which was previously installed with the Python package.
SERVICE_LOCATION=`which $SIGMADSP_BACKEND`
export SERVICE_LOCATION

echo "=== Setup '$SIGMADSP_BACKEND' service."
envsubst < ./templates/backend.service.template > $TEMP_FOLDER/$SIGMADSP_BACKEND.service
sudo mv $TEMP_FOLDER/$SIGMADSP_BACKEND.service /usr/lib/systemd/system/$SIGMADSP_BACKEND.service

sudo systemctl daemon-reload
sudo systemctl start $SIGMADSP_BACKEND
sudo systemctl enable $SIGMADSP_BACKEND

# Enable SPI for controlling DSP chipsets.
CONFIG=/boot/config.txt
TEMP_CONFIG=$TEMP_FOLDER/config.txt

cat $CONFIG | grep -v "dtparam=spi" > $TEMP_CONFIG
echo "dtparam=spi=on # SPI enabled for $SIGMADSP_BACKEND" >> $TEMP_CONFIG

sudo chmod --reference=$CONFIG $TEMP_CONFIG
sudo chown --reference=$CONFIG $TEMP_CONFIG

sudo mv $TEMP_CONFIG $CONFIG

echo "=== Finished installation of '$SIGMADSP' and its backend service '$SIGMADSP_BACKEND'."
