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

import discord
from discord.ext import commands

from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import misc as rpgtools
from utils.checks import has_char, has_money, is_class, user_is_patron


class Classes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @user_cooldown(86400)
    @commands.command(name="class")
    @locale_doc
    async def _class(self, ctx):
        _("""Change your class.""")
        embeds = [
            discord.Embed(
                title=_("Warrior"),
                description=_(
                    "The tank class. Charge into battle with additional defense!\n+1 defense per evolution added onto your shield."
                ),
                color=self.bot.config.primary_colour,
            ),
            discord.Embed(
                title=_("Thief"),
                description=_(
                    # xgettext: no-python-format
                    "The sneaky money stealer...\nGet access to `{prefix}steal` to steal 10% of the target's money, if successful.\n+8% success chance per evolution."
                ).format(prefix=ctx.prefix),
                color=self.bot.config.primary_colour,
            ),
            discord.Embed(
                title=_("Mage"),
                description=_(
                    "Utilise powerful magic for stronger attacks.\n+1 damage per evolution added onto your sword."
                ),
                color=self.bot.config.primary_colour,
            ),
            discord.Embed(
                title=_("Ranger"),
                description=_(
                    "Item hunter and trainer of their very own pet.\nGet access to `{prefix}hunt` and `{prefix}pet` to hunt a random item once a day.\n+3 minimum stat and +6 maximum stat per evolution."
                ).format(prefix=ctx.prefix),
                colour=self.bot.config.primary_colour,
            ),
        ]
        choices = ["Warrior", "Thief", "Mage", "Ranger"]
        if await user_is_patron(self.bot, ctx.author):
            embeds.append(
                discord.Embed(
                    title=_("Paragon"),
                    description=_(
                        "Absorb the appreciation of the devs into your soul to power up.\n+1 damage and defense per evolution added onto your items."
                    ),
                    color=self.bot.config.primary_colour,
                )
            )
            choices.append("Paragon")
        profession = await self.bot.paginator.ChoosePaginator(
            extras=embeds, choices=choices
        ).paginate(ctx)
        profession_ = profession
        if profession == "Paragon":
            profession_ = "Novice"
        if profession == "Ranger":
            profession_ = "Caretaker"
        if ctx.character_data["class"] == "No Class":
            await self.bot.pool.execute(
                'UPDATE profile SET "class"=$1 WHERE "user"=$2;',
                profession_,
                ctx.author.id,
            )
            await ctx.send(
                _("Your new class is now `{profession}`.").format(
                    profession=_(profession)
                )
            )
        else:
            if not await has_money(self.bot, ctx.author.id, 5000):
                await self.bot.reset_cooldown(ctx)
                return await ctx.send(
                    _("You're too poor for a class change, it costs **$5000**.")
                )

            await self.bot.pool.execute(
                'UPDATE profile SET "class"=$1, "money"="money"-$2 WHERE "user"=$3;',
                profession_,
                5000,
                ctx.author.id,
            )
            await ctx.send(
                _(
                    "Your new class is now `{profession}`. **$5000** was taken off your balance."
                ).format(profession=_(profession))
            )

    @has_char()
    @commands.command()
    @locale_doc
    async def myclass(self, ctx):
        _("""Views your class.""")
        class_ = ctx.character_data["class"]
        if class_ == "No Class" or not class_:
            return await ctx.send("You haven't got a class yet.")
        try:
            await ctx.send(
                file=discord.File(
                    f"assets/classes/{class_.lower().replace(' ', '_')}.png"
                )
            )
        except FileNotFoundError:
            await ctx.send(
                _(
                    "The image for your class **{class_}** hasn't been added yet."
                ).format(class_=class_)
            )

    @has_char()
    @commands.command()
    @locale_doc
    async def evolve(self, ctx):
        _("""Evolve to the next level of your class.""")
        level = int(rpgtools.xptolevel(ctx.character_data["xp"]))
        if level < 5:
            return await ctx.send(_("Your level isn't high enough to evolve."))
        if ctx.character_data["class"] == "No Class":
            return await ctx.send(_("You haven't got a class yet."))
        newindex = int(level / 5) - 1
        newclass = self.bot.get_class_evolves()[
            self.bot.get_class_line(ctx.character_data["class"])
        ][newindex]
        await self.bot.pool.execute(
            'UPDATE profile SET "class"=$1 WHERE "user"=$2;', newclass, ctx.author.id
        )
        await ctx.send(_("You are now a `{newclass}`.").format(newclass=newclass))

    @commands.command()
    @locale_doc
    async def tree(self, ctx):
        """Evolve tree."""
        await ctx.send(
            """```
Level 0   |  Level 5    |  Level 10     | Level 15        |  Level 20
----------------------------------------------------------------------
Warriors ->  Swordsmen ->  Knights     -> Warlords       ->  Berserker
Thieves  ->  Rogues    ->  Chunin      -> Renegades      ->  Assassins
Mage     ->  Wizards   ->  Pyromancers -> Elementalists  ->  Dark Caster
Novice   ->  Proficient->  Artisan     -> Master         ->  Paragon
Caretaker->  Trainer   ->  Bowman      -> Hunter         ->  Ranger
```"""
        )

    @has_char()
    @is_class("Thief")
    @user_cooldown(3600)
    @commands.command()
    @locale_doc
    async def steal(self, ctx):
        _("""[Thief Only] Steal money!""")
        if secrets.randbelow(100) in range(
            1, self.bot.get_class_grade(ctx.character_data["class"]) * 8 + 1
        ):
            async with self.bot.pool.acquire() as conn:
                usr = await conn.fetchrow(
                    'SELECT "user", "money" FROM profile WHERE "money">=0 ORDER BY RANDOM() LIMIT 1;'
                )
                stolen = int(usr["money"] * 0.1)
                await conn.execute(
                    'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                    stolen,
                    ctx.author.id,
                )
                await conn.execute(
                    'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                    stolen,
                    usr["user"],
                )
            user = await self.bot.get_user_global(usr["user"])
            await ctx.send(
                _("You stole **${stolen}** from **{user}**.").format(
                    stolen=stolen, user=user
                )
            )
        else:
            await ctx.send(_("Your attempt to steal money wasn't successful."))

    @has_char()
    @is_class("Ranger")
    @commands.command()
    @locale_doc
    async def pet(self, ctx):
        _("""[Ranger Only] View your pet!""")
        petlvl = self.bot.get_class_grade(ctx.character_data["class"])
        em = discord.Embed(title=_("{user}'s pet").format(user=ctx.disp))
        em.add_field(name=_("Level"), value=petlvl, inline=False)
        em.set_thumbnail(url=ctx.author.avatar_url)
        url = [
            "https://cdn.discordapp.com/attachments/456433263330852874/458568221189210122/fox.JPG",
            "https://cdn.discordapp.com/attachments/456433263330852874/458568217770721280/bird_2.jpg",
            "https://cdn.discordapp.com/attachments/456433263330852874/458568230110363649/hedgehog_2.JPG",
            "https://cdn.discordapp.com/attachments/456433263330852874/458568231918108673/wolf_2.jpg",
            "https://cdn.discordapp.com/attachments/456433263330852874/458577751226581024/dragon_2.jpg",
        ][petlvl - 1]
        em.set_image(url=url)
        await ctx.send(embed=em)

    @has_char()
    @is_class("Ranger")
    @user_cooldown(86400)
    @commands.command()
    @locale_doc
    async def hunt(self, ctx):
        _("""[Ranger Only] Let your pet get a weapon for you!""")
        petlvl = self.bot.get_class_grade(ctx.character_data["class"])
        item = await self.bot.create_random_item(
            minstat=petlvl * 3,
            maxstat=petlvl * 6,
            minvalue=1,
            maxvalue=250,
            owner=ctx.author,
        )
        embed = discord.Embed(
            title=_("You gained an item!"),
            description=_("Your pet found an item!"),
            color=0xFF0000,
        )
        embed.set_thumbnail(url=ctx.author.avatar_url)
        embed.add_field(name=_("ID"), value=item["id"], inline=False)
        embed.add_field(name=_("Name"), value=item["name"], inline=False)
        embed.add_field(name=_("Type"), value=item["type"], inline=False)
        if item["type"] == "Sword":
            embed.add_field(name=_("Damage"), value=item["damage"], inline=True)
        else:
            embed.add_field(name=_("Armor"), value=item["armor"], inline=True)
        embed.add_field(name=_("Value"), value=f"${item['value']}", inline=False)
        embed.set_footer(text=_("Your pet needs to recover, wait a day to retry"))
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Classes(bot))
