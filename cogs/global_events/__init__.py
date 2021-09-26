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
import asyncio
import datetime

import discord

from discord.ext import commands

from utils.loops import queue_manager


class GlobalEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.topgg_auth_headers = {"Authorization": bot.config.statistics.topggtoken}
        self.bfd_auth_headers = {"Authorization": bot.config.statistics.bfdtoken}
        self.dbl_auth_headers = {"Authorization": bot.config.statistics.dbltoken}
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
            self.bot.loop.create_task(queue_manager(self.bot, self.bot.queue))
            self.stats_updates = self.bot.loop.create_task(self.stats_updater())
            await self.bot.is_owner(self.bot.user)  # force getting the owners
            await self.reschedule_reminders()
            self.bot.schedule_manager.start()
        else:
            self.bot.logger.warning("[INFO] Discord fired on_ready...")

    @commands.Cog.listener()
    async def on_raw_member_update(self, data):
        user = data["user"]
        user_id = int(user["id"])

        # We can't know which roles they had before so just wipe the donator cache
        if int(data["guild_id"]) == self.bot.config.game.support_server_id:
            await self.bot.clear_donator_cache(user_id)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        if self.bot.config.bot.is_beta:
            return
        if self.bot.config.statistics.join_channel:
            await self.bot.http.send_message(
                self.bot.config.statistics.join_channel, f"Bye bye **{guild.name}**!"
            )

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        if guild.id in self.bot.config.game.banned_guilds:
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
                f" `{self.bot.config.bot.global_prefix}create`.\n\nA tutorial can be found"
                f" on **{self.bot.BASE_URL}/tutorial**.\n\nDon't like my prefix?"
                f" `{self.bot.config.bot.global_prefix}settings prefix` changes it.\n\nNot"
                f" English? `{self.bot.config.bot.global_prefix}language` and"
                f" `{self.bot.config.bot.global_prefix}language set` may include"
                " yours!\n\nHave fun! :wink:"
            ),
        )

        embed.set_image(url=f"{self.bot.BASE_URL}/IdleRPG.png")
        embed.set_footer(
            text=f"IdleRPG Version {self.bot.version}",
            icon_url=self.bot.user.display_avatar.url,
        )
        channels = list(
            filter(
                lambda x: x.permissions_for(guild.me).send_messages, guild.text_channels
            )
        )
        if channels:
            await channels[0].send(embed=embed)
        if self.bot.config.bot.is_beta:
            return
        if self.bot.config.statistics.join_channel:
            await self.bot.http.send_message(
                self.bot.config.statistics.join_channel,
                f"Joined a new server! **{guild.name}** with **{guild.member_count}**"
                " members!",
            )

    async def stats_updater(self):
        await self.bot.wait_until_ready()
        if (
            self.bot.shard_count - 1 not in self.bot.shards.keys()
        ) or self.bot.config.bot.is_beta:
            return
        while not self.bot.is_closed():
            await self.bot.session.post(
                f"https://top.gg/api/bots/{self.bot.user.id}/stats",
                data=await self.get_topgg_payload(),
                headers=self.topgg_auth_headers,
            )
            await self.bot.session.post(
                f"https://botsfordiscord.com/api/bot/{self.bot.user.id}",
                data=await self.get_bfd_payload(),
                headers=self.bfd_auth_headers,
            )
            await self.bot.session.post(
                f"https://discordbotlist.com/api/v1/bots/{self.bot.user.id}/stats",
                data=await self.get_dbl_payload(),
                headers=self.dbl_auth_headers,
            )
            await asyncio.sleep(60 * 10)  # update once every 10 minutes

    async def get_topgg_payload(self):
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

    async def get_dbl_payload(self):
        return {
            "guilds": sum(
                await self.bot.cogs["Sharding"].handler(
                    "guild_count", self.bot.shard_count
                )
            )
        }

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
                    if reminder["type"] == "reminder":
                        task = self.bot.schedule_manager.schedule(
                            self.bot.cogs["Scheduling"]._remind(
                                reminder["user"],
                                reminder["channel"],
                                reminder["content"],
                                str(reminder["end"] - reminder["start"]).split(".")[0],
                                reminder["id"],
                            ),
                            reminder["end"],
                        )
                    elif reminder["type"] == "adventure":
                        task = self.bot.schedule_manager.schedule(
                            self.bot.cogs["Scheduling"]._remind_adventure(
                                reminder["user"],
                                reminder["channel"],
                                reminder["content"],
                                reminder["id"],
                            ),
                            reminder["end"],
                        )
                    else:
                        continue
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
