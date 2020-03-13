#!/bin/bash
# Adrian's script for setting up a quick test deployment
podman pod create --name idlerpg
podman run --rm -d --pod idlerpg --name redis redis:6.0-rc-alpine
cat <<EOF > start.sh
createdb idlerpg
psql idlerpg -c "CREATE ROLE jens WITH PASSWORD 'owo';"
psql idlerpg -c "ALTER ROLE jens WITH LOGIN;"
psql idlerpg -c "CREATE ROLE prest WITH PASSWORD 'placeholder';"
psql idlerpg -c "CREATE ROLE votehandler WITH PASSWORD 'placeholder';"

psql idlerpg <<DONE
$(<schema.sql)
DONE
EOF

chmod 777 start.sh
podman run --rm -d --pod idlerpg --name postgres -e POSTGRES_PASSWORD="test" -v $(pwd)/start.sh:/docker-entrypoint-initdb.d/init.sh:Z postgres:12-alpine
sleep 15
rm start.sh
