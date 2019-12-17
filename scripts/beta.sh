#!/bin/bash
# Adrian's script for setting up a quick test deployment
podman pod create --name idlerpg
podman run --rm -d --pod idlerpg --name redis redis:5-alpine
cat <<EOF > start.sh
createdb idlerpg
psql idlerpg -c "CREATE ROLE jens WITH PASSWORD 'owo';"
psql idlerpg -c "ALTER ROLE jens WITH LOGIN;"
psql idlerpg -c "CREATE ROLE prest WITH PASSWORD 'placeholder';"
psql idlerpg -c "CREATE ROLE votehandler WITH PASSWORD 'placeholder';"
EOF
chmod 777 start.sh
chmod 777 schema.sql
podman run --rm -d --pod idlerpg --name postgres -v $(pwd)/start.sh:/docker-entrypoint-initdb.d/init.sh:Z -v $(pwd)/schema.sql:/docker-entrypoint-initdb.d/init.sql:Z postgres:12-alpine
sleep 15
chmod 600 schema.sql
rm start.sh
