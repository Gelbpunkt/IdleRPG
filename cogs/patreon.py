"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import copy
import functools
from io import BytesIO

import discord
from asyncpg.exceptions import StringDataRightTruncationError
from discord.ext import commands

from utils.checks import has_char, is_patron
from utils.misc import makebg


class Patreon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @is_patron()
    @has_char()
    @commands.command()
    async def weaponname(self, ctx, itemid: int, *, newname: str):
        """[Patreon Only] Changes an item name."""
        if len(newname) > 40:
            return await ctx.send("Name too long.")
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow(
                'SELECT * FROM allitems WHERE "owner"=$1 and "id"=$2;',
                ctx.author.id,
                itemid,
            )
            if not item:
                return await ctx.send(f"You don't have an item with the ID `{itemid}`.")
            await conn.execute(
                'UPDATE allitems SET "name"=$1 WHERE "id"=$2;', newname, itemid
            )
        await ctx.send(f"The item with the ID `{itemid}` is now called `{newname}`.")

    @is_patron()
    @has_char()
    @commands.command()
    async def background(self, ctx, url: str):
        """[Patreon Only] Changes your profile background."""
        premade = [f"{self.bot.BASE_URL}/profile/premade{i}.png" for i in range(1, 14)]
        if url == "reset":
            url = 0
        elif url.startswith("http") and (
            url.endswith(".png") or url.endswith(".jpg") or url.endswith(".jpeg")
        ):
            url = url
        elif url.isdigit():
            try:
                url = premade[int(url) - 1]
            except IndexError:
                return await ctx.send("That is not a valid premade background.")
        else:
            return await ctx.send(
                "I couldn't read that URL. Does it start with `http://` or `https://` and is either a png or jpeg?"
            )
        try:
            await self.bot.pool.execute(
                'UPDATE profile SET "background"=$1 WHERE "user"=$2;',
                str(url),
                ctx.author.id,
            )
        except StringDataRightTruncationError:
            return await ctx.send("The URL is too long.")
        if url != 0:
            await ctx.send(f"Your new profile picture is now:\n{url}")
        else:
            await ctx.send("Your profile picture has been reset.")

    @is_patron()
    @commands.command()
    async def makebackground(self, ctx, url: str, overlaytype: int):
        """[Patreon Only] Generates a profile background based on an image. Valid overlays are 1 or 2 for grey and black."""
        if overlaytype not in [1, 2]:
            return await ctx.send("Use either `1` or `2` as the overlay type.")
        if not url.startswith("http") and (
            url.endswith(".png") or url.endswith(".jpg") or url.endswith(".jpeg")
        ):
            return await ctx.send(
                "I couldn't read that URL. Does it start with `http://` or `https://` and is either a png or jpeg?"
            )
        async with self.bot.trusted_session.post(
            f"{self.bot.config.okapi_url}/api/genoverlay/{overlaytype}",
            data={"url": url},
        ) as req:
            background = BytesIO(await req.read())
        headers = {"Authorization": f"Client-ID {self.bot.config.imgur_token}"}
        data = {"image": copy.copy(background)}
        async with self.bot.session.post(
            "https://api.imgur.com/3/image", data=data, headers=headers
        ) as r:
            link = (await r.json())["data"]["link"]
        await ctx.send(
            f"Imgur Link for `{ctx.prefix}background`\n<{link}>",
            file=discord.File(fp=background, filename="GeneratedProfile.png"),
        )

    @is_patron()
    @is_guild_leader()
    @commands.command()
    async def updateguild(self, ctx):
        """[Patreon Only] Update your guild member limit."""
        await self.bot.pool.execute(
            'UPDATE guild SET memberlimit=$1 WHERE "leader"=$2;', 100, ctx.author.id
        )
        await ctx.send("Your guild member limit is now 100.")

    @has_char()
    @commands.command()
    async def eventbackground(self, ctx, number: int):
        """Update your background to one from the events."""
        async with self.bot.pool.acquire() as conn:
            bgs = await conn.fetchval(
                'SELECT backgrounds FROM profile WHERE "user"=$1;', ctx.author.id
            )
            try:
                bg = bgs[number - 1]
            except TypeError:
                return await ctx.send(
                    f"The background number {number} is not valid, you only have {len(bgs)} available."
                )
            await conn.execute(
                'UPDATE profile SET background=$1 WHERE "user"=$2;', bg, ctx.author.id
            )
        await ctx.send("Background updated!")


def setup(bot):
    bot.add_cog(Patreon(bot))
