"""
The IdleRPG Discord Bot
Copyright (C) 2018-2021 Diniboy and Gelbpunkt

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import logging
import sys

import orjson

# Ugly patch to use orjson globally
sys.modules["json"] = orjson

import asyncio
import os

import discord

from classes.bot import Bot
from classes.logger import file_handler, stream

if len(sys.argv) != 6:
    print(
        f"Usage: {sys.executable} idlerpg.py [shard_ids] [shard_count] [cluster_id]"
        " [cluster_count] [cluster_name]"
    )
    sys.exit(1)

if sys.platform == "linux":  # uvloop requires linux
    import uvloop

    uvloop.install()

# Set the timezone to UTC
os.environ["TZ"] = "UTC"

# Sharding stuff
shard_ids = orjson.loads(sys.argv[1])
shard_count = int(sys.argv[2])
cluster_id = int(sys.argv[3])
cluster_count = int(sys.argv[4])
cluster_name = sys.argv[5]

# Configure intents
intents = discord.Intents.none()
intents.guilds = True
intents.members = True
intents.messages = True
intents.reactions = True


async def start():
    bot = Bot(
        case_insensitive=True,
        status=discord.Status.idle,
        description="The one and only IdleRPG bot for discord",
        shard_ids=shard_ids,
        shard_count=shard_count,
        cluster_id=cluster_id,
        cluster_count=cluster_count,
        cluster_name=cluster_name,
        intents=intents,
        chunk_guilds_at_startup=False,  # chunking is nerfed
        guild_ready_timeout=30 * (len(shard_ids) // 4),  # fix on_ready firing too early
        max_messages=10000,  # We have a ton of incoming messages, higher cache means commands like activeadventure
        # or guild adventure joining will stay in cache so reactions are counted
    )
    await bot.connect_all()


if __name__ == "__main__":
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    log.addHandler(stream)
    log.addHandler(file_handler(cluster_id))

    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        pass
