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
from __future__ import annotations

import asyncio

from datetime import datetime, timedelta

import asyncpg
import discord

from discord.ext import commands

from classes.bot import Bot
from classes.context import Context
from classes.converters import DateTimeScheduler, IntGreaterThan
from cogs.help import chunks
from utils.checks import has_char
from utils.i18n import _, current_locale, locale_doc


class Timer:
    __slots__ = ("id", "user", "content", "channel", "type", "start", "end")

    def __init__(self, *, record):
        self.id: int = record["id"]
        self.user: int = record["user"]
        self.content: str = record["content"]
        self.channel: int = record["channel"]
        self.type: str = record["type"]
        self.start: datetime = record["start"]
        self.end: datetime = record["end"]

    def to_dict(self) -> dict[str, int | str | datetime]:
        return {
            "id": self.id,
            "user": self.user,
            "content": self.content,
            "channel": self.channel,
            "type": self.type,
            "start": self.start,
            "end": self.end,
        }

    @classmethod
    def temporary(cls, *, user, content, channel, type, start, end):
        pseudo = {
            "id": None,
            "user": user,
            "content": content,
            "channel": channel,
            "type": type,
            "start": start,
            "end": end,
        }
        return cls(record=pseudo)

    def __eq__(self, other: Timer) -> bool:
        try:
            return self.id == other.id
        except AttributeError:
            return False

    def __hash__(self) -> int:
        return hash(self.id)

    @property
    def human_delta(self) -> str:
        return f"{self.end - self.start}".split(".")[0]


