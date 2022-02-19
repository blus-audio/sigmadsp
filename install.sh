#!/bin/sh
sudo apt-get update
sudo apt-get install -y python3-pip
sudo pip3 install --upgrade sigmadsp

for i in sigmadsp; do
 sudo systemctl stop $i
 sudo systemctl disable $i
done

sudo mkdir -p /var/lib/sigmadsp

cat <<EOT >/var/lib/sigmadsp/sigmadsp.json
{
  "host": "0.0.0.0",
  "parameter_file_path": "/var/lib/sigmadsp/current.params",
  "dsp_type": "adau14xx"
}
EOT

# Create systemd config for the TCP server
LOC=`which sigmadsp-backend`

cat <<EOT >/tmp/sigmadsp-backend.service
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

sudo mv /tmp/sigmadsp-backend.service /lib/systemd/system/sigmadsp-backend.service

sudo systemctl daemon-reload

for i in sigmadsp; do
 sudo systemctl start $i
 sudo systemctl enable $i
done

cat /boot/config.txt | grep -v "dtparam=spi" >> /tmp/config.txt
echo "dtparam=spi=on" >> /tmp/config.txt
sudo mv /tmp/config.txt /boot/config.txt
