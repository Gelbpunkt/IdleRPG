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

from async_timeout import timeout
from discord.ext import commands

from classes.converters import (
    CrateRarity,
    IntFromTo,
    IntGreaterThan,
    MemberConverter,
    UserWithCharacter,
)
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils.checks import has_char, is_gm
from utils.i18n import _, locale_doc


class GameMaster(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.top_auction = self.auction_cm = None

    @is_gm()
    @commands.command(brief=_("Publish an announcement"))
    @locale_doc
    async def publish(self, ctx, message: discord.Message):
        _("Publish a message from an announement channel")
        try:
            await message.publish()
            await ctx.send(_("Message has been published!"))
        except discord.Forbidden:
            await ctx.send(_("This message is not from an announcement channel!"))

    @is_gm()
    @commands.command(
        aliases=["cleanshop", "cshop"], hidden=True, brief=_("Clean up the shop")
    )
    @locale_doc
    async def clearshop(self, ctx):
        _(
            """Remove items from the shop that have been there for more than 14 days, returning them to the owners' inventories.

            Only Game Masters can use this command."""
        )
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
    @commands.command(
        hidden=True, aliases=["gmcdc"], brief=_("Clear donator cache for a user")
    )
    @locale_doc
    async def gmcleardonatorcache(self, ctx, *, other: MemberConverter):
        _(
            """`<other>` - A server member

            Clears the cached donator rank for a user globally, allowing them to use the new commands after donating.

            Only Game Masters can use this command."""
        )
        await self.bot.clear_donator_cache(other)
        await ctx.send(_("Done"))

    @is_gm()
    @commands.command(hidden=True, brief=_("Bot-unban a user"))
    @locale_doc
    async def unban(self, ctx, *, other: discord.User):
        _(
            """`<other>` - A discord User

            Unbans a user from the bot, allowing them to use commands and reactions again.

            Only Game Masters can use this command."""
        )
        try:
            self.bot.bans.remove(other.id)
            await ctx.send(_("Unbanned: {other}").format(other=other.name))
        except ValueError:
            await ctx.send(_("{other} is not banned.").format(other=other.name))

    @is_gm()
    @commands.command(hidden=True, brief=_("Create money"))
    @locale_doc
    async def gmgive(
        self,
        ctx,
        money: int,
        other: UserWithCharacter,
        *,
        reason: str = None,
    ):
        _(
            """`<money>` - the amount of money to generate for the user
            `<other>` - A discord User with a character
            `[reason]` - The reason this action was done, defaults to the command message link

            Gives a user money without subtracting it from the command author's balance.

            Only Game Masters can use this command."""
        )
        await self.bot.pool.execute(
            'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;', money, other.id
        )
        await self.bot.cache.update_profile_cols_rel(other.id, money=money)
        await ctx.send(
            _(
                "Successfully gave **${money}** without a loss for you to **{other}**."
            ).format(money=money, other=other)
        )
        await self.bot.http.send_message(
            self.bot.config.gm_log_channel,
            "**{gm}** gave **${money}** to **{other}**.\n\nReason: *{reason}*".format(
                gm=ctx.author,
                money=money,
                other=other,
                reason=reason or f"<{ctx.message.jump_url}>",
            ),
        )

    @is_gm()
    @commands.command(hidden=True, brief=_("Remove money"))
    @locale_doc
    async def gmremove(
        self,
        ctx,
        money: int,
        other: UserWithCharacter,
        *,
        reason: str = None,
    ):
        _(
            """`<money>` - the amount of money to remove from the user
            `<other>` - a discord User with character
            `[reason]` - The reason this action was done, defaults to the command message link

            Removes money from a user without adding it to the command author's balance.

            Only Game Masters can use this command."""
        )
        await self.bot.pool.execute(
            'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;', money, other.id
        )
        await self.bot.cache.update_profile_cols_rel(other.id, money=-money)
        await ctx.send(
            _("Successfully removed **${money}** from **{other}**.").format(
                money=money, other=other
            )
        )
        await self.bot.http.send_message(
            self.bot.config.gm_log_channel,
            "**{gm}** removed **${money}** from **{other}**.\n\nReason: *{reason}*".format(
                gm=ctx.author,
                money=money,
                other=other,
                reason=reason or f"<{ctx.message.jump_url}>",
            ),
        )

    @is_gm()
    @commands.command(hidden=True, brief=_("Delete a character"))
    @locale_doc
    async def gmdelete(self, ctx, other: UserWithCharacter, *, reason: str = None):
        _(
            """`<other>` - a discord User with character
            `[reason]` - The reason this action was done, defaults to the command message link

            Delete a user's profile. The user cannot be a Game Master.

            Only Game Masters can use this command."""
        )
        if other.id in ctx.bot.config.game_masters:  # preserve deletion of admins
            return await ctx.send(_("Very funny..."))
        await self.bot.cache.wipe_profile(other.id)
        async with self.bot.pool.acquire() as conn:
            g = await conn.fetchval(
                'DELETE FROM guild WHERE "leader"=$1 RETURNING id;', other.id
            )
            if g:
                users = await conn.fetch(
                    'UPDATE profile SET "guildrank"=$1, "guild"=$2 WHERE "guild"=$3'
                    ' RETURNING "user";',
                    "Member",
                    0,
                    g,
                )
                for user in users:
                    await self.bot.cache.update_profile_cols_abs(
                        user["user"], guildrank="Member", guild=0
                    )
                await conn.execute('UPDATE city SET "owner"=1 WHERE "owner"=$1;', g)
            partner = await conn.fetchval(
                'UPDATE profile SET "marriage"=$1 WHERE "marriage"=$2 RETURNING'
                ' "user";',
                0,
                other.id,
            )
            await conn.execute(
                'UPDATE children SET "mother"=$1, "father"=0 WHERE ("father"=$1 AND'
                ' "mother"=$2) OR ("father"=$2 AND "mother"=$1);',
                partner,
                other.id,
            )
            await self.bot.delete_profile(other.id, conn=conn)
        await self.bot.cache.wipe_profile(other.id)
        if partner:
            await self.bot.cache.update_profile_cols_abs(partner, marriage=0)
        await ctx.send(_("Successfully deleted the character."))
        await self.bot.http.send_message(
            self.bot.config.gm_log_channel,
            "**{gm}** deleted **{other}**.\n\nReason: *{reason}*".format(
                gm=ctx.author, other=other, reason=reason or f"<{ctx.message.jump_url}>"
            ),
        )

    @is_gm()
    @commands.command(hidden=True, brief=_("Rename a character"))
    @locale_doc
    async def gmrename(self, ctx, target: UserWithCharacter, *, reason: str = None):
        _(
            """`<target>` - a discord User with character
            `[reason]` - The reason this action was done, defaults to the command message link

            Rename a user's profile. The user cannot be a Game Master.

            Only Game Masters can use this command."""
        )
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
        await self.bot.cache.update_profile_cols_abs(target.id, name=name.content)
        await ctx.send(_("Renamed."))
        await self.bot.http.send_message(
            self.bot.config.gm_log_channel,
            "**{gm}** renamed **{target}** to **{name}**.\n\nReason: *{reason}*".format(
                gm=ctx.author,
                target=target,
                name=name.content,
                reason=reason or f"<{ctx.message.jump_url}>",
            ),
        )

    @is_gm()
    @commands.command(hidden=True, brief=_("Create an item"))
    @locale_doc
    async def gmitem(
        self,
        ctx,
        stat: int,
        owner: UserWithCharacter,
        item_type: str.title,
        value: IntFromTo(0, 100000000),
        name: str,
        *,
        reason: str = None,
    ):
        _(
            """`<stat>` - the generated item's stat, must be between 0 and 100
            `<owner>` - a discord User with character
            `<item_type>` - the generated item's type, must be either Sword, Shield, Axe, Wand, Dagger, Knife, Spear, Bow, Hammer, Scythe or Howlet
            `<value>` - the generated item's value, a whole number from 0 to 100,000,000
            `<name>` - the generated item's name, should be in double quotes if the name has multiple words
            `[reason]` - The reason this action was done, defaults to the command message link

            Generate a custom item for a user.

            Only Game Masters can use this command."""
        )
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

        message = "{gm} created a {item_type} with name {name} and stat {stat}.\n\nReason: *{reason}*".format(
            gm=ctx.author,
            item_type=item_type,
            name=name,
            stat=stat,
            reason=reason or f"<{ctx.message.jump_url}>",
        )

        await ctx.send(_("Done."))
        await self.bot.http.send_message(self.bot.config.gm_log_channel, message)
        for user in self.bot.owner_ids:
            user = await self.bot.get_user_global(user)
            await user.send(message)

    @is_gm()
    @commands.command(hidden=True, brief=_("Create crates"))
    @locale_doc
    async def gmcrate(
        self,
        ctx,
        rarity: CrateRarity,
        amount: int,
        target: UserWithCharacter,
        *,
        reason: str = None,
    ):
        _(
            """`<rarity>` - the crates' rarity, can be common, uncommon, rare, magic or legendary
            `<amount>` - the amount of crates to generate for the given user, can be negative
            `<target>` - A discord User with character
            `[reason]` - The reason this action was done, defaults to the command message link

            Generate a set amount of crates of one rarity for a user.

            Only Game Masters can use this command."""
        )
        await self.bot.pool.execute(
            f'UPDATE profile SET "crates_{rarity}"="crates_{rarity}"+$1 WHERE'
            ' "user"=$2;',
            amount,
            target.id,
        )
        await self.bot.cache.update_profile_cols_rel(
            target.id, **{f"crates_{rarity}": amount}
        )
        await ctx.send(
            _("Successfully gave **{amount}** {rarity} crates to **{target}**.").format(
                amount=amount, target=target, rarity=rarity
            )
        )
        await self.bot.http.send_message(
            self.bot.config.gm_log_channel,
            "**{gm}** gave **{amount}** {rarity} crates to **{target}**.\n\nReason: *{reason}*".format(
                gm=ctx.author,
                amount=amount,
                rarity=rarity,
                target=target,
                reason=reason or f"<{ctx.message.jump_url}>",
            ),
        )

    @is_gm()
    @commands.command(hidden=True, brief=_("Generate XP"))
    @locale_doc
    async def gmxp(
        self,
        ctx,
        target: UserWithCharacter,
        amount: int,
        *,
        reason: str = None,
    ):
        _(
            """`<target>` - A discord User with character
            `<amount>` - The amount of XP to generate, can be negative
            `[reason]` - The reason this action was done, defaults to the command message link

            Generates a set amount of XP for a user.

            Only Game Masters can use this command."""
        )
        await self.bot.pool.execute(
            'UPDATE profile SET "xp"="xp"+$1 WHERE "user"=$2;', amount, target.id
        )
        await self.bot.cache.update_profile_cols_rel(target.id, xp=amount)
        await ctx.send(
            _("Successfully gave **{amount}** XP to **{target}**.").format(
                amount=amount, target=target
            )
        )
        await self.bot.http.send_message(
            self.bot.config.gm_log_channel,
            "**{gm}** gave **{amount}** XP to **{target}**.\n\nReason: *{reason}*".format(
                gm=ctx.author,
                amount=amount,
                target=target,
                reason=reason or f"<{ctx.message.jump_url}>",
            ),
        )

    @is_gm()
    @commands.command(hidden=True, brief=_("Wipe someone's donation perks."))
    @locale_doc
    async def gmwipeperks(self, ctx, target: UserWithCharacter, *, reason: str = None):
        _(
            """`<target>` - A discord User with character
            `[reason]` - The reason this action was done, defaults to the command message link

            Wipe a user's donation perks. This will:
              - set their background to the default
              - set both their classes to No Class
              - reverts all items to their original type and name
              - sets their guild's member limit to 50

            Only Game Masters can use this command."""
        )
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
        await self.bot.cache.update_profile_cols_abs(
            target.id, background="0", class_=["No Class", "No Class"]
        )

        await ctx.send(
            _(
                "Successfully reset {target}'s background, class, item names and guild"
                " member limit."
            ).format(target=target)
        )
        await self.bot.http.send_message(
            self.bot.config.gm_log_channel,
            "**{gm}** reset **{target}**'s donator perks.\n\nReason: *{reason}*".format(
                gm=ctx.author,
                target=target,
                reason=reason or f"<{ctx.message.jump_url}>",
            ),
        )

    @is_gm()
    @commands.command(hidden=True, brief=_("Reset someone's classes"))
    @locale_doc
    async def gmresetclass(self, ctx, target: UserWithCharacter, *, reason: str = None):
        _(
            """`<target>` - a discord User with character
            `[reason]` - The reason this action was done, defaults to the command message link

            Reset a user's classes to No Class. They can then choose their class again for free.

            Only Game Masters can use this command."""
        )
        await self.bot.pool.execute(
            """UPDATE profile SET "class"='{"No Class", "No Class"}' WHERE "user"=$1;""",
            target.id,
        )
        await self.bot.cache.update_profile_cols_abs(
            target.id, class_=["No Class", "No Class"]
        )

        await ctx.send(_("Successfully reset {target}'s class.").format(target=target))
        await self.bot.http.send_message(
            self.bot.config.gm_log_channel,
            "**{gm}** reset **{target}**'s class.\n\nReason: *{reason}*".format(
                gm=ctx.author,
                target=target,
                reason=reason or f"<{ctx.message.jump_url}>",
            ),
        )

    @is_gm()
    @user_cooldown(604800)  # 7 days
    @commands.command(hidden=True, brief=_("Sign an item"))
    @locale_doc
    async def gmsign(self, ctx, itemid: int, text: str, *, reason: str = None):
        _(
            """`<itemid>` - the item's ID to sign
            `<text>` - The signature to write, must be less than 50 characters combined with the Game Master's tag. This should be in double quotes if the text has multiple words.
            `[reason]` - The reason this action was done, defaults to the command message link

            Sign an item. The item's signature is visible in a user's inventory.

            Only Game Masters can use this command.
            (This command has a cooldown of 7 days.)"""
        )
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
            "**{gm}** signed {itemid} with *{text}*.\n\nReason: *{reason}*".format(
                gm=ctx.author,
                itemid=itemid,
                text=text,
                reason=reason or f"<{ctx.message.jump_url}>",
            ),
        )

    @is_gm()
    @commands.command(hidden=True, brief=_("Start an auction"))
    @locale_doc
    async def gmauction(self, ctx, *, item: str):
        _(
            """`<item>` - a description of what is being auctioned

            Starts an auction on the support server. Users are able to bid. The auction timeframe extends by 30 minutes if users keep betting.
            The auction ends when no user bids in a 30 minute timeframe.

            The item is not given automatically and the needs to be given manually.

            Only Game Masters can use this command."""
        )
        if self.top_auction is not None:
            return await ctx.send(_("There's still an auction running."))
        try:
            channel = discord.utils.get(
                self.bot.get_guild(self.bot.config.support_server_id).channels,
                name="auctions",
            )
        except AttributeError:
            return await ctx.send(_("Auctions channel wasn't found."))
        await channel.send(
            f"{ctx.author.mention} started auction on **{item}**! Please use"
            f" `{ctx.prefix}bid amount` to raise the bid. If no more bids are sent"
            " within a 30 minute timeframe, the auction is over."
        )
        self.top_auction = (ctx.author, 0)
        timer = 60 * 30
        try:
            async with timeout(timer) as cm:
                self.auction_cm = cm
                while True:
                    await asyncio.sleep(timer)
        except asyncio.TimeoutError:
            pass
        await channel.send(
            f"**{item}** sold to {self.top_auction[0].mention} for"
            f" **${self.top_auction[1]}**!"
        )
        self.top_auction = self.auction_cm = None

    @has_char()
    @commands.command(hidden=True, brief=_("Bid on an auction"))
    @locale_doc
    async def bid(self, ctx, amount: IntGreaterThan(0)):
        _(
            """`<amount>` - the amount of money to bid, must be higher than the current highest bid

            Bid on an ongoing auction.

            The amount is removed from you as soon as you bid and given back if someone outbids you. This is to prevent bidding impossibly high and then not paying up."""
        )
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
            await self.bot.cache.update_profile_cols_rel(
                self.top_auction[0].id, money=self.top_auction[1]
            )
            await self.bot.log_transaction(
                ctx,
                from_=1,
                to=self.top_auction[0].id,
                subject="bid",
                data={"Amount": self.top_auction[1]},
                conn=conn,
            )
            self.top_auction = (ctx.author, amount)
            self.auction_cm.shift_by(60 * 30)
            await conn.execute(
                'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;',
                amount,
                ctx.author.id,
            )
            await self.bot.cache.update_profile_cols_rel(ctx.author.id, money=-amount)
            await self.bot.log_transaction(
                ctx,
                from_=ctx.author.id,
                to=2,
                subject="bid",
                data={"Amount": amount},
                conn=conn,
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
    @commands.command(
        aliases=["gmcd", "gmsetcd"], hidden=True, brief=_("Set a cooldown")
    )
    @locale_doc
    async def gmsetcooldown(
        self,
        ctx,
        user: Union[discord.User, int],
        command: str,
        *,
        reason: str = None,
    ):
        _(
            """`<user>` - A discord User or their User ID
            `<command>` - the command which the cooldown is being set for (subcommands in double quotes, i.e. "guild create")
            `[reason]` - The reason this action was done, defaults to the command message link

            Reset a cooldown for a user and commmand.

            Only Game Masters can use this command."""
        )
        if not isinstance(user, int):
            user_id = user.id
        else:
            user_id = user

        result = await self.bot.redis.execute("DEL", f"cd:{user_id}:{command}")

        if result == 1:
            await ctx.send(_("The cooldown has been updated!"))
            await self.bot.http.send_message(
                self.bot.config.gm_log_channel,
                "**{gm}** reset **{user}**'s cooldown for the {command} command.\n\nReason: *{reason}*".format(
                    gm=ctx.author,
                    user=user,
                    command=command,
                    reason=reason or f"<{ctx.message.jump_url}>",
                ),
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
