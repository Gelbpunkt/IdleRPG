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
import secrets

from io import BytesIO

import discord

from discord.ext import commands

from classes.converters import IntGreaterThan, UserWithCharacter
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils.checks import has_char, has_god, has_no_god, is_god


class Gods(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.gods = {
            god["user"]: name for name, god in self.bot.config.gods.items()
        }

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
                value = round(
                    value
                    * (1 + 0.05 * self.bot.get_class_grade_from(class_, "Ritualist"))
                )

            await conn.execute('DELETE FROM loot WHERE "id"=$1;', loot_id)
            await conn.execute(
                'UPDATE profile SET "favor"="favor"+$1 WHERE "user"=$2;',
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

    @has_char()
    @has_god()
    @user_cooldown(86_400)
    @commands.command()
    @locale_doc
    async def pray(self, ctx):
        _("""Pray to your deity to gain favor.""")
        if (rand := secrets.randbelow(3)) == 0:
            message = secrets.choice(
                [
                    _("They obviously didn't like your prayer!"),
                    _("Noone heard you!"),
                    _("Your voice has made them screw off."),
                    _("Even a donkey would've been a better follower than you."),
                ]
            )
            val = 0
        elif rand == 1:
            val = secrets.randbelow(500) + 1
            message = secrets.choice(
                [
                    _("„Rather lousy, but okay“, they said."),
                    _("You were a little sleepy."),
                    _("They were a little amused about your singing."),
                    _("Hearing the same prayer over and over again made them tired."),
                ]
            )
            await self.bot.pool.execute(
                'UPDATE profile SET "favor"="favor"+$1 WHERE "user"=$2;',
                val,
                ctx.author.id,
            )
        elif rand == 2:
            val = secrets.randbelow(500) + 500
            message = secrets.choice(
                [
                    _("Your Gregorian chants were amazingly well sung."),
                    _("Even the birds joined in your singing."),
                    _(
                        "The other gods applauded while your god noted down the best mark."
                    ),
                    _("Rarely have you had a better day!"),
                ]
            )
            await self.bot.pool.execute(
                'UPDATE profile SET "favor"="favor"+$1 WHERE "user"=$2;',
                val,
                ctx.author.id,
            )
        await ctx.send(
            _("Your prayer resulted in **{val}** favor. {message}").format(
                val=val, message=message
            )
        )

    @has_char()
    @has_god()
    @commands.command(aliases=["favour"])
    @locale_doc
    async def favor(self, ctx):
        _("""Shows your god and favor.""")
        await ctx.send(
            _("Your god is **{god}** and you have **{favor}** favor with them.").format(
                god=ctx.character_data["god"], favor=ctx.character_data["favor"]
            )
        )

    # just like admin commands, these aren't translated
    @has_char()
    @is_god()
    @commands.command()
    @locale_doc
    async def followers(self, ctx, limit: IntGreaterThan(0)):
        _("""Lists top followers of your god (or yourself).""")
        if ctx.author.id in self.bot.gods:
            god = self.bot.gods[ctx.author.id]
        else:
            if limit > 25:
                return await ctx.send(_("Normal followers may only view the top 25."))
            god = ctx.character_data["god"]
        data = await self.bot.pool.fetch(
            'SELECT * FROM profile WHERE "god"=$1 ORDER BY "favor" DESC LIMIT $2;',
            god,
            limit,
        )
        formatted = "\n".join(
            [
                f"{idx + 1}. {i['user']}: {i['favor']} Favor, Luck: {i['luck']}"
                for idx, i in enumerate(data)
            ]
        )
        await ctx.send(
            file=discord.File(filename="followers.txt", fp=BytesIO(formatted.encode()))
        )

    @is_god()
    @commands.command(aliases=["resetfavour"])
    async def resetfavor(self, ctx):
        """[Gods Only] Reset all your followers' favor."""
        god = self.bot.gods[ctx.author.id]
        await self.bot.pool.execute('UPDATE profile SET "favor"=0 WHERE "god"=$1;', god)
        await ctx.send("Done.")

    @is_god()
    @commands.command()
    async def setluck(self, ctx, amount: float, target: UserWithCharacter = "all"):
        """[Gods Only] Gives luck to all of your followers or specific ones."""
        god = self.bot.gods[ctx.author.id]
        if target != "all" and ctx.user_data["god"] != god:
            return await ctx.send("Not a follower of yours.")
        amount = round(amount, 2)
        if amount < 0 or amount > 2:
            return await ctx.send("Be fair.")
        if target == "all":
            await self.bot.pool.execute(
                'UPDATE profile SET "luck"=round($1, 2) WHERE "god"=$2;', amount, god
            )
        else:
            await self.bot.pool.execute(
                'UPDATE profile SET "luck"=round($1, 2) WHERE "user"=$2;',
                amount,
                target.id,
            )
        await ctx.send(
            f"Gave {amount} luck to {'all of your followers' if target == 'all' else target}."
        )


def setup(bot):
    bot.add_cog(Gods(bot))
