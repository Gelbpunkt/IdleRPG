"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import asyncio

from discord.ext import commands

from classes.converters import User
from utils.checks import is_admin, user_has_char


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @is_admin()
    @commands.command(aliases=["agive"], hidden=True)
    async def admingive(self, ctx, money: int, other: User):
        """[Bot Admin only] Gives money to a user without loss."""
        if not await user_has_char(self.bot, other.id):
            return await ctx.send("That person hasn't got a character.")
        await self.bot.pool.execute(
            'UPDATE profile SET money=money+$1 WHERE "user"=$2;', money, other.id
        )
        await ctx.send(
            f"Successfully gave **${money}** without a loss for you to **{other}**."
        )
        await self.bot.http.send_message(
            self.bot.config.admin_log_channel,
            f"**{ctx.author}** gave **${money}** to **{other}**.",
        )

    @is_admin()
    @commands.command(aliases=["aremove"], hidden=True)
    async def adminremove(self, ctx, money: int, other: User):
        """[Bot Admin only] Removes money from a user without gain."""
        if not await user_has_char(self.bot, other.id):
            return await ctx.send("That person hasn't got a character.")
        await self.bot.pool.execute(
            'UPDATE profile SET money=money-$1 WHERE "user"=$2;', money, other.id
        )
        await ctx.send(f"Successfully removed **${money}** from **{other}**.")
        await self.bot.http.send_message(
            self.bot.config.admin_log_channel,
            f"**{ctx.author}** removed **${money}** from **{other}**.",
        )

    @is_admin()
    @commands.command(aliases=["adelete"], hidden=True)
    async def admindelete(self, ctx, other: User):
        """[Bot Admin only] Deletes any user's account."""
        if other.id in ctx.bot.config.admins:  # preserve deletion of admins
            return await ctx.send("Very funny...")
        if not await user_has_char(self.bot, other.id):
            return await ctx.send("That person doesn't have a character.")
        await self.bot.pool.execute('DELETE FROM profile WHERE "user"=$1;', other.id)
        await ctx.send("Successfully deleted the character.")
        await self.bot.http.send_message(
            self.bot.config.admin_log_channel, f"**{ctx.author}** deleted **{other}**."
        )

    @is_admin()
    @commands.command(aliases=["arename"], hidden=True)
    async def adminrename(self, ctx, target: User):
        """[Bot Admin only] Renames a character."""
        if target.id in ctx.bot.config.admins:  # preserve renaming of admins
            return await ctx.send("Very funny...")
        if not await user_has_char(self.bot, target.id):
            return await ctx.send("That person doesn't have a character.")

        await ctx.send("What shall the character's name be? (min. 3 letters, max. 20)")

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
            return await ctx.send("Timeout expired.")

        name = name.content
        await self.bot.pool.execute(
            'UPDATE profile SET "name"=$1 WHERE "user"=$2;', name, target.id
        )
        await ctx.send("Renamed.")
        await self.bot.http.send_message(
            self.bot.config.admin_log_channel,
            f"**{ctx.author}** renamed **{target}** to **{name}**.",
        )

    @is_admin()
    @commands.command(aliases=["acrate"], hidden=True)
    async def admincrate(self, ctx, target: User, amount: int = 1):
        """[Bot Admin only] Gives crates to a user without loss."""
        if not await user_has_char(self.bot, target.id):
            return await ctx.send("That person doesn't have a character.")

        await self.bot.pool.execute(
            'UPDATE profile SET "crates"="crates"+$1 WHERE "user"=$2;',
            amount,
            target.id,
        )
        await ctx.send(f"Successfully gave **{amount}** crates to **{target}**.")
        await self.bot.http.send_message(
            self.bot.config.admin_log_channel,
            f"**{ctx.author}** gave **{amount}** crates to **{target}**.",
        )

    @is_admin()
    @commands.command(aliases=["axp"], hidden=True)
    async def adminxp(self, ctx, target: User, amount: int):
        """[Bot Admin only] Gives xp to a user."""
        if not await user_has_char(self.bot, target.id):
            return await ctx.send("That person doesn't have a character.")

        await self.bot.pool.execute(
            'UPDATE profile SET "xp"="xp"+$1 WHERE "user"=$2;', amount, target.id
        )
        await ctx.send(f"Successfully gave **{amount}** XP to **{target}**.")
        await self.bot.http.send_message(
            self.bot.config.admin_log_channel,
            f"**{ctx.author}** gave **{amount}** XP to **{target}**.",
        )

    @is_admin()
    @commands.command(aliases=["awipeperks"], hidden=True)
    async def adminwipeperks(self, ctx, target: User):
        """[Bot Admin only] Wipes someone's donator perks."""
        if not await user_has_char(self.bot, target.id):
            return await ctx.send("That person doesn't have a character.")

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
            f"Successfully reset {target}'s background, class, item names and guild member limit."
        )
        await self.bot.http.send_message(
            self.bot.config.admin_log_channel,
            f"**{ctx.author}** reset **{target}**'s donator perks.",
        )


def setup(bot):
    bot.add_cog(Admin(bot))
