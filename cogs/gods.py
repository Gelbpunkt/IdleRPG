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
import discord
from discord.ext import commands

from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils.checks import has_char, has_god, has_no_god


class Gods(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @has_god()
    @commands.command()
    @locale_doc
    async def sacrifice(self, ctx, loot_id: int):
        _("""Sacrifice an item for favor.""")
        async with self.bot.pool.acquire() as conn:
            if not (
                item := await conn.fetchrow(
                    'SELECT * FROM loot WHERE "id"=$1 AND "user"=$2;',
                    loot_id,
                    ctx.author.id,
                )
            ):
                return await ctx.send(_("You do not own this loot item."))
            class_ = ctx.character_data["class"]
            value = item["value"]
            if self.bot.in_class_line(class_, "Ritualist"):
                value *= 1 + 0.05 * self.bot.get_class_grade(class_)

            await conn.execute('DELETE FROM loot WHERE "id"=$1;', loot_id)
            await conn.execute(
                'UPDATE profile SET "sacrifices"="sacrifices"+$1 WHERE "user"=$2;',
                value,
                ctx.author.id,
            )
        await ctx.send(
            _(
                "You prayed to {god}, and they accepted your sacrifice ({name}). Your standing with the god has increased by **{points}** points."
            ).format(god=ctx.character_data["god"], name=item["name"], points=value)
        )

    @has_char()
    @has_no_god()
    @user_cooldown(60)  # to prevent double invoke
    @commands.command()
    @locale_doc
    async def follow(self, ctx):
        _("""Choose your deity. This cannot be undone.""")
        embeds = [
            discord.Embed(
                title=name,
                description=god["description"],
                color=self.bot.config.primary_colour,
            )
            for name, god in self.bot.config.gods.items()
        ]
        god = await self.bot.paginator.ChoosePaginator(
            extras=embeds, choices=list(self.bot.config.gods.keys())
        ).paginate(ctx)

        await self.bot.pool.execute(
            'UPDATE profile SET "god"=$1 WHERE "user"=$2;', god, ctx.author.id
        )

        await ctx.send(_("You are now a follower of {god}.").format(god=god))


def setup(bot):
    bot.add_cog(Gods(bot))
