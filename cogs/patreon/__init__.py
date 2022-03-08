"""
The IdleRPG Discord Bot
Copyright (C) 2018-2021 Diniboy and Gelbpunkt

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

import discord

from aiohttp.client_exceptions import ContentTypeError
from asyncpg.exceptions import StringDataRightTruncationError
from discord.ext import commands

from classes.bot import Bot
from classes.items import ItemType
from cogs.shard_communication import next_day_cooldown
from utils import random
from utils.checks import (
    ImgurUploadError,
    has_char,
    is_guild_leader,
    is_patron,
    user_is_patron,
)
from utils.i18n import _, locale_doc


class Patreon(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.ruby_or_above = []

        if self.bot.config.external.patreon_token:
            asyncio.create_task(self.update_ruby_or_above())

    async def update_ruby_or_above(self) -> None:
        await self.bot.wait_until_ready()

        if not self.bot.get_guild(self.bot.config.game.support_server_id):
            return

        headers = {"Authorization": f"Bearer {self.bot.config.external.patreon_token}"}
        params = {
            "include": "user",
            "fields[member]": "lifetime_support_cents,patron_status,pledge_relationship_start,currently_entitled_amount_cents",
            "fields[user]": "social_connections",
            "page[size]": 100000,
        }

        async with self.bot.session.get(
            "https://www.patreon.com/api/oauth2/api/current_user/campaigns",
            headers=headers,
        ) as resp:
            json = await resp.json()
            campaign_id = json["data"][0]["id"]

        while not self.bot.is_closed():
            self.bot.logger.info("Starting patreon update")

            ruby_or_higher = []
            patreon_ids = []

            while True:
                async with self.bot.session.get(
                    f"https://www.patreon.com/api/oauth2/v2/campaigns/{campaign_id}/members",
                    headers=headers,
                    params=params,
                ) as resp:
                    json = await resp.json()

                for donator in json["data"]:
                    if donator["attributes"]["currently_entitled_amount_cents"] >= 7500:
                        user_id = int(donator["relationships"]["user"]["data"]["id"])
                        patreon_ids.append(user_id)

                for user in json["included"]:
                    if user.get("type") != "user":
                        continue

                    if not (attributes := user.get("attributes")):
                        continue
                    if not (connections := attributes.get("social_connections")):
                        continue
                    if not (discord := connections.get("discord")):
                        continue
                    discord_user_id = int(discord.get("user_id", "0"))
                    patreon_user_id = int(user["id"])

                    if patreon_user_id in patreon_ids:
                        ruby_or_higher.append(discord_user_id)

                pagination_data = json["meta"]["pagination"]
                if not pagination_data.get("cursors"):
                    break
                next_cursor_id = pagination_data["cursors"]["next"]
                params["page[cursor]"] = next_cursor_id

            self.ruby_or_above = ruby_or_higher

            self.bot.logger.info(
                f"Done with patreon update, found {len(self.ruby_or_above)} ruby or diamond donators"
            )

            # Run once per hour
            await asyncio.sleep(60 * 60)

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
                "SELECT * FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE"
                " ai.id=$1 AND ai.owner=$2;",
                itemid,
                ctx.author.id,
            )
            if not item:
                return await ctx.send(
                    _(
                        "You don't have an item in your inventory with the ID `{itemid}`."
                    ).format(itemid=itemid)
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
                "SELECT * FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE"
                " ai.id=$1 AND ai.owner=$2;",
                itemid,
                ctx.author.id,
            )
            if not item:
                return await ctx.send(
                    _(
                        "You don't have an item in your inventory with the ID `{itemid}`."
                    ).format(itemid=itemid)
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
    @next_day_cooldown()
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
        except StringDataRightTruncationError:
            return await ctx.send(_("The URL is too long."))
        if url != 0:
            await ctx.send(_("Your new profile picture is now:\n{url}").format(url=url))
        else:
            await ctx.send(_("Your profile picture has been reset."))

    @is_patron()
    @commands.command(brief=_("[basic] Formats an image for background compatability"))
    @locale_doc
    async def makebackground(self, ctx, url: str, style: str = "dark"):
        _(
            """`<url>` - The image URL to format
            `<style>` - The overlay type to use. Available options are dark and light.

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

        if style not in ("dark", "light"):
            return await ctx.send(_("Overlay type must be `dark` or `light`."))

        async with self.bot.trusted_session.post(
            f"{self.bot.config.external.okapi_url}/api/genoverlay",
            json={"url": url, "style": style},
            headers={"Authorization": self.bot.config.external.okapi_token},
        ) as req:
            if req.status == 200:
                background = await req.text()
            else:
                # Error, means try reading the response JSON error
                try:
                    error_json = await req.json()
                    return await ctx.send(
                        _(
                            "There was an error processing your image. Reason: {reason} ({detail})"
                        ).format(
                            reason=error_json["reason"], detail=error_json["detail"]
                        )
                    )
                except ContentTypeError:
                    return await ctx.send(
                        _("Unexpected internal error when generating image.")
                    )
                except Exception:
                    return await ctx.send(_("Unexpected error when generating image."))

        try:
            link = await self.bot.cogs["Miscellaneous"].get_imgur_url(background)
        except ImgurUploadError:
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
                    'UPDATE guild SET "banklimit"="upgrade"*250000*$1 WHERE "leader"=$2;',
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
        await ctx.send(_("Background updated!"))

    @has_char()
    @commands.command(brief=_("View your eventbackgrounds"))
    @locale_doc
    async def eventbackgrounds(self, ctx):
        _(
            """View a list of all backgrounds you have acquired from events. You can get event backgrounds from special events, for example easter or christmas.

            You can use one of these backgrounds on your profile using `{prefix}eventbackground`."""
        )
        if not (bgs := ctx.character_data["backgrounds"]):
            return await ctx.send(
                _(
                    "You do not have an eventbackground. They can be acquired on"
                    " seasonal events."
                )
            )
        pages = [
            discord.Embed(
                title=_("Background {number}/{total}").format(number=i, total=len(bgs)),
                color=discord.Color.blurple(),
            )
            .set_image(url=url)
            .set_footer(
                text=_(
                    "Use {prefix}eventbackground {number} to use this background"
                ).format(prefix=ctx.prefix, number=i)
            )
            for i, url in enumerate(bgs, 1)
        ]

        await self.bot.paginator.Paginator(extras=pages).paginate(ctx)


def setup(bot: Bot) -> None:
    bot.add_cog(Patreon(bot))
