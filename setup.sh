#!/bin/bash

# The IdleRPG Discord Bot
# Copyright (C) 2018-2019 Diniboy and Gelbpunkt
#
# This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
# For more information, see README.md and LICENSE.md.

PATTERN=".*version = \"\(.*\)\".*"
PATTERN2=".*\"user\": \"\(.*\)\".*"
PATTERN3=".*\"database\": \"\(.*\)\".*"
VERSION=$(sed -n "s/$PATTERN/\1/p" < config.py.example)
DBUSER=$(sed -n "s/$PATTERN2/\1/p" < config.py.example)
DBNAME=$(sed -n "s/$PATTERN3/\1/p" < config.py.example)

printf "====================\n"
printf "IdleRPG Setup Script\n"
printf "Version $VERSION\n"
printf "====================\n\n\n"
printf "WARNING: This script will only work as root or sudo and will touch files.\n"
printf "Make sure you have config.py.example set to the correct database credentials!\n\n"
read -r -p "Press enter to continue"

printf "\n\n\nMoving config.py.example to config.py...\n\n"

mv config.py.example config.py

printf "Copying service file to /etc/systemd/system/idlerpg.service...\n\n"

cp idlerpg.service /etc/systemd/system/idlerpg.service

printf "Replacing schema username with $DBUSER...\n\n"

sed -e "s:jens:$DBUSER:g" schema.sql > schema2.sql
rm schema.sql
mv schema2.sql schema.sql

printf "Loading database schema...\n\n"

psql $DBNAME < schema.sql

printf "Installing dependencies...\n\n"

pip3 install -r requirements.txt

printf "Done! Use systemctl start idlerpg to start the bot! Before, you may want to edit config.py more\n"
