"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import asyncio
import random

import discord
from discord.ext import commands

from classes.converters import IntFromTo, MemberWithCharacter
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import misc as rpgtools
from utils.checks import has_char


class Marriage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @commands.guild_only()
    @commands.command(aliases=["marry"])
    async def propose(self, ctx, partner: MemberWithCharacter):
        """Propose for a marriage."""
        if partner == ctx.author:
            return await ctx.send("You should have a better friend than only yourself.")
        if ctx.character_data["marriage"] != 0 or ctx.user_data["marriage"] != 0:
            return await ctx.send("One of you is married.")
        msg = await ctx.send(
            embed=discord.Embed(
                title=f"{ctx.author.name} has proposed for a marriage!",
                description=f"{ctx.author.mention} wants to marry you, {partner.mention}! React with :heart: to marry him/her!",
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
            return await ctx.send("They didn't want to marry.")
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
                    f"Owwwwwww! :heart: {ctx.author.mention} and {partner.mention} are now married!"
                )
            else:
                await ctx.send(
                    f"Either you or he/she married in the meantime, {ctx.author.mention}... :broken_heart:"
                )

    @has_char()
    @commands.command()
    async def divorce(self, ctx):
        """Break up with your partner."""
        if not ctx.character_data["marriage"]:
            return await ctx.send("You are not married yet.")
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "marriage"=0 WHERE "user"=$1;', ctx.author.id
            )
            await conn.execute(
                'UPDATE profile SET "marriage"=0 WHERE "user"=$1;',
                ctx.character_data["marriage"],
            )
            await conn.execute(
                'DELETE FROM children WHERE "father"=$1 OR "mother"=$2;',
                ctx.author.id,
                ctx.author.id,
            )
        await ctx.send("You are now divorced.")

    @has_char()
    @commands.command()
    async def relationship(self, ctx):
        """View who you're married to."""
        if not ctx.character_data["marriage"]:
            return await ctx.send("You are not married yet.")
        partner = await rpgtools.lookup(self.bot, ctx.character_data["marriage"])
        await ctx.send(f"You are currently married to **{partner}**.")

    @has_char()
    @commands.command()
    async def lovescore(self, ctx):
        """Views your lovescore."""
        if ctx.character_data["marriage"]:
            partner = await rpgtools.lookup(self.bot, ctx.character_data["marriage"])
        else:
            partner = "noone"
        await ctx.send(
            f"Your overall love score is **{ctx.character_data['lovescore']}**. You are married to **{partner}**."
        )

    @has_char()
    @commands.command()
    async def spoil(self, ctx, item: IntFromTo(1, 40) = None):
        """Buy something for your spouse and increase their lovescore."""
        items = [
            ("Dog :dog2:", 50),
            ("Cat :cat2:", 50),
            ("Cow :cow2:", 75),
            ("Penguin :penguin:", 100),
            ("Unicorn :unicorn:", 1000),
            ("Potato :potato:", 1),
            ("Sweet potato :sweet_potato:", 2),
            ("Peach :peach:", 5),
            ("Ice Cream :ice_cream:", 10),
            ("Bento Box :bento:", 50),
            ("Movie Night :ticket:", 75),
            ("Video Game Night :video_game:", 10),
            ("Camping Night :fishing_pole_and_fish:", 15),
            ("Couple Competition :trophy:", 30),
            ("Concert Night :musical_keyboard:", 100),
            ("Bicycle :bike:", 100),
            ("Motorcycle :motorcycle:", 250),
            ("Car :red_car:", 300),
            ("Private Jet :airplane:", 1000),
            ("Space Rocket :rocket:", 10000),
            ("Credit Card :credit_card:", 20),
            ("Watch :watch:", 100),
            ("Phone :iphone:", 100),
            ("Bed :bed:", 500),
            ("Home films :projector:", 750),
            ("Satchel :school_satchel:", 25),
            ("Purse :purse:", 30),
            ("Shoes :athletic_shoe:", 150),
            ("Casual Attire :shirt:", 200),
            ("Ring :ring:", 1000),
            ("Balloon :balloon:", 10),
            ("Flower Bouquet :bouquet:", 25),
            ("Expensive Chocolates :chocolate_bar:", 40),
            ("Declaration of Love :love_letter:", 50),
            ("Key to Heart :key2:", 100),
            ("Ancient Vase :amphora:", 15000),
            ("House :house:", 25000),
            ("Super Computer :computer:", 50000),
            ("Precious Gemstone Collection :gem:", 75000),
            ("Planet :earth_americas:", 1_000_000),
        ]
        items_str = "\n".join(
            [
                f"{idx + 1}.) {item} ... Price: **${price}**"
                for idx, (item, price) in enumerate(items)
            ]
        )
        if not item:
            return await ctx.send(
                f"{items_str}\n\nTo buy one of these items for your partner, use `{ctx.prefix}spoil shopid`"
            )
        item = items[item - 1]
        if ctx.character_data["money"] < item[1]:
            return await ctx.send("You are too poor to buy this.")
        if not ctx.character_data["marriage"]:
            return await ctx.send("You're not married yet.")
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
            f"You bought a **{item[0]}** for your partner and increased their love score by **{item[1]}** points!"
        )
        user = await self.bot.get_user_global(ctx.character_data["marriage"])
        if not user:
            return await ctx.send(
                "Failed to DM your spouse, could not find their discord account"
            )
        await user.send(
            f"**{ctx.author}** bought you a **{item[0]}** and increased your love score by **{item[1]}** points!"
        )

    @has_char()
    @commands.command()
    @user_cooldown(43200)
    async def date(self, ctx):
        """Take your loved one on a date to increase your lovescore."""
        num = random.randint(1, 15) * 10
        marriage = ctx.character_data["marriage"]
        if not marriage:
            await self.bot.reset_cooldown(ctx)
            return await ctx.send("You are not married yet.")
        await self.bot.pool.execute(
            'UPDATE profile SET lovescore=lovescore+$1 WHERE "user"=$2;', num, marriage
        )

        partner = await self.bot.get_user_global(marriage)
        scenario = random.choice(
            [
                f"You and {partner.mention} went on a nice candlelit dinner.",
                f"You and {partner.mention} had stargazed all night.",
                f"You and {partner.mention} went to a circus that was in town.",
                f"You and {partner.mention} went out to see a romantic movie.",
                f"You and {partner.mention} went out to get ice cream.",
                f"You and {partner.mention} had an anime marathon.",
                f"You and {partner.mention} went for a spontaneous hiking trip.",
                f"You and {partner.mention} decided to visit Paris.",
                f"You and {partner.mention} went ice skating together.",
            ]
        )
        await ctx.send(f"{scenario} This increased your lovescore by {num}")

    @has_char()
    @commands.guild_only()
    @user_cooldown(3600)
    @commands.command(aliases=["fuck", "sex", "breed"])
    async def child(self, ctx):
        """Make a child with your spouse."""
        marriage = ctx.character_data["marriage"]
        if not marriage:
            return await ctx.send("Can't produce a child alone, can you?")
        names = await self.bot.pool.fetch(
            'SELECT name FROM children WHERE "mother"=$1 OR "father"=$1;', ctx.author.id
        )
        if len(names) >= 10:
            return await ctx.send("You already have 10 children.")
        names = [name["name"] for name in names]
        if not await ctx.confirm(
            f"<@{marriage}>, do you want to make a child with {ctx.author.mention}?"
        ):
            return await ctx.send("O.o not in the mood today?")

        if random.randint(1, 2) == 1:
            return await ctx.send("You were unsuccessful at making a child.")
        gender = random.choice(["m", "f"])
        if gender == "m":
            await ctx.send(
                "It's a boy! Your night of love was successful! Please enter a name for your child."
            )
        elif gender == "f":
            await ctx.send(
                "It's a girl! Your night of love was successful! Please enter a name for your child."
            )

        def check(msg):
            return (
                msg.author.id in [ctx.author.id, marriage]
                and len(msg.content) <= 20
                and msg.content not in names
                and msg.channel.id == ctx.channel.id
            )

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            return await ctx.send("You didn't enter a name.")
        name = msg.content.replace("@", "@\u200b")
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO children ("mother", "father", "name", "age", "gender") VALUES ($1, $2, $3, $4, $5);',
                ctx.author.id,
                marriage,
                name,
                0,
                gender,
            )
        await ctx.send(f"{name} was born.")

    @has_char()
    @commands.command()
    async def family(self, ctx):
        """View your children."""
        marriage = ctx.character_data["marriage"]
        if not marriage:
            return await ctx.send("Lonely...")
        children = await self.bot.pool.fetch(
            'SELECT * FROM children WHERE "mother"=$1 OR "father"=$1;', ctx.author.id
        )
        em = discord.Embed(
            title="Your family",
            description=f"Family of {ctx.author.mention} and <@{marriage}>",
        )
        if not children:
            em.add_field(
                name="No children yet", value=f"Use {ctx.prefix}child to make one!"
            )
        for child in children:
            em.add_field(
                name=child["name"],
                value=f"Gender: {child['gender']}, Age: {child['age']}",
                inline=False,
            )
        em.set_thumbnail(url=ctx.author.avatar_url)
        await ctx.send(embed=em)

    @has_char()
    @user_cooldown(1800)
    @commands.command()
    async def familyevent(self, ctx):
        """Events happening to your family."""
        if not ctx.character_data["marriage"]:
            return await ctx.send("You're lonely.")
        children = await self.bot.pool.fetch(
            'SELECT * FROM children WHERE "mother"=$1 OR "father"=$1;', ctx.author.id
        )
        if not children:
            return await ctx.send("You don't have kids yet.")
        target = random.choice(children)
        event = random.choice(["death"] + ["age"] * 7 + ["namechange"] * 2)
        if event == "death":
            cause = random.choice(
                [
                    "They died because of a shampoo overdose!",
                    "They died of lovesickness...",
                    "They've died of age.",
                    "They died of loneliness.",
                    "A horde of goblins got them.",
                    "They have finally decided to move out after all these years, but couldn't survive a second alone.",
                    "Spontaneous combustion removed them from existence.",
                    "While exploring the forest, they have gotten lost.",
                    "They've left through a portal into another dimension...",
                    "The unbearable pain of stepping on a Lego\© brick killed them.",  # noqa
                    "You heard a landmine going off nearby...",
                    "They have been abducted by aliens!",
                    "The Catholic Church got them...",
                ]
            )
            await self.bot.pool.execute(
                'DELETE FROM children WHERE "name"=$1 AND ("mother"=$2 OR "father"=$2);',
                target["name"],
                ctx.author.id,
            )
            return await ctx.send(
                f"{target['name']} died at the age of {target['age']}! {cause}"
            )
        elif event == "age":
            await self.bot.pool.execute(
                'UPDATE children SET age=age+1 WHERE "name"=$1 AND ("mother"=$2 OR "father"=$2);',
                target["name"],
                ctx.author.id,
            )
            return await ctx.send(
                f"{target['name']} is now {target['age'] + 1} years old."
            )
        elif event == "namechange":
            await ctx.send(f"{target['name']} can be renamed! Enter a new name:")
            names = [c["name"] for c in children]
            names.remove(target["name"])

            def check(msg):
                return (
                    msg.author.id in [ctx.author.id, ctx.character_data["marriage"]]
                    and msg.channel.id == ctx.channel.id
                    and len(msg.content) <= 20
                    and msg.content not in names
                )

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=30)
            except asyncio.TimeoutError:
                return await ctx.send("You didn't enter a name.")
            name = msg.content.replace("@", "@\u200b")
            await self.bot.pool.execute(
                'UPDATE children SET "name"=$1 WHERE "name"=$2 AND ("mother"=$3 OR "father"=$3);',
                name,
                target["name"],
                ctx.author.id,
            )
            return await ctx.send(f"{target['name']} is now called {name}.")


def setup(bot):
    bot.add_cog(Marriage(bot))
