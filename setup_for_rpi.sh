#!/bin/sh

sudo apt update -y
sudo apt upgrade -y
sudo apt install -y libbluetooth3-dev libglib2.0 libboost-python-dev libboost-thread-dev gcc g++ make
sudo apt install -y prometheus-node-exporter
sudo pip3 install ipython
sudo pip3 install requests
sudo pip3 install bluepy
sudo pip3 install prometheus-client
sudo pip3 install paho-mqtt

sudo cp ./switchbot_probe.service /etc/systemd/system/
sudo systemctl enable switchbot_probe

echo setup completed.
echo please run following to start switchbot_probe.
echo sudo systemctl start switchbot_probe
