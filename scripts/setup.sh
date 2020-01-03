#!/bin/bash

# The IdleRPG Discord Bot
# Copyright (C) 2018-2020 Diniboy and Gelbpunkt
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

bold=$(tput bold)
normal=$(tput sgr0)
cwd=$(pwd)

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
else
  echo "Check... Running as root OK"
fi

if [ -x "$(command -v podman)" ]; then
    echo "Check... Podman installed OK"
else
    echo "podman is not installed. Use your package manager"
    exit
fi

if [ -x "$(command -v git)" ]; then
    echo "Check... git installed OK"
else
    echo "git is not installed. Use your package manager"
    exit
fi

printf "====================\n"
printf "IdleRPG Setup Script\n"
printf "Version 3.0\n"
printf "====================\n\n\n"
printf "This script will walk you through setting up Podman with IdleRPG and its components\n\n${bold}Make sure you are in the base directory of IdleRPG${normal}\n\n"

printf "First is the PostgreSQL installation.\n"
printf "We will generate a one-time startup file to load the schema\n"
read -p "IdleRPG Database User: " idlerpg_db_user
printf "${idlerpg_db_user} Password: "
read -s idlerpg_db_user_password
printf "\n"
read -p "Teatro Database User: " teatro_db_user
printf "${teatro_db_user} Password: "
read -s teatro_db_user_password

printf "\n${idlerpg_db_user} and ${teatro_db_user} will be created...\n"

printf "Generating the sql file...\n"

header="
    CREATE USER ${idlerpg_db_user};
    CREATE USER ${teatro_db_user};
    CREATE DATABASE idlerpg;
    GRANT ALL PRIVILEGES ON DATABASE idlerpg TO ${idlerpg_db_user};
    GRANT ALL PRIVILEGES ON DATABASE idlerpg TO ${teatro_db_user};
    ALTER USER ${idlerpg_db_user} WITH PASSWORD '${idlerpg_db_user_password}';
    ALTER USER ${teatro_db_user} WITH PASSWORD '${teatro_db_user_password}';
"
sed -i "s:jens:${idlerpg_db_user}:" schema.sql
schema=$(<schema.sql)
script="
#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username \"\$POSTGRES_USER\" --dbname \"\$POSTGRES_DB\" <<-EOSQL
${header}
EOSQL
psql -v ON_ERROR_STOP=1 --username \"\$POSTGRES_USER\" --dbname idlerpg <<-EOSQL
${schema}
EOSQL
"

echo "${script}" >> init.sh

printf "Creating podman pod...\n"
podman pod create -p 7666:7666 -n idlerpg
printf "Creating /opt directories for mounting configs...\n"
mkdir /opt/pgdata
mkdir /opt/redisdata
mkdir /opt/andesite
curl https://raw.githubusercontent.com/natanbc/andesite-node/master/application.conf.example -o /opt/andesite/application.conf
mkdir /opt/teatro
curl https://raw.githubusercontent.com/Kenvyra/teatro/master/config.example.json -o /opt/teatro/config.json
mkdir /opt/pginit
mkdir /opt/okapi
cd /opt/teatro
curl https://raw.githubusercontent.com/Kenvyra/okapi/master/config.json -o /opt/okapi/config.json
mkdir /opt/idlerpg
curl https://raw.githubusercontent.com/Gelbpunkt/IdleRPG/v4/config.example.py -o /opt/idlerpg/config.py
mv init.sh /opt/pginit/init.sh
chmod 0777 /opt/pgdata
chmod 0777 /opt/redisdata

printf "Copying units...\n"
cp units/* /etc/systemd/system/
systemctl daemon-reload

printf "Done.\n"
printf "Now edit /opt/teatro/config.json\n"
printf "and /opt/idlerpg/config.py\n"
printf "and /opt/andesite/application.conf\n"
printf "and /opt/okapi/config.json\n"
printf "Then start your units and enjoy :)\n"
