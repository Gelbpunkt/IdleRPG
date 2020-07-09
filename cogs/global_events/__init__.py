"""
The IdleRPG Discord Bot
Copyright (C) 2018-2020 Diniboy and Gelbpunkt

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

from discord import utils
from discord.activity import create_activity
from discord.ext import commands

from classes.converters import MemberConverter, User
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
        self.is_first_ready = True

    @commands.Cog.listener()
    async def on_ready(self):
        if self.is_first_ready:
            self.is_first_ready = False
            text1 = f"Logged in as {self.bot.user.name} (ID: {self.bot.user.id})"
            text2 = f"Using discord.py {discord.__version__}"
            text3 = f"You are running IdleRPG Bot {self.bot.version}"
            text4 = "Created by Adrian#1337 and Mary Johanna#0420"
            max_string = max([len(i) for i in (text1, text2, text3, text4)])
            self.bot.logger.info(f"┌─{'─' * max_string}─┐")
            self.bot.logger.info(f"│ {text1.center(max_string, ' ')} │")
            self.bot.logger.info(f"│ {' ' * max_string} │")
            self.bot.logger.info(f"│ {text2.center(max_string, ' ')} │")
            self.bot.logger.info(f"│ {' ' * max_string} │")
            self.bot.logger.info(f"│ {text3.center(max_string, ' ')} │")
            self.bot.logger.info(f"│ {' ' * max_string} │")
            self.bot.logger.info(f"│ {text4.center(max_string, ' ')} │")
            self.bot.logger.info(f"└─{'─' * max_string}─┘")
            await self.load_settings()
            self.bot.loop.create_task(queue_manager(self.bot, self.bot.queue))
            await self.bot.is_owner(self.bot.user)  # force getting the owners
            await self.status_updater()
        else:
            self.bot.logger.warning("[INFO] Discord fired on_ready...")

    def parse_member_update(self, data):
        """Replacement for hacky https://github.com/Rapptz/discord.py/blob/master/discord/state.py#L547"""
        guild_id = utils._get_as_snowflake(data, "guild_id")
        guild = self.bot._connection._get_guild(guild_id)
        if guild is None:
            print("NO GUILD")
            return

        user = data["user"]
        member_id = int(user["id"])
        member = guild.get_member(member_id)
        if member is None:
            if "username" not in user:
                # sometimes we receive 'incomplete' member data post-removal.
                # skip these useless cases.
                print("NO USERNAME")
                return

            # https://github.com/Rapptz/discord.py/blob/master/discord/member.py#L214
            clone = discord.Member(data=data, guild=guild, state=self.bot._connection)
            to_return = discord.Member(
                data=data, guild=guild, state=self.bot._connection
            )
            to_return._client_status = {
                key: value for key, value in data.get("client_status", {}).items()
            }
            # to_return._client_status[None] = data['status']
            to_return._client_status[None] = "online"
            member, old_member = to_return, clone

            print("ADDED MEMBER TO GUILD")
            guild._add_member(member)
        else:
            old_member = discord.Member._copy(member)

            # https://github.com/Rapptz/discord.py/blob/master/discord/member.py#L260
            member.activities = tuple(map(create_activity, data.get("activities", [])))
            member._client_status = {
                key: value for key, value in data.get("client_status", {}).items()
            }
            # member._client_status[None] = data['status']
            member._client_status[None] = "online"

            if len(user) > 1:
                u = member._user
                original = (u.name, u.avatar, u.discriminator)
                # These keys seem to always be available
                modified = (user["username"], user["avatar"], user["discriminator"])
                if original != modified:
                    to_return = discord.User._copy(member._user)
                    u.name, u.avatar, u.discriminator = modified
                    # Signal to dispatch on_user_update
                    user_update = to_return, u
                else:
                    user_update = False
            else:
                user_update = False
            if user_update:
                self.bot._connection.dispatch(
                    "user_update", user_update[0], user_update[1]
                )

            print("COPIED MEMBER")

        self.bot._connection.dispatch("member_update", old_member, member)

    @commands.Cog.listener()
    async def on_socket_response(self, data):
        if data["t"] != "GUILD_MEMBER_UPDATE":
            return

        user = data["d"]["user"]
        user_id = int(user["id"])

        self.parse_member_update(data["d"])
        # Wipe the cache for the converters
        MemberConverter.convert.invalidate_value(lambda member: member.id == user_id)
        User.convert.invalidate_value(lambda user: user.id == user_id)

        # If they were a donator, wipe that cache as well
        roles = [int(i) for i in data["d"]["roles"]]
        if int(data["d"]["guild_id"]) == self.bot.config.support_server_id and any(
            id_ in roles for id_ in self.bot.config.donator_roles
        ):
            await self.bot.clear_donator_cache(user_id)

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
            description=(
                "Hi! I am **IdleRPG**, a Discord Bot by `Adrian#1337`.\nI simulate a"
                " whole Roleplay with everything it needs!\n\nVisit"
                f" **{self.bot.BASE_URL}** for a documentation on all my commands."
                " :innocent:\nTo get started, type"
                f" `{self.bot.config.global_prefix}create`.\n\nA tutorial can be found"
                f" on **{self.bot.BASE_URL}/tutorial**.\n\nDon't like my prefix?"
                f" `{self.bot.config.global_prefix}settings prefix` changes it.\n\nNot"
                f" English? `{self.bot.config.global_prefix}language` and"
                f" `{self.bot.config.global_prefix}language set` may include"
                " yours!\n\nHave fun! :wink:"
            ),
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
            f"Joined a new server! **{guild.name}** with **{guild.member_count}**"
            " members!",
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
                f"https://top.gg/api/bots/{self.bot.user.id}/stats",
                data=await self.get_dbl_payload(),
                headers=self.auth_headers,
            )
            await self.bot.session.post(
                f"https://botsfordiscord.com/api/bot/{self.bot.user.id}",
                data=await self.get_bfd_payload(),
                headers=self.auth_headers2,
            )
            await asyncio.sleep(60 * 10)  # update once every 10 minutes

    async def load_settings(self):
        if self.bot.config.is_beta:
            self.bot.command_prefix = commands.when_mentioned_or(
                self.bot.config.global_prefix
            )
            return  # we're using the default prefix in beta
        # ids = [g.id for g in self.bot.guilds]
        prefixes = await self.bot.pool.fetch("SELECT id, prefix FROM server;")
        for row in prefixes:
            # Temporary intents fix
            # if row["id"] in ids:
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
