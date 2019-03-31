"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""


import discord
import datetime

from discord.ext import commands


class Bot(commands.AutoShardedBot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.launch_time = (
            datetime.datetime.now()
        )  # we assume the bot is created for use right now

        self.mention_formatter = commands.clean_content()

    @property
    def disp(self):
        return self.author.display_name

    @property
    def uptime(self):
        return datetime.datetime.now() - self.launch_time

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

    async def send_message(
        self,
        target,
        content=None,
        *,
        escape_mass_mentions=True,
        escape_mentions=False,
        **fields,
    ):
        if escape_mass_mentions:
            content = content.replace("@here", "@\u200bhere").replace(
                "@everyone", "@\u200beveryone"
            )
        if escape_mentions:
            # content = await self.mention_formatter.convert(self, content)
            pass

        await super(Bot, self).send_message(target, content=content, **fields)
