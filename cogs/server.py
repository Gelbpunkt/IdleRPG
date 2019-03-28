"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""


import discord
import asyncio

from discord.ext import commands
from cogs.help import chunks


def get_guilds(bot, user):
    return [guild for guild in bot.guilds if user in guild.members]


class Server(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @commands.command(
        description="See information about this server.", aliases=["server"]
    )
    async def serverinfo(self, ctx):
        if ctx.guild.icon_url:
            urltext = (
                f"[Link <:external_link:429288989560930314>]({ctx.guild.icon_url})"
            )
        else:
            urltext = "`No icon has been set yet!`"
        em = discord.Embed(
            title="Server Information",
            description="Compact information about this server",
            colour=0xDEADBF,
        )
        em.add_field(
            name="Information",
            value=f"Server: `{str(ctx.guild)}`\nServer Region: `{ctx.guild.region}`\nMembers Total: `{ctx.guild.member_count}`\nID: `{ctx.guild.id}`\nIcon: {urltext}\nOwner: {ctx.guild.owner.mention}\nServer created at: `{ctx.guild.created_at.__format__('%A %d. %B %Y at %H:%M:%S')}`",
        )
        em.add_field(
            name="Roles", value=f"{', '.join([role.name for role in ctx.guild.roles])}"
        )
        em.add_field(
            name="Shard",
            value=f"`{ctx.guild.shard_id + 1}` of `{len(self.bot.shards)}`",
        )
        em.set_thumbnail(url=ctx.guild.icon_url)
        await ctx.send(embed=em)

    @commands.guild_only()
    @commands.group(description="Change the settings.", invoke_without_command=True)
    async def settings(self, ctx):
        await ctx.send(f"Please use `{ctx.prefix}settings (prefix/unknown) value`")

    @commands.has_permissions(manage_guild=True)
    @settings.command(description="Change the prefix.", name="prefix")
    async def prefix_(self, ctx, prefix: str):
        if self.bot.all_prefixes.get(ctx.guild.id):
            await self.bot.pool.execute(
                'UPDATE server SET "prefix"=$1 WHERE "id"=$2;', prefix, ctx.guild.id
            )
        else:
            await self.bot.pool.execute(
                'INSERT INTO server ("id", "prefix", "unknown") VALUES ($1, $2, $3);',
                ctx.guild.id,
                prefix,
                False,
            )
        self.bot.all_prefixes[ctx.guild.id] = prefix
        await ctx.send(f"Prefix changed to `{prefix}`.")

    @commands.has_permissions(manage_guild=True)
    @settings.command(description="Enable/Disable unknown command messages")
    async def unknown(self, ctx, value: bool):
        async with self.bot.pool.acquire() as conn:
            settings = await conn.fetchrow(
                'SELECT * FROM server WHERE "id"=$1;', ctx.guild.id
            )
            if not settings:
                await conn.execute(
                    'INSERT INTO server ("id", "prefix", "unknown") VALUES ($1, $2, $3);',
                    ctx.guild.id,
                    self.bot.config.global_prefix,
                    value,
                )
            else:
                await conn.execute(
                    'UPDATE server SET "unknown"=$1 WHERE "id"=$2;', value, ctx.guild.id
                )
        await ctx.send("Successfully updated the settings.")

    @commands.has_permissions(manage_guild=True)
    @settings.command(description="Reset the settings.")
    async def reset(self, ctx):
        await self.bot.pool.execute('DELETE FROM server WHERE "id"=$1;', ctx.guild.id)
        try:
            del self.bot.all_prefixes[ctx.guild.id]
        except KeyError:
            pass
        await ctx.send("Done!")

    @commands.guild_only()
    @commands.command(
        description="Information about a user.",
        aliases=["user", "member", "memberinfo"],
    )
    async def userinfo(self, ctx, member: discord.Member = None):
        ticks = {
            "True": "<:check:314349398811475968>",
            "False": "<:xmark:314349398824058880>",
        }
        statuses = {
            "online": "<:online:313956277808005120>",
            "idle": "<:away:313956277220802560>",
            "dnd": "<:dnd:313956276893646850>",
            "offline": "<:offline:313956277237710868>",
        }
        nl = "\n"
        auser = member
        if not auser:
            auser = ctx.author
        shared = get_guilds(self.bot, auser)
        embed = discord.Embed(
            title=f"{auser}",
            description=f"`Joined at`: {auser.joined_at}\n`Status...`: {statuses[str(auser.status)]}{str(auser.status).capitalize()}\n`Top Role.`: {auser.top_role.name}\n`Roles....`: {', '.join([role.name for role in auser.roles])}\n`Game.....`: {auser.activity if auser.activity else 'No Game Playing'}",
            color=auser.color.value,
        )
        embed.add_field(
            name="Shared Servers",
            value=f"**{len(shared)}**\n{nl.join([guild.name for guild in shared])}",
        )
        embed.set_thumbnail(url=auser.avatar_url)
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("\U000025c0")
        await msg.add_reaction("\U000025b6")

        def reactioncheck(reaction, user):
            return (
                (str(reaction.emoji) in ["\U000025c0", "\U000025b6"])
                and reaction.message.id == msg.id
                and user.id == ctx.author.id
            )

        waiting = True
        while waiting:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=60.0, check=reactioncheck
                )
                if reaction.emoji == "\U000025b6":
                    em = discord.Embed(
                        title="Permissions",
                        description=f"{nl.join(['`'+value[0].replace('_', ' ').title().ljust(21, '.')+'`'+': '+ticks[str(value[1])] for value in auser.guild_permissions])}",
                        color=auser.color.value,
                    ).set_thumbnail(url=auser.avatar_url)
                    await msg.edit(embed=em)
                elif reaction.emoji == "\U000025c0":
                    embed = discord.Embed(
                        title=f"{auser}",
                        description=f"`Joined at`: {auser.joined_at}\n`Status...`: {statuses[str(auser.status)]}{str(auser.status).capitalize()}\n`Top Role.`: {auser.top_role.name}\n`Roles....`: {', '.join([role.name for role in auser.roles])}\n`Game.....`: {auser.activity if auser.activity else 'No Game Playing'}",
                        color=auser.color.value,
                    )
                    embed.add_field(
                        name="Shared Servers",
                        value=f"**{len(shared)}**\n{nl.join([guild.name for guild in shared])}",
                    )
                    embed.set_thumbnail(url=auser.avatar_url)
                    await msg.edit(embed=embed)
                try:
                    await msg.remove_reaction(reaction.emoji, user)
                except discord.Forbidden:
                    pass
            except asyncio.TimeoutError:
                waiting = False
                try:
                    await msg.clear_reactions()
                except discord.Forbidden:
                    pass

    @commands.guild_only()
    @commands.command(description="See your prefix.")
    async def prefix(self, ctx):
        try:
            await ctx.send(
                f"The prefix for server **{ctx.guild.name}** is `{self.bot.all_prefixes[ctx.guild.id]}`.\n\n`{ctx.prefix}settings prefix` changes it."
            )
        except KeyError:
            await ctx.send(
                f"The prefix for server **{ctx.guild.name}** is `{self.bot.config.global_prefix}`.\n\n`{ctx.prefix}settings prefix` changes it."
            )

    @commands.command(description="Who uses your discriminator?", enabled=False)
    async def discrim(self, ctx, discrim: str):
        if len(discrim) != 4:
            return await ctx.send("A discrim is 4 numbers.")
        all = list(
            chunks(
                [str(user) for user in self.bot.users if user.discriminator == discrim],
                54,
            )
        )
        for i in all:
            await ctx.send("```" + "\n".join(i) + "```")

    @commands.command(description="Steal Avatars.")
    async def avatar(self, ctx, target: discord.Member):
        await ctx.send(
            embed=discord.Embed(
                title="Download Link",
                url=target.avatar_url_as(static_format="png"),
                color=target.color,
            ).set_image(url=target.avatar_url_as(static_format="png"))
        )


def setup(bot):
    bot.add_cog(Server(bot))
