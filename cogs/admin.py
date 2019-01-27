import discord
from discord.ext import commands
from utils.checks import *


class Admin:
    def __init__(self, bot):
        self.bot = bot

    @is_admin()
    @commands.command(aliases=["agive"], description="Gift money!", hidden=True)
    async def admingive(self, ctx, money: int, other: discord.User):
        if not await user_has_char(self.bot, other.id):
            return await ctx.send("That person hasn't got a character.")
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2;', money, other.id
            )
        await ctx.send(
            f"Successfully gave **${money}** without a loss for you to **{other}**."
        )
        channel = self.bot.get_channel(self.bot.config.admin_log_channel)
        await channel.send(f"**{ctx.author}** gave **${money}** to **{other}**.")

    @is_admin()
    @commands.command(aliases=["aremove"], description="Delete money!", hidden=True)
    async def adminremove(self, ctx, money: int, other: discord.User):
        if not await user_has_char(self.bot, other.id):
            return await ctx.send("That person hasn't got a character.")
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET money=money-$1 WHERE "user"=$2;', money, other.id
            )
        await ctx.send(f"Successfully removed **${money}** from **{other}**.")
        channel = self.bot.get_channel(self.bot.config.admin_log_channel)
        await channel.send(f"**{ctx.author}** removed **${money}** from **{other}**.")

    @is_admin()
    @commands.command(
        aliases=["adelete"], description="Deletes a character.", hidden=True
    )
    async def admindelete(self, ctx, other: discord.User):
        if other.id in ctx.bot.config.admins:
            return await ctx.send("Very funny...")
        if not await user_has_char(self.bot, other.id):
            return await ctx.send("That person doesn't have a character.")
        async with self.bot.pool.acquire() as conn:
            await conn.execute('DELETE FROM profile WHERE "user"=$1;', other.id)
        await ctx.send("Successfully deleted the character.")
        channel = self.bot.get_channel(self.bot.config.admin_log_channel)
        await channel.send(f"**{ctx.author}** deleted **{other}**.")

    @is_admin()
    @commands.command(aliases=["arename"], description="Changes a character name")
    async def adminrename(self, ctx, target: discord.User):
        if target.id in ctx.bot.config.admins:
            return await ctx.send("Very funny...")
        if not await user_has_char(self.bot, target.id):
            return await ctx.send("That person doesn't have a character.")
        await ctx.send(
            "What shall the character's name be? (Minimum 3 Characters, Maximum 20)"
        )

        def mycheck(amsg):
            return (
                amsg.author == ctx.author
                and len(amsg.content) < 21
                and len(amsg.content) > 2
            )

        try:
            name = await self.bot.wait_for("message", timeout=60, check=mycheck)
        except:
            return await ctx.send("Timeout expired.")
        name = name.content
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "name"=$1 WHERE "user"=$2;', name, target.id
            )
        channel = self.bot.get_channel(self.bot.config.admin_log_channel)
        await channel.send(f"**{ctx.author}** renamed **{target}** to **{name}**.")

    @is_admin()
    @commands.command(aliases=["acrate"], description="Gives crates to a user.")
    async def admincrate(self, ctx, target: discord.Member, amount: int = 1):
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "crates"="crates"+$1 WHERE "user"=$2;',
                amount,
                target.id,
            )
        await ctx.send(f"Successfully gave **{amount}** crates to **{target}**.")
        channel = self.bot.get_channel(self.bot.config.admin_log_channel)
        await channel.send(
            f"**{ctx.author}** gave **{amount}** crates to **{target}**."
        )

    @is_admin()
    @commands.command(aliases=["axp"], description="Gives XP to a user.")
    async def adminxp(self, ctx, target: discord.Member, amount: int):
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "xp"="xp"+$1 WHERE "user"=$2;', amount, target.id
            )
        await ctx.send(f"Successfully gave **{amount}** XP to **{target}**.")
        channel = self.bot.get_channel(self.bot.config.admin_log_channel)
        await channel.send(f"**{ctx.author}** gave **{amount}** XP to **{target}**.")


def setup(bot):
    bot.add_cog(Admin(bot))
