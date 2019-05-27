"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import copy
from io import BytesIO

import discord
from asyncpg.exceptions import StringDataRightTruncationError
from discord.ext import commands

from utils.checks import has_char, is_guild_leader, is_patron


class Patreon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @is_patron()
    @has_char()
    @commands.command()
    @locale_doc
    async def weaponname(self, ctx, itemid: int, *, newname: str):
        _("""[Patreon Only] Changes an item name.""")
        if len(newname) > 40:
            return await ctx.send(_("Name too long."))
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow(
                'SELECT * FROM allitems WHERE "owner"=$1 and "id"=$2;',
                ctx.author.id,
                itemid,
            )
            if not item:
                return await ctx.send(
                    _("You don't have an item with the ID `{itemid}`.").format(
                        itemid=itemid
                    )
                )
            await conn.execute(
                'UPDATE allitems SET "name"=$1 WHERE "id"=$2;', newname, itemid
            )
        await ctx.send(
            _("The item with the ID `{itemid}` is now called `{newname}`.").format(
                itemid=itemid, newname=newname
            )
        )

    @is_patron()
    @has_char()
    @commands.command()
    @locale_doc
    async def background(self, ctx, url: str):
        _("""[Patreon Only] Changes your profile background.""")
        premade = [f"{self.bot.BASE_URL}/profile/premade{i}.png" for i in range(1, 14)]
        if url == _("reset"):
            url = 0
        elif url.startswith("http") and (
            url.endswith(".png") or url.endswith(".jpg") or url.endswith(".jpeg")
        ):
            url = url
        elif url.isdigit():
            try:
                url = premade[int(url) - 1]
            except IndexError:
                return await ctx.send(_("That is not a valid premade background."))
        else:
            return await ctx.send(
                _(
                    "I couldn't read that URL. Does it start with `http://` or `https://` and is either a png or jpeg?"
                )
            )
        try:
            await self.bot.pool.execute(
                'UPDATE profile SET "background"=$1 WHERE "user"=$2;',
                str(url),
                ctx.author.id,
            )
        except StringDataRightTruncationError:
            return await ctx.send(_("The URL is too long."))
        if url != 0:
            await ctx.send(_("Your new profile picture is now:\n{url}").format(url=url))
        else:
            await ctx.send(_("Your profile picture has been reset."))

    @is_patron()
    @commands.command()
    @locale_doc
    async def makebackground(self, ctx, url: str, overlaytype: int):
        _(
            """[Patreon Only] Generates a profile background based on an image. Valid overlays are 1 or 2 for grey and black."""
        )
        if overlaytype not in [1, 2]:
            return await ctx.send(_("Use either `1` or `2` as the overlay type."))
        if not url.startswith("http") and (
            url.endswith(".png") or url.endswith(".jpg") or url.endswith(".jpeg")
        ):
            return await ctx.send(
                _(
                    "I couldn't read that URL. Does it start with `http://` or `https://` and is either a png or jpeg?"
                )
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
            try:
                link = (await r.json())["data"]["link"]
            except KeyError:
                return await ctx.send(_("Error when uploading to Imgur."))
        await ctx.send(
            _("Imgur Link for `{prefix}background`\n<{link}>").format(
                prefix=ctx.prefix, link=link
            ),
            file=discord.File(fp=background, filename="GeneratedProfile.png"),
        )

    @is_patron()
    @is_guild_leader()
    @commands.command()
    @locale_doc
    async def updateguild(self, ctx):
        _("""[Patreon Only] Update your guild member limit.""")
        await self.bot.pool.execute(
            'UPDATE guild SET memberlimit=$1 WHERE "leader"=$2;', 100, ctx.author.id
        )
        await ctx.send(_("Your guild member limit is now 100."))

    @has_char()
    @commands.command()
    @locale_doc
    async def eventbackground(self, ctx, number: int):
        _("""Update your background to one from the events.""")
        async with self.bot.pool.acquire() as conn:
            bgs = await conn.fetchval(
                'SELECT backgrounds FROM profile WHERE "user"=$1;', ctx.author.id
            )
            try:
                bg = bgs[number - 1]
            except TypeError:
                return await ctx.send(
                    _(
                        "The background number {number} is not valid, you only have {total} available."
                    ).format(number=number, total=len(bgs))
                )
            await conn.execute(
                'UPDATE profile SET background=$1 WHERE "user"=$2;', bg, ctx.author.id
            )
        await ctx.send(_("Background updated!"))


def setup(bot):
    bot.add_cog(Patreon(bot))
