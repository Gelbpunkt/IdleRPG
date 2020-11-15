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
from asyncpg.exceptions import StringDataRightTruncationError
from discord.ext import commands

from classes.items import ItemType
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import random
from utils.checks import has_char, is_guild_leader, is_patron, user_is_patron
from utils.i18n import _, locale_doc


class Patreon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @commands.command(brief=_("Reset a modified item"))
    @locale_doc
    async def resetitem(self, ctx, itemid: int):
        _(
            """`<itemid>` - The ID of the item to reset

            Reset an item's type and name, if modified. Once an item is reset, it can be sold again."""
        )
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow('SELECT * FROM allitems WHERE "id"=$1;', itemid)

            if not item or item["owner"] != ctx.author.id:
                return await ctx.send(_("You do not own this item."))

            if not item["original_name"] and not item["original_type"]:
                return await ctx.send(_("Nothing to do..."))

            new_type = item["original_type"] or item["type"]
            old_type = item["type"]

            if old_type == "Shield" and new_type != "Shield":
                dmg, armor = item["armor"], 0
            elif old_type != "Shield" and new_type == "Shield":
                dmg, armor = 0, item["damage"]
            else:
                dmg, armor = item["damage"], item["armor"]

            if new_type == "Shield":
                hand = "left"
            elif new_type in ("Spear", "Wand"):
                hand = "right"
            elif new_type in ("Bow", "Howlet", "Scythe"):
                hand = "both"
            else:
                hand = "any"

            await conn.execute(
                'UPDATE allitems SET "name"=CASE WHEN "original_name" IS NULL THEN'
                ' "name" ELSE "original_name" END, "original_name"=NULL, "damage"=$2,'
                ' "armor"=$3, "type"=$4, "hand"=$5, "original_type"=NULL WHERE'
                ' "id"=$1;',
                itemid,
                dmg,
                armor,
                new_type,
                hand,
            )
            await conn.execute(
                'UPDATE inventory SET "equipped"=$1 WHERE "item"=$2;', False, itemid
            )

        await ctx.send(_("Item reset."))

    @is_patron()
    @has_char()
    @commands.command(brief=_("[basic] Change an item's name"))
    @locale_doc
    async def weaponname(self, ctx, itemid: int, *, newname: str):
        _(
            """`<itemid>` - The ID of the item to rename
            `<newname>` - The name to give the item, must be shorter than 40 characters

            Change an item's name. Once an item is renamed, it can no longer be sold.

            Only basic (or above) tier patrons can use this command."""
        )
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
                'UPDATE allitems SET "name"=$1, "original_name"=CASE WHEN'
                ' "original_name" IS NULL THEN "name" ELSE "original_name" END WHERE'
                ' "id"=$2;',
                newname,
                itemid,
            )
        await ctx.send(
            _("The item with the ID `{itemid}` is now called `{newname}`.").format(
                itemid=itemid, newname=newname
            )
        )

    @is_patron("bronze")
    @has_char()
    @commands.command(brief=_("[bronze] Change an item's type"))
    @locale_doc
    async def weapontype(self, ctx, itemid: int, new_type: str.title):
        _(
            """`<itemid>` - The ID of the item to change type
            `<new_type>` - The type to transform the item into

            Change an item's type. Once the type changed, the item becomes unsellable.

            You may not change a two-handed item into a one-handed one, or vice versa.
            This proves useful for merging items.

            Only bronze (or above) tier patrons can use this command."""
        )
        item_type = ItemType.from_string(new_type)
        if item_type is None:
            return await ctx.send(_("Invalid type."))
        hand = item_type.get_hand().value
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

            if (item["hand"] == "both" and hand != "both") or (
                item["hand"] != "both" and hand == "both"
            ):
                return await ctx.send(
                    _(
                        "You may not change a two-handed item to a single-handed one"
                        " and vice-versa due to weapon damage reasons."
                    )
                )

            stat = item["damage"] or item["armor"]

            await conn.execute(
                'UPDATE allitems SET "type"=$1, "original_type"=CASE WHEN'
                ' "original_type" IS NULL THEN "type" ELSE "original_type" END,'
                ' "damage"=$2, "armor"=$3, "hand"=$4 WHERE "id"=$5;',
                new_type,
                0 if new_type == "Shield" else stat,
                stat if new_type == "Shield" else 0,
                hand,
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

    @is_patron("gold")
    @has_char()
    @user_cooldown(86400)
    @commands.command(brief=_("[gold] Receive a daily booster"))
    @locale_doc
    async def donatordaily(self, ctx):
        _(
            """Receive a daily booster. The booster can be a time, money or luck booster.

            (This command has a cooldown of 24 hours.)"""
        )
        type_ = random.choice(["time", "money", "luck"])
        await self.bot.pool.execute(
            f'UPDATE profile SET "{type_}_booster"="{type_}_booster"+1 WHERE'
            ' "user"=$1;',
            ctx.author.id,
        )
        await self.bot.cache.update_profile_cols_rel(
            ctx.author.id, **{f"{type_}_booster": 1}
        )
        await ctx.send(_("You received a daily {type_} booster!").format(type_=type_))

    @has_char()
    @commands.command(brief=_("[basic] Change your profile background"))
    @locale_doc
    async def background(self, ctx, url: str):
        _(
            """`<url>` - The image URL to use as the background, may not exceed 60 characters.

            Change your profile's background image. `{prefix}background reset` sets it to the default one again.

            This image should be formatted by the `{prefix}makebackground` command, however if you want to get creative and not use an overlay, or create your own, the image dimensions are 800x650.
            Having trouble finding a short URL? Try following [this tutorial](https://wiki.idlerpg.xyz/index.php?title=Tutorial:_Short_Image_URLs)!

            Only basic (or above) tier patrons can use this command."""
        )
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
                    "I couldn't read that URL. Does it start with `http://` or"
                    " `https://` and is either a png or jpeg?"
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
            await self.bot.cache.update_profile_cols_abs(
                ctx.author.id, background=str(url)
            )
        except StringDataRightTruncationError:
            return await ctx.send(_("The URL is too long."))
        if url != 0:
            await ctx.send(_("Your new profile picture is now:\n{url}").format(url=url))
        else:
            await ctx.send(_("Your profile picture has been reset."))

    @is_patron()
    @commands.command(brief=_("[basic] Formats an image for background compatability"))
    @locale_doc
    async def makebackground(self, ctx, url: str):
        _(
            """`<url>` - The image URL to format

            Generate a profile background for you. This will stretch/compress your image to 800x650 pixels and layer on an overlay.
            This will return a link you can then use for `{prefix}background`.

            Only basic (or above) tier patrons can use this command."""
        )
        if not url.startswith("http") and (
            url.endswith(".png") or url.endswith(".jpg") or url.endswith(".jpeg")
        ):
            return await ctx.send(
                _(
                    "I couldn't read that URL. Does it start with `http://` or"
                    " `https://` and is either a png or jpeg?"
                )
            )
        async with self.bot.trusted_session.post(
            f"{self.bot.config.external.okapi_url}/api/genoverlay", json={"url": url}
        ) as req:
            background = await req.text()
        headers = {
            "Authorization": f"Client-ID {self.bot.config.external.imgur_token}",
            "Content-Type": "application/json",
        }
        data = {"image": background, "type": "base64"}
        async with self.bot.session.post(
            "https://api.imgur.com/3/image", json=data, headers=headers
        ) as r:
            try:
                link = (await r.json())["data"]["link"]
            except KeyError:
                return await ctx.send(_("Error when uploading to Imgur."))
        await ctx.send(
            _("Imgur Link for `{prefix}background`\n{link}").format(
                prefix=ctx.prefix, link=link
            )
        )

    @is_patron()
    @is_guild_leader()
    @commands.command(brief=_("[basic] Upgrade your guild"))
    @locale_doc
    async def updateguild(self, ctx):
        _(
            """Update your guild member limit and bank size according to your donation tier.

            Gold (and above) Donators have their bank space quintupled (x5), Silver Donators have theirs doubled.
            The member limit is set to 100 regardless of donation tier.

            ⚠ To use this, you have to be the leader of a guild, not just a member.

            Only basic (or above) tier patrons can use this command."""
        )
        # Silver x2, Gold x5
        if await user_is_patron(self.bot, ctx.author, "gold"):
            m = 5
        elif await user_is_patron(self.bot, ctx.author, "silver"):
            m = 2
        else:
            m = 1
        async with self.bot.pool.acquire() as conn:
            old = await conn.fetchrow(
                'SELECT * FROM guild WHERE "leader"=$1;', ctx.author.id
            )
            if old["memberlimit"] < 100:
                await conn.execute(
                    'UPDATE guild SET "memberlimit"=$1, "banklimit"="upgrade"*250000*$2'
                    ' WHERE "leader"=$3;',
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
    @commands.command(brief=_("Change your background"))
    @locale_doc
    async def eventbackground(self, ctx, number: int):
        _(
            """`<number>` - The number of the eventbackground to use

            Update your background to one from the events. You can get event backgrounds from special events, for example easter or christmas."""
        )
        if not (bgs := ctx.character_data["backgrounds"]):
            return await ctx.send(
                _(
                    "You do not have an eventbackground. They can be acquired on"
                    " seasonal events."
                )
            )
        try:
            bg = bgs[number - 1]
        except IndexError:
            return await ctx.send(
                _(
                    "The background number {number} is not valid, you only have"
                    " {total} available."
                ).format(number=number, total=len(bgs))
            )
        await self.bot.pool.execute(
            'UPDATE profile SET "background"=$1 WHERE "user"=$2;', bg, ctx.author.id
        )
        await self.bot.cache.update_profile_cols_abs(ctx.author.id, background=bg)
        await ctx.send(_("Background updated!"))


def setup(bot):
    bot.add_cog(Patreon(bot))
