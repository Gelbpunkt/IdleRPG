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

import discord
from discord.ext import commands

from classes.converters import UserWithCharacter
from utils.checks import is_admin


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @is_admin()
    @commands.command(hidden=True)
    @locale_doc
    async def unban(self, ctx, *, other: discord.User):
        _("""[Bot Admin only] Unban someone from the bot.""")
        try:
            self.bot.bans.remove(other.id)
            await ctx.send(_("Unbanned: {other}").format(other=other.name))
        except ValueError:
            await ctx.send(_("{other} is not banned.").format(other=other.name))

    @is_admin()
    @commands.command(aliases=["agive"], hidden=True)
    @locale_doc
    async def admingive(self, ctx, money: int, other: UserWithCharacter):
        _("""[Bot Admin only] Gives money to a user without loss.""")
        await self.bot.pool.execute(
            'UPDATE profile SET money=money+$1 WHERE "user"=$2;', money, other.id
        )
        await ctx.send(
            _(
                "Successfully gave **${money}** without a loss for you to **{other}**."
            ).format(money=money, other=other)
        )
        await self.bot.http.send_message(
            self.bot.config.admin_log_channel,
            f"**{ctx.author}** gave **${money}** to **{other}**.",
        )

    @is_admin()
    @commands.command(aliases=["aremove"], hidden=True)
    @locale_doc
    async def adminremove(self, ctx, money: int, other: UserWithCharacter):
        _("""[Bot Admin only] Removes money from a user without gain.""")
        await self.bot.pool.execute(
            'UPDATE profile SET money=money-$1 WHERE "user"=$2;', money, other.id
        )
        await ctx.send(
            _("Successfully removed **${money}** from **{other}**.").format(
                money=money, other=other
            )
        )
        await self.bot.http.send_message(
            self.bot.config.admin_log_channel,
            f"**{ctx.author}** removed **${money}** from **{other}**.",
        )

    @is_admin()
    @commands.command(aliases=["adelete"], hidden=True)
    @locale_doc
    async def admindelete(self, ctx, other: UserWithCharacter):
        _("""[Bot Admin only] Deletes any user's account.""")
        if other.id in ctx.bot.config.admins:  # preserve deletion of admins
            return await ctx.send(_("Very funny..."))
        await self.bot.pool.execute('DELETE FROM profile WHERE "user"=$1;', other.id)
        await ctx.send(_("Successfully deleted the character."))
        await self.bot.http.send_message(
            self.bot.config.admin_log_channel, f"**{ctx.author}** deleted **{other}**."
        )

    @is_admin()
    @commands.command(aliases=["arename"], hidden=True)
    @locale_doc
    async def adminrename(self, ctx, target: UserWithCharacter):
        _("""[Bot Admin only] Renames a character.""")
        if target.id in ctx.bot.config.admins:  # preserve renaming of admins
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
            self.bot.config.admin_log_channel,
            f"**{ctx.author}** renamed **{target}** to **{name.content}**.",
        )

    @is_admin()
    @commands.command(aliases=["acrate"], hidden=True)
    @locale_doc
    async def admincrate(
        self, ctx, rarity: str.lower, amount: int, target: UserWithCharacter
    ):
        _("""[Bot Admin only] Gives/removes crates to a user without loss.""")
        if rarity not in ["common", "uncommon", "rare", "magic", "legendary"]:
            return await ctx.send(
                _("{rarity} is not a valid rarity.").format(rarity=rarity)
            )
        await self.bot.pool.execute(
            f'UPDATE profile SET "crates_{rarity}"="crates_{rarity}"+$1 WHERE "user"=$2;',
            amount,
            target.id,
        )
        await ctx.send(
            _("Successfully gave **{amount}** {rarity} crates to **{target}**.").format(
                amount=amount, target=target, rarity=rarity
            )
        )
        await self.bot.http.send_message(
            self.bot.config.admin_log_channel,
            f"**{ctx.author}** gave **{amount}** crates to **{target}**.",
        )

    @is_admin()
    @commands.command(aliases=["axp"], hidden=True)
    @locale_doc
    async def adminxp(self, ctx, target: UserWithCharacter, amount: int):
        _("""[Bot Admin only] Gives xp to a user.""")
        await self.bot.pool.execute(
            'UPDATE profile SET "xp"="xp"+$1 WHERE "user"=$2;', amount, target.id
        )
        await ctx.send(
            _("Successfully gave **{amount}** XP to **{target}**.").format(
                amount=amount, target=target
            )
        )
        await self.bot.http.send_message(
            self.bot.config.admin_log_channel,
            f"**{ctx.author}** gave **{amount}** XP to **{target}**.",
        )

    @is_admin()
    @commands.command(aliases=["awipeperks"], hidden=True)
    @locale_doc
    async def adminwipeperks(self, ctx, target: UserWithCharacter):
        _("""[Bot Admin only] Wipes someone's donator perks.""")
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "background"=$1, "class"=$2 WHERE "user"=$3;',
                "0",
                "No Class",
                target.id,
            )
            await conn.execute(
                'UPDATE allitems SET "name"=$1 WHERE "owner"=$2 AND "type"=$3;',
                "Broken Sword",
                target.id,
                "Sword",
            )
            await conn.execute(
                'UPDATE allitems SET "name"=$1 WHERE "owner"=$2 AND "type"=$3;',
                "Broken Shield",
                target.id,
                "Shield",
            )
            await conn.execute(
                'UPDATE guild SET "memberlimit"=$1 WHERE "leader"=$2;', 50, target.id
            )

        await ctx.send(
            _(
                "Successfully reset {target}'s background, class, item names and guild member limit."
            ).format(target=target)
        )
        await self.bot.http.send_message(
            self.bot.config.admin_log_channel,
            f"**{ctx.author}** reset **{target}**'s donator perks.",
        )


def setup(bot):
    bot.add_cog(Admin(bot))
