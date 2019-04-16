"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""


import discord
import asyncio
import random

from cogs.shard_communication import user_on_cooldown as user_cooldown
from discord.ext import commands
from utils import misc as rpgtools
from utils.checks import has_char, has_money


class Marriage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @commands.guild_only()
    @commands.command(aliases=["marry"], description="Propose for a marriage!")
    async def propose(self, ctx, partner: discord.Member):
        if partner.id == ctx.author.id:
            return await ctx.send("You should have a better friend than only yourself.")
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

            except asyncio.TimeoutError:
                await ctx.send("They didn't want to marry.")
        else:
            await ctx.send(
                "One of you both doesn't have a character or is already married... :broken_heart:"
            )

    @has_char()
    @commands.command(description="Divorce from your partner.")
    async def divorce(self, ctx):
        async with self.bot.pool.acquire() as conn:
            test = await conn.fetchval(
                'SELECT marriage FROM profile WHERE "user"=$1;', ctx.author.id
            )
            if test == 0:
                return await ctx.send("You are not married yet.")
            await conn.execute(
                'UPDATE profile SET "marriage"=0 WHERE "user"=$1;', ctx.author.id
            )
            await conn.execute('UPDATE profile SET "marriage"=0 WHERE "user"=$1;', test)
            await conn.execute(
                'DELETE FROM children WHERE "father"=$1 OR "mother"=$2;',
                ctx.author.id,
                ctx.author.id,
            )
        await ctx.send("You are now divorced.")

    @has_char()
    @commands.command(description="View your marriage status.")
    async def relationship(self, ctx):
        async with self.bot.pool.acquire() as conn:
            marriage = await conn.fetchval(
                'SELECT marriage FROM profile WHERE "user"=$1;', ctx.author.id
            )
        if marriage == 0:
            return await ctx.send("You are not married yet.")
        partner = await rpgtools.lookup(self.bot, marriage)
        await ctx.send(f"You are currently married to **{partner}**.")

    @has_char()
    @commands.command(description="Views your love score.")
    async def lovescore(self, ctx):
        async with self.bot.pool.acquire() as conn:
            score = await conn.fetchrow(
                'SELECT lovescore, marriage FROM profile WHERE "user"=$1;',
                ctx.author.id,
            )
        if score[1] != 0:
            partner = await rpgtools.lookup(self.bot, score[1])
        else:
            partner = "noone"
        await ctx.send(
            f"Your overall love score is **{score[0]}**. You are married to **{partner}**."
        )

    @has_char()
    @commands.command(
        description="Buy something for your love and increase their score!"
    )
    async def spoil(self, ctx, item: int = None):
        items = [
            [0, "Dog :dog2:", 50],
            [1, "Cat :cat2:", 50],
            [2, "Cow :cow2:", 75],
            [3, "Penguin :penguin:", 100],
            [4, "Unicorn :unicorn:", 1000],
            [5, "Potato :potato:", 1],
            [6, "Sweet potato :sweet_potato:", 2],
            [7, "Peach :peach:", 5],
            [8, "Ice Cream :ice_cream:", 10],
            [9, "Bento Box :bento:", 50],
            [10, "Movie Night :ticket:", 7],
            [11, "Video Game Night :video_game:", 10],
            [12, "Camping Night :fishing_pole_and_fish:", 15],
            [13, "Couple Competition :trophy:", 30],
            [14, "Concert Night :musical_keyboard:", 100],
            [15, "Bicycle :bike:", 100],
            [16, "Motorcycle :motorcycle:", 250],
            [17, "Car :red_car:", 300],
            [18, "Private Jet :airplane:", 1000],
            [19, "Space Rocket :rocket:", 10000],
            [20, "Credit Card :credit_card:", 20],
            [21, "Watch :watch:", 100],
            [22, "Phone :iphone:", 100],
            [23, "Bed :bed:", 500],
            [24, "Home films :projector:", 750],
            [25, "Satchel :school_satchel:", 25],
            [26, "Purse :purse:", 30],
            [27, "Shoes :athletic_shoe:", 150],
            [28, "Casual Attire :shirt:", 200],
            [29, "Ring :ring:", 1000],
            [30, "Balloon :balloon:", 10],
            [31, "Flower Bouquet :bouquet:", 25],
            [32, "Expensive Chocolates :chocolate_bar:", 40],
            [33, "Declaration of Love :love_letter:", 50],
            [34, "Key to Heart :key2:", 100],
            [35, "Ancient Vase :amphora:", 15000],
            [36, "House :house:", 25000],
            [37, "Super Computer :computer:", 50000],
            [38, "Precious Gemstone Collection :gem:", 75000],
            [39, "Planet :earth_americas:", 1_000_000],
        ]
        nl = "\n"
        if item is None:
            shop = f"""
{nl.join([str(item[0])+') '+item[1]+' ... Price: **$'+str(item[2])+'**' for item in items])}

To buy one of these items for your partner, use `{ctx.prefix}spoil shopid`
"""
            return await ctx.send(shop)
        elif item not in range(len(items)):
            return await ctx.send("That's not a valid item to buy.")
        item = items[item]
        if not await has_money(self.bot, ctx.author.id, item[2]):
            return await ctx.send("You are too poor to buy this.")
        async with self.bot.pool.acquire() as conn:
            marriage = await conn.fetchval(
                'SELECT marriage FROM profile WHERE "user"=$1;', ctx.author.id
            )
            if marriage == 0:
                return await ctx.send("You are not married.")
            await conn.execute(
                'UPDATE profile SET lovescore=lovescore+$1 WHERE "user"=$2;',
                item[2],
                marriage,
            )
            await conn.execute(
                'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                item[2],
                ctx.author.id,
            )
        await ctx.send(
            f"You bought a **{item[1]}** for your partner and increased their love score by **{item[2]}** points!"
        )
        user = await self.bot.get_user_global(marriage)
        if not user:
            return await ctx.send(
                "Failed to DM your spouse, could not find their discord account"
            )
        await user.send(
            f"**{ctx.author}** bought you a **{item[1]}** and increased your love score by **{item[2]}** points!"
        )
        
    @has_char()
    @commands.command(name="date")
    @user_cooldown(43200)
    async def _date(self, ctx):
        """Take your loved one on a date to increase your lovescore."""
        num = random.randint(1, 15) * 10
        marriage = ctx.character_data["marriage"]
        if not marriage:
            await ctx.send("You are not married yet.")
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET lovescore=lovescore+$1 WHERE "user"=$2;',
                num,
                marriage,
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
    @commands.command(description="Make a child!", aliases=["fuck", "sex", "breed"])
    async def child(self, ctx):
        async with self.bot.pool.acquire() as conn:
            marriage = await conn.fetchval(
                'SELECT marriage FROM profile WHERE "user"=$1;', ctx.author.id
            )
            count = await conn.fetchval(
                'SELECT count(*) FROM children WHERE "mother"=$1 OR "father"=$2;',
                ctx.author.id,
                ctx.author.id,
            )
            names = await conn.fetch(
                'SELECT name FROM children WHERE "mother"=$1 OR "father"=$2;',
                ctx.author.id,
                ctx.author.id,
            )
        if marriage == 0:
            return await ctx.send("You are not married yet.")
        elif count >= 10:
            return await ctx.send("You already have 10 children.")
        names = [name[0] for name in names]
        msg = await ctx.send(
            f"Asking <@{marriage}> for a night...\nDo you want to make a child with {ctx.author.mention}? Type `I do`"
        )

        def check(msg):
            return (
                msg.author.id == marriage
                and msg.content.lower() == "i do"
                and msg.channel.id == ctx.channel.id
            )

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            return await ctx.send(f"They didn't want to have a child :(")
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
    @commands.command(description="View your children.")
    async def family(self, ctx):
        async with self.bot.pool.acquire() as conn:
            marriage = await conn.fetchval(
                'SELECT marriage FROM profile WHERE "user"=$1;', ctx.author.id
            )
            if marriage == 0:
                return await ctx.send("You are not married yet.")
            children = await conn.fetch(
                'SELECT * FROM children WHERE "mother"=$1 OR "father"=$1;',
                ctx.author.id,
            )
        em = discord.Embed(
            title="Your family",
            description=f"Family of {ctx.author.mention} and <@{marriage}>",
        )
        if children == []:
            em.add_field(
                name="No children yet", value=f"Use {ctx.prefix}child to make one!"
            )
        for child in children:
            em.add_field(
                name=child[2] or "Unnamed",
                value=f"Gender: {child[4]}, Age: {child[3]}",
                inline=False,
            )
        em.set_thumbnail(url=ctx.author.avatar_url)
        await ctx.send(embed=em)

    @has_char()
    @user_cooldown(1800)
    @commands.command(description="Events happening to your family.")
    async def familyevent(self, ctx):
        async with self.bot.pool.acquire() as conn:
            marriage = await conn.fetchval(
                'SELECT marriage FROM profile WHERE "user"=$1;', ctx.author.id
            )
            if marriage == 0:
                return await ctx.send("You are not married yet.")
            children = await conn.fetch(
                'SELECT * FROM children WHERE "mother"=$1 OR "father"=$1;',
                ctx.author.id,
            )
        if children == []:
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
                    "Spontanious combustion removed them from existence",
                    "While exploring the forest, they have gotten lost.",
                    "They've left through a portal into another dimension...",
                    "The unbearable pain of stepping on a Lego\© brick killed them.",  # noqa
                    "You heard a landmine going off nearby...",
                    "They have been abducted by aliens!",
                    "The Catholic Church got them...",
                ]
            )
            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    'DELETE FROM children WHERE "name"=$1 AND ("mother"=$2 OR "father"=$2);',
                    target[2],
                    ctx.author.id,
                )
            return await ctx.send(
                f"{target[2]} died at the age of {target[3]}! {cause}"
            )
        elif event == "age":
            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    'UPDATE children SET age=age+1 WHERE "name"=$1 AND ("mother"=$2 OR "father"=$2);',
                    target[2],
                    ctx.author.id,
                )
            return await ctx.send(f"{target[2]} is now {target[3]+1} years old.")
        elif event == "namechange":
            await ctx.send(f"{target[2]} can be renamed! Enter a new name:")

            def check(msg):
                return (
                    msg.author.id in [ctx.author.id, marriage]
                    and msg.channel.id == ctx.channel.id
                    and len(msg.content) <= 20
                )

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=30)
            except asyncio.TimeoutError:
                return await ctx.send("You didn't enter a name.")
            name = msg.content.replace("@", "@\u200b")
            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    'UPDATE children SET "name"=$1 WHERE "name"=$2 AND ("mother"=$3 OR "father"=$3);',
                    name,
                    target[2],
                    ctx.author.id,
                )
            return await ctx.send(f"{target[2]} is now called {name}.")


def setup(bot):
    bot.add_cog(Marriage(bot))
