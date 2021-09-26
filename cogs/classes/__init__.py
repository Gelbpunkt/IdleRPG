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
from copy import copy
from decimal import Decimal

import discord

from discord.ext import commands

from classes.classes import (
    ALL_CLASSES_TYPES,
    Mage,
    Paragon,
    Raider,
    Ranger,
    Ritualist,
    Thief,
    Warrior,
)
from classes.classes import from_string as class_from_string
from classes.classes import get_class_evolves, get_first_evolution, get_name
from classes.converters import ImageFormat, ImageUrl
from cogs.shard_communication import next_day_cooldown
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import misc as rpgtools
from utils import random
from utils.checks import has_char, has_money, is_class, update_pet, user_is_patron
from utils.i18n import _, locale_doc


class Classes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @user_cooldown(86400)
    @commands.command(name="class", brief=_("Choose or change your class(es)"))
    @locale_doc
    async def _class(self, ctx):
        _(
            """Change or select your primary or secondary class.

            - Warriors gain added defense
            - Thieves gain access to `{prefix}steal`
            - Mages gain added damage
            - Rangers gain access to a pet which can hunt for gear items
            - Raiders gain additional raidstats, used in raidbattles and raids
            - Ritualists gain additional favor from sacrificing items and are twice as likely to receive loot from adventures
            (- Paragons gain added damage *and* defense; the class is only available to donators)

            The second class unlocks at level 12. Selecting a class the first time is free (No Class -> Class), but changing it later will cost $5,000 (Class -> another Class)

            (This command has a cooldown of 24 hours)"""
        )
        if rpgtools.xptolevel(ctx.character_data["xp"]) >= 12:
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
                    "The tank class. Charge into battle with additional defense!\n+1"
                    " defense per evolution."
                ),
                color=self.bot.config.game.primary_colour,
            ),
            discord.Embed(
                title=_("Thief"),
                description=_(
                    # xgettext: no-python-format
                    "The sneaky money stealer...\nGet access to `{prefix}steal` to"
                    " steal 10% of a random player's money, if successful.\n+8% success"
                    " chance per evolution."
                ).format(prefix=ctx.prefix),
                color=self.bot.config.game.primary_colour,
            ),
            discord.Embed(
                title=_("Mage"),
                description=_(
                    "Utilise powerful magic for stronger attacks.\n+1 damage per"
                    " evolution."
                ),
                color=self.bot.config.game.primary_colour,
            ),
            discord.Embed(
                title=_("Ranger"),
                description=_(
                    "Item hunter and trainer of their very own pet.\nGet access to"
                    " `{prefix}pet` to interact with your pet and let it get items for"
                    " you.\n+3 minimum stat and +6 maximum stat per evolution."
                ).format(prefix=ctx.prefix),
                colour=self.bot.config.game.primary_colour,
            ),
            discord.Embed(
                title=_("Raider"),
                description=_(
                    "A strong warrior who gives their life for the fight against"
                    " Zerekiel.\nEvery evolution boosts your raidstats by an additional"
                    " 10%."
                ),
                colour=self.bot.config.game.primary_colour,
            ),
            discord.Embed(
                title=_("Ritualist"),
                description=_(
                    "A seer, a sacrificer and a follower.\nThe Ritualist devotes their"
                    " life to the god they follow. For every evolution, their"
                    " sacrifices are 5% more effective. They have twice the chance to"
                    " get loot from adventures."
                ),
                colour=self.bot.config.game.primary_colour,
            ),
        ]
        choices = [Warrior, Thief, Mage, Ranger, Raider, Ritualist]
        if await user_is_patron(self.bot, ctx.author):
            embeds.append(
                discord.Embed(
                    title=_("Paragon"),
                    description=_(
                        "Absorb the appreciation of the devs into your soul to power"
                        " up.\n+1 damage and defense per evolution."
                    ),
                    color=self.bot.config.game.primary_colour,
                )
            )
            choices.append(Paragon)
        classes = [class_from_string(c) for c in ctx.character_data["class"]]
        lines = [c.get_class_line() for c in classes if c]
        for line in lines:
            for e in embeds:
                if _(get_name(line)) == e.title:
                    embeds.remove(e)
            try:
                choices.remove(line)
            except ValueError:
                pass
        idx = await self.bot.paginator.ChoosePaginator(
            extras=embeds,
            placeholder=_("Choose a class"),
            choices=[line.__name__ for line in choices],
            return_index=True,
        ).paginate(ctx)
        profession = choices[idx]
        profession_ = get_first_evolution(profession).class_name()
        new_classes = copy(ctx.character_data["class"])
        new_classes[val] = profession_
        if not await ctx.confirm(
            _(
                "You are about to select the `{profession}` class for yourself."
                " {textaddon} Proceed?"
            ).format(
                textaddon=_(
                    "This **costs nothing**, but changing it later will cost **$5000**."
                )
                if ctx.character_data["class"][val] == "No Class"
                else _("This will cost **$5000**."),
                profession=get_name(profession),
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
                if profession == Ranger:
                    await conn.execute(
                        'INSERT INTO pets ("user") VALUES ($1);', ctx.author.id
                    )
            await ctx.send(
                _("Your new class is now `{profession}`.").format(
                    profession=_(get_name(profession))
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
                    'UPDATE profile SET "class"=$1, "money"="money"-$2 WHERE'
                    ' "user"=$3;',
                    new_classes,
                    5000,
                    ctx.author.id,
                )
                await conn.execute('DELETE FROM pets WHERE "user"=$1;', ctx.author.id)
                if profession == Ranger:
                    await conn.execute(
                        'INSERT INTO pets ("user") VALUES ($1);', ctx.author.id
                    )
                await self.bot.log_transaction(
                    ctx,
                    from_=ctx.author.id,
                    to=2,
                    subject="money",
                    data={"Amount": 5000},
                    conn=conn,
                )
            await ctx.send(
                _(
                    "You selected the class `{profession}`. **$5000** was taken off"
                    " your balance."
                ).format(profession=_(get_name(profession)))
            )

    @has_char()
    @commands.command(brief=_("View your class(es)"))
    @locale_doc
    async def myclass(self, ctx):
        _("""Show your class(es) and their added benefits, sent as images.""")
        if (classes := ctx.character_data["class"]) == ["No Class", "No Class"]:
            return await ctx.send("You haven't got a class yet.")
        for class_ in classes:
            if class_ != "No Class":
                try:
                    await ctx.send(
                        file=discord.File(
                            f"assets/classes/{class_.lower().replace(' ', '_')}.png"
                        )
                    )
                except FileNotFoundError:
                    await ctx.send(
                        _(
                            "The image for your class **{class_}** hasn't been added"
                            " yet."
                        ).format(class_=class_)
                    )

    @has_char()
    @commands.command(brief=_("Evolve your class(es)"))
    @locale_doc
    async def evolve(self, ctx):
        _(
            # xgettext: no-python-format
            """Evolve your class, bringing it to the next level and giving better class bonuses.

            You can evolve every 5 levels, i.e. at level 5, level 10, level 15, level 20, level 25 and finally level 30.

            - Warriors gain +1 defense per evolution
            - Thieves gain +8% for their success chance per evolution
            - Mages gain +1 damage per evolution
            - Rangers' pets' hunted item get +3 minimum stat and +6 maximum stat per evolution
              - This means level 1 pets can hunt items from stat 3 to stat 6; level 2 pets from stat 6 to stat 12
            - Raiders gain +0.1 defense and damage raidstats
            - Ritualists gain +5% extra favor when sacrificing per evolution
            (- Paragons gain +1 damage *and* +1 defense per evolution)"""
        )
        level = rpgtools.xptolevel(ctx.character_data["xp"])
        if level < 5:
            return await ctx.send(_("Your level isn't high enough to evolve."))
        newindex = int(level / 5)
        updated = 0
        new_classes = []
        for class_ in ctx.character_data["class"]:
            c = class_from_string(class_)
            if c:
                evolves = get_class_evolves(c.get_class_line())
                new_classes.append(evolves[newindex].class_name())
                updated += 1
            else:
                new_classes.append("No Class")
        if updated == 0:
            return await ctx.send(_("You haven't got a class yet."))
        if ctx.character_data["class"] == new_classes:
            return await ctx.send(_("Nothing to evolve."))
        await self.bot.pool.execute(
            'UPDATE profile SET "class"=$1 WHERE "user"=$2;', new_classes, ctx.author.id
        )
        await ctx.send(
            _("You are now a `{class1}` and a `{class2}`.").format(
                class1=new_classes[0], class2=new_classes[1]
            )
        )

    @commands.command(brief=_("Shows the evolution tree"))
    @locale_doc
    async def tree(self, ctx):
        _(
            """Shows the evolution tree for each class.
            This will only show the names, not the respective benefits."""
        )
        embeds = []
        for name, class_ in ALL_CLASSES_TYPES.items():
            evos = [
                f"Level {idx * 5}: {evo.class_name()}"
                for idx, evo in enumerate(get_class_evolves(class_))
            ]
            embed = discord.Embed(
                title=name,
                description="\n".join(evos),
                colour=self.bot.config.game.primary_colour,
            )
            embeds.append(embed)
        await self.bot.paginator.Paginator(extras=embeds).paginate(ctx)

    @is_class(Thief)
    @has_char()
    @user_cooldown(3600)
    @commands.command(brief=_("Steal money"))
    @locale_doc
    async def steal(self, ctx):
        _(
            # xgettext: no-python-format
            """Steal money from a random user.

            Your steal chance is increased by evolving your class and your alliance's thief buildings, if you have an alliance that owns a city.
            If you succeed in stealing, you will steal 10% of a random player's money.

            You *cannot* choose your target, it is always a random player. If the bot can't find the player's name, it will be replaced with "a traveller passing by".
            The random player cannot be anyone with money less than $10, yourself, or one of the bot owners.

            Only thieves can use this command.
            (This command has a cooldown of 1 hour.)"""
        )
        if buildings := await self.bot.get_city_buildings(ctx.character_data["guild"]):
            bonus = buildings["thief_building"] * 5
        else:
            bonus = 0
        grade = 0
        for class_ in ctx.character_data["class"]:
            c = class_from_string(class_)
            if c and c.in_class_line(Thief):
                grade = c.class_grade()
        if random.randint(0, 99) in range(
            1,
            grade * 8 + 1 + bonus,
        ):
            async with self.bot.pool.acquire() as conn:
                usr = await conn.fetchrow(
                    'SELECT "user", "money" FROM profile WHERE "money">=10 AND'
                    ' "user"!=$1 ORDER BY RANDOM() LIMIT 1;',
                    ctx.author.id,
                )

                if usr["user"] in self.bot.owner_ids:
                    return await ctx.send(
                        _(
                            "You attempted to steal from a bot VIP, but the bodyguards"
                            " caught you."
                        )
                    )

                stolen = int(usr["money"] * 0.1)
                await conn.execute(
                    'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                    stolen,
                    ctx.author.id,
                )
                await conn.execute(
                    'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;',
                    stolen,
                    usr["user"],
                )
                await self.bot.log_transaction(
                    ctx,
                    from_=usr["user"],
                    to=ctx.author.id,
                    subject="money",
                    data={"Amount": stolen},
                    conn=conn,
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

    @is_class(Ranger)
    @has_char()
    @commands.group(invoke_without_command=True, brief=_("Interact with your pet"))
    @update_pet()
    @locale_doc
    async def pet(self, ctx):
        _(
            """Interact with your pet. Be sure to see `{prefix}help pet`.

            Every two hours, your pet will lose 2 food points, 4 drink points, 1 joy point and 1 love point.

            If food or drink drop below zero, your pet dies and the ranger class is removed from you.
            If love sinks below 75, your pet has a chance to run away which increases the lower its love drops.

            Your pet's joy influences the items it hunts, acting as a multiplier for the item's stat.

            Only rangers can use this command."""
        )
        petlvl = 0
        for class_ in ctx.character_data["class"]:
            c = class_from_string(class_)
            if c and c.in_class_line(Ranger):
                petlvl = c.class_grade()
        em = discord.Embed(title=_("{user}'s pet").format(user=ctx.disp))
        em.add_field(name=_("Name"), value=ctx.pet_data["name"], inline=False)
        em.add_field(name=_("Level"), value=petlvl, inline=False)
        em.add_field(name=_("Food"), value=f"{ctx.pet_data['food']}/100", inline=False)
        em.add_field(
            name=_("Drinks"), value=f"{ctx.pet_data['drink']}/100", inline=False
        )
        em.add_field(name=_("Love"), value=f"{ctx.pet_data['love']}/100", inline=False)
        em.add_field(name=_("Joy"), value=f"{ctx.pet_data['joy']}/100", inline=False)
        em.set_thumbnail(url=ctx.author.display_avatar.url)
        em.set_image(url=ctx.pet_data["image"])
        await ctx.send(embed=em)

    @update_pet()
    @is_class(Ranger)
    @has_char()
    @pet.command(brief=_("Feed your pet"))
    @locale_doc
    async def feed(self, ctx):
        _(
            """Feed your pet. This brings up an interactive menu where you can buy a food item.

            Only rangers can use this command."""
        )
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
                choices=[i[0] for i in items],
                placeholder=_("Select a dish for your pet"),
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
                'UPDATE pets SET "food"=CASE WHEN "food"+$1>=100 THEN 100 ELSE'
                ' "food"+$1 END WHERE "user"=$2;',
                item[3],
                ctx.author.id,
            )
            await self.bot.log_transaction(
                ctx,
                from_=ctx.author.id,
                to=2,
                subject="money",
                data={"Amount": item[1]},
                conn=conn,
            )
        await ctx.send(
            _(
                "You bought **{item}** for your pet and increased its food bar by"
                " **{points}** points."
            ).format(item=f"{item[2]} {item[0]}", points=item[3])
        )

    @update_pet()
    @is_class(Ranger)
    @has_char()
    @pet.command(brief=_("Give your pet something to drink."))
    @locale_doc
    async def drink(self, ctx):
        _(
            """Give your pet something to drink. This brings up an interactive menu where you can buy a drink item.

            Only rangers can use this command."""
        )
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
                choices=[i[0] for i in items],
                placeholder=_("Select a drink for your pet"),
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
                'UPDATE pets SET "drink"=CASE WHEN "drink"+$1>=100 THEN 100 ELSE'
                ' "drink"+$1 END WHERE "user"=$2;',
                item[3],
                ctx.author.id,
            )
            await self.bot.log_transaction(
                ctx,
                from_=ctx.author.id,
                to=2,
                subject="money",
                data={"Amount": item[1]},
                conn=conn,
            )
        await ctx.send(
            _(
                "You bought **{item}** for your pet and increased its drinks bar by"
                " **{points}** points."
            ).format(item=f"{item[2]} {item[0]}", points=item[3])
        )

    @update_pet()
    @is_class(Ranger)
    @has_char()
    @user_cooldown(21600)
    @pet.command(aliases=["caress", "hug", "kiss"], brief=_("Love your pet"))
    @locale_doc
    async def cuddle(self, ctx):
        _(
            """Cuddle with your pet to raise its love points. Your pet can gain from 1 to 12 Love points per cuddle.

            Only rangers can use this command.
            (This command has a cooldown of 6 hours.)"""
        )
        value = random.randint(0, 11) + 1  # On average, it'll stay as is
        await self.bot.pool.execute(
            'UPDATE pets SET "love"=CASE WHEN "love"+$1>=100 THEN 100 ELSE "love"+$1'
            ' END WHERE "user"=$2;',
            value,
            ctx.author.id,
        )
        await ctx.send(
            _(
                "Your pet adores you! :heart: Cuddling it has increased its love for"
                " you by **{value}** points."
            ).format(value=value)
        )

    @update_pet()
    @is_class(Ranger)
    @has_char()
    @user_cooldown(21600)  # We are mean, indeed
    @pet.command(aliases=["fun"], brief=_("Play with your pet"))
    @locale_doc
    async def play(self, ctx):
        _(
            """Play with your pet to raise its joy points. Your pet can gain from 1 to 12 Joy points per play.

            Only rangers can use this command.
            (This command has a cooldown of 6 hours.)"""
        )
        value = random.randint(0, 11) + 1  # On average, it'll stay as is
        await self.bot.pool.execute(
            'UPDATE pets SET "joy"=CASE WHEN "joy"+$1>=100 THEN 100 ELSE "joy"+$1 END'
            ' WHERE "user"=$2;',
            value,
            ctx.author.id,
        )
        await ctx.send(
            _(
                "You have been {activity} with your pet and it gained **{value}** joy!"
            ).format(
                activity=random.choice(
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
    @is_class(Ranger)
    @has_char()
    @pet.command(aliases=["name"], brief=_("Rename your pet"))
    @locale_doc
    async def rename(self, ctx, *, name: str):
        _(
            """Give your pet a new name. The name cannot be longer than 20 characters.

            Only rangers can use this command."""
        )
        if len(name) > 20:
            return await ctx.send(_("Please enter a name shorter than 20 characters."))
        await self.bot.pool.execute(
            'UPDATE pets SET "name"=$1 WHERE "user"=$2;', name, ctx.author.id
        )
        await ctx.send(_("Pet name updated."))

    @update_pet()
    @is_class(Ranger)
    @has_char()
    @pet.command(brief=_("Set a new image for your pet"))
    @locale_doc
    async def image(self, ctx, *, url: ImageUrl(ImageFormat.all) = ""):
        _(
            """`[url]` - An image url for the pet's image, must be 60 characters or shorter

            Updates the image that shows in `{prefix}pet`.

            Having trouble finding a short image link? Follow [this tutorial](https://wiki.idlerpg.xyz/index.php?title=Tutorial:_Short_Image_URLs) or just attach the image you want to use (png, jpg, webp and gif are supported)!

            Only rangers can use this command."""
        )
        if (urllength := len(url)) == 0:
            if not ctx.message.attachments:
                current_icon = ctx.pet_data["image"]
                return await ctx.send(
                    _("Your current pet image is: {url}").format(url=current_icon)
                )
            file_url = await ImageUrl(ImageFormat.all).convert(
                ctx, ctx.message.attachments[0].url
            )
            await ctx.send(
                _("No image URL found in your message, using image attachment...")
            )
            icon_url = await self.bot.cogs["Miscellaneous"].get_imgur_url(file_url)
        elif urllength > 60:
            await ctx.send(_("Image URL too long, shortening..."))
            icon_url = await self.bot.cogs["Miscellaneous"].get_imgur_url(url)
        else:
            icon_url = url
        await self.bot.pool.execute(
            'UPDATE pets SET "image"=$1 WHERE "user"=$2;', icon_url, ctx.author.id
        )
        await ctx.send(_("Your pet's image was successfully updated."))

    @update_pet()
    @is_class(Ranger)
    @has_char()
    @next_day_cooldown()
    @pet.command(brief=_("Let your pet hunt a weapon"))
    @locale_doc
    async def hunt(self, ctx):
        _(
            # xgettext: no-python-format
            """Make your pet hunt an item for you.

            The items stat depends on your pet's level (determined by class evolution) as well as its joy score.
            The lowest base stat your pet can find is three times its level, the highest is 6 times its level.
            Your pet's joy score in percent is multiplied with these base stats.

            For example:
              - Your pet is on level 2, its  joy score is 50.
              - The item's base stats are (3x2) to (6x2), so 6 to 12.
              - Its joy score in percent is multiplied: 50% x 6 to 50% x 12, so 3 to 6

            In this example, your pet can hunt an item with stats 3 to 6. It has a hard cap at 30.
            The item's value will be between 0 and 250.

            Only rangers can use this command.
            (This command has a cooldown until 12am UTC.)"""
        )
        petlvl = 0
        for class_ in ctx.character_data["class"]:
            c = class_from_string(class_)
            if c and c.in_class_line(Ranger):
                petlvl = c.class_grade()
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
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name=_("ID"), value=item["id"], inline=False)
        embed.add_field(name=_("Name"), value=item["name"], inline=False)
        embed.add_field(name=_("Type"), value=item["type"], inline=False)
        if item["type"] == "Shield":
            embed.add_field(name=_("Armor"), value=item["armor"], inline=True)
        else:
            embed.add_field(name=_("Damage"), value=item["damage"], inline=True)
        embed.add_field(name=_("Value"), value=f"${item['value']}", inline=False)
        embed.set_footer(text=_("Your pet needs to recover, wait a day to retry"))
        await ctx.send(embed=embed)
        await self.bot.log_transaction(
            ctx,
            from_=1,
            to=ctx.author.id,
            subject="item",
            data={"Name": item["name"], "Value": item["value"]},
        )


def setup(bot):
    bot.add_cog(Classes(bot))
