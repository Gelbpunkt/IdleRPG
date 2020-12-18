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
from datetime import datetime, timedelta
from functools import partial

import discord

from aioscheduler.task import Task
from discord.ext import commands

from classes.converters import DateTimeScheduler, IntGreaterThan
from cogs.help import chunks
from utils.checks import has_char
from utils.i18n import _, current_locale, locale_doc
from utils.misc import nice_join


class Scheduling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _remind(self, user_id, channel_id, subject, diff, task_id):
        locale = await self.bot.get_cog("Locale").locale(user_id)
        current_locale.set(locale)
        await self.bot.pool.execute('DELETE FROM reminders WHERE "id"=$1;', task_id)
        await self.bot.http.send_message(
            channel_id,
            _("{user}, you wanted to be reminded about {subject} {diff} ago.").format(
                user=f"<@{user_id}>", subject=subject, diff=diff
            ),
        )

    async def _remind_adventure(self, user_id, channel_id, adventure, task_id):
        locale = await self.bot.get_cog("Locale").locale(user_id)
        current_locale.set(locale)
        await self.bot.pool.execute('DELETE FROM reminders WHERE "id"=$1;', task_id)
        await self.bot.http.send_message(
            channel_id,
            _("{user}, your adventure {num} has finished.").format(
                user=f"<@{user_id}>", num=adventure
            ),
        )

    async def create_reminder(
        self, subject, ctx, end, callback, type="reminder", conn=None
    ):
        if conn is None:
            conn = await self.bot.pool.acquire()
            local = True
        else:
            local = False

        task_id = await conn.fetchval(
            'INSERT INTO reminders ("user", content, channel, "start", "end", "type") VALUES'
            " ($1, $2, $3, $4, $5, $6) RETURNING id;",
            ctx.author.id,
            subject,
            ctx.channel.id,
            datetime.utcnow(),
            end,
            type,
        )
        task = self.bot.schedule_manager.schedule(callback(task_id=task_id), end)
        await conn.execute(
            'UPDATE reminders SET "internal_id"=$1 WHERE "id"=$2;', task.uuid, task_id
        )

        if local:
            await self.bot.pool.release(conn)

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
            partial(self._remind, ctx.author.id, ctx.channel.id, subject, diff),
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
    async def cancel(self, ctx, *ids: IntGreaterThan(0)):
        _(
            """`[ids...]` - A list of reminder IDs, separated by space

            Cancels running reminders using their IDs.

            To find a reminder's ID, use `{prefix}reminder list`."""
        )
        reminders = await self.bot.pool.fetch(
            'SELECT id, internal_id FROM reminders WHERE "id"=ANY($1) AND "user"=$2 AND "type"=$3;',
            ids,
            ctx.author.id,
            "reminder",
        )
        if not reminders:
            return await ctx.send(_("None of these reminder IDs belong to you."))
        for reminder in reminders:
            fake_task = Task(0, reminder["internal_id"], 0)
            self.bot.schedule_manager.cancel(fake_task)
        await self.bot.pool.execute(
            'DELETE FROM reminders WHERE "id"=ANY($1);',
            ids := [reminder["id"] for reminder in reminders],
        )
        await ctx.send(
            _("Removed the following reminders: `{ids}`").format(ids=nice_join(ids))
        )

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
