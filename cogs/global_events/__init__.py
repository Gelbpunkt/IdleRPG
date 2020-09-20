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
import datetime

import discord

from discord.ext import commands

from classes.converters import MemberConverter, User
from utils import i18n
from utils.i18n import _
from utils.loops import queue_manager


class GlobalEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.auth_headers = {
            "Authorization": bot.config.dbltoken
        }  # needed for DBL requests
        self.auth_headers2 = {"Authorization": bot.config.bfdtoken}
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
            self.stats_updates = self.bot.loop.create_task(self.stats_updater())
            await self.bot.is_owner(self.bot.user)  # force getting the owners
            await self.reschedule_reminders()
            self.bot.schedule_manager.start()
        else:
            self.bot.logger.warning("[INFO] Discord fired on_ready...")

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        self.bot.logger.info(f"User updated fired for {after}")
        MemberConverter.convert.invalidate_value(lambda member: member.id == after.id)
        User.convert.invalidate_value(lambda user: user.id == after.id)
        await self.bot.clear_donator_cache(after.id)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        if self.bot.config.is_beta:
            return
        await self.bot.http.send_message(
            self.bot.config.join_channel, f"Bye bye **{guild.name}**!"
        )

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        if guild.id in self.bot.config.banned_guilds:
            await guild.leave()
            return
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

    async def stats_updater(self):
        await self.bot.wait_until_ready()
        if (
            self.bot.shard_count - 1 not in self.bot.shards.keys()
        ) or self.bot.config.is_beta:
            return
        while not self.bot.is_closed():
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
        ids = [g.id for g in self.bot.guilds]
        prefixes = await self.bot.pool.fetch(
            'SELECT id, prefix FROM server WHERE "id"=ANY($1);', ids
        )
        for row in prefixes:
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

    async def send_reminder(
        self,
        reminder_id: int,
        channel_id: int,
        user_id: int,
        reminder_text: str,
        time_diff: str,
    ):
        await self.bot.pool.execute('DELETE FROM reminders WHERE "id"=$1;', reminder_id)
        locale = await self.bot.get_cog("Locale").locale(user_id)
        i18n.current_locale.set(locale)
        await self.bot.http.send_message(
            channel_id,
            _("{user}, you wanted to be reminded about {subject} {diff} ago.").format(
                user=f"<@{user_id}>",
                subject=reminder_text,
                diff=time_diff,
            ),
        )

    async def reschedule_reminders(self):
        valid_channels = [channel.id for channel in self.bot.get_all_channels()]
        all_reminders = await self.bot.pool.fetch("SELECT * FROM reminders;")
        now = datetime.datetime.utcnow()
        invalid_reminders = []
        new_reminders = {}
        for reminder in all_reminders:
            try:
                if reminder["end"] < now:
                    invalid_reminders.append(reminder["id"])
                elif reminder["channel"] not in valid_channels:
                    pass  # don't schedule channels that the bot won't be able to send to
                else:
                    task = self.bot.schedule_manager.schedule(
                        self.send_reminder(
                            reminder["id"],
                            reminder["channel"],
                            reminder["user"],
                            reminder["content"],
                            str(reminder["end"] - reminder["start"]).split(".")[0],
                        ),
                        reminder["end"],
                    )
                    new_reminders.update({reminder["id"]: task.uuid})
            except (KeyError, ValueError, TypeError) as e:
                self.bot.logger.warning(f"{type(e).__name__}: {e}")
                pass
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'DELETE FROM reminders WHERE "id"=ANY($1);', invalid_reminders
            )
            await conn.executemany(
                'UPDATE reminders SET "internal_id"=$2 WHERE "id"=$1',
                new_reminders.items(),
            )

    def cog_unload(self):
        self.stats_updates.cancel()


def setup(bot):
    bot.add_cog(GlobalEvents(bot))
