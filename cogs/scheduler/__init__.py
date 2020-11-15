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

import discord

from aioscheduler.task import Task
from discord.ext import commands

from classes.converters import DateTimeScheduler, IntGreaterThan
from cogs.help import chunks
from utils.i18n import _, locale_doc
from utils.misc import nice_join


class Scheduling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _remind(self, ctx, subject, diff, task_id):
        await self.bot.pool.execute("DELETE FROM reminders WHERE id=$1;", task_id)
        await ctx.send(
            _("{user}, you wanted to be reminded about {subject} {diff} ago.").format(
                user=ctx.author.mention, subject=subject, diff=diff
            )
        )

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
        id = await self.bot.pool.fetchval(
            'INSERT INTO reminders ("user", content, channel, "start", "end") VALUES'
            " ($1, $2, $3, $4, $5) RETURNING id;",
            ctx.author.id,
            subject,
            ctx.channel.id,
            datetime.utcnow(),
            time,
        )
        task = self.bot.schedule_manager.schedule(
            self._remind(ctx, subject, diff, id), time
        )
        await self.bot.pool.execute(
            'UPDATE reminders SET "internal_id"=$1 WHERE "id"=$2;', task.uuid, id
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
            'SELECT * FROM reminders WHERE "user"=$1 ORDER BY "end" ASC;', ctx.author.id
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
            'SELECT id, internal_id FROM reminders WHERE "id"=ANY($1) AND "user"=$2;',
            ids,
            ctx.author.id,
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


def setup(bot):
    bot.add_cog(Scheduling(bot))
