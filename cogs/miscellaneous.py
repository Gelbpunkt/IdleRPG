"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import asyncio
import datetime
import platform
import random
from datetime import date

import discord
import pkg_resources as pkg
import psutil
from discord.ext import commands
from discord.ext.commands import BucketType

from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils.checks import has_char


class Miscellaneous(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def dab(self, ctx):
        """Let's dab together."""
        await ctx.send("No. Just no. I am a bot. What did you think?")

    @has_char()
    @user_cooldown(86400)
    @commands.command()
    async def daily(self, ctx):
        """Receive a daily reward based on your streak."""
        streak = await self.bot.redis.execute("INCR", f"idle:daily:{ctx.author.id}")
        await self.bot.redis.execute(
            "EXPIRE", f"idle:daily:{ctx.author.id}", 48 * 60 * 60
        )  # 48h: after 2 days, they missed it
        money = 2 ** ((streak + 9) % 10) * 50
        await self.bot.pool.execute(
            'UPDATE profile SET money=money+$1 WHERE "user"=$2;', money, ctx.author.id
        )
        await ctx.send(
            f"You received your daily **${money}**!\nYou are on a streak of **{streak}** days!"
        )

    @commands.command()
    async def ping(self, ctx):
        """My current websocket latency."""
        await ctx.send(
            embed=discord.Embed(
                title="Pong!",
                description=f"My current latency is {round(self.bot.latency*1000, 2)}ms",
                color=0xF1C60C,
            )
        )

    @commands.command(aliases=["donate"])
    async def patreon(self, ctx):
        """Support maintenance of the bot."""
        guild_count = sum(
            await self.bot.cogs["Sharding"].handler("guild_count", self.bot.shard_count)
        )
        await ctx.send(
            f"This bot has its own patreon page.\n\n**Why should I donate?**\nThis bot is currently on {guild_count} servers, and it is growing"
            " fast.\nHosting this bot for all users is not easy and costs money.\nIf you want to continue using the bot or just help us, please donate a small amount.\nEven"
            " $1 can help us.\n**Thank you!**\n\n<https://patreon.com/idlerpg>"
        )

    @commands.command()
    async def invite(self, ctx):
        """Invite link for the bot."""
        await ctx.send(
            f"You are running version **{self.bot.version}** by Adrian.\nInvite me! "
            f"<https://discordapp.com/oauth2/authorize?client_id={self.bot.user.id}&scope=bot&permissions=8>"
        )

    @commands.command()
    async def support(self, ctx):
        """Information on the support server."""
        await ctx.send(
            "Got problems or feature requests? Looking for people to play with? Join the support server:\nhttps://discord.gg/axBKXBv"
        )

    @commands.command()
    async def stats(self, ctx):
        """Statistics on the bot."""
        async with self.bot.pool.acquire() as conn:
            characters = await conn.fetchval("SELECT COUNT(*) FROM profile;")
            items = await conn.fetchval("SELECT COUNT(*) FROM allitems;")
            pg_version = conn.get_server_version()
        pg_version = f"{pg_version.major}.{pg_version.minor}.{pg_version.micro} {pg_version.releaselevel}"
        total_online = len(
            {
                m.id
                for m in self.bot.get_all_members()
                if m.status is discord.Status.online
            }
        )
        total_idle = len(
            {
                m.id
                for m in self.bot.get_all_members()
                if m.status is discord.Status.idle
            }
        )
        total_dnd = len(
            {m.id for m in self.bot.get_all_members() if m.status is discord.Status.dnd}
        )
        total_offline = len(
            {
                m.id
                for m in self.bot.get_all_members()
                if m.status is discord.Status.offline
            }
        )
        d0 = date(2018, 3, 17)
        d1 = date.today()
        delta = d1 - d0
        myhours = delta.days * 1.5
        sysinfo = platform.linux_distribution()
        # owner = await self.bot.get_user_global(self.bot.owner_id)
        # sad that teams are fucky
        owner = " and ".join(
            [str(await self.bot.get_user_global(u)) for u in self.bot.config.owners]
        )
        guild_count = sum(
            await self.bot.cogs["Sharding"].handler("guild_count", self.bot.shard_count)
        )

        embed = discord.Embed(
            title="IdleRPG Statistics",
            colour=0xB8BBFF,
            url=self.bot.BASE_URL,
            description="Official Support Server Invite: https://discord.gg/MSBatf6",
        )
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.set_footer(
            text=f"IdleRPG {self.bot.version} | By {owner}",
            icon_url=self.bot.user.avatar_url,
        )
        embed.add_field(
            name="General Statistics (this instance only)",
            value=f"<:online:313956277808005120>{total_online}<:away:313956277220802560>{total_idle}<:dnd:313956276893646850>"
            f"{total_dnd}<:offline:313956277237710868>{total_offline}",
            inline=False,
        )
        embed.add_field(
            name="Hosting Statistics",
            value=f"CPU Usage: **{psutil.cpu_percent()}%**\nRAM Usage: **{psutil.virtual_memory().percent}%**\nPython Version"
            f" **{platform.python_version()}** <:python:445247273065250817>\ndiscord.py Version **{pkg.get_distribution('discord.py').version}**\nOperating System: "
            f"**{sysinfo[0].title()} {sysinfo[1].title()}**\nPostgreSQL Version **{pg_version}**",
            inline=False,
        )
        embed.add_field(
            name="Bot Statistics",
            value=f"Code lines written: **{self.bot.linecount}**\nShards: **{self.bot.shard_count}**\nServers: **{guild_count}**\nMembers: "
            f"**{len(self.bot.users)}**\nChannels: **{len(set(self.bot.get_all_channels()))}**\nCharacters: **{characters}**\nItems: **{items}**\nAverage hours of work: "
            f"**{myhours}**",
            inline=False,
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def roll(self, ctx, maximum: int):
        """Roll a random number."""
        if maximum < 0:
            return await ctx.send("Mustn't be negative!")
        await ctx.send(
            f":1234: You rolled **{random.randint(0,maximum)}**, {ctx.author.mention}!"
        )

    @commands.command()
    async def changelog(self, ctx):
        """The bot's update log."""
        await ctx.send(
            """
**IdleRPG v3.5 is released :tada:**
This update had 3 focuses:
    - Making the source code prettier
    - Making the bot more accessible (more reactions, less typing)
    - Making the bot have higher performance (we got only 3 more things of this kind to do, yay!)

**Soo... What's new?**
- Guild descriptions will show up in `$guild` and `$guild info`
- The new v5 item naming system was added (looong names will make profiles look weird though, we're working on new profiles)
- Confirmation is now done via ticking a box
- Active battles and adventures should be more fun due to reactions
- Joining challenges is now also reaction-based
- The shop and `$pending` are now embeds and paginated
- Internally, database calls were reduced by about 25-40%

**Have fun!!!** <:idlerpg:453946311524220949>

*Note: This is tested mostly, but not 100%. I appreciate bug reports.*
*GitHub folks update your forks and branches!*
"""
        )

    @commands.has_permissions(manage_messages=True)
    @commands.command()
    async def clear(self, ctx, num: int, target: discord.Member = None):
        """Deletes an amount of messages from the history, optionally only by one member."""
        if num > 1000 or num < 0:
            return await ctx.send("Invalid amount. Maximum is 1000.")

        def msgcheck(amsg):
            if target:
                return amsg.author.id == target.id
            return True

        await ctx.channel.purge(limit=num + 1, check=msgcheck)
        await ctx.send(f"👍 Deleted **{num}** messages for you.", delete_after=10)

    @commands.command(name="8ball")
    async def _ball(self, ctx, *, question: str):
        """The magic 8 ball answers your questions."""
        results = [
            "It is certain",
            "It is decidedly so",
            "Without a doubt",
            "Yes, definitely",
            "You may rely on it",
            "As I see it, yes",
            "Most likely",
            "Outlook good",
            "Yes",
            "Signs point to yes",
            "Reply hazy try again",
            "Ask again later",
            "Better not tell you now",
            "Cannot predict now",
            "Concentrate and ask again",
            "Don't count on it",
            "My reply is no",
            "My sources say no",
            "Outlook not so good",
            "Very doubtful",
        ]
        await ctx.send(f"The :8ball: says: **{random.choice(results)}**.")

    @commands.command(aliases=["say"])
    async def echo(self, ctx, *, phrase: str):
        """Repeats what you said."""
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        await ctx.send(phrase, escape_mentions=True)

    @commands.command()
    async def choose(self, ctx, *results: str):
        """Chooses a random option of supplied possiblies."""
        if not results:
            return await ctx.send("Cannot choose from an empty list...")
        results = list(filter(lambda a: a.lower() != "or", results))
        await ctx.send(
            f"My choice is: **{random.choice(results)}**.", escape_mentions=True
        )

    @commands.guild_only()
    @commands.command()
    async def love(self, ctx, first: discord.Member, second: discord.Member):
        """Calculates the potential love for 2 members."""
        msg = await ctx.send(
            embed=discord.Embed(
                description=f"Calculating Love for {first.mention} and {second.mention}...",
                color=0xFF0000,
            )
        )
        await asyncio.sleep(5)
        random.seed(int(str(first.id) + str(second.id)))
        if first == second:
            love = 100.00
        else:
            love = random.randint(1, 10000) / 100
        embed = discord.Embed(
            title="Love Calculation",
            description=f"Love for {first.mention} and {second.mention} is at **{love}%**! ❤",
            color=0xFF0000,
        )
        await msg.edit(embed=embed)

    @commands.command()
    async def fancy(self, ctx, *, text: str):
        """Fancies text with big emojis."""
        nums = [
            "zero",
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
        ]
        newtext = ""
        for letter in text:
            if letter.lower() in list(map(chr, range(97, 123))):
                newtext += f":regional_indicator_{letter.lower()}:"
            elif letter in [str(anum) for anum in range(10)]:
                newtext += f":{nums[int(letter)]}:"
            else:
                newtext += letter
        await ctx.send(newtext)

    @commands.command()
    async def meme(self, ctx):
        """A random bad meme."""
        async with self.bot.session.get(
            f"https://some-random-api.ml/meme?lol={random.randint(1,1000000)}"
        ) as resp:
            await ctx.send(
                embed=discord.Embed(color=0x0A00FF).set_image(
                    url=(await resp.json())["url"]
                )
            )

    @commands.command()
    async def dice(self, ctx, dice_type: str):
        """Tabletop RPG-ready dice. Rolls in the ndx format (3d20 is 3 dice with 20 sides)."""
        try:
            dice_type = list(map(int, dice_type.split("d")))
        except ValueError:
            await ctx.send(
                "Use the ndx format. E.g. `5d20` will roll 5 dices with 20 sides each."
            )
        if len(dice_type) != 2:
            return await ctx.send("Use the ndx format.")
        if dice_type[0] > 100:
            return await ctx.send("Too many dice.")
        if dice_type[1] <= 0:
            return await ctx.send("Dice must have at least one side.")
        results = []
        for _ in range(dice_type[0]):
            results.append(random.randint(1, dice_type[1]))
        sumall = 0
        for i in results:
            sumall += i
        if results:
            average = sumall / len(results)
        else:
            average = 0
        nl = "\n"
        results = [str(result) for result in results]
        await ctx.send(
            f"```Sum: {sumall}\nAverage: {average}\nResults:\n{nl.join(results)}```"
        )

    @commands.command()
    async def randomname(self, ctx):
        """Sends my nickname in a random server."""
        g = random.choice(
            [g for g in self.bot.guilds if g.me.display_name != self.bot.user.name]
        )
        info = (g.me.display_name, g.name)
        await ctx.send(f"In **{info[1]}** I am called **{info[0]}**.")

    @commands.command()
    async def cat(self, ctx):
        """Cat pics."""
        await ctx.send(
            embed=discord.Embed(title="Meow!", color=ctx.author.color.value).set_image(
                url=f"http://thecatapi.com/api/images/get?results_per_page=1&anticache={random.randint(1,10000)}"
            )
        )

    @commands.command()
    async def dog(self, ctx):
        """Dog pics."""
        async with self.bot.session.get(
            "https://api.thedogapi.com/v1/images/search"
        ) as r:
            res = await r.json()
        await ctx.send(
            embed=discord.Embed(title="Wouff!", color=ctx.author.color.value).set_image(
                url=res[0]["url"]
            )
        )

    @commands.command()
    async def uptime(self, ctx):
        """Shows how long the bot is connected to Discord already."""
        await ctx.send(f"I am online for **{str(self.bot.uptime).split('.')[0]}**.")

    @commands.command(hidden=True)
    async def easteregg(self, ctx):
        """Every good software has an Easter egg."""
        await ctx.send("Find it!")

    @commands.guild_only()
    @commands.command()
    async def cookie(self, ctx, user: discord.Member):
        """Gives a cookie to a user."""
        await ctx.send(
            f"**{user.display_name}**, you've been given a cookie by **{ctx.author.display_name}**. :cookie:"
        )

    @commands.guild_only()
    @commands.command(aliases=["ice-cream"])
    async def ice(self, ctx, other: discord.Member):
        """Gives ice cream to a user."""
        await ctx.send(f"{other.mention}, here is your ice: :ice_cream:!")

    @commands.guild_only()
    @commands.cooldown(1, 20, BucketType.channel)
    @commands.command()
    async def guess(self, ctx):
        """User guessing game."""
        m = random.choice(ctx.guild.members)
        em = discord.Embed(
            title="Can you guess who this is?",
            description=f"Their discriminant is `#{m.discriminator}`",
            color=m.color,
        )
        em.set_image(url=m.avatar_url)
        await ctx.send(embed=em)

        def check(msg):
            return (
                msg.content == m.name or msg.content == m.nick or msg.content == str(m)
            ) and msg.channel == ctx.channel

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=20)
        except asyncio.TimeoutError:
            return await ctx.send(f"You didn't guess correctly! It was `{m}`!")
        await ctx.send(f"{msg.author.mention}, you are correct!")

    @commands.command(aliases=["yn"])
    async def yesno(self, ctx, *, question: str):
        """An alternative to 8ball, but has more bitchy answers."""
        async with self.bot.session.get("http://gelbpunkt.troet.org/api/") as r:
            res = await r.json()
        em = discord.Embed(
            title=question, description=res.get("result"), colour=ctx.author.colour
        )
        em.set_thumbnail(url=ctx.author.avatar_url)
        em.timestamp = datetime.datetime.strptime(res.get("time"), "%Y-%m-%dT%H:%M:%SZ")
        await ctx.send(embed=em)

    @commands.command()
    async def partners(self, ctx):
        """Awesome bots by other coffee-drinking individuals."""
        em = discord.Embed(
            title="Partnered Bots",
            description="Awesome bots made by other people!",
            colour=discord.Colour.blurple(),
        )
        em.add_field(
            name="GamesROB",
            value="Trivia, Hangman, Minesweeper, Connect 4 and more, right from your chat! A bot offering non-RPG games made by deprilula28 and Fin.\n[discordbots.org Page](https://discordbots.org/bot/gamesrob)",
        )
        await ctx.send(embed=em)


def setup(bot):
    bot.add_cog(Miscellaneous(bot))
