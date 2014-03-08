#!/bin/sh
echo "****** andyt installer **********"
echo
echo "apt-get update"
apt-get update
echo
echo "apt-get -y upgrade"
apt-get -y upgrade
echo
echo "apt-get -y install python-pip"
apt-get -y install python-pip
echo
echo "pip install beautifulsoup4"
pip install beautifulsoup4
echo
echo "pip install requests"
pip install requests
echo
echo"pip install python-mpd2"
pip install python-mpd2
echo
echo "pip install logging"
pip install logging
echo
echo "apt-get -y install python-serial"
apt-get -y install python-serial
echo
echo "install feedparser"
pip install feedparser
pip install urllib3
echo
echo "apt-get -y install mpd mpc"	
apt-get -y install mpd mpc	
mkdir log
cp mpd.conf /etc
cp startradio /etc/init.d
chmod 755 /etc/init.d/startradio
update-rc.d startradio defaults
echo "You still need to update the keys in the config.py file"
echo "You still need to edit /boot/cmdline.txt to remove the refs to AMA0"
echo "You still need to edit /etc/mpd.conf to change the bind_to_address to any"
echo
