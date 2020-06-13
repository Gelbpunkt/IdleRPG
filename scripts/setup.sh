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

if [ "$EUID" -eq 0 ]
  then echo "Please do not run as root"
  exit
else
  echo "Check... Running rootless OK"
fi

if [ -x "$(command -v podman)" ]; then
    echo "Check... Podman installed OK"
else
    echo "podman is not installed. Use your package manager, for example: dnf install -y podman"
    exit
fi

if [ -x "$(command -v git)" ]; then
    echo "Check... git installed OK"
else
    echo "git is not installed. Use your package manager, for example: dnf install -y git-core"
    exit
fi

IDLEDIR=$(pwd)
BASEDIR=$(echo $HOME)

printf "====================\n"
printf "IdleRPG Setup Script\n"
printf "Version 4.0\n"
printf "====================\n\n\n"
printf "This script will walk you through setting up IdleRPG and its components\n\n${bold}Make sure you are in the base directory of IdleRPG. It will only install the basics!${normal}\n\n"

printf "The base directory I detected is $BASEDIR\n"

printf "First is the PostgreSQL installation.\n"
printf "We will generate a one-time startup file to load the schema\n"
read -p "IdleRPG Database User: " idlerpg_db_user
printf "${idlerpg_db_user} Password: "
read -s idlerpg_db_user_password
printf "\n"

printf "\n${idlerpg_db_user} will be created...\n"

printf "Generating the sql file...\n"

header="
    CREATE USER ${idlerpg_db_user};
    CREATE DATABASE idlerpg;
    GRANT ALL PRIVILEGES ON DATABASE idlerpg TO ${idlerpg_db_user};
    ALTER USER ${idlerpg_db_user} WITH PASSWORD '${idlerpg_db_user_password}';
"
cp schema.sql schematmp.sql
sed -i "s:jens:${idlerpg_db_user}:" schematmp.sql
schema=$(<schematmp.sql)
rm schematmp.sql
script="
#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username \"\$POSTGRES_USER\" --dbname \"\$POSTGRES_DB\" <<'EOSQL'
${header}
EOSQL
psql -v ON_ERROR_STOP=1 --username \"\$POSTGRES_USER\" --dbname idlerpg <<'EOSQL'
${schema}
EOSQL
"

echo "${script}" >> init.sh

printf "Creating podman pod...\n"
podman pod create --name idlerpg
printf "Creating directories for mounting configs...\n"
mkdir $BASEDIR/pgdata
mkdir $BASEDIR/redisdata
mkdir $BASEDIR/okapi
mkdir $BASEDIR/pginit
cd $BASEDIR/okapi
curl https://raw.githubusercontent.com/Kenvyra/okapi-rewrite/master/config.example.json -o $BASEDIR/okapi/config.json
mkdir $BASEDIR/idlerpg
cp $IDLEDIR/config.example.py config.py
mv $IDLEDIR/init.sh $BASEDIR/pginit/init.sh
chmod 0777 $BASEDIR/pgdata
chmod 0777 $BASEDIR/redisdata

printf "Copying units...\n"

loginctl enable-linger $(whoami)
mkdir -p $BASEDIR/.config/systemd/user/
cp $IDLEDIR/units/*.service $BASEDIR/.config/systemd/user/

printf "Done. Please update these configs now:\n"
printf "$BASEDIR/idlerpg/config.py\n"
printf "and $BASEDIR/okapi/config.json\n"
printf "Then systemctl --user enable \"podman-*\" --now"
