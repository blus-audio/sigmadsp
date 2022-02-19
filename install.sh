#!/bin/sh

# The name of the python package
PYTHON_PACKAGE=sigmadsp

# The name of the sigmadsp-backend service
SIGMADSP_BACKEND=sigmadsp-backend

# The folder, where all sigmadsp configuration goes
CONFIGURATION_FOLDER=/var/lib/sigmadsp

# The main settings file name. This file is stored within the configuration folder.
CONFIGURATION_FILE=sigmadsp.json

# The default DSP type. This is written to the configuration file.
DSP_TYPE=adau14xx

# The parameter file name. This file stores DSP application parameters.
PARAMETER_FILE=current.params

# A temporary folder, used during installation
TEMP_FOLDER=/tmp

### Installation starts below. ###
sudo apt-get update

# Install the prerequisite pip3
sudo apt-get install -y python3-pip

# Install the package itself, along with its scripts
sudo pip3 install $PYTHON_PACKAGE --upgrade

echo "Stopping any old $SIGMADSP_BACKEND services."
for i in $SIGMADSP_BACKEND; do
 sudo systemctl stop $i
 sudo systemctl disable $i
done

sudo mkdir -p $CONFIGURATION_FOLDER
echo "Generate configuration folder for sigmadsp at $CONFIGURATION_FOLDER."

cat <<EOT >$TEMP_FOLDER/$CONFIGURATION_FILE
{
  "host": "0.0.0.0",
  "parameter_file_path": "$CONFIGURATION_FOLDER/$PARAMETER_FILE",
  "dsp_type": "$DSP_TYPE"
}
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
ExecStart=$LOC
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

# Ignore failed removal of temporary config
sudo rm $TEMP_CONFIG || true

cat $CONFIG | grep -v "dtparam=spi" > $TEMP_CONFIG
echo "dtparam=spi=on # SPI enabled for $SIGMADSP_BACKEND" >> $TEMP_CONFIG

sudo chmod --reference=$CONFIG $TEMP_CONFIG
sudo chown --reference=$CONFIG $TEMP_CONFIG

sudo mv $TEMP_CONFIG $CONFIG
echo "Finished installation of $SIGMADSP_BACKEND successfully."
