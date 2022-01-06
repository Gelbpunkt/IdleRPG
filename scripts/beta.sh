#!/bin/bash
# Adrian's script for setting up a quick test deployment
podman pull docker://docker.io/library/redis:6-alpine
podman pull docker://docker.io/library/postgres:14-alpine
podman pull quay.io/gelbpunkt/stockfish:latest
podman pull docker://docker.io/twilightrs/http-proxy:latest
podman pull docker://docker.io/gelbpunkt/gateway-proxy:latest
podman pod create --name idlerpgbeta -p 5432:5432 -p 6379:6379

TOKEN=$(python3 -c 'from utils.config import ConfigLoader; config = ConfigLoader("config.toml"); print(config.bot.token)')

podman run --rm -it -d --pod idlerpgbeta --name http-proxy -e HOST=0.0.0.0 -e PORT=5113 -e DISCORD_TOKEN=$TOKEN http-proxy:latest

cat <<EOF > config.json
{
    "log_level": "info",
    "token": "$TOKEN",
    "intents": 13827,
    "port": 5112,
    "activity": {
        "type": 0,
        "name": "https://idlerpg.xyz"
    },
    "status": "idle",
    "backpressure": 100,
    "twilight_http_proxy": "127.0.0.1:5113",
    "shards": 5,
    "cache": {
        "channels": true,
        "presences": false,
        "emojis": false,
        "current_member": true,
        "members": false,
        "roles": true,
        "stage_instances": false,
        "stickers": false,
        "users": false,
        "voice_states": false
    }
}
EOF

podman run --rm -it -d --pod idlerpgbeta --name gateway-proxy -v $(pwd)/config.json:/config.json:Z gateway-proxy:latest

podman run --rm -it -d --pod idlerpgbeta --name redis-beta redis:6-alpine
cat <<EOF > start.sh
createdb idlerpg
psql idlerpg -c "CREATE ROLE jens WITH PASSWORD 'owo';"
psql idlerpg -c "ALTER ROLE jens WITH LOGIN;"
psql idlerpg -c "CREATE ROLE prest WITH PASSWORD 'placeholder';"
psql idlerpg -c "CREATE ROLE votehandler WITH PASSWORD 'placeholder';"

psql idlerpg <<'DONE'
$(<schema.sql)
DONE
EOF

chmod 777 start.sh
podman run --rm -it -d --pod idlerpgbeta --name postgres-beta -e POSTGRES_PASSWORD="test" -v $(pwd)/start.sh:/docker-entrypoint-initdb.d/init.sh:Z postgres:14-alpine -N 1000
sleep 15
rm start.sh
podman run --rm -it -d --pod idlerpgbeta --name stockfish-beta gelbpunkt/stockfish:latest
