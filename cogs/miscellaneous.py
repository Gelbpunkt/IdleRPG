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
import asyncio
import datetime
import platform
import random
from collections import defaultdict, deque
from functools import partial

import discord
import pkg_resources as pkg
import psutil
from discord.ext import commands
from discord.ext.commands import BucketType

from classes.converters import IntFromTo, IntGreaterThan
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils.checks import has_char


class Miscellaneous(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.talk_context = defaultdict(partial(deque, maxlen=3))

    @commands.command()
    @locale_doc
    async def dab(self, ctx):
        _("""Let's dab together.""")
        await ctx.send(_("No. Just no. I am a bot. What did you think?"))

    @has_char()
    @user_cooldown(86400)
    @commands.command()
    @locale_doc
    async def daily(self, ctx):
        _("""Receive a daily reward based on your streak.""")
        streak = await self.bot.redis.execute("INCR", f"idle:daily:{ctx.author.id}")
        await self.bot.redis.execute(
            "EXPIRE", f"idle:daily:{ctx.author.id}", 48 * 60 * 60
        )  # 48h: after 2 days, they missed it
        money = 2 ** ((streak + 9) % 10) * 50
        await self.bot.pool.execute(
            'UPDATE profile SET money=money+$1 WHERE "user"=$2;', money, ctx.author.id
        )
        await ctx.send(
            _(
                "You received your daily **${money}**!\nYou are on a streak of **{streak}** days!"
            ).format(money=money, streak=streak)
        )

    @commands.command()
    @locale_doc
    async def ping(self, ctx):
        _("""My current websocket latency.""")
        await ctx.send(
            embed=discord.Embed(
                title=_("Pong!"),
                description=_("My current latency is {lat}ms").format(
                    lat=round(self.bot.latency * 1000, 2)
                ),
                color=0xF1C60C,
            )
        )

    @commands.command(aliases=["donate"])
    @locale_doc
    async def patreon(self, ctx):
        _("""Support maintenance of the bot.""")
        guild_count = sum(
            await self.bot.cogs["Sharding"].handler("guild_count", self.bot.shard_count)
        )
        await ctx.send(
            _(
                """\
This bot has its own patreon page.

**Why should I donate?**
This bot is currently on {guild_count} servers, and it is growing fast.
Hosting this bot for all users is not easy and costs a lot of money.
If you want to continue using the bot or just help us, please donate a small amount.
Even $1 can help us.
**Thank you!**

<https://patreon.com/idlerpg>"""
            ).format(guild_count=guild_count)
        )

    @commands.command(aliases=["license"])
    @locale_doc
    async def source(self, ctx):
        _("""Shows the source code and license.""")
        await ctx.send("AGPLv3+\nhttps://github.com/Gelbpunkt/IdleRPG")

    @commands.command()
    @locale_doc
    async def invite(self, ctx):
        _("""Invite link for the bot.""")
        await ctx.send(
            _(
                "You are running version **{version}** by Adrian.\nInvite me! {url}"
            ).format(
                version=self.bot.version,
                url=discord.utils.oauth_url(
                    self.bot.user.id, permissions=discord.Permissions(8)
                ),
            )
        )

    @commands.command()
    @locale_doc
    async def support(self, ctx):
        _("""Information on the support server.""")
        await ctx.send(
            _(
                "Got problems or feature requests? Looking for people to play with? Join the support server:\nhttps://discord.gg/axBKXBv"
            )
        )

    @commands.command()
    @locale_doc
    async def stats(self, ctx):
        _("""Statistics on the bot.""")
        async with self.bot.pool.acquire() as conn:
            characters = await conn.fetchval("SELECT COUNT(*) FROM profile;")
            items = await conn.fetchval("SELECT COUNT(*) FROM allitems;")
            pg_version = conn.get_server_version()
        pg_version = f"{pg_version.major}.{pg_version.micro} {pg_version.releaselevel}"
        all_members = set(self.bot.get_all_members())
        total_online = sum(1 for m in all_members if m.status is discord.Status.online)
        total_idle = sum(1 for m in all_members if m.status is discord.Status.idle)
        total_dnd = sum(1 for m in all_members if m.status is discord.Status.dnd)
        total_offline = sum(
            1 for m in all_members if m.status is discord.Status.offline
        )
        d0 = self.bot.user.created_at
        d1 = datetime.datetime.now()
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
            title=_("IdleRPG Statistics"),
            colour=0xB8BBFF,
            url=self.bot.BASE_URL,
            description=_("Official Support Server Invite: https://discord.gg/MSBatf6"),
        )
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.set_footer(
            text=f"IdleRPG {self.bot.version} | By {owner}",
            icon_url=self.bot.user.avatar_url,
        )
        embed.add_field(
            name=_("General Statistics (this instance only)"),
            value=f"<:online:313956277808005120>{total_online}<:away:313956277220802560>{total_idle}<:dnd:313956276893646850>"
            f"{total_dnd}<:offline:313956277237710868>{total_offline}",
            inline=False,
        )
        embed.add_field(
            name=_("Hosting Statistics"),
            value=_(
                """\
CPU Usage: **{cpu}%**
RAM Usage: **{ram}%**
Python Version **{python}** <:python:445247273065250817>
discord.py Version **{dpy}**
Operating System: **{osname} {osversion}**
PostgreSQL Version **{pg_version}**"""
            ).format(
                cpu=psutil.cpu_percent(),
                ram=psutil.virtual_memory().percent,
                python=platform.python_version(),
                dpy=pkg.get_distribution("discord.py").version,
                osname=sysinfo[0].title(),
                osversion=sysinfo[1],
                pg_version=pg_version,
            ),
            inline=False,
        )
        embed.add_field(
            name=_("Bot Statistics"),
            value=_(
                """\
Code lines written: **{lines}**
Shards: **{shards}**
Servers: **{guild_count}**
Characters: **{characters}**
Items: **{items}**
Average hours of work: **{hours}**"""
            ).format(
                lines=self.bot.linecount,
                shards=self.bot.shard_count,
                guild_count=guild_count,
                characters=characters,
                items=items,
                hours=myhours,
            ),
            inline=False,
        )
        await ctx.send(embed=embed)

    @commands.command()
    @locale_doc
    async def roll(self, ctx, maximum: IntGreaterThan(0)):
        _("""Roll a random number.""")
        await ctx.send(
            _(":1234: You rolled **{num}**, {author}!").format(
                num=random.randint(0, maximum), author=ctx.author.mention
            )
        )

    @commands.command()
    @locale_doc
    async def changelog(self, ctx):
        _("""The bot's update log.""")
        await ctx.send(
            """\
**IdleRPG v3.6 is released! :tada:!**

**What's new?**
- IdleRPG can be translated now
- Some commands were rewritten
- `$language` shows available languages, `$language set LANGUAGE` will change your language
- `$source` was added
- The bot is now no longer dual licensed, it is now only AGPLv3+

**What's fixed?**
A bunch

**Are there bugs?**
Of course

**How to translate?**
Head to #translate in the support server for more information

Thank you for playing IdleRPG! :heart:"""
        )

    @commands.has_permissions(manage_messages=True)
    @commands.command()
    @locale_doc
    async def clear(self, ctx, num: IntFromTo(1, 1000), target: discord.Member = None):
        _(
            """Deletes an amount of messages from the history, optionally only by one member."""
        )

        def msgcheck(amsg):
            if target:
                return amsg.author.id == target.id
            return True

        num = len(await ctx.channel.purge(limit=num + 1, check=msgcheck))
        await ctx.send(
            _("👍 Deleted **{num}** messages for you.").format(num=num), delete_after=10
        )

    @commands.command(name="8ball")
    @locale_doc
    async def _ball(self, ctx, *, question: str):
        _("""The magic 8 ball answers your questions.""")
        results = [
            _("It is certain"),
            _("It is decidedly so"),
            _("Without a doubt"),
            _("Yes, definitely"),
            _("You may rely on it"),
            _("As I see it, yes"),
            _("Most likely"),
            _("Outlook good"),
            _("Yes"),
            _("Signs point to yes"),
            _("Reply hazy try again"),
            _("Ask again later"),
            _("Better not tell you now"),
            _("Cannot predict now"),
            _("Concentrate and ask again"),
            _("Don't count on it"),
            _("My reply is no"),
            _("My sources say no"),
            _("Outlook not so good"),
            _("Very doubtful"),
        ]
        await ctx.send(
            _("The :8ball: says: **{result}**.").format(result=random.choice(results))
        )

    @commands.command(aliases=["say"])
    @locale_doc
    async def echo(self, ctx, *, phrase: str):
        _("""Repeats what you said.""")
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        await ctx.send(phrase, escape_mentions=True)

    @commands.command()
    @locale_doc
    async def choose(self, ctx, *results: str):
        _("""Chooses a random option of supplied possiblies.""")
        results = list(filter(lambda a: a.lower() != "or", results))
        if not results:
            return await ctx.send(_("Cannot choose from an empty list..."))
        await ctx.send(
            _("My choice is: **{result}**.").format(result=random.choice(results)),
            escape_mentions=True,
        )

    @commands.guild_only()
    @commands.command()
    @locale_doc
    async def love(self, ctx, first: discord.Member, second: discord.Member):
        _("""Calculates the potential love for 2 members.""")
        msg = await ctx.send(
            embed=discord.Embed(
                description=_("Calculating Love for {first} and {second}...").format(
                    first=first.mention, second=second.mention
                ),
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
            title=_("Love Calculation"),
            description=_("Love for {first} and {second} is at **{love}%**! ❤").format(
                first=first.mention, second=second.mention, love=love
            ),
            color=0xFF0000,
        )
        await msg.edit(embed=embed)

    @commands.command()
    @locale_doc
    async def fancy(self, ctx, *, text: str):
        _("""Fancies text with big emojis.""")
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
    @locale_doc
    async def meme(self, ctx):
        _("""A random bad meme.""")
        async with self.bot.session.get(
            f"https://some-random-api.ml/meme?lol={random.randint(1,1000000)}"
        ) as resp:
            await ctx.send(
                embed=discord.Embed(color=0x0A00FF).set_image(
                    url=(await resp.json())["image"]
                )
            )

    @commands.command()
    @locale_doc
    async def dice(self, ctx, dice_type: str):
        _(
            """Tabletop RPG-ready dice. Rolls in the ndx format (3d20 is 3 dice with 20 sides)."""
        )
        try:
            dice_type = list(map(int, dice_type.split("d")))
        except ValueError:
            return await ctx.send(
                _(
                    "Use the ndx format. E.g. `5d20` will roll 5 dices with 20 sides each."
                )
            )
        if len(dice_type) != 2:
            return await ctx.send(_("Use the ndx format."))
        if dice_type[0] > 100:
            return await ctx.send(_("Too many dice."))
        if dice_type[1] <= 0 or dice_type[1] > 10000:
            return await ctx.send(
                _("Dice must have at least one side and not more than 10000.")
            )
        results = []
        for x in range(dice_type[0]):
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
            _("```Sum: {sumall}\nAverage: {average}\nResults:\n{results}```").format(
                sumall=sumall, average=average, results=nl.join(results)
            )
        )

    @commands.command()
    @locale_doc
    async def randomname(self, ctx):
        _("""Sends my nickname in a random server.""")
        g = random.choice(
            [g for g in self.bot.guilds if g.me.display_name != self.bot.user.name]
        )
        info = (g.me.display_name, g.name)
        await ctx.send(
            _("In **{server}** I am called **{name}**.").format(
                server=info[1], name=info[0]
            )
        )

    @commands.command()
    @locale_doc
    async def cat(self, ctx):
        _("""Cat pics.""")
        await ctx.send(
            embed=discord.Embed(
                title=_("Meow!"), color=ctx.author.color.value
            ).set_image(
                url=f"http://thecatapi.com/api/images/get?results_per_page=1&anticache={random.randint(1,10000)}"
            )
        )

    @commands.command()
    @locale_doc
    async def dog(self, ctx):
        _("""Dog pics.""")
        async with self.bot.session.get(
            "https://api.thedogapi.com/v1/images/search"
        ) as r:
            res = await r.json()
        await ctx.send(
            embed=discord.Embed(
                title=_("Wouff!"), color=ctx.author.color.value
            ).set_image(url=res[0]["url"])
        )

    @commands.command()
    @locale_doc
    async def uptime(self, ctx):
        _("""Shows how long the bot is connected to Discord already.""")
        await ctx.send(
            _("I am online for **{time}**.").format(
                time=str(self.bot.uptime).split(".")[0]
            )
        )

    @commands.command(hidden=True)
    @locale_doc
    async def easteregg(self, ctx):
        _("""Every good software has an Easter egg.""")
        await ctx.send(_("Find it!"))

    @commands.guild_only()
    @commands.command()
    @locale_doc
    async def cookie(self, ctx, user: discord.Member):
        _("""Gives a cookie to a user.""")
        await ctx.send(
            _(
                "**{user}**, you've been given a cookie by **{author}**. :cookie:"
            ).format(author=ctx.disp, user=user.display_name)
        )

    @commands.guild_only()
    @commands.command(aliases=["ice-cream"])
    @locale_doc
    async def ice(self, ctx, other: discord.Member):
        _("""Gives ice cream to a user.""")
        await ctx.send(
            _("{other}, here is your ice: :ice_cream:!").format(other=other.mention)
        )

    @commands.guild_only()
    @commands.cooldown(1, 20, BucketType.channel)
    @commands.command()
    @locale_doc
    async def guess(self, ctx):
        _("""User guessing game.""")
        m = random.choice(ctx.guild.members)
        em = discord.Embed(
            title=_("Can you guess who this is?"),
            description=_("Their discriminant is `#{disc}`").format(
                disc=m.discriminator
            ),
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
            return await ctx.send(
                _("You didn't guess correctly! It was `{member}`!").format(member=m)
            )
        await ctx.send(_("{user}, you are correct!").format(user=msg.author.mention))

    @commands.command(aliases=["yn"])
    @locale_doc
    async def yesno(self, ctx, *, question: str):
        _("""An alternative to 8ball, but has more bitchy answers.""")
        async with self.bot.session.get("http://gelbpunkt.troet.org/api/") as r:
            res = await r.json()
        em = discord.Embed(
            title=question, description=res.get("result"), colour=ctx.author.colour
        )
        em.set_thumbnail(url=ctx.author.avatar_url)
        em.timestamp = datetime.datetime.strptime(res.get("time"), "%Y-%m-%dT%H:%M:%SZ")
        await ctx.send(embed=em)

    @commands.command(aliases=["cb", "chat"])
    async def talk(self, ctx, *, text: str):
        _("""Talk to me! (Supports only English)""")
        if not (3 <= len(text) <= 60):
            return await ctx.send(
                _("Text too long or too short. May be 3 to 60 characters.")
            )
        self.talk_context[ctx.author.id].append(text)
        context = list(self.talk_context[ctx.author.id])[:-1]
        async with self.bot.session.post(
            "https://public-api.travitia.xyz/talk",
            json={"text": text, "context": context},
            headers={"authorization": self.bot.config.traviapi},
        ) as req:
            json = await req.json()
        await ctx.send(f"{ctx.author.mention}, {json['response']}")

    @commands.command()
    @locale_doc
    async def partners(self, ctx):
        _("""Awesome bots by other coffee-drinking individuals.""")
        em = discord.Embed(
            title=_("Partnered Bots"),
            description=_("Awesome bots made by other people!"),
            colour=discord.Colour.blurple(),
        )
        em.add_field(
            name="GamesROB",
            value=_(
                "Trivia, Hangman, Minesweeper, Connect 4 and more, right from your chat! A bot offering non-RPG games made by deprilula28 and Fin.\n[discordbots.org Page](https://discordbots.org/bot/gamesrob)"
            ),
        )
        em.add_field(
            name="Cautious Memory",
            value=_(
                "Cautious Memory brings wiki-style pages to your server. Use it to document who's who in your server, inside jokes, or community lore. Includes a full featured permissions system to keep your pages squeaky clean.\n[discordbots.org Page](https://discordbots.org/bot/541707781665718302)"
            ),
        )
        await ctx.send(embed=em)


def setup(bot):
    bot.add_cog(Miscellaneous(bot))
