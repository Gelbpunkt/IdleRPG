"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

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
import asyncio

import discord
from discord.ext import commands

from utils.loops import queue_manager


class GlobalEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.auth_headers = {
            "Authorization": bot.config.dbltoken
        }  # needed for DBL requests
        self.auth_headers2 = {"Authorization": bot.config.bfdtoken}
        self.stats_updates = bot.loop.create_task(
            self.stats_updater()
        )  # Initiate the stats updates and save it for the further close

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Logged in as {self.bot.user.name} (ID: {self.bot.user.id})")
        print("--------")
        print(f"Using discord.py {discord.__version__}")
        print("--------")
        print(f"You are running IdleRPG Bot {self.bot.version}")
        owner = (await self.bot.application_info()).owner
        self.bot.owner_id = owner.id
        print(f"Created by {owner}")
        await self.load_settings()
        self.bot.loop.create_task(queue_manager(self.bot, self.bot.queue))
        await self.status_updater()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        if self.bot.config.is_beta:
            return
        await self.bot.http.send_message(
            self.bot.config.join_channel, f"Bye bye **{guild.name}**!"
        )

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        embed = discord.Embed(
            title="Thanks for adding me!",
            colour=0xEEC340,
            description=f"Hi! I am **IdleRPG**, a Discord Bot by `Adrian#1337`.\nI simulate"
            f" a whole Roleplay with everything it needs!\n\nVisit **{self.bot.BASE_URL}** for a documentation on all my commands. :innocent:\nTo get started, type "
            f"`{self.bot.config.global_prefix}create`.\n\nA tutorial can be found on **{self.bot.BASE_URL}/tutorial**.\n\nDon't like my prefix? `{self.bot.config.global_prefix}"
            "settings prefix` changes it.\n\n"
            f"Not English? `{self.bot.config.global_prefix}language` and `{self.bot.config.global_prefix}language set` may include yours!\n\n"
            "Have fun! :wink:",
        )

        embed.set_image(url=f"{self.bot.BASE_URL}/IdleRPG.png")
        embed.set_footer(
            text=f"IdleRPG Version {self.bot.version}",
            icon_url=self.bot.user.avatar_url,
        )
        channels = list(
            filter(
                lambda x: x.permissions_for(guild.me).send_messages, guild.text_channels
            )
        )
        if channels:
            await channels[0].send(embed=embed)
        if self.bot.config.is_beta:
            return
        await self.bot.http.send_message(
            self.bot.config.join_channel,
            f"Joined a new server! **{guild.name}** with **{guild.member_count}** members!",
        )

    async def status_updater(self):
        await self.bot.wait_until_ready()
        await self.bot.change_presence(
            activity=discord.Game(
                name=f"IdleRPG v{self.bot.version}"
                if self.bot.config.is_beta
                else self.bot.BASE_URL
            ),
            status=discord.Status.idle,
        )

    async def stats_updater(self):
        await self.bot.wait_until_ready()
        if (
            self.bot.shard_count - 1 not in self.bot.shards.keys()
        ) or self.bot.config.is_beta:
            return
        while True:
            await self.bot.session.post(
                f"https://discordbots.org/api/bots/{self.bot.user.id}/stats",
                data=await self.get_dbl_payload(),
                headers=self.auth_headers,
            )
            await self.bot.session.post(
                f"https://botsfordiscord.com/api/bot/{self.bot.user.id}",
                data=await self.get_bfd_payload(),
                headers=self.auth_headers2,
            )
            await asyncio.sleep(120)

    async def load_settings(self):
        if self.bot.config.is_beta:
            return  # we're using the default prefix in beta
        ids = [g.id for g in self.bot.guilds]
        prefixes = await self.bot.pool.fetch("SELECT id, prefix FROM server;")
        for row in prefixes:
            if row["id"] in ids:
                self.bot.all_prefixes[row["id"]] = row["prefix"]
        self.bot.command_prefix = self.bot._get_prefix

    async def get_dbl_payload(self):
        return {
            "server_count": sum(
                await self.bot.cogs["Sharding"].handler(
                    "guild_count", self.bot.shard_count
                )
            ),
            "shard_count": self.bot.shard_count,
        }

    async def get_bfd_payload(self):
        return {
            "server_count": sum(
                await self.bot.cogs["Sharding"].handler(
                    "guild_count", self.bot.shard_count
                )
            )
        }

    def cog_unload(self):
        self.stats_updates.cancel()


def setup(bot):
    bot.add_cog(GlobalEvents(bot))
