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
import os
import platform
import random
import re
import secrets

from collections import defaultdict, deque
from functools import partial

import aiowiki
import discord
import distro
import humanize
import pkg_resources as pkg
import psutil

from discord.ext import commands
from discord.ext.commands import BucketType

from classes.converters import DateNewerThan, IntFromTo, IntGreaterThan
from cogs.help import chunks
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils.checks import has_char


class Miscellaneous(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.talk_context = defaultdict(partial(deque, maxlen=3))
        self.bot.loop.create_task(self.make_wikis())

    async def make_wikis(self):
        self.bot.wikipedia = aiowiki.Wiki.wikipedia("en", session=self.bot.session)
        self.bot.idlewiki = aiowiki.Wiki(
            "https://wiki.travitia.xyz/api.php", session=self.bot.session
        )

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
        # Either money or crates
        if secrets.randbelow(3) > 0:
            money = 2 ** ((streak + 9) % 10) * 50
            await self.bot.pool.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                money,
                ctx.author.id,
            )
            txt = f"**${money}**"
        else:
            num = round(((streak + 9) % 10 + 1) / 2)
            amt = random.randint(1, 6 - num)
            types = [
                "common",
                "uncommon",
                "rare",
                "magic",
                "legendary",
                "common",
                "common",
                "common",
            ]  # Trick for -1
            type_ = secrets.choice(
                [types[num - 3]] * 80 + [types[num - 2]] * 19 + [types[num - 1]] * 1
            )
            await self.bot.pool.execute(
                f'UPDATE profile SET "crates_{type_}"="crates_{type_}"+$1 WHERE "user"=$2;',
                amt,
                ctx.author.id,
            )
            txt = f"**{amt}** {getattr(self.bot.cogs['Crates'].emotes, type_)}"

        await ctx.send(
            _(
                "You received your daily {txt}!\nYou are on a streak of **{streak}** days!"
            ).format(txt=txt, money=money, streak=streak)
        )

    @commands.command()
    @locale_doc
    async def ping(self, ctx):
        _("""Shows you the bot's current websocket latency.""")
        await ctx.send(
            embed=discord.Embed(
                title=_("Pong!"),
                description=_("My current latency is {lat}ms").format(
                    lat=round(self.bot.latency * 1000, 2)
                ),
                color=0xF1C60C,
            )
        )

    @commands.command(aliases=["shorten"])
    @locale_doc
    async def imgur(self, ctx, given_url: str = None):
        _("""Gives you a short URL from an image or long URL""")
        if not given_url and not ctx.message.attachments:
            return await ctx.send(_("Please supply a URL or an image attachment"))
        if ctx.message.attachments:
            if len(ctx.message.attachments) > 1:
                return await ctx.send(_("Please only use one image at a time."))
            url = ctx.message.attachments[0].url
            if not (
                url.endswith(".png") or url.endswith(".jpg") or url.endswith(".jpeg")
            ):
                return await ctx.send(_("This is not a valid image file."))
            given_url = url

        async with self.bot.session.post(
            "https://api.imgur.com/3/image",
            headers={"Authorization": f"Client-ID {self.bot.config.imgur_token}"},
            data={"image": given_url},
        ) as r:
            try:
                link = (await r.json())["data"]["link"]
            except KeyError:
                return await ctx.send(_("Error when uploading to Imgur."))
        await ctx.send(_("Here's your short image URL: <{link}>").format(link=link))

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
                "You are running version **{version}** by The IdleRPG Developers.\nInvite me! {url}"
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
        _("""Sends you the link to the official IdleRPG Support server.""")
        await ctx.send(
            _(
                "Got problems or feature requests? Looking for people to play with? Join the support server:\nhttps://discord.gg/MSBatf6"
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
        d0 = self.bot.user.created_at
        d1 = datetime.datetime.now()
        delta = d1 - d0
        myhours = delta.days * 1.5
        sysinfo = distro.linux_distribution()
        if self.bot.owner_ids:
            owner = " and ".join(
                [str(await self.bot.get_user_global(u)) for u in self.bot.owner_ids]
            )
        else:
            owner = str(await self.bot.get_user_global(self.bot.owner_id))
        guild_count = sum(
            await self.bot.cogs["Sharding"].handler("guild_count", self.bot.shard_count)
        )
        meminfo = psutil.virtual_memory()

        embed = discord.Embed(
            title=_("IdleRPG Statistics"),
            colour=0xB8BBFF,
            url=self.bot.BASE_URL,
            description=_("Official Support Server Invite: https://discord.gg/idlerpg"),
        )
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.set_footer(
            text=f"IdleRPG {self.bot.version} | By {owner}",
            icon_url=self.bot.user.avatar_url,
        )
        embed.add_field(
            name=_("Hosting Statistics"),
            value=_(
                """\
CPU Usage: **{cpu}%**, **{cores}** cores @ **{freq}** GHz
RAM Usage: **{ram}%** (Total: **{total_ram}**)
Python Version **{python}** <:python:445247273065250817>
discord.py Version **{dpy}**
Operating System: **{osname} {osversion}**
Kernel Version: **{kernel}**
PostgreSQL Version **{pg_version}**"""
            ).format(
                cpu=psutil.cpu_percent(),
                cores=psutil.cpu_count(),
                freq=psutil.cpu_freq().max / 1000,
                ram=meminfo.percent,
                total_ram=humanize.naturalsize(meminfo.total),
                python=platform.python_version(),
                dpy=pkg.get_distribution("discord.py").version,
                osname=sysinfo[0].title(),
                osversion=sysinfo[1],
                kernel=os.uname().release,
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
        _("""Shows you the bots current version along with its new updates.""")
        await ctx.send(
            """\
**IdleRPG v4.1.0 has been released :tada:**

- Added Akinator again, but they changed their backend (so it is removed again)
- Switched to Podman. Huge change, therefore selfhosting is far easier now, but all redis data (dailies, cooldowns, etc.) was lost
- Lyrics are now a thing! `$lyrics` (will auto-search for current playing song if none specified)
- Maths is back from Travitia. `$calc`
- Music remake is done! Featuring `$lock/unlock`, DJs, `$equalizer`s, `$loop` and much more
- Added `$wikipedia` and `$wiki` (`$wiki` checks IdleRPG Wiki)
- `$activate all`
- Fixed Shin's Raid
- Updated Bandit Raids
- Voting is now in timers (may be broken, should be fine though)
- Voting is now in NodeJS and open source at https://github.com/Kenvyra/teatro
- Adventure luck chances are properly fixed
- setup.sh will walk you through a full IdleRPG install

**Thank you for playing IdleRPG!**"""
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
        _("""Sends you my nickname from a random server.""")
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
        _("""Shows how long the bot has been connected to Discord.""")
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
    @locale_doc
    async def talk(self, ctx, *, text: str):
        _("""Talk to me! (Supports only English)""")
        await ctx.trigger_typing()
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
    async def garfield(
        self,
        ctx,
        *,
        date: DateNewerThan(
            datetime.date(year=1978, month=6, day=19)
        ) = datetime.date.today(),
    ):
        _(
            """Sends today's garfield comic if no date info is passed. Else, it will use YYYY MM DD or DD MM YYYY depending on where the year is, with the date parts being seperated with spaces."""
        )
        await ctx.send(
            embed=discord.Embed(color=self.bot.config.primary_colour).set_image(
                url=f"https://d1ejxu6vysztl5.cloudfront.net/comics/garfield/{date.year}/{date.strftime('%Y-%m-%d')}.gif?format=png"
            )
        )

    @commands.command(aliases=["uf"])
    @locale_doc
    async def userfriendly(
        self,
        ctx,
        *,
        date: DateNewerThan(
            datetime.date(year=1997, month=11, day=17)
        ) = datetime.date.today(),
    ):
        _(
            """Sends today's userfriendly comic if no date info is passed. Else, it will use YYYY MM DD or DD MM YYYY depending on where the year is, with the date parts being seperated with spaces."""
        )
        async with self.bot.session.get(
            f"http://ars.userfriendly.org/cartoons/?id={date.strftime('%Y%m%d')}&mode=classic"
        ) as r:
            stuff = await r.text()

        await ctx.send(
            embed=discord.Embed(
                color=self.bot.config.primary_colour,
                url="http://userfriendly.org",
                title=_("Taken from userfriendly.org"),
                description=str(date),
            ).set_image(
                url=re.compile('<img border="0" src="([^"]+)"').search(stuff).group(1)
            )
        )

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

    @commands.command()
    @locale_doc
    async def wikipedia(self, ctx, *, query: str):
        _("""Searches Wikipedia for an entry.""")
        try:
            page = (await self.bot.wikipedia.opensearch(query))[0]
            text = await page.summary()
        except (aiowiki.exceptions.PageNotFound, IndexError):
            return await ctx.send(_("No wikipedia entry found."))
        p = commands.Paginator()
        for l in text.split("\n"):
            for i in chunks(l, 1900):
                p.add_line(i)
        await self.bot.paginator.Paginator(
            title=page.title, entries=p.pages, length=1
        ).paginate(ctx)

    @commands.command(aliases=["wiki"])
    @locale_doc
    async def idlewiki(self, ctx, *, query: str = None):
        _("""Searches IdleRPG Wiki for an entry.""")
        if not query:
            return await ctx.send(
                _(
                    "Check out the official IdleRPG Wiki here:\n<https://wiki.travitia.xyz/index.php?title=Main_Page>"
                )
            )
        try:
            page = (await self.bot.idlewiki.opensearch(query))[0]
            text = await page.text()
        except (aiowiki.exceptions.PageNotFound, IndexError):
            return await ctx.send(_("No entry found."))
        else:
            if not text:
                return await ctx.send(_("No content to display."))
        p = commands.Paginator()
        for l in text.split("\n"):
            for i in chunks(l, 1900):
                p.add_line(i)
        await self.bot.paginator.Paginator(
            title=page.title, entries=p.pages, length=1
        ).paginate(ctx)


def setup(bot):
    bot.add_cog(Miscellaneous(bot))
