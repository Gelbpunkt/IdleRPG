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

from typing import Union

import discord

from discord.ext import commands

from classes.converters import IntFromTo, IntGreaterThan, UserWithCharacter
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils.checks import has_char, is_gm


class GameMaster(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.top_auction = None

    @is_gm()
    @commands.command(aliases=["cleanshop", "cshop"], hidden=True)
    @locale_doc
    async def clearshop(self, ctx):
        _("""[Game Master only] Clean up the shop.""")
        async with self.bot.pool.acquire() as conn:
            timed_out = await conn.fetch(
                """DELETE FROM market WHERE "published" + '14 days'::interval < NOW() RETURNING *;""",
                timeout=600,
            )
            await conn.executemany(
                'INSERT INTO inventory ("item", "equipped") VALUES ($1, $2);',
                [(i["item"], False) for i in timed_out],
                timeout=600,
            )
        await ctx.send(
            _("Cleared {num} shop items which timed out.").format(num=len(timed_out))
        )

    @is_gm()
    @commands.command(hidden=True)
    @locale_doc
    async def unban(self, ctx, *, other: discord.User):
        _("""[Game Master only] Unban someone from the bot.""")
        try:
            self.bot.bans.remove(other.id)
            await ctx.send(_("Unbanned: {other}").format(other=other.name))
        except ValueError:
            await ctx.send(_("{other} is not banned.").format(other=other.name))

    @is_gm()
    @commands.command(hidden=True)
    @locale_doc
    async def gmgive(self, ctx, money: int, other: UserWithCharacter):
        _("""[Game Master only] Gives money to a user without loss.""")
        await self.bot.pool.execute(
            'UPDATE profile SET money=money+$1 WHERE "user"=$2;', money, other.id
        )
        await ctx.send(
            _(
                "Successfully gave **${money}** without a loss for you to **{other}**."
            ).format(money=money, other=other)
        )
        await self.bot.http.send_message(
            self.bot.config.gm_log_channel,
            f"**{ctx.author}** gave **${money}** to **{other}**.",
        )

    @is_gm()
    @commands.command(hidden=True)
    @locale_doc
    async def gmremove(self, ctx, money: int, other: UserWithCharacter):
        _("""[Game Master only] Removes money from a user without gain.""")
        await self.bot.pool.execute(
            'UPDATE profile SET money=money-$1 WHERE "user"=$2;', money, other.id
        )
        await ctx.send(
            _("Successfully removed **${money}** from **{other}**.").format(
                money=money, other=other
            )
        )
        await self.bot.http.send_message(
            self.bot.config.gm_log_channel,
            f"**{ctx.author}** removed **${money}** from **{other}**.",
        )

    @is_gm()
    @commands.command(hidden=True)
    @locale_doc
    async def gmdelete(self, ctx, other: UserWithCharacter):
        _("""[Game Master only] Deletes any user's account.""")
        if other.id in ctx.bot.config.game_masters:  # preserve deletion of admins
            return await ctx.send(_("Very funny..."))
        async with self.bot.pool.acquire() as conn:
            g = await conn.fetchval(
                'DELETE FROM guild WHERE "leader"=$1 RETURNING id;', other.id
            )
            if g:
                await conn.execute(
                    'UPDATE profile SET "guildrank"=$1, "guild"=$2 WHERE "guild"=$3;',
                    "Member",
                    0,
                    g,
                )
                await conn.execute('UPDATE city SET "owner"=1 WHERE "owner"=$1;', g)
            await conn.execute(
                'UPDATE profile SET "marriage"=$1 WHERE "marriage"=$2;', 0, other.id
            )
            await conn.execute(
                'DELETE FROM children WHERE "father"=$1 OR "mother"=$1;', other.id
            )
        await self.bot.pool.execute('DELETE FROM profile WHERE "user"=$1;', other.id)
        await ctx.send(_("Successfully deleted the character."))
        await self.bot.http.send_message(
            self.bot.config.gm_log_channel, f"**{ctx.author}** deleted **{other}**."
        )

    @is_gm()
    @commands.command(hidden=True)
    @locale_doc
    async def gmrename(self, ctx, target: UserWithCharacter):
        _("""[Game Master only] Renames a character.""")
        if target.id in ctx.bot.config.game_masters:  # preserve renaming of admins
            return await ctx.send(_("Very funny..."))

        await ctx.send(
            _("What shall the character's name be? (min. 3 letters, max. 20)")
        )

        def mycheck(amsg):
            return (
                amsg.author == ctx.author
                and amsg.channel == ctx.channel
                and len(amsg.content) < 21
                and len(amsg.content) > 2
            )

        try:
            name = await self.bot.wait_for("message", timeout=60, check=mycheck)
        except asyncio.TimeoutError:
            return await ctx.send(_("Timeout expired."))

        await self.bot.pool.execute(
            'UPDATE profile SET "name"=$1 WHERE "user"=$2;', name.content, target.id
        )
        await ctx.send(_("Renamed."))
        await self.bot.http.send_message(
            self.bot.config.gm_log_channel,
            f"**{ctx.author}** renamed **{target}** to **{name.content}**.",
        )

    @is_gm()
    @commands.command(hidden=True)
    @locale_doc
    async def gmitem(
        self,
        ctx,
        stat: int,
        owner: UserWithCharacter,
        item_type: str.title,
        value: IntFromTo(0, 100000000),
        *,
        name: str,
    ):
        _("""[Game Master only] Create an item.""")
        if item_type not in self.bot.config.item_types:
            return await ctx.send(_("Invalid item type."))
        if not 0 <= stat <= 100:
            return await ctx.send(_("Invalid stat."))
        if item_type in ["Scythe", "Bow", "Howlet"]:
            hand = "both"
        elif item_type in ["Spear", "Wand"]:
            hand = "right"
        elif item_type == "Shield":
            hand = "left"
        else:
            hand = "any"
        await self.bot.create_item(
            name=name,
            value=value,
            type_=item_type,
            damage=stat if item_type != "Shield" else 0,
            armor=stat if item_type == "Shield" else 0,
            hand=hand,
            owner=owner,
        )

        message = (
            f"{ctx.author} created a {item_type} with name {name} and stat {stat}."
        )

        await ctx.send(_("Done."))
        await self.bot.http.send_message(self.bot.config.gm_log_channel, message)
        for user in self.bot.owner_ids:
            user = await self.bot.get_user_global(user)
            await user.send(message)

    @is_gm()
    @commands.command(hidden=True)
    @locale_doc
    async def gmcrate(
        self, ctx, rarity: str.lower, amount: int, target: UserWithCharacter
    ):
        _("""[Game Master only] Gives/removes crates to a user without loss.""")
        if rarity not in ["common", "uncommon", "rare", "magic", "legendary"]:
            return await ctx.send(
                _("{rarity} is not a valid rarity.").format(rarity=rarity)
            )
        await self.bot.pool.execute(
            f'UPDATE profile SET "crates_{rarity}"="crates_{rarity}"+$1 WHERE'
            ' "user"=$2;',
            amount,
            target.id,
        )
        await ctx.send(
            _("Successfully gave **{amount}** {rarity} crates to **{target}**.").format(
                amount=amount, target=target, rarity=rarity
            )
        )
        await self.bot.http.send_message(
            self.bot.config.gm_log_channel,
            f"**{ctx.author}** gave **{amount}** {rarity} crates to **{target}**.",
        )

    @is_gm()
    @commands.command(hidden=True)
    @locale_doc
    async def gmxp(self, ctx, target: UserWithCharacter, amount: int):
        _("""[Game Master only] Gives xp to a user.""")
        await self.bot.pool.execute(
            'UPDATE profile SET "xp"="xp"+$1 WHERE "user"=$2;', amount, target.id
        )
        await ctx.send(
            _("Successfully gave **{amount}** XP to **{target}**.").format(
                amount=amount, target=target
            )
        )
        await self.bot.http.send_message(
            self.bot.config.gm_log_channel,
            f"**{ctx.author}** gave **{amount}** XP to **{target}**.",
        )

    @is_gm()
    @commands.command(hidden=True)
    @locale_doc
    async def gmwipeperks(self, ctx, target: UserWithCharacter):
        _("""[Game Master only] Wipes someone's donator perks.""")
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "background"=$1, "class"=$2 WHERE "user"=$3;',
                "0",
                ["No Class", "No Class"],
                target.id,
            )
            await conn.execute(
                'UPDATE allitems SET "name"=CASE WHEN "original_name" IS NULL THEN'
                ' "name" ELSE "original_name" END, "type"=CASE WHEN "original_type" IS'
                ' NULL THEN "type" ELSE "original_type" END WHERE "owner"=$1;',
                target.id,
            )
            await conn.execute(
                'UPDATE guild SET "memberlimit"=$1 WHERE "leader"=$2;', 50, target.id
            )

        await ctx.send(
            _(
                "Successfully reset {target}'s background, class, item names and guild"
                " member limit."
            ).format(target=target)
        )
        await self.bot.http.send_message(
            self.bot.config.gm_log_channel,
            f"**{ctx.author}** reset **{target}**'s donator perks.",
        )

    @is_gm()
    @commands.command(hidden=True)
    @locale_doc
    async def gmresetclass(self, ctx, target: UserWithCharacter):
        _("""[Game Master only] Resets someone's class(es).""")
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                """UPDATE profile SET "class"='{"No Class", "No Class"}' WHERE "user"=$1;""",
                target.id,
            )

        await ctx.send(_("Successfully reset {target}'s class.").format(target=target))
        await self.bot.http.send_message(
            self.bot.config.gm_log_channel,
            f"**{ctx.author}** reset **{target}**'s class.",
        )

    @is_gm()
    @user_cooldown(604800)  # 7 days
    @commands.command(hidden=True)
    @locale_doc
    async def gmsign(self, ctx, itemid: int, *, text: str):
        _("""[Game Master only] Sign an item""")
        text = f"{text} (signed by {ctx.author})"
        if len(text) > 50:
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(_("Text exceeds 50 characters."))
        await self.bot.pool.execute(
            'UPDATE allitems SET "signature"=$1 WHERE "id"=$2;', text, itemid
        )
        await ctx.send(_("Item successfully signed."))
        await self.bot.http.send_message(
            self.bot.config.gm_log_channel,
            f"**{ctx.author}** signed {itemid} with *{text}*.",
        )

    @is_gm()
    @commands.command(hidden=True)
    @locale_doc
    async def gmauction(self, ctx, *, item: str):
        _("""[Game Master only] Start an auction on something.""")
        channel = discord.utils.get(
            self.bot.get_guild(self.bot.config.support_server_id).channels,
            name="auctions",
        )
        await channel.send(
            f"{ctx.author.mention} started auction on **{item}**! Please use"
            f" `{ctx.prefix}bid amount` to raise the bid. If no more bids are sent"
            " within a 30 minute timeframe, the auction is over."
        )
        self.top_auction = (ctx.author, 0)
        last_top_bid = -1
        while True:
            await asyncio.sleep(60 * 30)
            new_top_bid = self.top_auction[1]
            if new_top_bid == last_top_bid:
                break
            last_top_bid = new_top_bid
        await channel.send(
            f"**{item}** sold to {self.top_auction[0].mention} for"
            f" **${self.top_auction[1]}**!"
        )
        self.top_auction = None

    @has_char()
    @commands.command(hidden=True)
    @locale_doc
    async def bid(self, ctx, amount: IntGreaterThan(0)):
        _("""Bid on an auction.""")
        if self.top_auction is None:
            return await ctx.send(_("No auction running."))
        if amount <= self.top_auction[1]:
            return await ctx.send(_("Bid too low."))
        if ctx.character_data["money"] < amount:
            return await ctx.send(_("You are too poor."))
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                self.top_auction[1],
                self.top_auction[0].id,
            )
            await self.bot.log_transaction(
                ctx,
                from_=1,
                to=self.top_auction[0].id,
                subject="bid",
                data={"Amount": self.top_auction[1]},
            )
            self.top_auction = (ctx.author, amount)
            await conn.execute(
                'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;',
                amount,
                ctx.author.id,
            )
            await self.bot.log_transaction(
                ctx, from_=ctx.author.id, to=2, subject="bid", data={"Amount": amount}
            )
        await ctx.send(_("Bid submitted."))
        channel = discord.utils.get(
            self.bot.get_guild(self.bot.config.support_server_id).channels,
            name="auctions",
        )
        await channel.send(
            f"**{ctx.author.mention}** bids **${amount}**! Check above for what's being"
            " auctioned."
        )

    @is_gm()
    @commands.command(aliases=["gmcd", "gmsetcd"], hidden=True)
    @locale_doc
    async def gmsetcooldown(
        self,
        ctx,
        user: Union[discord.User, int],
        command: str,
        cooldown: IntGreaterThan(-1) = 0,
    ):
        _(
            """[Game Master only] Sets someone's cooldown to a specific time in seconds (by default removes the cooldown)"""
        )
        if not isinstance(user, int):
            user_id = user.id
        else:
            user_id = user

        if cooldown == 0:
            result = await self.bot.redis.execute("DEL", f"cd:{user_id}:{command}")
        else:
            result = await self.bot.redis.execute(
                "EXPIRE", f"cd:{user_id}:{command}", cooldown
            )

        if result == 1:
            await ctx.send(_("The cooldown has been updated!"))
            await self.bot.http.send_message(
                self.bot.config.gm_log_channel,
                f"**{ctx.author}** set **{user}**'s cooldown to {cooldown}.",
            )
        else:
            await ctx.send(
                _(
                    "Cooldown setting unsuccessful (maybe you mistyped the command name"
                    " or there is no cooldown for the user?)."
                )
            )


def setup(bot):
    bot.add_cog(GameMaster(bot))