class Scheduling(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._handles = 0 in self.bot.shard_ids

        self._have_data = asyncio.Event()
        self._current_timer = None

        if self._handles:
            self._task = asyncio.create_task(self.dispatch_timers())
        else:
            self._task = None

    async def get_active_timer(self, *, connection=None, days=7) -> Timer | None:
        query = 'SELECT * FROM reminders WHERE "end" < (CURRENT_DATE + $1::interval) ORDER BY "end" LIMIT 1;'
        con = connection or self.bot.pool

        record = await con.fetchrow(query, timedelta(days=days))
        return Timer(record=record) if record else None

    async def wait_for_active_timers(self, *, conn=None, days=7) -> Timer:
        async with self.bot.pool.acquire() as conn:
            timer = await self.get_active_timer(connection=conn, days=days)
            if timer is not None:
                self._have_data.set()
                return timer

            self._have_data.clear()
            self._current_timer = None
            await self._have_data.wait()
            return await self.get_active_timer(connection=conn, days=days)

    async def dispatch_timers(self):
        try:
            while not self.bot.is_closed():
                timer = self._current_timer = await self.wait_for_active_timers(days=40)
                now = datetime.utcnow()

                if timer.end >= now:
                    to_sleep = (timer.end - now).total_seconds()
                    await asyncio.sleep(to_sleep)

                try:
                    await self._remind(timer)
                except (discord.NotFound, discord.Forbidden):
                    pass
        except asyncio.CancelledError:
            raise
        except (OSError, discord.ConnectionClosed, asyncpg.PostgresConnectionError):
            self.restart()

    @commands.Cog.listener()
    async def on_timer_add(self, timer: Timer) -> None:
        if not self._handles:
            return

        if (timer.end - timer.start).total_seconds() <= (86400 * 40):  # 40 days
            self._have_data.set()
        if self._current_timer and timer.end < self._current_timer.end:
            self.restart()

    @commands.Cog.listener()
    async def on_timer_remove(self, timer_id: int) -> None:
        if not self._handles:
            return

        if self._current_timer and self._current_timer.id == timer_id:
            self.restart()

    async def add_timer(self, timer: Timer) -> None:
        await self.bot.cogs["Sharding"].handler("add_timer", 0, args=timer.to_dict())

    async def remove_timer(self, timer_id: int) -> None:
        await self.bot.cogs["Sharding"].handler(
            "remove_timer", 0, args={"timer_id": timer_id}
        )

    def restart(self):
        if self._task:
            self._task.cancel()
            self._task = asyncio.create_task(self.dispatch_timers())

    async def short_timer_optimisation(self, seconds: int, timer: Timer) -> None:
        await asyncio.sleep(seconds)
        await self._remind(timer)

    async def _remind(self, timer: Timer):
        locale = await self.bot.get_cog("Locale").locale(timer.user)
        current_locale.set(locale)
        await self.bot.pool.execute('DELETE FROM reminders WHERE "id"=$1;', timer.id)

        if timer.type == "reminder":
            await self.bot.http.send_message(
                timer.channel,
                _(
                    "{user}, you wanted to be reminded about {subject} {diff} ago."
                ).format(
                    user=f"<@{timer.user}>",
                    subject=timer.content,
                    diff=timer.human_delta,
                ),
            )
        else:
            await self.bot.http.send_message(
                timer.channel,
                _("{user}, your adventure {num} has finished.").format(
                    user=f"<@{timer.user}>", num=timer.content
                ),
            )

    async def create_reminder(
        self,
        content: str,
        ctx: Context,
        end: datetime,
        type: str = "reminder",
        conn=None,
    ):
        conn = conn or self.bot.pool

        now = datetime.utcnow()

        timer = Timer.temporary(
            user=ctx.author.id,
            content=content,
            channel=ctx.channel.id,
            type=type,
            start=now,
            end=end,
        )
        delta = (end - now).total_seconds()

        if delta <= 60:
            # a shortcut for small timers
            asyncio.create_task(self.short_timer_optimisation(delta, timer))
            return timer

        id = await conn.fetchval(
            'INSERT INTO reminders ("user", "content", "channel", "start", "end", "type") VALUES'
            ' ($1, $2, $3, $4, $5, $6) RETURNING "id";',
            ctx.author.id,
            content,
            ctx.channel.id,
            now,
            end,
            type,
        )
        timer.id = id

        await self.add_timer(timer)

        return timer

    @commands.group(
        aliases=["r", "reminder", "remindme"],
        invoke_without_command=True,
        brief=_("Reminds you about something"),
    )
    @locale_doc
    async def remind(self, ctx, *, when_and_what: DateTimeScheduler):
        _(
            """<when_and_what> - The reminder subject and time, see below for more info.

            Remind yourself about something you should do in the future.

            `<when_and_what>` can be you reminder and time, several formats are accepted:
              - {prefix}remind 12h vote on top.gg
              - {prefix}remind 12am use {prefix}daily
              - {prefix}remind next monday check out the new God luck

            Please keep it in order of {prefix}remind time subject to make sure this works properly"""
        )
        time, subject = when_and_what
        if len(subject) > 100:
            return await ctx.send(_("Please choose a shorter reminder text."))
        diff = str(time - datetime.utcnow()).split(".")[0]
        await self.create_reminder(
            subject,
            ctx,
            time,
            "reminder",
        )
        await ctx.send(
            _("{user}, reminder set for {subject} in {time}.").format(
                user=ctx.author.mention, subject=subject, time=diff
            )
        )

    @remind.command(brief=_("Shows a list of your running reminders."))
    @locale_doc
    async def list(self, ctx):
        _(
            """Shows you a list of your currently running reminders

            Reminders can be cancelled using `{prefix}reminder cancel <id>`."""
        )
        reminders = await self.bot.pool.fetch(
            'SELECT * FROM reminders WHERE "user"=$1 AND "type"=$2 ORDER BY "end" ASC;',
            ctx.author.id,
            "reminder",
        )
        if not reminders:
            return await ctx.send(_("No running reminders."))
        now = datetime.utcnow()
        reminder_chunks = chunks(reminders, 5)
        embeds = []
        for chunk in reminder_chunks:
            embed = discord.Embed(
                title=_("{user}'s reminders").format(user=ctx.disp),
                color=self.bot.config.game.primary_colour,
            )
            for reminder in chunk:
                time = reminder["end"] - now
                time -= timedelta(microseconds=time.microseconds)
                embed.add_field(
                    name=str(reminder["id"]),
                    value=f"{reminder['content']} - {time}",
                    inline=False,
                )
            embeds.append(embed)
        await self.bot.paginator.Paginator(extras=embeds).paginate(ctx)

    @remind.command(
        aliases=["remove", "rm", "delete", "del"], brief=_("Remove running reminders")
    )
    @locale_doc
    async def cancel(self, ctx, id: IntGreaterThan(0)):
        _(
            """`[id]` - A reminder ID

            Cancels a running reminder using its ID.

            To find a reminder's ID, use `{prefix}reminder list`."""
        )
        status = await self.bot.pool.execute(
            'DELETE FROM reminders WHERE "id"=$1 AND "user"=$2 AND "type"=$3;',
            id,
            ctx.author.id,
            "reminder",
        )

        if status == "DELETE 0":
            return await ctx.send(_("None of these reminder IDs belong to you."))

        await self.remove_timer(id)

        await ctx.send(_("Successfully cancelled the reminder."))

    @commands.command(brief=_("Shows a list of your running reminders."))
    @locale_doc
    async def reminders(self, ctx):
        _(
            """Shows you a list of your currently running reminders

            Reminders can be cancelled using `{prefix}reminder cancel <id>`.

            (serves as an alias for `{prefix}reminder list`)"""
        )
        await ctx.invoke(self.bot.get_command("reminder list"))

    @has_char()
    @commands.command(brief=_("Enable or disable automatic adventure reminders"))
    @locale_doc
    async def adventureremind(self, ctx):
        _("""Toggles automatic adventure reminders when you finish an adventure.""")
        current_settings = await self.bot.pool.fetchval(
            'SELECT "adventure_reminder" FROM user_settings WHERE "user"=$1;',
            ctx.author.id,
        )
        if current_settings is None:
            await self.bot.pool.execute(
                'INSERT INTO user_settings ("user", "adventure_reminder") VALUES ($1, $2);',
                ctx.author.id,
                True,
            )
            new = True
        else:
            new = await self.bot.pool.fetchval(
                'UPDATE user_settings SET "adventure_reminder"=NOT "adventure_reminder" WHERE "user"=$1 RETURNING "adventure_reminder";',
                ctx.author.id,
            )
        if new:
            await ctx.send(_("Successfully opted in to automatic adventure reminders."))
        else:
            await ctx.send(_("Opted out of automatic adventure reminders."))


def setup(bot):
    bot.add_cog(Scheduling(bot))
