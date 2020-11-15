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
import datetime
import os
import platform
import random as random_
import re
import statistics
import sys

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

from classes.converters import (
    DateNewerThan,
    ImageFormat,
    ImageUrl,
    IntFromTo,
    IntGreaterThan,
    MemberConverter,
)
from cogs.help import chunks
from cogs.shard_communication import next_day_cooldown
from utils import random
from utils.checks import ImgurUploadError, has_char, user_is_patron
from utils.i18n import _, locale_doc
from utils.misc import nice_join
from utils.shell import get_cpu_name


class Miscellaneous(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.talk_context = defaultdict(partial(deque, maxlen=3))
        self.bot.loop.create_task(self.make_wikis())

    async def make_wikis(self):
        self.bot.wikipedia = aiowiki.Wiki.wikipedia("en", session=self.bot.session)
        self.bot.idlewiki = aiowiki.Wiki(
            "https://wiki.idlerpg.xyz/api.php", session=self.bot.session
        )

    async def get_imgur_url(self, url: str):
        async with self.bot.session.post(
            "https://api.imgur.com/3/image",
            headers={
                "Authorization": f"Client-ID {self.bot.config.external.imgur_token}"
            },
            json={"image": url},
        ) as r:
            try:
                short_url = (await r.json())["data"]["link"]
            except KeyError:
                raise ImgurUploadError()
        return short_url

    @commands.command(brief=_("Evoke cringe"))
    @locale_doc
    async def dab(self, ctx):
        _("""Let's dab together.""")
        await ctx.send(_("No. Just no. I am a bot. What did you think?"))

    @has_char()
    @next_day_cooldown()
    @commands.command(brief=_("Get your daily reward"))
    @locale_doc
    async def daily(self, ctx):
        _(
            """Get your daily reward. Depending on your streak, you will gain better rewards.

            After ten days, your rewards will reset. Day 11 and day 1 have the same rewards.
            The rewards will either be money (2/3 chance) or crates (1/3 chance).

            The possible rewards are:

              __Day 1__
              $50 or 1-6 common crates

              __Day 2__
              $100 or 1-5 common crates

              __Day 3__
              $200 or 1-4 common (99%) or uncommon (1%) crates

              __Day 4__
              $400 or 1-4 common (99%) or uncommon (1%) crates

              __Day 5__
              $800 or 1-4 common (99%) or uncommon (1%) crates

              __Day 6__
              $1,600 or 1-3 common (80%), uncommon (19%) or rare (1%) crates

              __Day 7__
              $3,200 or 1-2 uncommon (80%), rare (19%) or magic (1%) crates

              __Day 8__
              $6,400 or 1-2 uncommon (80%), rare (19%) or magic (1%) crates

              __Day 9__
              $12,800 or 1-2 uncommon (80%), rare (19%) or magic (1%) crates

              __Day 10__
              $25,600 or 1 rare (80%), magic (19%) or legendary (1%) crate

            If you don't use this command up to 48 hours after the first use, you will lose your streak.

            (This command has a cooldown until 12am UTC.)"""
        )
        streak = await self.bot.redis.execute("INCR", f"idle:daily:{ctx.author.id}")
        await self.bot.redis.execute(
            "EXPIRE", f"idle:daily:{ctx.author.id}", 48 * 60 * 60
        )  # 48h: after 2 days, they missed it
        money = 2 ** ((streak + 9) % 10) * 50
        # Either money or crates
        if random.randint(0, 2) > 0:
            money = 2 ** ((streak + 9) % 10) * 50
            # Silver = 1.5x
            if await user_is_patron(self.bot, ctx.author, "silver"):
                money = round(money * 1.5)
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
            type_ = random.choice(
                [types[num - 3]] * 80 + [types[num - 2]] * 19 + [types[num - 1]] * 1
            )
            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    f'UPDATE profile SET "crates_{type_}"="crates_{type_}"+$1 WHERE'
                    ' "user"=$2;',
                    amt,
                    ctx.author.id,
                )
                await self.bot.log_transaction(
                    ctx,
                    from_=1,
                    to=ctx.author.id,
                    subject="crates",
                    data={"Rarity": type_, "Amount": amt},
                    conn=conn,
                )
            await self.bot.cache.update_profile_cols_rel(
                ctx.author.id, **{f"crates_{type_}": amt}
            )
            txt = f"**{amt}** {getattr(self.bot.cogs['Crates'].emotes, type_)}"

        await ctx.send(
            _(
                "You received your daily {txt}!\nYou are on a streak of **{streak}**"
                " days!\n*Tip: `{prefix}vote` every 12 hours to get an up to legendary"
                " crate with possibly rare items!*"
            ).format(txt=txt, money=money, streak=streak, prefix=ctx.prefix)
        )

    @has_char()
    @commands.command(brief=_("View your current streak"))
    @locale_doc
    async def streak(self, ctx):
        _(
            """Want to flex your streak on someone or just check how many days in a row you've claimed your daily reward? This command is for you"""
        )
        streak = await self.bot.redis.execute("GET", f"idle:daily:{ctx.author.id}")
        if not streak:
            return await ctx.send(
                _(
                    "You don't have a daily streak yet. You can get one going by using"
                    " the command `{prefix}daily`!"
                ).format(prefix=ctx.prefix)
            )
        await ctx.send(
            _("You are on a daily streak of **{streak}!**").format(
                streak=streak.decode()
            )
        )

    @commands.command(brief=_("Show the bot's ping"))
    @locale_doc
    async def ping(self, ctx):
        _("""Shows you the bot's current websocket latency in milliseconds.""")
        await ctx.send(
            embed=discord.Embed(
                title=_("Pong!"),
                description=_("My current latency is {lat}ms").format(
                    lat=round(self.bot.latency * 1000, 2)
                ),
                color=0xF1C60C,
            )
        )

    @commands.command(aliases=["shorten"], brief=_("Shorten an image URL."))
    @locale_doc
    async def imgur(self, ctx, given_url: ImageUrl(ImageFormat.all) = None):
        _(
            """`[given_url]` - The URL to shorten; if not given, this command will look for image attachments

            Get a short URL from a long one or an image attachment.

            If both a URL and an attachment is given, the attachment is preferred. GIFs are not supported, only JPG and PNG.
            In case this command fails, you can [manually upload your image to Imgur](https://imgur.com/upload)."""
        )
        if not given_url and not ctx.message.attachments:
            return await ctx.send(_("Please supply a URL or an image attachment"))
        if ctx.message.attachments:
            if len(ctx.message.attachments) > 1:
                return await ctx.send(_("Please only use one image at a time."))
            given_url = await ImageUrl(ImageFormat.all).convert(
                ctx, ctx.message.attachments[0].url
            )

        link = await self.get_imgur_url(given_url)
        await ctx.send(_("Here's your short image URL: <{link}>").format(link=link))

    @commands.command(aliases=["donate"], brief=_("Support the bot financially"))
    @locale_doc
    async def patreon(self, ctx):
        _(
            """View the Patreon page of the bot. The different tiers will grant different rewards.
            View `{prefix}help module Patreon` to find the different commands.

            Thank you for supporting IdleRPG!"""
        )
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

    @commands.command(
        aliases=["license"], brief=_("Shows the source code and license.")
    )
    @locale_doc
    async def source(self, ctx):
        _(
            """Shows our GitLab page and license.
            If you want to contribute, feel free to create an account and submit issues and merge requests."""
        )
        await ctx.send("AGPLv3+\nhttps://git.travitia.xyz/Kenvyra/IdleRPG")

    @commands.command(brief=_("Invite the bot to your server."))
    @locale_doc
    async def invite(self, ctx):
        _(
            """Invite the bot to your server.

            Use this [backup link](https://discord.com/oauth2/authorize?client_id=424606447867789312&scope=bot&permissions=8) in case the above does not work."""
        )
        await ctx.send(
            _(
                "You are running version **{version}** by The IdleRPG"
                " Developers.\nInvite me! https://invite.idlerpg.xyz"
            ).format(version=self.bot.version)
        )

    @commands.command(brief=_("Join the Support server"))
    @locale_doc
    async def support(self, ctx):
        _(
            """Sends you the link to join the official IdleRPG Support server.

            Use this [backup link](https://discord.gg/MSBatf6) in case the above does not work."""
        )
        await ctx.send(
            _(
                "Got problems or feature requests? Looking for people to play with?"
                " Join the support server:\nhttps://support.idlerpg.xyz"
            )
        )

    @commands.command(brief=_("Shows statistics about the bot"))
    @locale_doc
    async def stats(self, ctx):
        _(
            """Show some stats about the bot, ranging from hard- and software statistics, over performance to ingame stats."""
        )
        async with self.bot.pool.acquire() as conn:
            characters = await conn.fetchval("SELECT COUNT(*) FROM profile;")
            items = await conn.fetchval("SELECT COUNT(*) FROM allitems;")
            pg_version = conn.get_server_version()
        temps = psutil.sensors_temperatures()
        temps = temps[list(temps.keys())[0]]
        cpu_temp = statistics.mean(x.current for x in temps)
        pg_version = f"{pg_version.major}.{pg_version.micro} {pg_version.releaselevel}"
        d0 = self.bot.user.created_at
        d1 = datetime.datetime.now()
        delta = d1 - d0
        myhours = delta.days * 1.5
        sysinfo = distro.linux_distribution()
        if self.bot.owner_ids:
            owner = nice_join(
                [str(await self.bot.get_user_global(u)) for u in self.bot.owner_ids]
            )
        else:
            owner = str(await self.bot.get_user_global(self.bot.owner_id))
        guild_count = sum(
            await self.bot.cogs["Sharding"].handler("guild_count", self.bot.shard_count)
        )
        meminfo = psutil.virtual_memory()
        cpu_freq = psutil.cpu_freq()
        cpu_name = await get_cpu_name()
        compiler = re.search(r".*\[(.*)\]", sys.version)[1]

        embed = discord.Embed(
            title=_("IdleRPG Statistics"),
            colour=0xB8BBFF,
            url=self.bot.BASE_URL,
            description=_(
                "Official Support Server Invite: https://support.idlerpg.xyz"
            ),
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
CPU: **{cpu_name}**
CPU Usage: **{cpu}%**, **{cores}** cores @ **{freq}** GHz
RAM Usage: **{ram}%** (Total: **{total_ram}**)
CPU Temperature: **{cpu_temp}°C**
Python Version **{python}** <:python:445247273065250817>
discord.py Version **{dpy}**
Compiler: **{compiler}**
Operating System: **{osname} {osversion}**
Kernel Version: **{kernel}**
PostgreSQL Version: **{pg_version}**
Redis Version: **{redis_version}**"""
            ).format(
                cpu_name=cpu_name,
                cpu=psutil.cpu_percent(),
                cores=psutil.cpu_count(),
                cpu_temp=round(cpu_temp, 2),
                freq=cpu_freq.max / 1000
                if cpu_freq.max
                else round(cpu_freq.current / 1000, 2),
                ram=meminfo.percent,
                total_ram=humanize.naturalsize(meminfo.total),
                python=platform.python_version(),
                dpy=pkg.get_distribution("discord.py").version,
                compiler=compiler,
                osname=sysinfo[0].title(),
                osversion=sysinfo[1],
                kernel=os.uname().release if os.name == "posix" else "NT",
                pg_version=pg_version,
                redis_version=self.bot.redis_version,
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

    @commands.command(brief=_("Roll a dice"))
    @locale_doc
    async def roll(self, ctx, maximum: IntGreaterThan(0)):
        _(
            """`<maximum>` - A whole number greater than 0

            Roll a dice with `<maximum>` sides and let the bot display the outcome."""
        )
        await ctx.send(
            _(":1234: You rolled **{num}**, {author}!").format(
                num=random.randint(0, maximum), author=ctx.author.mention
            )
        )

    @commands.command(brief=_("View the changelog"))
    @locale_doc
    async def changelog(self, ctx):
        _("""Shows you the bots current version along with its major updates.""")
        await ctx.send(
            """\
**v4.10.0**

> 2020-09-20

**Additions**

* Added `$guild rename`
* Added a buy-item-button to the `$shop`
* Several command helps were added and/or reworked
* Check for not included players in Hungergames
* The bot now uses our new and enhanced music backend
* `$profile` custom images that error the backend will display information how to fix it
* Again, `$werewolf` got new features (too many to list) and a few bugfixes

**Changes**

* We have reworked the formulas for adventure success calculation - more on that at https://git.travitia.xyz/Kenvyra/IdleRPG/-/issues/551#note_3441
* Corrected wrong info in the `$steal` help message
* The use of eventbackgrounds is now possible again
* Active adventures were fixed
* Fixed a bug in the `$cat` command
* Fixed misleading text in `$date`
* Fixed `$banfromhelpme`
* Fixed a few typos
* Fixed `$lyrics`
* Fixed guild logs send order
* Fixed an exploit in `$trade`
* Fixed active battle bug when both players died and no money returned
* Fix bug with `$guild info id:0`
* Fixed guild deletion if city is owned
* Fixes for `$trade`
* Minor changes to prefix loading
* Ordered `$loot`
* Rephrase "Target" to "Random Player" in `$steal`'s info"""
        )

    @commands.has_permissions(manage_messages=True)
    @commands.command(brief=_("Delete messages"))
    @locale_doc
    async def clear(self, ctx, num: IntFromTo(1, 1000), target: MemberConverter = None):
        _(
            """`<num>` - A whole number from 1 to 1000
            `[target]` - The user whose messages to delete; defaults to everyone

            Deletes an amount of messages in the channel, optionally only by one member.
            If no target is given, all messages are cleared.

            Note that this will *scan* `<num>` messages and will only delete them, if they are from the target, if one is given.
            If the target sent 30 messages, other people sent 70 messages and you cleared 100 messages by the target, only those 30 will be deleted.

            Only users with the Manage Messages permission can use this command."""
        )

        def msgcheck(amsg):
            if target:
                return amsg.author.id == target.id
            return True

        num = len(await ctx.channel.purge(limit=num + 1, check=msgcheck))
        await ctx.send(
            _("👍 Deleted **{num}** messages for you.").format(num=num), delete_after=10
        )

    @commands.command(name="8ball", brief=_("Ask the magic 8ball a question"))
    @locale_doc
    async def _ball(self, ctx, *, question: str):
        _(
            """Provides a variety of answers to all of your questions. If in doubt, ask the magic 8ball."""
        )
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

    @commands.command(aliases=["say"], brief=_("Repeat what you said."))
    @locale_doc
    async def echo(self, ctx, *, phrase: str):
        _(
            """`<phrase>` - The text to repeat

            Repeats what you said. This will delete the command message if possible."""
        )
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        await ctx.send(phrase, escape_mentions=True)

    @commands.command(brief=_("Help you decide"))
    @locale_doc
    async def choose(self, ctx, *results: str):
        _(
            """`<results...>` - The options to choose from

            Chooses a random option of supplied possiblies. For an option with multiple words, put it in "double quotes"."""
        )
        results = list(filter(lambda a: a.lower() != "or", results))
        if not results:
            return await ctx.send(_("Cannot choose from an empty list..."))
        await ctx.send(
            _("My choice is: **{result}**.").format(result=random.choice(results)),
            escape_mentions=True,
        )

    @commands.guild_only()
    @commands.command(brief=_("Calculates love for two users"))
    @locale_doc
    async def love(self, ctx, first: MemberConverter, second: MemberConverter):
        _(
            """`<first>` - A discord User
            `<second>` - Also a discord User

            Calculates the love between two people. Don't be disappointed when the result is low, you'll find your Romeo/Juliet someday."""
        )
        msg = await ctx.send(
            embed=discord.Embed(
                description=_("Calculating Love for {first} and {second}...").format(
                    first=first.mention, second=second.mention
                ),
                color=0xFF0000,
            )
        )
        await asyncio.sleep(5)
        random_.seed(int(str(first.id) + str(second.id)))
        if first == second:
            love = 100.00
        else:
            love = random_.randint(1, 10000) / 100
        embed = discord.Embed(
            title=_("Love Calculation"),
            description=_("Love for {first} and {second} is at **{love}%**! ❤").format(
                first=first.mention, second=second.mention, love=love
            ),
            color=0xFF0000,
        )
        await msg.edit(embed=embed)

    @commands.command(brief=_("Replaces text with emoji"))
    @locale_doc
    async def fancy(self, ctx, *, text: str):
        _(
            """`<text>` - The text to enlarge

            Replaces text and numbers with emoji."""
        )
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
            if letter.lower() in "abcdefghijklmnopqrstuvwxyz":
                newtext += f":regional_indicator_{letter.lower()}:"
            elif letter in "0123456789":
                newtext += f":{nums[int(letter)]}:"
            else:
                newtext += letter
        await ctx.send(newtext)

    @commands.command(brief=_("Evoke cringe"))
    @locale_doc
    async def meme(self, ctx):
        _(
            """Sends a random meme from [Some Random API](https://some-random-api.ml/)."""
        )
        async with self.bot.session.get(
            f"https://some-random-api.ml/meme?lol={random.randint(1,1000000)}"
        ) as resp:
            await ctx.send(
                embed=discord.Embed(color=0x0A00FF).set_image(
                    url=(await resp.json())["image"]
                )
            )

    @commands.command(brief=_("Roll some dice"))
    @locale_doc
    async def dice(self, ctx, dice_type: str):
        _(
            """`<dice_type>` - The dice to roll, uses the ndx format

            Rolls n dice with x sides (3d20 rolls 3 20-sided dice)."""
        )
        try:
            dice_type = list(map(int, dice_type.split("d")))
        except ValueError:
            return await ctx.send(
                _(
                    "Use the ndx format. E.g. `5d20` will roll 5 dice with 20 sides"
                    " each."
                )
            )
        if len(dice_type) != 2:
            return await ctx.send(_("Use the ndx format."))
        if not 1 <= dice_type[0] <= 100:
            return await ctx.send(
                _("The number of dice to roll should be between 1 and 100.")
            )
        if not 1 <= dice_type[1] <= 10000:
            return await ctx.send(
                _("Dice must have at least one side and not more than 10000.")
            )
        results = []
        sumall = 0
        for x in range(dice_type[0]):
            diceroll = random.randint(1, dice_type[1])
            results.append(diceroll)
            sumall += diceroll

        average = sumall / len(results)
        nl = "\n"
        results = [str(result) for result in results]
        await ctx.send(
            _(
                "{user}'s dice rolled:\n```Sum: {sumall}\nAverage:"
                " {average}\nResults:\n{results}```"
            ).format(
                user=ctx.author.mention,
                sumall=sumall,
                average=average,
                results=nl.join(results),
            )
        )

    @commands.command(brief=_("Show my nickname in a random server"))
    @locale_doc
    async def randomname(self, ctx):
        _(
            """Sends you my nickname from a random server.

            ⚠ Caution: may contain NSFW."""
        )
        g = random.choice(
            [g for g in self.bot.guilds if g.me.display_name != self.bot.user.name]
        )
        info = (g.me.display_name, g.name)
        await ctx.send(
            _("In **{server}** I am called **{name}**.").format(
                server=info[1], name=info[0]
            )
        )

    @commands.command(
        aliases=["chuck", "cn", "norris", "theman"],
        brief=_("Facts about Chuck Norris."),
    )
    @locale_doc
    async def chucknorris(self, ctx):
        _(
            """Sends a random Chuck Norris ~~joke~~ fact from [The Chuck Norris API](https://api.chucknorris.io/)"""
        )
        async with self.bot.session.get("https://api.chucknorris.io/jokes/random") as r:
            content = await r.json()
        await ctx.send(content["value"])

    @commands.command(brief=_("Cat pics"), aliases=["meow"])
    @locale_doc
    async def cat(self, ctx):
        _("""Sends cute cat pics from [The Cat API](https://thecatapi.com/).""")
        async with self.bot.session.get(
            "https://api.thecatapi.com/v1/images/search"
        ) as r:
            res = await r.json()
        await ctx.send(
            embed=discord.Embed(
                title=_("Meow!"), color=ctx.author.color.value
            ).set_image(url=res[0]["url"])
        )

    @commands.command(brief=_("Dog pics"), aliases=["woof"])
    @locale_doc
    async def dog(self, ctx):
        _("""Sends cute dog pics from [The Dog API](https://thedogapi.com/).""")
        async with self.bot.session.get(
            "https://api.thedogapi.com/v1/images/search"
        ) as r:
            res = await r.json()
        await ctx.send(
            embed=discord.Embed(
                title=_("Wouff!"), color=ctx.author.color.value
            ).set_image(url=res[0]["url"])
        )

    @commands.command(brief=_("View the uptime"))
    @locale_doc
    async def uptime(self, ctx):
        _("""Shows how long the bot has been connected to Discord.""")
        await ctx.send(
            _("I am online for **{time}**.").format(
                time=str(self.bot.uptime).split(".")[0]
            )
        )

    @commands.command(hidden=True, brief=_("Every good software has an Easter egg."))
    @locale_doc
    async def easteregg(self, ctx):
        _("""Wouldn't be any fun if I told you how to find it, right?""")
        await ctx.send(_("Find it!"))

    @commands.guild_only()
    @commands.command(brief=_("Give a cookie to a user"))
    @locale_doc
    async def cookie(self, ctx, user: MemberConverter):
        _(
            """`<user>` - the discord user to give the cookie to

            Gives a cookie to a user. Sadly, this cookie does not have an effect on gameplay."""
        )
        await ctx.send(
            _(
                "**{user}**, you've been given a cookie by **{author}**. :cookie:"
            ).format(author=ctx.disp, user=user.display_name)
        )

    @commands.guild_only()
    @commands.command(aliases=["ice-cream"], brief=_("Give icecream to a user"))
    @locale_doc
    async def ice(self, ctx, other: MemberConverter):
        _(
            """`<other>` - the discord user to give the icecream to

            Gives icecream to a user. Sadly, this ice does not have an effect on gameplay."""
        )
        await ctx.send(
            _("{other}, here is your ice: :ice_cream:!").format(other=other.mention)
        )

    @commands.guild_only()
    @commands.cooldown(1, 20, BucketType.channel)
    @commands.command(brief=_("User guessing game"))
    @locale_doc
    async def guess(self, ctx):
        _(
            """Guess a user by their avatar and discriminator (the four numbers after the # in a discord tag).

            Both their tag and nickname are accepted as answers. You have 20 seconds to guess.

            (This command has a channel cooldown of 20 seconds.)"""
        )
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

    @commands.command(aliases=["yn"], brief=_("Get a yes/no answer"))
    @locale_doc
    async def yesno(self, ctx, *, question: str):
        _(
            """`<question>` - The question to answer

            An alternative to `{prefix}8ball` with some more blunt answers."""
        )
        possible_answers = [
            "Maybe",
            "I think so",
            "Why are you asking?",
            "I'd say yes",
            "Sure!",
            "I don't think so",
            "Leave me alone",
            "I need some time for myself",
            "Let's please talk about something else",
            "I like it",
            "Do you know what love is?",
            "I don't want to answer this",
            "Definitely",
            "Noone cares about that",
            "Let's talk about you and me",
            "Stop it and let's have fun together",
            "Life is a lie",
            "Are you gay?",
            "Do you know I am female?",
            "42",
            "No, just no",
            "What is the meaning of life?",
            "Ohhh, of course!",
            "Kiss me pleeeease",
            "I am tending to no",
            "Are you kidding me?",
            "Uhm... Yes",
            "Can I be your waifu?",
            "I don't care at all",
            "Sorry, sweetie, I am busy",
            "Let me sleep!",
            "Do you have plans for today?",
            "A biscuit is more entertaining than you",
            "Suicide isn't always the answer",
            "It could be yes, but I don't know",
            "Who knows?",
            "Actually you bore me",
            "Are you really that boring?",
            "Having sex with you is like waking up: BORING",
            "Orum sed non laborum",
            "Eyo noone is intered in that",
            "Possibly yes",
            "Wanna have a drink?",
        ]
        result = random.choice(possible_answers)
        em = discord.Embed(title=question, description=result, colour=ctx.author.colour)
        em.set_thumbnail(url=ctx.author.avatar_url)
        em.timestamp = datetime.datetime.now()
        await ctx.send(embed=em)

    @commands.command(aliases=["cb", "chat"], brief=_("Talk to me"))
    @locale_doc
    async def talk(self, ctx, *, text: str):
        _(
            """`<text>` - The text to say, must be between 3 and 60 characters.

            Talk to me! This uses a chatbot AI backend."""
        )
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
            headers={"authorization": self.bot.config.external.traviapi},
        ) as req:
            json = await req.json()
        await ctx.send(f"{ctx.author.mention}, {json['response']}")

    @commands.command(brief=_("Show a Garfield comic strip"))
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
            """`[date]` - The date on which the comic strip was released, see below for more info

            Sends today's garfield comic if no date info is given.
            Otherwise, the format is `YYYY MM DD` or `DD MM YYYY`, depending on where the year is, with the date parts being seperated with spaces.
            For example: `2013 12 25` is the same as `25 12 2013`, both meaning December 25th 2013."""
        )
        await ctx.send(
            embed=discord.Embed(color=self.bot.config.game.primary_colour).set_image(
                url=f"https://d1ejxu6vysztl5.cloudfront.net/comics/garfield/{date.year}/{date.strftime('%Y-%m-%d')}.gif?format=png"
            )
        )

    @commands.command(aliases=["uf"], brief=_("Shows a userfriendly comic strip"))
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
            """`[date]` - The date on which the comic strip was released, see below for more info

            Sends today's userfriendly comic if no date info is given.
            Otherwise, the format is `YYYY MM DD` or `DD MM YYYY`, depending on where the year is, with the date parts being seperated with spaces.
            For example: `2013 12 25` is the same as `25 12 2013`, both meaning December 25th 2013."""
        )
        async with self.bot.session.get(
            f"http://ars.userfriendly.org/cartoons/?id={date.strftime('%Y%m%d')}&mode=classic"
        ) as r:
            stuff = await r.text()

        await ctx.send(
            embed=discord.Embed(
                color=self.bot.config.game.primary_colour,
                url="http://userfriendly.org",
                title=_("Taken from userfriendly.org"),
                description=str(date),
            ).set_image(
                url=re.compile('<img border="0" src="([^"]+)"').search(stuff).group(1)
            )
        )

    @commands.command(brief=_("Our partnered bots"))
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
                "Trivia, Hangman, Minesweeper, Connect 4 and more, right from your"
                " chat! A bot offering non-RPG games made by deprilula28 and"
                " Fin.\n[top.gg Page](https://top.gg/bot/gamesrob)"
            ),
        )
        em.add_field(
            name="Cautious Memory",
            value=_(
                "Cautious Memory brings wiki-style pages to your server. Use it to"
                " document who's who in your server, inside jokes, or community lore."
                " Includes a full featured permissions system to keep your pages"
                " squeaky clean.\n[top.gg Page](https://top.gg/bot/541707781665718302)"
            ),
        )
        em.add_field(
            name="Cleverbot",
            value=_(
                "Cleverbot is a Discord bot that will chat with you and your"
                " friends.\n[top.gg Page](https://top.gg/bot/508012980194115595)"
            ),
        )
        await ctx.send(embed=em)

    @commands.command(brief=_("Search wikipedia"))
    @locale_doc
    async def wikipedia(self, ctx, *, query: str):
        _(
            """`<query>` - The wikipedia query to search for

            Searches Wikipedia for an entry."""
        )
        try:
            page = (await self.bot.wikipedia.opensearch(query))[0]
            text = await page.summary()
        except (aiowiki.exceptions.PageNotFound, IndexError):
            return await ctx.send(_("No wikipedia entry found."))
        if not text:
            return await ctx.send(_("Could not parse article summary."))
        p = commands.Paginator()
        for line in text.split("\n"):
            for i in chunks(line, 1900):
                p.add_line(i)
        await self.bot.paginator.Paginator(
            title=page.title, entries=p.pages, length=1
        ).paginate(ctx)

    @commands.command(aliases=["wiki"], brief=_("Search the Idle Wiki"))
    @locale_doc
    async def idlewiki(self, ctx, *, query: str = None):
        _(
            """`[query]` - The idlewiki query to search for

            Searches Idle's wiki for an entry."""
        )
        if not query:
            return await ctx.send(
                _(
                    "Check out the official IdleRPG Wiki"
                    " here:\n<https://wiki.idlerpg.xyz/index.php?title=Main_Page>"
                )
            )
        try:
            page = (await self.bot.idlewiki.opensearch(query))[0]
            text = await page.summary()
        except (aiowiki.exceptions.PageNotFound, IndexError):
            return await ctx.send(_("No entry found."))
        else:
            if not text:
                return await ctx.send(_("No content to display."))
        p = commands.Paginator()
        for line in text.split("\n"):
            for i in chunks(line, 1900):
                p.add_line(i)
        await self.bot.paginator.Paginator(
            title=page.title, entries=p.pages, length=1
        ).paginate(ctx)

    @commands.command(
        aliases=["pages", "about"], brief=_("Info about the bot and related sites")
    )
    @locale_doc
    async def web(self, ctx):
        _("""About the bot and our websites.""")
        await ctx.send(
            _(
                # xgettext: no-python-format
                """\
**IdleRPG** is Discord's most advanced medieval RPG bot.
We aim to provide the perfect experience at RPG in Discord with minimum effort for the user.

We are not collecting any data apart from your character information and our transaction logs.
The bot is 100% free to use and open source.
This bot is developed by people who love to code for a good cause and improving your gameplay experience.

**Links**
<https://git.travitia.xyz/Kenvyra/IdleRPG> - Source Code
<https://git.travitia.xyz> - GitLab (Public)
<https://idlerpg.xyz> - Bot Website
<https://wiki.idlerpg.xyz> - IdleRPG wiki
<https://raid.idlerpg.xyz> - Raid Website
<https://travitia.xyz> - IdleRPG's next major upgrade
<https://idlerpg.xyz> - Our forums
<https://public-api.travitia.xyz> - Our public API
<https://cloud.idlerpg.xyz> - VPS hosting by IdleRPG
<https://github.com/Kenvyra> - Other IdleRPG related code
<https://discord.com/terms> - Discord's ToS
<https://www.ncpgambling.org/help-treatment/national-helpline-1-800-522-4700/> - Gambling Helpline"""
            )
        )

    @commands.command(brief=_("Show the rules again"))
    @locale_doc
    async def rules(self, ctx):
        _(
            """Shows the rules you consent to when creating a character. Don't forget them!"""
        )
        await ctx.send(
            _(
                """\
1) Only up to two characters per individual
2) No abusing or benefiting from bugs or exploits
3) Be friendly and kind to other players
4) Trading in-game items or currency for real money or items directly comparable to currency is forbidden
5) Giving or selling renamed items is forbidden

IdleRPG is a global bot, your characters are valid everywhere"""
            )
        )


def setup(bot):
    bot.add_cog(Miscellaneous(bot))
