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
import secrets

from copy import copy
from decimal import Decimal

import discord

from discord.ext import commands

from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import misc as rpgtools
from utils.checks import has_char, has_money, is_class, update_pet, user_is_patron


class Classes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @user_cooldown(86400)
    @commands.command(name="class")
    @locale_doc
    async def _class(self, ctx):
        _("""Change your primary or secondary class.""")
        if int(rpgtools.xptolevel(ctx.character_data["xp"])) >= 12:
            val = await self.bot.paginator.Choose(
                title=_("Select class to change"),
                entries=[_("Primary Class"), _("Secondary Class")],
                return_index=True,
            ).paginate(ctx)
        else:
            val = 0
        embeds = [
            discord.Embed(
                title=_("Warrior"),
                description=_(
                    "The tank class. Charge into battle with additional defense!\n+1 defense per evolution."
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
                    "Utilise powerful magic for stronger attacks.\n+1 damage per evolution."
                ),
                color=self.bot.config.primary_colour,
            ),
            discord.Embed(
                title=_("Ranger"),
                description=_(
                    "Item hunter and trainer of their very own pet.\nGet access to `{prefix}pet` to interact with your pet and let it get items for you.\n+3 minimum stat and +6 maximum stat per evolution."
                ).format(prefix=ctx.prefix),
                colour=self.bot.config.primary_colour,
            ),
            discord.Embed(
                title=_("Raider"),
                description=_(
                    "A strong warrior who gives their life for the fight against Zerekiel.\nEvery evolution boosts your raidstats by an additional 10%."
                ),
                colour=self.bot.config.primary_colour,
            ),
            discord.Embed(
                title=_("Ritualist"),
                description=_(
                    "A seer, a sacrificer and a follower.\nThe Ritualist devotes their life to the god they follow. For every evolution, their sacrifices are 5% more effective. They have twice the chance to get loot from adventures."
                ),
                colour=self.bot.config.primary_colour,
            ),
        ]
        choices = ["Warrior", "Thief", "Mage", "Ranger", "Raider", "Ritualist"]
        if await user_is_patron(self.bot, ctx.author):
            embeds.append(
                discord.Embed(
                    title=_("Paragon"),
                    description=_(
                        "Absorb the appreciation of the devs into your soul to power up.\n+1 damage and defense per evolution."
                    ),
                    color=self.bot.config.primary_colour,
                )
            )
            choices.append("Paragon")
        lines = [
            self.bot.get_class_line(class_) for class_ in ctx.character_data["class"]
        ]
        for line in lines:
            for e in embeds:
                if _(line) == e.title:
                    embeds.remove(e)
            try:
                choices.remove(line)
            except ValueError:
                pass
        profession = await self.bot.paginator.ChoosePaginator(
            extras=embeds, choices=choices
        ).paginate(ctx)
        profession_ = profession
        if profession == "Paragon":
            profession_ = "Novice"
        elif profession == "Ranger":
            profession_ = "Caretaker"
        elif profession == "Raider":
            profession_ = "Stabber"
        elif profession == "Ritualist":
            profession_ = "Priest"
        new_classes = copy(ctx.character_data["class"])
        new_classes[val] = profession_
        if not await ctx.confirm(
            _(
                "You are about to select the `{profession}` class for yourself. {textaddon} Proceed?"
            ).format(
                textaddon=_("Changing it later will cost **$5000**.")
                if ctx.character_data["class"][val] == "No Class"
                else _("This will cost **$5000**."),
                profession=profession,
            )
        ):
            return await ctx.send(_("Class selection cancelled."))
        if ctx.character_data["class"][val] == "No Class":
            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    'UPDATE profile SET "class"=$1 WHERE "user"=$2;',
                    new_classes,
                    ctx.author.id,
                )
                if profession == "Ranger":
                    await conn.execute(
                        'INSERT INTO pets ("user") VALUES ($1);', ctx.author.id
                    )
            await ctx.send(
                _("Your new class is now `{profession}`.").format(
                    profession=_(profession)
                )
            )
        else:
            if not await self.bot.has_money(ctx.author.id, 5000):
                await self.bot.reset_cooldown(ctx)
                return await ctx.send(
                    _("You're too poor for a class change, it costs **$5000**.")
                )

            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    'UPDATE profile SET "class"=$1, "money"="money"-$2 WHERE "user"=$3;',
                    new_classes,
                    5000,
                    ctx.author.id,
                )
                await conn.execute('DELETE FROM pets WHERE "user"=$1;', ctx.author.id)
                if profession == "Ranger":
                    await conn.execute(
                        'INSERT INTO pets ("user") VALUES ($1);', ctx.author.id
                    )
            await ctx.send(
                _(
                    "You selected the class `{profession}`. **$5000** was taken off your balance."
                ).format(profession=_(profession))
            )

    @has_char()
    @commands.command()
    @locale_doc
    async def myclass(self, ctx):
        _("""Views your classes.""")
        if (classes := ctx.character_data["class"]) == ["No Class", "No Class"]:
            return await ctx.send("You haven't got a class yet.")
        for class_ in classes:
            if class_ != "No Class":
                try:
                    await ctx.send(
                        file=discord.File(
                            f"assets/classes/{class_.lower().replace(' ', '_')}.jpg"
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
        _("""Evolve to the next level of your classes.""")
        level = int(rpgtools.xptolevel(ctx.character_data["xp"]))
        if level < 5:
            return await ctx.send(_("Your level isn't high enough to evolve."))
        newindex = int(level / 5) - 1
        updated = 0
        new_classes = []
        for class_ in ctx.character_data["class"]:
            if class_ != "No Class":
                new_classes.append(
                    self.bot.get_class_evolves()[self.bot.get_class_line(class_)][
                        newindex
                    ]
                )
                updated += 1
            else:
                new_classes.append("No Class")
        if updated == 0:
            return await ctx.send(_("You haven't got a class yet."))
        await self.bot.pool.execute(
            'UPDATE profile SET "class"=$1 WHERE "user"=$2;', new_classes, ctx.author.id
        )
        await ctx.send(
            _("You are now a `{class1}` and a `{class2}`.").format(
                class1=new_classes[0], class2=new_classes[1]
            )
        )

    @commands.command()
    @locale_doc
    async def tree(self, ctx):
        _("""Evolve tree.""")
        await ctx.send(
            """```
Level 0   |  Level 5    |  Level 10     | Level 15        |  Level 20
----------------------------------------------------------------------
Warriors ->  Swordsmen ->  Knights     -> Warlords       ->  Berserker
Thieves  ->  Rogues    ->  Chunin      -> Renegades      ->  Assassins
Mage     ->  Wizards   ->  Pyromancers -> Elementalists  ->  Dark Caster
Novice   ->  Proficient->  Artisan     -> Master         ->  Paragon
Caretaker->  Trainer   ->  Bowman      -> Hunter         ->  Ranger
Stabber  ->  Fighter   ->  Hero        -> Dragonslayer   ->  Raider
Priest   ->  Mysticist ->  Summoner    -> Seer           ->  Ritualist
```"""
        )

    @has_char()
    @is_class("Thief")
    @user_cooldown(3600)
    @commands.command()
    @locale_doc
    async def steal(self, ctx):
        _("""[Thief Only] Steal money!""")
        if (
            buildings := await self.bot.get_city_buildings(ctx.character_data["guild"])
        ) :
            bonus = buildings["thief_building"] * 5
        else:
            bonus = 0
        if secrets.randbelow(100) in range(
            1,
            self.bot.get_class_grade_from(ctx.character_data["class"], "Thief") * 8
            + 1
            + bonus,
        ):
            async with self.bot.pool.acquire() as conn:
                usr = await conn.fetchrow(
                    'SELECT "user", "money" FROM profile WHERE "money">=10 AND "user"!=$1 ORDER BY RANDOM() LIMIT 1;',
                    ctx.author.id,
                )

                if usr["user"] in self.bot.owner_ids:
                    return await ctx.send(
                        _(
                            "You attempted to steal from a bot VIP, but the bodyguards caught you."
                        )
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
                _("You stole **${stolen}** from {user}.").format(
                    stolen=stolen,
                    user=f"**{user}**" if user else _("a traveller just passing by"),
                )
            )
        else:
            await ctx.send(_("Your attempt to steal money wasn't successful."))

    @has_char()
    @is_class("Ranger")
    @commands.group(invoke_without_command=True)
    @update_pet()
    @locale_doc
    async def pet(self, ctx):
        _("""[Ranger Only] View your pet or interact with it.""")
        petlvl = self.bot.get_class_grade_from(ctx.character_data["class"], "Ranger")
        em = discord.Embed(title=_("{user}'s pet").format(user=ctx.disp))
        em.add_field(name=_("Name"), value=ctx.pet_data["name"], inline=False)
        em.add_field(name=_("Level"), value=petlvl, inline=False)
        em.add_field(name=_("Food"), value=f"{ctx.pet_data['food']}/100", inline=False)
        em.add_field(
            name=_("Drinks"), value=f"{ctx.pet_data['drink']}/100", inline=False
        )
        em.add_field(name=_("Love"), value=f"{ctx.pet_data['love']}/100", inline=False)
        em.add_field(name=_("Joy"), value=f"{ctx.pet_data['joy']}/100", inline=False)
        em.set_thumbnail(url=ctx.author.avatar_url)
        em.set_image(url=ctx.pet_data["image"])
        await ctx.send(embed=em)

    @update_pet()
    @has_char()
    @is_class("Ranger")
    @pet.command()
    @locale_doc
    async def feed(self, ctx):
        _("""[Ranger Only] Feed your pet.""")
        items = [
            (_("Potato"), 10, ":potato:", 1),
            (_("Apple"), 30, ":apple:", 2),
            (_("Cucumber"), 50, ":cucumber:", 4),
            (_("Meat"), 150, ":meat_on_bone:", 10),
            (_("Salad"), 250, ":salad:", 20),
            (_("Sushi"), 800, ":sushi:", 50),
            (_("Adrian's Power Poop"), 2000, ":poop:", 100),
        ]
        item = items[
            await self.bot.paginator.Choose(
                entries=[f"{i[2]} {i[0]} **${i[1]}** -> +{i[3]}" for i in items],
                return_index=True,
                timeout=30,
                title=_("Feed your pet"),
            ).paginate(ctx)
        ]
        if not await has_money(self.bot, ctx.author.id, item[1]):
            return await ctx.send(_("You are too poor to buy this."))
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;',
                item[1],
                ctx.author.id,
            )
            await conn.execute(
                'UPDATE pets SET "food"=CASE WHEN "food"+$1>=100 THEN 100 ELSE "food"+$1 END WHERE "user"=$2;',
                item[3],
                ctx.author.id,
            )
        await ctx.send(
            _(
                "You bought **{item}** for your pet and increased its food bar by **{points}** points."
            ).format(item=f"{item[2]} {item[0]}", points=item[3])
        )

    @update_pet()
    @has_char()
    @is_class("Ranger")
    @pet.command()
    @locale_doc
    async def drink(self, ctx):
        _("""[Ranger Only] Give your pet something to drink.""")
        items = [
            (_("Some Water"), 10, ":droplet:", 1),
            (_("A bottle of water"), 30, ":baby_bottle:", 2),
            (_("Cocktail"), 50, ":cocktail:", 4),
            (_("Wine"), 150, ":wine_glass:", 10),
            (_("Beer"), 250, ":beer:", 20),
            (_("Vodka"), 800, ":flag_ru:", 50),
            (_("Adrian's Cocktail"), 2000, ":tropical_drink:", 100),
        ]
        item = items[
            await self.bot.paginator.Choose(
                entries=[f"{i[2]} {i[0]} **${i[1]}** -> +{i[3]}" for i in items],
                return_index=True,
                timeout=30,
                title=_("Give your pet something to drink"),
            ).paginate(ctx)
        ]
        if not await has_money(self.bot, ctx.author.id, item[1]):
            return await ctx.send(_("You are too poor to buy this."))
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;',
                item[1],
                ctx.author.id,
            )
            await conn.execute(
                'UPDATE pets SET "drink"=CASE WHEN "drink"+$1>=100 THEN 100 ELSE "drink"+$1 END WHERE "user"=$2;',
                item[3],
                ctx.author.id,
            )
        await ctx.send(
            _(
                "You bought **{item}** for your pet and increased its drinks bar by **{points}** points."
            ).format(item=f"{item[2]} {item[0]}", points=item[3])
        )

    @update_pet()
    @has_char()
    @is_class("Ranger")
    @user_cooldown(21600)
    @pet.command(aliases=["caress", "hug", "kiss"])
    @locale_doc
    async def cuddle(self, ctx):
        _("""[Ranger Only] Cuddle your pet to make it love you.""")
        value = secrets.randbelow(12) + 1  # On average, it'll stay as is
        await self.bot.pool.execute(
            'UPDATE pets SET "love"=CASE WHEN "love"+$1>=100 THEN 100 ELSE "love"+$1 END WHERE "user"=$2;',
            value,
            ctx.author.id,
        )
        await ctx.send(
            _(
                "Your pet adores you! :heart: Cuddling it has increased its love for you by **{value}** points."
            ).format(value=value)
        )

    @update_pet()
    @has_char()
    @is_class("Ranger")
    @user_cooldown(21600)  # We are mean, indeed
    @pet.command(aliases=["fun"])
    @locale_doc
    async def play(self, ctx):
        _("""[Ranger Only] Play with your pet to make it happier.""")
        value = secrets.randbelow(12) + 1  # On average, it'll stay as is
        await self.bot.pool.execute(
            'UPDATE pets SET "joy"=CASE WHEN "joy"+$1>=100 THEN 100 ELSE "joy"+$1 END WHERE "user"=$2;',
            value,
            ctx.author.id,
        )
        await ctx.send(
            _(
                "You have been {activity} with your pet and it gained **{value}** joy!"
            ).format(
                activity=secrets.choice(
                    [
                        _("playing football :soccer:"),
                        _("playing American football :football:"),
                        _("playing rugby :rugby_football:"),
                        _("playing basketball :basketball:"),
                        _("playing tennis :tennis:"),
                        _("playing ping-pong :ping_pong:"),
                        _("boxing :boxing_glove:"),
                        _("skiing :ski:"),
                    ]
                ),
                value=value,
            )
        )

    @update_pet()
    @has_char()
    @is_class("Ranger")
    @pet.command(aliases=["name"])
    @locale_doc
    async def rename(self, ctx, *, name: str):
        _("""[Ranger Only] Renames your pet.""")
        if len(name) > 20:
            return await ctx.send(_("Please enter a name shorter than 20 characters."))
        await self.bot.pool.execute(
            'UPDATE pets SET "name"=$1 WHERE "user"=$2;', name, ctx.author.id
        )
        await ctx.send(_("Pet name updated."))

    @update_pet()
    @has_char()
    @is_class("Ranger")
    @pet.command()
    @locale_doc
    async def image(self, ctx, *, url: str):
        _("""[Ranger Only] Sets your pet's image by URL.""")
        if len(url) > 60:
            return await ctx.send(_("URLs mustn't exceed 60 characters ."))
        if not (
            url.startswith("http")
            and (url.endswith(".png") or url.endswith(".jpg") or url.endswith(".jpeg"))
        ):
            return await ctx.send(
                _(
                    "I couldn't read that URL. Does it start with `http://` or `https://` and is either a png or jpeg?"
                )
            )
        await self.bot.pool.execute(
            'UPDATE pets SET "image"=$1 WHERE "user"=$2;', url, ctx.author.id
        )
        await ctx.send(_("Your pet's image was successfully updated."))

    @update_pet()
    @has_char()
    @is_class("Ranger")
    @user_cooldown(86400)
    @pet.command()
    @locale_doc
    async def hunt(self, ctx):
        _("""[Ranger Only] Let your pet get a weapon for you!""")
        petlvl = self.bot.get_class_grade_from(ctx.character_data["class"], "Ranger")
        joy_multiply = Decimal(ctx.pet_data["joy"] / 100)
        luck_multiply = ctx.character_data["luck"]
        minstat = round(petlvl * 3 * luck_multiply * joy_multiply)
        maxstat = round(petlvl * 6 * luck_multiply * joy_multiply)
        if minstat < 1 or maxstat < 1:
            return await ctx.send(
                _("Your pet is not happy enough to hunt an item. Try making it joyful!")
            )
        item = await self.bot.create_random_item(
            minstat=minstat if minstat < 30 else 30,
            maxstat=maxstat if maxstat < 30 else 30,
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
