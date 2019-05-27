"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import asyncio

import discord
from discord.ext import commands

from utils import i18n
from utils.loops import queue_manager


class GlobalEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.auth_headers = {
            "Authorization": bot.config.dbltoken
        }  # needed for DBL requests
        self.auth_headers2 = {"Authorization": bot.config.bfdtoken}
        self.bot_owner = None
        self.stats_updates = bot.loop.create_task(
            self.stats_updater()
        )  # Initiate the stats updates and save it for the further close

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.author.id in self.bot.bans:
            return
        locale = await self.bot.get_cog("Locale").locale(message)
        i18n.current_locale.set(locale)

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
        announce_channel = self.bot.get_channel(self.bot.config.join_channel)
        await announce_channel.send(f"Bye bye **{guild.name}**!")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        if not self.bot_owner:  # just for performance reasons (+1 API call)
            self.bot_owner = await self.bot.fetch_user(self.bot.owner_id)

        embed = discord.Embed(
            title="Thanks for adding me!",
            colour=0xEEC340,
            description=f"Hi! I am **IdleRPG**, a Discord Bot by `{self.bot_owner}`.\nI simulate"
            f" a whole Roleplay with everything it needs!\n\nVisit **{self.bot.BASE_URL}** for a documentation on all my commands. :innocent:\nTo get started, type "
            f"`{self.bot.config.global_prefix}create`.\n\nA tutorial can be found on **{self.bot.BASE_URL}/tutorial**.\n\nDon't like my prefix? `{self.bot.config.global_prefix}"
            "settings prefix` changes it.\n\nHave fun! :wink:",
        )

        embed.set_image(url=f"{self.bot.BASE_URL}/IdleRPG.png")
        embed.set_footer(
            text=f"IdleRPG Version {self.bot.version}",
            icon_url=self.bot.user.avatar_url,
        )
        allchannels = guild.text_channels
        for channel in allchannels:
            if (
                channel.permissions_for(guild.me).send_messages
                and channel.permissions_for(guild.me).read_messages
            ):
                await channel.send(embed=embed)
                break
        if self.bot.config.is_beta:
            return
        announce_channel = self.bot.get_channel(self.bot.config.join_channel)
        await announce_channel.send(
            f"Joined a new server! **{guild.name}** with **{len(guild.members)}** members!"
        )

    async def status_updater(self):
        await self.bot.wait_until_ready()
        await self.bot.change_presence(
            activity=discord.Game(name=self.bot.BASE_URL), status=discord.Status.idle
        )

    async def stats_updater(self):
        if (
            self.bot.shard_count - 1 not in self.bot.shards.keys()
        ) or self.bot.config.is_beta:
            return
        await self.bot.wait_until_ready()
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
