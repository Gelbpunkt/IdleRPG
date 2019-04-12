"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import aiohttp
import aioredis
import asyncio
import asyncpg
import config
import datetime
import discord
import os
import sys
import traceback

from discord.ext import commands
from classes.context import Context
from utils import paginator


class Bot(commands.AutoShardedBot):
    def __init__(self, **kwargs):
        super().__init__(command_prefix=self._get_prefix, **kwargs)

        # setup stuff
        self.queue = asyncio.Queue(loop=self.loop)  # global queue for ordered tasks
        self.config = config
        self.version = config.version
        self.paginator = paginator
        self.BASE_URL = config.base_url
        self.bans = config.bans
        self.remove_command("help")
        self.linecount = 0
        self.make_linecount()
        self.all_prefixes = {}

        # global cooldown
        self.add_check(self.global_cooldown, call_once=True)

        self.launch_time = (
            datetime.datetime.now()
        )  # we assume the bot is created for use right now

    async def global_cooldown(self, ctx: commands.Context):
        bucket = self.config.cooldown.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()

        if retry_after:
            raise commands.CommandOnCooldown(bucket, retry_after)
        else:
            return True

    def make_linecount(self):
        for root, dirs, files in os.walk(os.getcwd()):
            for file_ in files:
                if file_.endswith(".py"):
                    with open(f"{root}/{file_}") as f:
                        self.linecount += len(f.readlines())

    async def connect_all(self):
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.redis = await aioredis.create_pool(
            "redis://localhost", minsize=5, maxsize=10, loop=self.loop
        )
        self.pool = await asyncpg.create_pool(**self.config.database, max_size=10)

        # ToDo: Move this to on_ready?
        async with self.pool.acquire() as conn:
            prefixes = await conn.fetch("SELECT id, prefix FROM server;")
            for row in prefixes:
                self.all_prefixes[row["id"]] = row["prefix"]

        for extension in self.config.initial_extensions:
            try:
                self.load_extension(extension)
            except Exception:
                print(f"Failed to load extension {extension}.", file=sys.stderr)
                traceback.print_exc()
        await self.start(self.config.token)

    @property
    def uptime(self):
        return datetime.datetime.now() - self.launch_time

    async def get_context(self, message, *, cls=None):
        return await super().get_context(message, cls=Context)

    def _get_prefix(self, message):
        if not message.guild or self.config.is_beta:
            return (
                self.config.global_prefix
            )  # Use global prefix in DMs and if the bot is beta
        try:
            return commands.when_mentioned_or(self.all_prefixes[message.guild.id])(
                self, message
            )
        except KeyError:
            return commands.when_mentioned_or(self.config.global_prefix)(self, message)
        return self.config.global_prefix

    async def get_user_global(self, user_id: int):
        user = self.get_user(user_id)
        if user:
            return user
        data = await self.cogs["Sharding"].handler("get_user", 1, {"user_id": user_id})
        if not data:
            return None
        data = data[0]
        data["username"] = data["name"]
        user = discord.User(state=self._connection, data=data)
        self.users.append(user)
        return user

    async def reset_cooldown(self, ctx):
        await self.redis.execute(
            "DEL", f"cd:{ctx.author.id}:{ctx.command.qualified_name}"
        )
