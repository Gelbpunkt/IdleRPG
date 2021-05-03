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
import asyncio

import discord

from discord.ext import commands
from discord.ext.commands.default import Author

from classes.converters import IntFromTo, MemberWithCharacter, UserWithCharacter
from cogs.help import chunks
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import misc as rpgtools
from utils import random
from utils.checks import has_char
from utils.i18n import _, locale_doc


class Marriage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("assets/data/boynames.txt") as boy_names:
            self.boynames = boy_names.readlines()
        with open("assets/data/girlnames.txt") as girl_names:
            self.girlnames = girl_names.readlines()

    def get_max_kids(self, lovescore):
        max_, missing = divmod(lovescore, 250_000)
        return 10 + max_, 250_000 - missing

    @has_char()
    @commands.guild_only()
    @commands.command(aliases=["marry"], brief=_("Propose to a player"))
    @locale_doc
    async def propose(self, ctx, partner: MemberWithCharacter):
        _(
            """`<partner>` - A discord User with a character who is not yet married

            Propose to a player for marriage. Once they accept, you are married.

            When married, your partner will get bonuses from your adventures, you can have children, which can do different things (see `{prefix}help familyevent`) and increase your lovescore, which has an effect on the [adventure bonus](https://wiki.idlerpg.xyz/index.php?title=Family#Adventure_Bonus).
            If any of you has children, they will be brought together to one family.

            Only players who are not already married can use this command."""
        )
        if partner == ctx.author:
            return await ctx.send(
                _("You should have a better friend than only yourself.")
            )
        if ctx.character_data["marriage"] != 0 or ctx.user_data["marriage"] != 0:
            return await ctx.send(_("One of you is married."))
        msg = await ctx.send(
            embed=discord.Embed(
                title=_("{author} has proposed for a marriage!").format(
                    author=ctx.disp,
                ),
                description=_(
                    "{author} wants to marry you, {partner}! React with :heart: to"
                    " marry them!"
                ).format(author=ctx.author.mention, partner=partner.mention),
                colour=0xff0000,
            )
            .set_image(url=ctx.author.avatar.url)
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
            _reaction, _user = await self.bot.wait_for(
                "reaction_add", timeout=120.0, check=reactioncheck
            )
        except asyncio.TimeoutError:
            return await ctx.send(_("They didn't want to marry."))
        # check if someone married in the meantime
        check1 = await self.bot.cache.get_profile_col(ctx.author.id, "marriage")
        check2 = await self.bot.cache.get_profile_col(partner.id, "marriage")
        if check1 or check2:
            return await ctx.send(
                _("Either you or your lovee married in the meantime... :broken_heart:")
            )
        async with self.bot.pool.acquire() as conn:
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
            await conn.execute(
                'UPDATE children SET "father"=$1 WHERE "father"=0 AND "mother"=$2;',
                partner.id,
                ctx.author.id,
            )
            await conn.execute(
                'UPDATE children SET "father"=$1 WHERE "father"=0 AND "mother"=$2;',
                ctx.author.id,
                partner.id,
            )
        await self.bot.cache.update_profile_cols_abs(ctx.author.id, marriage=partner.id)
        await self.bot.cache.update_profile_cols_abs(partner.id, marriage=ctx.author.id)
        # we give familyevent cooldown to the new partner to avoid exploitation
        await self.bot.set_cooldown(partner.id, 1800, "familyevent")
        await ctx.send(
            _("Aww! :heart: {author} and {partner} are now married!").format(
                author=ctx.author.mention, partner=partner.mention
            )
        )

    @has_char()
    @commands.command(brief=_("Break up with your partner"))
    @locale_doc
    async def divorce(self, ctx):
        _(
            """Divorce your partner, effectively un-marrying them.

            When divorcing, any kids you have will be split between you and your partner. Each partner will get the children born with their `{prefix}child` commands.
            You can marry another person right away, if you so choose. Divorcing has no negative consequences on gameplay.

            Both players' lovescore will be reset.

            Only married players can use this command."""
        )
        if not ctx.character_data["marriage"]:
            return await ctx.send(_("You are not married yet."))
        if not await ctx.confirm(
            _(
                "Are you sure you want to divorce your partner? Some of your children"
                " may be given to your partner and your lovescore will be reset."
            )
        ):
            return await ctx.send(
                _("Cancelled the divorce. I guess the marriage is safe for now?")
            )
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "marriage"=0, "lovescore"=0 WHERE "user"=$1;',
                ctx.author.id,
            )
            await conn.execute(
                'UPDATE profile SET "marriage"=0, "lovescore"=0 WHERE "user"=$1;',
                ctx.character_data["marriage"],
            )
            await conn.execute(
                'UPDATE children SET "father"=0 WHERE "mother"=$1;', ctx.author.id
            )
            await conn.execute(
                'UPDATE children SET "father"=0 WHERE "mother"=$1;',
                ctx.character_data["marriage"],
            )
        await self.bot.cache.update_profile_cols_abs(
            ctx.author.id, marriage=0, lovescore=0
        )
        await self.bot.cache.update_profile_cols_abs(
            ctx.character_data["marriage"], marriage=0, lovescore=0
        )
        await ctx.send(_("You are now divorced."))

    @has_char()
    @commands.command(brief=_("Show your partner"))
    @locale_doc
    async def relationship(self, ctx):
        _(
            """Show your partner's Discord Tag. This works fine across server.

            Only married players can use this command."""
        )
        if not ctx.character_data["marriage"]:
            return await ctx.send(_("You are not married yet."))
        partner = await rpgtools.lookup(self.bot, ctx.character_data["marriage"])
        await ctx.send(
            _("You are currently married to **{partner}**.").format(partner=partner)
        )

    @has_char()
    @commands.command(brief=_("Show a player's lovescore"))
    @locale_doc
    async def lovescore(self, ctx, user: UserWithCharacter = Author):
        _(
            """`[user]` - The user whose lovescore to show; defaults to oneself

            Show the lovescore a player has. Lovescore can be increased by their partner spoiling them or going on dates.

            Lovescore affects the [adventure bonus](https://wiki.idlerpg.xyz/index.php?title=Family#Adventure_Bonus) and the amount of children you can have."""
        )
        data = ctx.character_data if user == ctx.author else ctx.user_data
        if data["marriage"]:
            partner = await rpgtools.lookup(self.bot, data["marriage"])
        else:
            partner = _("noone")
        await ctx.send(
            _(
                "{user}'s overall love score is **{score}**. {user} is married to"
                " **{partner}**."
            ).format(user=user.name, score=data["lovescore"], partner=partner)
        )

    @has_char()
    @commands.command(brief=_("Increase your partner's lovescore"))
    @locale_doc
    async def spoil(self, ctx, item: IntFromTo(1, 40) = None):
        _(
            """`[item]` - The item to buy, a whole number from 1 to 40; if not given, displays the list of items

            Buy something for your partner to increase *their* lovescore. To increase your own lovescore, your partner should spoil you.

            Please note that these items are not usable and do not have an effect on gameplay, beside increasing lovescore.

            Only players who are married can use this command."""
        )
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
                'UPDATE profile SET "lovescore"="lovescore"+$1 WHERE "user"=$2;',
                item[1],
                ctx.character_data["marriage"],
            )
            await conn.execute(
                'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;',
                item[1],
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
        await self.bot.cache.update_profile_cols_rel(ctx.author.id, money=-item[1])
        await self.bot.cache.update_profile_cols_rel(
            ctx.character_data["marriage"], lovescore=item[1]
        )
        await ctx.send(
            _(
                "You bought a **{item}** for your partner and increased their love"
                " score by **{points}** points!"
            ).format(item=item[0], points=item[1])
        )
        user = await self.bot.get_user_global(ctx.character_data["marriage"])
        if not user:
            return await ctx.send(
                _("Failed to DM your spouse, could not find their Discord account")
            )
        await user.send(
            "**{author}** bought you a **{item}** and increased your love score by"
            " **{points}** points!".format(
                author=ctx.author, item=item[0], points=item[1]
            )
        )

    @has_char()
    @commands.command(brief=_("Take your partner on a date"))
    @locale_doc
    @user_cooldown(43200)
    async def date(self, ctx):
        _(
            """Take your partner on a date to increase *their* lovescore. To increase your own lovescore, your partner should go on a date with you.

            The lovescore gained from dates can range from 10 to 150 in steps of 10.

            Only players who are married can use this command.
            (This command has a cooldown of 12 hours.)"""
        )
        num = random.randint(1, 15) * 10
        marriage = ctx.character_data["marriage"]
        if not marriage:
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(_("You are not married yet."))
        await self.bot.pool.execute(
            'UPDATE profile SET "lovescore"="lovescore"+$1 WHERE "user"=$2;',
            num,
            marriage,
        )
        await self.bot.cache.update_profile_cols_rel(marriage, lovescore=num)

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
        text = _("This increased their lovescore by {num}").format(num=num)
        await ctx.send(f"{scenario} {text}")

    async def get_random_name(self, gender, avoid):
        if gender == "f":
            data = self.girlnames
        else:
            data = self.boynames
        name = random.choice(data).strip("\n")
        while name in avoid:
            name = random.choice(data)  # avoid duplicate names
        return name

    async def lovescore_up(self, ctx, marriage, max_, missing, toomany):
        additional = (
            ""
            if not toomany
            else _(
                "You already have {max_} children. You can increase this limit"
                " by increasing your lovescores to get {amount} more."
            ).format(max_=max_, amount=f"{missing:,}")
        )
        ls = random.randint(10, 50)
        await self.bot.pool.execute(
            'UPDATE profile SET "lovescore"="lovescore"+$1 WHERE "user"=$2 OR'
            ' "user"=$3;',
            ls,
            ctx.author.id,
            marriage,
        )
        await self.bot.cache.update_profile_cols_rel(marriage, lovescore=ls)
        await self.bot.cache.update_profile_cols_rel(ctx.author.id, lovescore=ls)
        return await ctx.send(
            _(
                "You had a lovely night and gained {ls} lovescore. 😏\n\n{additional}".format(
                    ls=ls, additional=additional
                )
            )
        )

    @has_char()
    @commands.guild_only()
    @user_cooldown(3600)
    @commands.command(
        aliases=["fuck", "sex", "breed"], brief=_("Have a child with your partner")
    )
    @locale_doc
    async def child(self, ctx):
        _(
            # xgettext: no-python-format
            """Have a child with your partner.

            Children on their own don't do much, but `{prefix}familyevent` can effect your money and crates.
            To have a child, your partner has to be on the server to accept the checkbox.

            There is a 50% chance that you will have a child, and a 50% chance to just *have fun* (if you know what I'm saying) and gain between 10 and 50 lovescore.
            When you have a child, there is a 50% chance for it to be a boy and a 50% chance to be a girl.

            Your partner and you can enter a name for your child once the bot prompts you to. (Do not include `{prefix}`)
            If you fail to choose a name in time, the bot will choose one for you from about 500 pre-picked ones.

            For identification purposes, you cannot have two children with the same name in your family, so make sure to pick a unique one.

            Only players who are married can use this command.
            (This command has a cooldown of 1 hour.)"""
        )
        marriage = ctx.character_data["marriage"]
        if not marriage:
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(_("Can't produce a child alone, can you?"))
        async with self.bot.pool.acquire() as conn:
            names = await conn.fetch(
                'SELECT name FROM children WHERE "mother"=$1 OR "father"=$1;',
                ctx.author.id,
            )
            spouse = await self.bot.cache.get_profile_col(
                marriage, "lovescore", conn=conn
            )
        max_, missing = self.get_max_kids(ctx.character_data["lovescore"] + spouse)
        names = [name["name"] for name in names]
        user = await self.bot.get_user_global(marriage)
        if not await ctx.confirm(
            _("{user}, do you want to make a child with {author}?").format(
                user=user.mention, author=ctx.author.mention
            ),
            user=user,
        ):
            return await ctx.send(_("O.o not in the mood today?"))

        if len(names) >= max_:
            return await self.lovescore_up(ctx, marriage, max_, missing, True)

        if random.choice([True, False]):
            return await self.lovescore_up(ctx, marriage, max_, missing, False)
        gender = random.choice(["m", "f"])
        if gender == "m":
            await ctx.send(
                _(
                    "It's a boy! Your night of love was successful! Please enter a name"
                    " for your child."
                )
            )
        elif gender == "f":
            await ctx.send(
                _(
                    "It's a girl! Your night of love was successful! Please enter a"
                    " name for your child."
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
                await ctx.send(
                    _("You didn't enter a name, so we chose {name} for you.").format(
                        name=name
                    )
                )
                break
            if name in names:
                await ctx.send(
                    _(
                        "One of your children already has that name, please choose"
                        " another one."
                    )
                )
                name = None
        await self.bot.pool.execute(
            'INSERT INTO children ("mother", "father", "name", "age", "gender")'
            " VALUES ($1, $2, $3, $4, $5);",
            ctx.author.id,
            marriage,
            name,
            0,
            gender,
        )
        await ctx.send(_("{name} was born.").format(name=name))

    @has_char()
    @commands.command(brief=_("View your children"))
    @locale_doc
    async def family(self, ctx):
        _("""View your children. This will display their name, age and gender.""")
        marriage = ctx.character_data["marriage"]
        children = await self.bot.pool.fetch(
            'SELECT * FROM children WHERE ("mother"=$1 AND "father"=$2) OR ("father"=$1'
            ' AND "mother"=$2);',
            ctx.author.id,
            marriage,
        )

        additional = (
            _("{amount} children").format(amount=len(children))
            if len(children) != 1
            else _("one child")
        )
        em = discord.Embed(
            title=_("Your family, {additional}.").format(additional=additional),
            description=_("{author}'s family").format(author=ctx.author.mention)
            if not marriage
            else _("Family of {author} and <@{marriage}>").format(
                author=ctx.author.mention, marriage=marriage
            ),
        )
        if not children:
            em.add_field(
                name=_("No children yet"),
                value=_("Use `{prefix}child` to make one!").format(prefix=ctx.prefix)
                if marriage
                else _(
                    "Get yourself a partner and use `{prefix}child` to make one!"
                ).format(prefix=ctx.prefix),
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
            em.set_thumbnail(url=ctx.author.avatar.url)
            await ctx.send(embed=em)
        else:
            embeds = []
            children_lists = list(chunks(children, 9))
            for small_list in children_lists:
                em = discord.Embed(
                    title=_("Your family, {additional}.").format(additional=additional),
                    description=_("{author}'s family").format(author=ctx.author.mention)
                    if not marriage
                    else _("Family of {author} and <@{marriage}>").format(
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
    @commands.command(aliases=["fe"], brief=_("Events happening to your family"))
    @locale_doc
    async def familyevent(self, ctx):
        _(
            """Allow your children to do something, this includes a multitude of events.

            Every time you or your partner uses this command, your children:
              - have an 8/23 chance to grow older by one year
              - have a 4/23 chance to be renamed
              - have a 4/23 chance to take up to 1/64th of your money
              - have a 4/23 chance to give you up to 1/64th of your current money extra
              - have a 2/23 chance to find a random crate for you:
                + 500/761 (65%) chance for a common crate
                + 200/761 (26%) chance for an uncommon crate
                + 50/761 (6%) chance for a rare crate
                + 10/761 (1%) chance for a magic crate
                + 1/761 (0.1%) chance for a legendary crate
              - have a 1/23 chance to die

            In each event you will know what happened.

            Only players who are married and have children can use this command.
            (This command has a cooldown of 30 minutes.)"""
        )
        children = await self.bot.pool.fetch(
            'SELECT * FROM children WHERE ("mother"=$1 AND "father"=$2) OR ("father"=$1'
            ' AND "mother"=$2);',
            ctx.author.id,
            ctx.character_data["marriage"],
        )
        if not children:
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(_("You don't have kids yet."))
        target = random.choice(children)
        event = random.choice(
            ["death"]
            + ["age"] * 8
            + ["namechange"] * 4
            + ["crate"] * 2
            + ["moneylose"] * 4
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
                        "They have finally decided to move out after all these years,"
                        " but couldn't survive a second alone."
                    ),
                    _("Spontaneous combustion removed them from existence."),
                    _("While exploring the forest, they have gotten lost."),
                    _("They've left through a portal into another dimension..."),
                    _(
                        "The unbearable pain of stepping on a Lego\© brick killed them."  # noqa
                    ),
                    _("You heard a landmine going off nearby..."),
                    _("They have been abducted by aliens!"),
                    _("The Catholic Church got them..."),
                    _("They starved after becoming a communist."),
                ]
            )
            await self.bot.pool.execute(
                'DELETE FROM children WHERE "name"=$1 AND (("mother"=$2 AND'
                ' "father"=$4) OR ("father"=$2 AND "mother"=$4)) AND "age"=$3;',
                target["name"],
                ctx.author.id,
                target["age"],
                ctx.character_data["marriage"],
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
                        "fell in love with a woman on the internet, but the woman was a"
                        " man and stole their money."
                    ),
                    _("has been arrested and had to post bail."),
                    _("bought fortnite skins with your credit card."),
                    _("decided to become communist and gave the money to others."),
                    _("was caught pickpocketing and you had to pay the fine."),
                    _("gave it to a beggar."),
                    _("borrowed it to attend the local knights course."),
                    _("spent it in the shop."),
                    _("bought some toys."),
                    _("has gambling addiction and lost the money..."),
                ]
            )
            money = random.randint(0, int(ctx.character_data["money"] / 64))
            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;',
                    money,
                    ctx.author.id,
                )
                await self.bot.log_transaction(
                    ctx,
                    from_=ctx.author.id,
                    to=2,
                    subject="money",
                    data={"Amount": -money},
                    conn=conn,
                )
            await self.bot.cache.update_profile_cols_rel(ctx.author.id, money=-money)

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
            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                    money,
                    ctx.author.id,
                )
                await self.bot.log_transaction(
                    ctx,
                    from_=1,
                    to=ctx.author.id,
                    subject="money",
                    data={"Amount": money},
                    conn=conn,
                )
            await self.bot.cache.update_profile_cols_rel(ctx.author.id, money=money)
            return await ctx.send(
                _("{name} gave you ${money}, they {cause}").format(
                    name=target["name"], money=money, cause=cause
                )
            )
        elif event == "crate":
            type_ = random.choice(
                ["common"] * 500
                + ["uncommon"] * 200
                + ["rare"] * 50
                + ["magic"] * 10
                + ["legendary"]
            )
            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    f'UPDATE profile SET "crates_{type_}"="crates_{type_}"+1 WHERE'
                    ' "user"=$1;',
                    ctx.author.id,
                )
                await self.bot.log_transaction(
                    ctx,
                    from_=ctx.author.id,
                    to=2,
                    subject="crates",
                    data={"Rarity": type_, "Amount": 1},
                    conn=conn,
                )
            await self.bot.cache.update_profile_cols_rel(
                ctx.author.id, **{f"crates_{type_}": 1}
            )
            emoji = getattr(self.bot.cogs["Crates"].emotes, type_)
            return await ctx.send(
                _("{name} found a {emoji} {type_} crate for you!").format(
                    name=target["name"], emoji=emoji, type_=type_
                )
            )
        elif event == "age":
            await self.bot.pool.execute(
                'UPDATE children SET "age"="age"+1 WHERE "name"=$1 AND (("mother"=$2'
                ' AND "father"=$4) OR ("father"=$2 AND "mother"=$4)) AND "age"=$3;',
                target["name"],
                ctx.author.id,
                target["age"],
                ctx.character_data["marriage"],
            )
            return await ctx.send(
                _("{name} is now {age} years old.").format(
                    name=target["name"], age=target["age"] + 1
                )
            )
        elif event == "namechange":
            names = [c["name"] for c in children]
            names.remove(target["name"])

            def check(msg):
                return (
                    msg.author.id in [ctx.author.id, ctx.character_data["marriage"]]
                    and msg.channel.id == ctx.channel.id
                )

            name = None
            while not name:
                await ctx.send(
                    _(
                        "{name} can be renamed! Within 30 seconds, enter a new"
                        " name:\nType `cancel` to leave the name unchanged."
                    ).format(name=target["name"])
                )
                try:
                    msg = await self.bot.wait_for("message", check=check, timeout=30)
                    name = msg.content.replace("@", "@\u200b")
                except asyncio.TimeoutError:
                    return await ctx.send(_("You didn't enter a name."))
                if name.lower() == "cancel":
                    return await ctx.send(_("You didn't want to rename."))
                if len(name) == 0 or len(name) > 20:
                    await ctx.send(_("Name must be 1 to 20 characters only."))
                    name = None
                    continue
                if name in names:
                    await ctx.send(
                        _(
                            "One of your children already has that name, please choose"
                            " another one."
                        )
                    )
                    name = None
                    continue
                try:
                    if not await ctx.confirm(
                        _(
                            '{author} Are you sure you want to rename "{old_name}" to'
                            ' "{new_name}"?'
                        ).format(
                            author=ctx.author.mention,
                            old_name=target["name"],
                            new_name=name,
                        )
                    ):
                        await ctx.send(
                            _('You didn\'t change the name to "{new_name}".').format(
                                new_name=name
                            )
                        )
                        name = None
                        await self.bot.set_cooldown(ctx, 1800)
                except self.bot.paginator.NoChoice:
                    await ctx.send(_("You didn't confirm."))
                    name = None

            if name == target["name"]:
                return await ctx.send(_("You didn't change their name."))
            await self.bot.pool.execute(
                'UPDATE children SET "name"=$1 WHERE "name"=$2 AND (("mother"=$3 AND'
                ' "father"=$5) OR ("father"=$3 AND "mother"=$5)) AND "age"=$4;',
                name,
                target["name"],
                ctx.author.id,
                target["age"],
                ctx.character_data["marriage"],
            )
            return await ctx.send(
                _("{old_name} is now called {new_name}.").format(
                    old_name=target["name"], new_name=name
                )
            )


def setup(bot):
    bot.add_cog(Marriage(bot))
