#!/bin/bash

# The IdleRPG Discord Bot
# Copyright (C) 2018-2019 Diniboy and Gelbpunkt
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


PATTERN=".*version = \"\(.*\)\".*"
PATTERN2=".*\"user\": \"\(.*\)\".*"
PATTERN3=".*\"database\": \"\(.*\)\".*"
VERSION=$(sed -n "s/$PATTERN/\1/p" < config.example.py)
DBUSER=$(sed -n "s/$PATTERN2/\1/p" < config.example.py)
DBNAME=$(sed -n "s/$PATTERN3/\1/p" < config.example.py)

printf "====================\n"
printf "IdleRPG Setup Script\n"
printf "Version $VERSION\n"
printf "====================\n\n\n"
printf "WARNING: This script will only work as root or sudo and will touch files.\n"
printf "Make sure you have config.example.py set to the correct database credentials!\n\n"
read -r -p "Press enter to continue"

printf "\n\n\nMoving config.example.py to config.py...\n\n"

mv config.example.py config.py

printf "Copying service file to /etc/systemd/system/idlerpg.service...\n\n"

sed -i "s:/path/to/launcher.py:$(pwd)/launcher.py:" idlerpg.service
sed -i "s:my_username:$(whoami)" idlerpg.service
cp idlerpg.service /etc/systemd/system/idlerpg.service

printf "Replacing schema username with $DBUSER...\n\n"

sed -i "s:jens:$DBUSER:" schema.sql

printf "Loading database schema...\n\n"

psql $DBNAME < schema.sql

printf "Installing dependencies...\n\n"

pip3 install -r requirements.txt

printf "Done! Use systemctl start idlerpg to start the bot! Before, you may want to edit config.py more\n"
