#!/bin/sh
# startup.sh

cd /home/pi/MATE/2017-pi
git pull
sudo python3 controller.py
