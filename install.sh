#!/bin/sh

# The name of the python package to install
PYTHON_PACKAGE=sigmadsp

# The name of the sigmadsp-backend service
SIGMADSP_BACKEND=sigmadsp-backend

# The folder, where all sigmadsp configuration goes
CONFIGURATION_FOLDER=/var/lib/sigmadsp

# The main settings file name. This file is stored within the configuration folder.
CONFIGURATION_FILE=config.yaml

# The default DSP type. This is written to the configuration file.
DSP_TYPE=adau14xx

# The parameter file name. This file stores DSP application parameters.
PARAMETER_FILE=current.params

# A temporary folder, used during installation
TEMP_FOLDER=/tmp

### Installation starts below. ###
sudo apt-get update

Install the prerequisite pip3
sudo apt-get install -y python3-pip

Install the package itself, along with its scripts
sudo pip3 install $PYTHON_PACKAGE --upgrade

echo "Stopping old $SIGMADSP_BACKEND services."
for i in $SIGMADSP_BACKEND; do
 sudo systemctl stop $i
 sudo systemctl disable $i
done

sudo mkdir -p $CONFIGURATION_FOLDER
echo "Generate configuration folder for sigmadsp at $CONFIGURATION_FOLDER."

cat <<EOT >$TEMP_FOLDER/$CONFIGURATION_FILE
# The $CONFIGURATION_FILE.yaml file contains all settings that can be changed on the $SIGMADSP_BACKEND.

# The IP address and port, on which the $SIGMADSP_BACKEND listens for requests from SigmaStudio.
host:
  # The default value "0.0.0.0" allows listening on any address.
  ip: "0.0.0.0"
  port: 8087

# Settings for the $SIGMADSP_BACKEND.
backend:
  # The port, on which the $SIGMADSP_BACKEND is reachable.
  port: 50051

parameters:
  # The parameter file path, which contains DSP application parameters,
  # such as cell names, addresses and other information. This parameter file is required
  # for the backend, in order to be able to control DSP functionality at runtime, e.g. volume.
  path: "$CONFIGURATION_FOLDER/$PARAMETER_FILE"

dsp:
  # The type of the DSP to control with the $SIGMADSP_BACKEND service.
  type: "$DSP_TYPE"
EOT

# Write default settings for sigmadsp. Simply change them in the .json file.
sudo mv $TEMP_FOLDER/$CONFIGURATION_FILE $CONFIGURATION_FOLDER/$CONFIGURATION_FILE

# Create systemd config for the sigmadsp-backend service
# This location looks for the backend service executable, which was previously installed with the Python package.
LOC=`which $SIGMADSP_BACKEND`

cat <<EOT > $TEMP_FOLDER/$SIGMADSP_BACKEND.service
[Unit]
Description=Sigma DSP backend
Wants=network-online.target
After=network.target network-online.target
[Service]
Type=simple
ExecStart=$LOC -s $CONFIGURATION_FOLDER/$CONFIGURATION_FILE
StandardOutput=journal
[Install]
WantedBy=multi-user.target
EOT

sudo mv $TEMP_FOLDER/$SIGMADSP_BACKEND.service /usr/lib/systemd/system/$SIGMADSP_BACKEND.service

sudo systemctl daemon-reload

for i in $SIGMADSP_BACKEND; do
 sudo systemctl start $i
 sudo systemctl enable $i
done

# Enable SPI for controlling DSP chipsets.
CONFIG=/boot/config.txt
TEMP_CONFIG=$TEMP_FOLDER/config.txt

cat $CONFIG | grep -v "dtparam=spi" > $TEMP_CONFIG
echo "dtparam=spi=on # SPI enabled for $SIGMADSP_BACKEND" >> $TEMP_CONFIG

sudo chmod --reference=$CONFIG $TEMP_CONFIG
sudo chown --reference=$CONFIG $TEMP_CONFIG

sudo mv $TEMP_CONFIG $CONFIG

echo ""
echo "Finished installation of $SIGMADSP_BACKEND."
echo "Find its configuration file in '$CONFIGURATION_FOLDER/$CONFIGURATION_FILE'."
