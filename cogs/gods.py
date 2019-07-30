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
from discord.ext import commands

from utils.checks import has_char, has_god


class Gods(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @has_god()
    @commands.command()
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


def setup(bot):
    bot.add_cog(Gods(bot))
