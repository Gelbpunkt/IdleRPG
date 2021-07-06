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
import discord

from discord.ext import commands

from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import checks as checks
from utils import random
from utils.i18n import _, locale_doc


class Halloween(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.waiting = None

    @checks.has_char()
    @user_cooldown(10800)
    @commands.command(aliases=["tot"], brief=_("Trick or treat!"))
    @locale_doc
    async def trickortreat(self, ctx):
        _(
            # xgettext: no-python-format
            """Walk around the houses and scare the residents! Maybe they have a gift for you?

            This command requires two players, one that is waiting and one that rings at the door.
            If you are the one waiting, you will get a direct message from the bot later, otherwise you will get a reply immediately.

            There is a 50% chance you will receive a halloween bag from the other person.

            (This command has a cooldown of 3h)"""
        )
        waiting = self.waiting
        if not waiting:
            self.waiting = ctx.author
            return await ctx.send(
                _("You walk around the houses... Noone is there... *yet*")
            )
        self.waiting = None
        async with self.bot.pool.acquire() as conn:
            if random.randint(0, 1) == 1:
                await ctx.send(
                    _(
                        "You walk around the houses and ring at {waiting}'s house!"
                        " That's a trick or treat bag for you, yay!"
                    ).format(waiting=waiting)
                )
                await conn.execute(
                    'UPDATE profile SET "trickortreat"="trickortreat"+1 WHERE'
                    ' "user"=$1;',
                    ctx.author.id,
                )
            else:
                await ctx.send(
                    _(
                        "You walk around the houses and ring at {waiting}'s house!"
                        " Sadly they don't have anything for you..."
                    ).format(waiting=waiting)
                )
            try:
                if random.randint(0, 1) == 1:
                    await waiting.send(
                        "The waiting was worth it: {author} rang! That's a trick or"
                        " treat bag for you, yay!".format(author=ctx.author)
                    )
                    await conn.execute(
                        'UPDATE profile SET "trickortreat"="trickortreat"+1 WHERE'
                        ' "user"=$1;',
                        waiting.id,
                    )
                else:
                    await waiting.send(
                        "{author} rings at your house, but... Nothing for you! 👻".format(
                            author=ctx.author
                        )
                    )
            except discord.Forbidden:
                pass

            if random.randint(1, 100) < 5:
                await conn.execute(
                    'UPDATE profile SET "backgrounds"=array_append("backgrounds", $1) WHERE "user"=$2;',
                    "https://i.imgur.com/dJqwM1H.png",
                    ctx.author.id,
                )
                await ctx.send(
                    _(
                        "🎃 As you step out of the door, you open your candy and plastic reveals an ancient image on top of a chocolate bar, passed along for generations. You decide to keep it in your `{prefix}eventbackground`s."
                    ).format(
                        prefix=ctx.prefix,
                    )
                )

    @checks.has_char()
    @commands.command(brief=_("Open a trick or treat bag"))
    @locale_doc
    async def yummy(self, ctx):
        _(
            """Open a trick or treat bag, you can get some with `{prefix}trickortreat`.

            Trick or treat bags contain halloween-themed items, ranging from 1 to 50 base stat.
            Their value will be between 1 and 200."""
        )
        # better name?
        if ctx.character_data["trickortreat"] < 1:
            return await ctx.send(
                _("Seems you haven't got a trick or treat bag yet. Go get some!")
            )
        mytry = random.randint(1, 100)
        if mytry == 1:
            minstat, maxstat = 42, 50
        elif mytry < 10:
            minstat, maxstat = 30, 41
        elif mytry < 30:
            minstat, maxstat = 20, 29
        elif mytry < 50:
            minstat, maxstat = 10, 19
        else:
            minstat, maxstat = 1, 9
        item = await self.bot.create_random_item(
            minstat=minstat,
            maxstat=maxstat,
            minvalue=1,
            maxvalue=200,
            owner=ctx.author,
            insert=False,
        )
        name = random.choice(
            [
                "Jack's",
                "Spooky",
                "Ghostly",
                "Skeletal",
                "Glowing",
                "Moonlight",
                "Adrian's really awesome",
                "Ghost Buster's",
                "Ghoulish",
                "Vampiric",
                "Living",
                "Undead",
                "Glooming",
            ]
        )
        item["name"] = f"{name} {item['type_']}"
        async with self.bot.pool.acquire() as conn:
            await self.bot.create_item(**item, conn=conn)
            await conn.execute(
                'UPDATE profile SET "trickortreat"="trickortreat"-1 WHERE "user"=$1;',
                ctx.author.id,
            )
        embed = discord.Embed(
            title=_("You gained an item!"),
            description=_("You found a new item when opening a trick-or-treat bag!"),
            color=self.bot.config.game.primary_colour,
        )
        embed.set_thumbnail(url=ctx.author.avatar.url)
        embed.add_field(name=_("Name"), value=item["name"], inline=False)
        embed.add_field(name=_("Type"), value=item["type_"], inline=False)
        embed.add_field(name=_("Damage"), value=item["damage"], inline=True)
        embed.add_field(name=_("Armor"), value=item["armor"], inline=True)
        embed.add_field(name=_("Value"), value=f"${item['value']}", inline=False)
        embed.set_footer(
            text=_("Remaining trick-or-treat bags: {bags}").format(
                bags=ctx.character_data["trickortreat"] - 1
            )
        )
        await ctx.send(embed=embed)

    @checks.has_char()
    @commands.command(
        aliases=["totbags", "halloweenbags"], brief=_("Shows your trick or treat bags")
    )
    @locale_doc
    async def bags(self, ctx):
        _(
            """Shows the amount of trick or treat bags you have. You can get more by using `{prefix}trickortreat`."""
        )
        await ctx.send(
            _(
                "You currently have **{trickortreat}** Trick or Treat Bags, {author}!"
            ).format(
                trickortreat=ctx.character_data["trickortreat"],
                author=ctx.author.mention,
            )
        )


def setup(bot):
    bot.add_cog(Halloween(bot))
