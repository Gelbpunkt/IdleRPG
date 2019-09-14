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

prompt_paths () {
    read -p "Path to okapi: " okapi_path
    okapi_path=$(echo $okapi_path | sed 's:/*$::')
    read -p "Path to teatro: " teatro_path
    teatro_path=$(echo $teatro_path | sed 's:/*$::')
}

get_dependencies () {
    printf "Cloning okapi and teatro...\n"
    printf "Please enter a directory for the files\n"
    printf "e.g. /home/kevin/ will install to /home/kevin/okapi and /home/kevin/teatro\n"
    read -p "Enter a path (must exist already): " base_dir
    base_dir=$(echo $base_dir | sed 's:/*$::')
    printf "Entering ${base_dir}\n\n"
    cd $base_dir
    printf "Cloning...\n"
    git clone https://github.com/Kenvyra/okapi
    git clone https://github.com/Kenvyra/teatro
    okapi_path="${base_dir}/okapi"
    teatro_path="${base_dir}/teatro"
    printf "Done cloning. Going back.\n"
    cd $cwd
}

printf "====================\n"
printf "IdleRPG Setup Script\n"
printf "Version 2.0\n"
printf "====================\n\n\n"
printf "This script will walk you through setting up Podman with IdleRPG and its components\n\n${bold}Make sure you are in the base directory of IdleRPG${normal}\n\n"

printf "IdleRPG depends on okapi and teatro.\n"

while true; do
    read -p "Are they cloned? [y/n] " yn
    case $yn in
        [Yy]* ) prompt_paths; break;;
        [Nn]* ) get_dependencies; break;;
        * ) printf "Please answer yes or no.\n";;
    esac
done

printf "\n\nDependencies OK\n"
printf "Okapi Path: ${okapi_path}\n"
printf "Teatro Path: ${teatro_path}\n\n"

printf "Next is the PostgreSQL installation.\n"
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
mkdir /opt/teatro
mkdir /opt/pginit
mkdir /opt/idlerpg
mv init.sh /opt/pginit/init.sh
chmod 0777 /opt/pgdata
chmod 0777 /opt/redisdata

printf "Modifying unit file paths for podman builds...\n"

sed -i "s:IDLERPG_PATH:${cwd}:" units/podman-idlerpg.service
sed -i "s:OKAPI_PATH:${okapi_path}:" units/podman-okapi.service
sed -i "s:TEATRO_PATH:${teatro_path}:" units/podman-teatro.service

printf "Copying units...\n"
cp units/* /etc/systemd/system/
systemctl daemon-reload

printf "Done.\n"
printf "Create /opt/teatro/config.json with the teatro config (https://github.com/Kenvyra/teatro/blob/master/config.example.json)\n"
printf "Create /opt/idlerpg/config.py with the IdleRPG config (https://github.com/Gelbpunkt/IdleRPG/blob/v4/config.example.py)\n"
printf "Create /opt/andesite/application.conf with the Andesite config (https://github.com/natanbc/andesite-node/blob/master/application.conf.example)\n"
printf "Create /opt/okapi/config.json with a proxy value\n"
printf "Then start your units (probably build them manually due to systemd timeout) and enjoy :)\n"
