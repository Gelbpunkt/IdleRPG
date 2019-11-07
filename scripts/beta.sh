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
podman run --rm -d --pod idlerpg --name postgres -v $(pwd)/start.sh:/docker-entrypoint-initdb.d/init.sh:z -v $(pwd)/schema.sql:/docker-entrypoint-initdb.d/init.sql:z postgres:12-alpine
