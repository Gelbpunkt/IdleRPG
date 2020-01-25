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
import copy
import random

from io import BytesIO

import discord

from asyncpg.exceptions import StringDataRightTruncationError
from discord.ext import commands

from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils.checks import has_char, is_guild_leader, is_patron, user_is_patron


class Patreon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @commands.command()
    @locale_doc
    async def resetitem(self, ctx, itemid: int):
        _("""Reset an item's type and name, if modified.""")
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow('SELECT * FROM allitems WHERE "id"=$1;', itemid)
            if not item or item["owner"] != ctx.author.id:
                return await ctx.send(_("You do not own this item."))
            if not item["original_name"] and not item["original_type"]:
                return await ctx.send(_("Nothing to do..."))
            if item["original_type"] == item["type"]:
                dmg, armor = item["damage"], item["armor"]
            else:
                dmg, armor = item["armor"], item["damage"]
            await conn.execute(
                'UPDATE allitems SET "name"=CASE WHEN "original_name" IS NULL THEN "name" ELSE "original_name" END, "original_name"=NULL, "damage"=$2, "armor"=$3, "type"=CASE WHEN "original_type" IS NULL THEN "type" ELSE "original_type" END, "original_type"=NULL WHERE "id"=$1;',
                itemid,
                dmg,
                armor,
            )
            await conn.execute(
                'UPDATE inventory SET "equipped"=$1 WHERE "item"=$2;', False, itemid
            )
        await ctx.send(_("Item reset."))

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
                'UPDATE allitems SET "name"=$1, "original_name"=CASE WHEN "original_name" IS NULL THEN "name" ELSE "original_name" END WHERE "id"=$2;',
                newname,
                itemid,
            )
        await ctx.send(
            _("The item with the ID `{itemid}` is now called `{newname}`.").format(
                itemid=itemid, newname=newname
            )
        )

    @is_patron("Bronze Donators")
    @has_char()
    @commands.command()
    @locale_doc
    async def weapontype(self, ctx, itemid: int, new_type: str.title):
        _("""[Patreon Only, Bronze and above] Changes an item type.""")
        if new_type not in ["Sword", "Shield"]:
            return await ctx.send(_("Invalid type. Try Sword or Shield."))
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

            if item["type"] == new_type:
                return await ctx.send(
                    _("The item is already a {item_type}.").format(item_type=new_type)
                )

            await conn.execute(
                'UPDATE allitems SET "type"=$1, "original_type"=CASE WHEN "original_type" IS NULL THEN "type" ELSE "original_type" END, "damage"=$2, "armor"=$3 WHERE "id"=$4;',
                new_type,
                item["armor"],
                item["damage"],
                itemid,
            )
            await conn.execute(
                'UPDATE inventory SET "equipped"=$1 WHERE "item"=$2;', False, itemid
            )
        await ctx.send(
            _("The item with the ID `{itemid}` is now a `{itemtype}`.").format(
                itemid=itemid, itemtype=new_type
            )
        )

    @is_patron("Gold Donators")
    @has_char()
    @user_cooldown(86400)
    @commands.command()
    @locale_doc
    async def donatordaily(self, ctx):
        _("""[Patreon Only, Gold and above] Receive a daily booster.""")
        type_ = random.choice(["time", "money", "luck"])
        await self.bot.pool.execute(
            f'UPDATE profile SET "{type_}_booster"="{type_}_booster"+1 WHERE "user"=$1;',
            ctx.author.id,
        )
        await ctx.send(_("You received a daily {type_} booster!").format(type_=type_))

    @has_char()
    @commands.command()
    @locale_doc
    async def background(self, ctx, url: str):
        _("""[Patreon Only] Changes your profile background.""")
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
                return await ctx.send(_("That is not a valid premade background."))
        else:
            return await ctx.send(
                _(
                    "I couldn't read that URL. Does it start with `http://` or `https://` and is either a png or jpeg?"
                )
            )
        if url != 0 and not await user_is_patron(self.bot, ctx.author):
            raise commands.CheckFailure("You are not a donator.")
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
    async def makebackground(self, ctx, url: str):
        _("""[Patreon Only] Generates a profile background based on an image.""")
        if not url.startswith("http") and (
            url.endswith(".png") or url.endswith(".jpg") or url.endswith(".jpeg")
        ):
            return await ctx.send(
                _(
                    "I couldn't read that URL. Does it start with `http://` or `https://` and is either a png or jpeg?"
                )
            )
        async with self.bot.trusted_session.post(
            f"{self.bot.config.okapi_url}/api/genoverlay", data={"url": url}
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
        _("""[Patreon Only] Update your guild member limit and bank size.""")
        # Silver x2, Gold x5
        if await user_is_patron(self.bot, ctx.author, "Gold Donators"):
            m = 5
        elif await user_is_patron(self.bot, ctx.author, "Silver Donators"):
            m = 2
        else:
            m = 1
        async with self.bot.pool.acquire() as conn:
            old = await conn.fetchrow(
                'SELECT * FROM guild WHERE "leader"=$1;', ctx.author.id
            )
            if old["memberlimit"] < 100:
                await conn.execute(
                    'UPDATE guild SET "memberlimit"=$1, "banklimit"="upgrade"*250000*$2 WHERE "leader"=$3;',
                    100,
                    m,
                    ctx.author.id,
                )
            else:
                await conn.execute(
                    'UPDATE guild SET "banklimit"="banklimit"*$1 WHERE "leader"=$2;',
                    m,
                    ctx.author.id,
                )
        await ctx.send(_("Your guild was updated."))

    @has_char()
    @commands.command()
    @locale_doc
    async def eventbackground(self, ctx, number: int):
        _("""Update your background to one from the events.""")
        async with self.bot.pool.acquire() as conn:
            bgs = await conn.fetchval(
                'SELECT backgrounds FROM profile WHERE "user"=$1;', ctx.author.id
            )
            if not bgs:
                return await ctx.send(
                    _(
                        "You do not have an eventbackground. They can be acquired on seasonal events."
                    )
                )
            try:
                bg = bgs[number - 1]
            except IndexError:
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
