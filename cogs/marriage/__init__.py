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
import asyncio
import random

import discord

from discord.ext import commands
from discord.ext.commands.default import Author

from classes.converters import IntFromTo, MemberWithCharacter, UserWithCharacter
from cogs.help import chunks
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import misc as rpgtools
from utils.checks import has_char


class Marriage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_max_kids(self, lovescore):
        return 10 + lovescore // 250_000

    @has_char()
    @commands.guild_only()
    @commands.command(aliases=["marry"])
    @locale_doc
    async def propose(self, ctx, partner: MemberWithCharacter):
        _("""Propose for a marriage.""")
        if partner == ctx.author:
            return await ctx.send(
                _("You should have a better friend than only yourself.")
            )
        if ctx.character_data["marriage"] != 0 or ctx.user_data["marriage"] != 0:
            return await ctx.send(_("One of you is married."))
        msg = await ctx.send(
            embed=discord.Embed(
                title=_("{author} has proposed for a marriage!").format(
                    author=ctx.author.mention
                ),
                description=_(
                    "{author} wants to marry you, {partner}! React with :heart: to marry them!"
                ).format(author=ctx.author.mention, partner=partner.mention),
                colour=0xFF0000,
            )
            .set_image(url=ctx.author.avatar_url)
            .set_thumbnail(
                url="http://www.maasbach.com/wp-content/uploads/The-heart.png"
            )
        )
        await msg.add_reaction("\U00002764")

        def reactioncheck(reaction, user):
            return (
                str(reaction.emoji) == "\U00002764"
                and reaction.message.id == msg.id
                and user.id == partner.id
            )

        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add", timeout=120.0, check=reactioncheck
            )
        except asyncio.TimeoutError:
            return await ctx.send(_("They didn't want to marry."))
        # check if someone married in the meantime
        async with self.bot.pool.acquire() as conn:
            check1 = await conn.fetchrow(
                'SELECT * FROM profile WHERE "user"=$1 AND "marriage"=$2;',
                ctx.author.id,
                0,
            )
            check2 = await conn.fetchrow(
                'SELECT * FROM profile WHERE "user"=$1 AND "marriage"=$2;',
                partner.id,
                0,
            )
            if check1 and check2:
                await conn.execute(
                    'UPDATE profile SET "marriage"=$1 WHERE "user"=$2;',
                    partner.id,
                    ctx.author.id,
                )
                await conn.execute(
                    'UPDATE profile SET "marriage"=$1 WHERE "user"=$2;',
                    ctx.author.id,
                    partner.id,
                )
                await ctx.send(
                    _(
                        "Owwwwwww! :heart: {author} and {partner} are now married!"
                    ).format(author=ctx.author.mention, partner=partner.mention)
                )
            else:
                await ctx.send(
                    _(
                        "Either you or your lovee married in the meantime... :broken_heart:"
                    )
                )

    @has_char()
    @commands.command()
    @locale_doc
    async def divorce(self, ctx):
        _("""Break up with your partner.""")
        if not ctx.character_data["marriage"]:
            return await ctx.send(_("You are not married yet."))
        if not await ctx.confirm(
            _(
                "Are you sure you want to divorce your partner? You will lose all your children!"
            )
        ):
            return await ctx.send(
                _("Cancelled the divorce. I guess the marriage is safe for now?")
            )
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "marriage"=0 WHERE "user"=$1;', ctx.author.id
            )
            await conn.execute(
                'UPDATE profile SET "marriage"=0 WHERE "user"=$1;',
                ctx.character_data["marriage"],
            )
            await conn.execute(
                'DELETE FROM children WHERE "father"=$1 OR "mother"=$1;', ctx.author.id
            )
        await ctx.send(_("You are now divorced."))

    @has_char()
    @commands.command()
    @locale_doc
    async def relationship(self, ctx):
        _("""View who you're married to.""")
        if not ctx.character_data["marriage"]:
            return await ctx.send(_("You are not married yet."))
        partner = await rpgtools.lookup(self.bot, ctx.character_data["marriage"])
        await ctx.send(
            _("You are currently married to **{partner}**.").format(partner=partner)
        )

    @has_char()
    @commands.command()
    @locale_doc
    async def lovescore(self, ctx, user: UserWithCharacter = Author):
        _("""Views someone's lovescore.""")
        data = ctx.character_data if user == ctx.author else ctx.user_data
        if data["marriage"]:
            partner = await rpgtools.lookup(self.bot, data["marriage"])
        else:
            partner = _("noone")
        await ctx.send(
            _(
                "{user}'s overall love score is **{score}**. {user} is married to **{partner}**."
            ).format(user=user.name, score=data["lovescore"], partner=partner)
        )

    @has_char()
    @commands.command()
    @locale_doc
    async def spoil(self, ctx, item: IntFromTo(1, 40) = None):
        _("""Buy something for your spouse and increase their lovescore.""")
        items = [
            (_("Dog :dog2:"), 50),
            (_("Cat :cat2:"), 50),
            (_("Cow :cow2:"), 75),
            (_("Penguin :penguin:"), 100),
            (_("Unicorn :unicorn:"), 1000),
            (_("Potato :potato:"), 1),
            (_("Sweet potato :sweet_potato:"), 2),
            (_("Peach :peach:"), 5),
            (_("Ice Cream :ice_cream:"), 10),
            (_("Bento Box :bento:"), 50),
            (_("Movie Night :ticket:"), 75),
            (_("Video Game Night :video_game:"), 10),
            (_("Camping Night :fishing_pole_and_fish:"), 15),
            (_("Couple Competition :trophy:"), 30),
            (_("Concert Night :musical_keyboard:"), 100),
            (_("Bicycle :bike:"), 100),
            (_("Motorcycle :motorcycle:"), 250),
            (_("Car :red_car:"), 300),
            (_("Private Jet :airplane:"), 1000),
            (_("Space Rocket :rocket:"), 10000),
            (_("Credit Card :credit_card:"), 20),
            (_("Watch :watch:"), 100),
            (_("Phone :iphone:"), 100),
            (_("Bed :bed:"), 500),
            (_("Home films :projector:"), 750),
            (_("Satchel :school_satchel:"), 25),
            (_("Purse :purse:"), 30),
            (_("Shoes :athletic_shoe:"), 150),
            (_("Casual Attire :shirt:"), 200),
            (_("Ring :ring:"), 1000),
            (_("Balloon :balloon:"), 10),
            (_("Flower Bouquet :bouquet:"), 25),
            (_("Expensive Chocolates :chocolate_bar:"), 40),
            (_("Declaration of Love :love_letter:"), 50),
            (_("Key to Heart :key2:"), 100),
            (_("Ancient Vase :amphora:"), 15000),
            (_("House :house:"), 25000),
            (_("Super Computer :computer:"), 50000),
            (_("Precious Gemstone Collection :gem:"), 75000),
            (_("Planet :earth_americas:"), 1_000_000),
        ]
        text = _("Price")
        items_str = "\n".join(
            [
                f"{idx + 1}.) {item} ... {text}: **${price}**"
                for idx, (item, price) in enumerate(items)
            ]
        )
        if not item:
            text = _(
                "To buy one of these items for your partner, use `{prefix}spoil shopid`"
            ).format(prefix=ctx.prefix)
            return await ctx.send(f"{items_str}\n\n{text}")
        item = items[item - 1]
        if ctx.character_data["money"] < item[1]:
            return await ctx.send(_("You are too poor to buy this."))
        if not ctx.character_data["marriage"]:
            return await ctx.send(_("You're not married yet."))
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET lovescore=lovescore+$1 WHERE "user"=$2;',
                item[1],
                ctx.character_data["marriage"],
            )
            await conn.execute(
                'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                item[1],
                ctx.author.id,
            )
        await ctx.send(
            _(
                "You bought a **{item}** for your partner and increased their love score by **{points}** points!"
            ).format(item=item[0], points=item[1])
        )
        user = await self.bot.get_user_global(ctx.character_data["marriage"])
        if not user:
            return await ctx.send(
                _("Failed to DM your spouse, could not find their Discord account")
            )
        await user.send(
            _(
                "**{author}** bought you a **{item}** and increased your love score by **{points}** points!"
            ).format(author=ctx.author, item=item[0], points=item[1])
        )

    @has_char()
    @commands.command()
    @locale_doc
    @user_cooldown(43200)
    async def date(self, ctx):
        _("""Take your loved one on a date to increase your lovescore.""")
        num = random.randint(1, 15) * 10
        marriage = ctx.character_data["marriage"]
        if not marriage:
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(_("You are not married yet."))
        await self.bot.pool.execute(
            'UPDATE profile SET lovescore=lovescore+$1 WHERE "user"=$2;', num, marriage
        )

        partner = await self.bot.get_user_global(marriage)
        scenario = random.choice(
            [
                _("You and {partner} went on a nice candlelit dinner."),
                _("You and {partner} had stargazed all night."),
                _("You and {partner} went to a circus that was in town."),
                _("You and {partner} went out to see a romantic movie."),
                _("You and {partner} went out to get ice cream."),
                _("You and {partner} had an anime marathon."),
                _("You and {partner} went for a spontaneous hiking trip."),
                _("You and {partner} decided to visit Paris."),
                _("You and {partner} went ice skating together."),
            ]
        ).format(partner=(partner.mention if partner else _("Unknown User")))
        text = _("This increased your lovescore by {num}").format(num=num)
        await ctx.send(f"{scenario} {text}")

    async def get_random_name(self, gender, avoid):
        if gender == "f":
            data = "assets/data/girlnames.txt"
        else:
            data = "assets/data/boynames.txt"
        with open(data, "r") as file:
            all_names = file.readlines()  # this is a list
        file.close()
        name = random.choice(all_names)
        while name in avoid:
            name = random.choice(all_names)  # avoid duplicate names
        return name.strip("\n")

    @has_char()
    @commands.guild_only()
    @user_cooldown(3600)
    @commands.command(aliases=["fuck", "sex", "breed"])
    @locale_doc
    async def child(self, ctx):
        _("""Make a child with your spouse.""")
        marriage = ctx.character_data["marriage"]
        if not marriage:
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(_("Can't produce a child alone, can you?"))
        async with self.bot.pool.acquire() as conn:
            names = await conn.fetch(
                'SELECT name FROM children WHERE "mother"=$1 OR "father"=$1;',
                ctx.author.id,
            )
            spouse = await conn.fetchval(
                'SELECT lovescore FROM profile WHERE "user"=$1;', marriage
            )
        max_ = self.get_max_kids(ctx.character_data["lovescore"] + spouse)
        if len(names) >= max_:
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(
                _(
                    "You already have {max_} children. You can increase this limit by increasing your lovescores."
                ).format(max_=max_)
            )
        names = [name["name"] for name in names]
        user = self.bot.get_user(marriage)
        if not user:
            return await ctx.send(_("Your spouse is not here."))
        if not await ctx.confirm(
            _("{user}, do you want to make a child with {author}?").format(
                user=user.mention, author=ctx.author.mention
            ),
            user=user,
        ):
            return await ctx.send(_("O.o not in the mood today?"))

        if random.choice([True, False]):
            ls = random.randint(10, 50)
            await self.bot.pool.execute(
                'UPDATE profile SET "lovescore"="lovescore"+$1 WHERE "user"=$2 OR "user"=$3;',
                ls,
                ctx.author.id,
                marriage,
            )
            return await ctx.send(
                _("You had a lovely night and gained {ls} lovescore. 😏".format(ls=ls))
            )
        gender = random.choice(["m", "f"])
        if gender == "m":
            await ctx.send(
                _(
                    "It's a boy! Your night of love was successful! Please enter a name for your child."
                )
            )
        elif gender == "f":
            await ctx.send(
                _(
                    "It's a girl! Your night of love was successful! Please enter a name for your child."
                )
            )

        def check(msg):
            return (
                msg.author.id in [ctx.author.id, marriage]
                and 1 <= len(msg.content) <= 20
                and msg.channel.id == ctx.channel.id
            )

        name = None
        while not name:
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=30)
                name = msg.content.replace("@", "@\u200b")
            except asyncio.TimeoutError:
                name = await self.get_random_name(gender, names)
                await ctx.send(_("You didn't enter a name, so we chose {name} for you.").format(name=name))
                break
            if name in names:
                await ctx.send(
                    _(
                        "One of your children already has that name, please choose another one."
                    )
                )
                name = None
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO children ("mother", "father", "name", "age", "gender") VALUES ($1, $2, $3, $4, $5);',
                ctx.author.id,
                marriage,
                name,
                0,
                gender,
            )
        await ctx.send(_("{name} was born.").format(name=name))

    @has_char()
    @commands.command()
    @locale_doc
    async def family(self, ctx):
        _("""View your children.""")
        marriage = ctx.character_data["marriage"]
        if not marriage:
            return await ctx.send(_("Lonely..."))
        children = await self.bot.pool.fetch(
            'SELECT * FROM children WHERE "mother"=$1 OR "father"=$1;', ctx.author.id
        )
        em = discord.Embed(
            title=_("Your family"),
            description=_("Family of {author} and <@{marriage}>").format(
                author=ctx.author.mention, marriage=marriage
            ),
        )
        if not children:
            em.add_field(
                name=_("No children yet"),
                value=_("Use {prefix}child to make one!").format(prefix=ctx.prefix),
            )
        if len(children) <= 5:
            for child in children:
                em.add_field(
                    name=child["name"],
                    value=_("Gender: {gender}, Age: {age}").format(
                        gender=child["gender"], age=child["age"]
                    ),
                    inline=False,
                )
            em.set_thumbnail(url=ctx.author.avatar_url)
            await ctx.send(embed=em)
        else:
            embeds = []
            children_lists = list(chunks(children, 9))
            for small_list in children_lists:
                em = discord.Embed(
                    title=_("Your family"),
                    description=_("Family of {author} and <@{marriage}>").format(
                        author=ctx.author.mention, marriage=marriage
                    ),
                )
                for child in small_list:
                    em.add_field(
                        name=child["name"],
                        value=_("Gender: {gender}, Age: {age}").format(
                            gender=child["gender"], age=child["age"]
                        ),
                        inline=True,
                    )
                em.set_footer(
                    text=_("Page {cur} of {max}").format(
                        cur=children_lists.index(small_list) + 1,
                        max=len(children_lists),
                    )
                )
                embeds.append(em)
            await self.bot.paginator.Paginator(extras=embeds).paginate(ctx)

    @has_char()
    @user_cooldown(1800)
    @commands.command(aliases=["fe"])
    @locale_doc
    async def familyevent(self, ctx):
        _("""Events happening to your family.""")
        if not ctx.character_data["marriage"]:
            return await ctx.send(_("You're lonely."))
        children = await self.bot.pool.fetch(
            'SELECT * FROM children WHERE "mother"=$1 OR "father"=$1;', ctx.author.id
        )
        if not children:
            return await ctx.send(_("You don't have kids yet."))
        target = random.choice(children)
        event = random.choice(
            ["death"]
            + ["age"] * 8
            + ["namechange"] * 4
            + ["chest"] * 2
            + ["moneylose"] * 3
            + ["moneygain"] * 4
        )
        if event == "death":
            cause = random.choice(
                [
                    _("They died because of a shampoo overdose!"),
                    _("They died of lovesickness..."),
                    _("They've died of age."),
                    _("They died of loneliness."),
                    _("A horde of goblins got them."),
                    _(
                        "They have finally decided to move out after all these years, but couldn't survive a second alone."
                    ),
                    _("Spontaneous combustion removed them from existence."),
                    _("While exploring the forest, they have gotten lost."),
                    _("They've left through a portal into another dimension..."),
                    _(
                        "The unbearable pain of stepping on a Lego\© brick killed them."
                    ),  # noqa
                    _("You heard a landmine going off nearby..."),
                    _("They have been abducted by aliens!"),
                    _("The Catholic Church got them..."),
                    _("They starved after becoming a communist."),
                ]
            )
            await self.bot.pool.execute(
                'DELETE FROM children WHERE "name"=$1 AND ("mother"=$2 OR "father"=$2) AND "age"=$3;',
                target["name"],
                ctx.author.id,
                target["age"],
            )
            return await ctx.send(
                _("{name} died at the age of {age}! {cause}").format(
                    name=target["name"], age=target["age"], cause=cause
                )
            )
        elif event == "moneylose":
            cause = random.choice(
                [
                    _(
                        "fell in love with a woman on the internet, but the woman was a man and stole their money."
                    ),
                    _("has been arrested and had to post bail."),
                    _("bought fortnite skins with your credit card."),
                    _("decided to become communist and gave the money to others."),
                    _("bought an inflatable loli."),
                    _("was caught pickpocketing and you had to pay the fine."),
                    _("gave it to a beggar."),
                    _("borrowed it to attend the local knights course."),
                    _("spent it in the shop."),
                    _("bought some toys."),
                    _("has gambling addiction and lost the money..."),
                ]
            )
            money = random.randint(0, int(ctx.character_data["money"] / 64))
            await self.bot.pool.execute(
                'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;',
                money,
                ctx.author.id,
            )

            return await ctx.send(
                _("You lost ${money} because {name} {cause}").format(
                    money=money, name=target["name"], cause=cause
                )
            )
        elif event == "moneygain":
            cause = random.choice(
                [
                    _("finally found a job!"),
                    _("won a lottery."),
                    _("sold their toys."),
                    _("got money from another kid that decided to become communist."),
                    _("stole it from a traveller."),
                    _("finished a quest with a money reward."),
                    _("used dark magic to summon some money."),
                    _("looted a local warehouse and sold the wares."),
                    _("solved an enigma with a money reward."),
                ]
            )
            money = random.randint(0, int(ctx.character_data["money"] / 64))
            await self.bot.pool.execute(
                'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                money,
                ctx.author.id,
            )
            return await ctx.send(
                _("{name} gave you ${money}, they {cause}").format(
                    name=target["name"], money=money, cause=cause
                )
            )
        elif event == "chest":
            type_ = random.choice(
                ["common"] * 500
                + ["uncommon"] * 200
                + ["rare"] * 50
                + ["magic"] * 10
                + ["legendary"]
            )
            await self.bot.pool.execute(
                f'UPDATE profile SET "crates_{type_}"="crates_{type_}"+1 WHERE "user"=$1;',
                ctx.author.id,
            )
            emoji = getattr(self.bot.cogs["Crates"].emotes, type_)
            return await ctx.send(
                _("{name} found a {emoji} {type_} crate for you!").format(
                    name=target["name"], emoji=emoji, type_=type_
                )
            )
        elif event == "age":
            await self.bot.pool.execute(
                'UPDATE children SET "age"="age"+1 WHERE "name"=$1 AND ("mother"=$2 OR "father"=$2) AND "age"=$3;',
                target["name"],
                ctx.author.id,
                target["age"],
            )
            return await ctx.send(
                _("{name} is now {age} years old.").format(
                    name=target["name"], age=target["age"] + 1
                )
            )
        elif event == "namechange":
            await ctx.send(
                _("{name} can be renamed! Enter a new name:").format(
                    name=target["name"]
                )
            )
            names = [c["name"] for c in children]
            names.remove(target["name"])

            def check(msg):
                return (
                    msg.author.id in [ctx.author.id, ctx.character_data["marriage"]]
                    and msg.channel.id == ctx.channel.id
                    and 0 < len(msg.content) <= 20
                )

            name = None
            while not name:
                try:
                    msg = await self.bot.wait_for("message", check=check, timeout=30)
                    name = msg.content.replace("@", "@\u200b")
                except asyncio.TimeoutError:
                    await self.bot.reset_cooldown(ctx)
                    return await ctx.send(_("You didn't enter a name."))
                if name in names:
                    await ctx.send(
                        _(
                            "One of your children already has that name, please choose another one."
                        )
                    )
                    name = None
            await self.bot.pool.execute(
                'UPDATE children SET "name"=$1 WHERE "name"=$2 AND ("mother"=$3 OR "father"=$3) AND "age"=$4;',
                name,
                target["name"],
                ctx.author.id,
                target["age"],
            )
            if name == target["name"]:
                return await ctx.send(_("You didn't change their name."))
            return await ctx.send(
                _("{old_name} is now called {new_name}.").format(
                    old_name=target["name"], new_name=name
                )
            )


def setup(bot):
    bot.add_cog(Marriage(bot))
