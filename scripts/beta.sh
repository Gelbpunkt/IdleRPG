#!/bin/bash
# Adrian's script for setting up a quick test deployment
podman pod create idlerpg
podman run --rm --pod idlerpg --name redis redis:5-alpine
cat <<EOF > start.sh
wget https://git.travitia.xyz/Adrian/IdleRPG/raw/v4/schema.sql
chown postgres schema.sql
su postgres
createdb idlerpg
psql idlerpg -c "CREATE ROLE jens WITH PASSWORD 'owo';"
psql idlerpg -c "ALTER ROLE jens WITH LOGIN;"
psql idlerpg -c "GRANT ALL ON SCHEMA public TO jens;"
psql idlerpg < schema.sql
EOF
podman run --rm --pod idlerpg --name postgres -v start.sh:/docker-entrypoint-initdb.d/init.sh:z postgres:12-alpine
