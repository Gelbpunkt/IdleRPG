"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import discord
from discord.ext import commands
from discord.ext.commands.default import Author


class Server(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @commands.command(aliases=["server"])
    async def serverinfo(self, ctx):
        urltext = (
            f"[Link <:external_link:429288989560930314>]({ctx.guild.icon_url})"
            if ctx.guild.icon_url
            else "`No icon has been set yet!`"
        )
        em = discord.Embed(
            title="Server Information",
            description="Compact information about this server",
            colour=0xDEADBF,
        )
        em.add_field(
            name="Information",
            value=f"Server: `{ctx.guild.name}`\nServer Region: `{ctx.guild.region}`\nMembers Total: `{ctx.guild.member_count}`\nID: `{ctx.guild.id}`\nIcon: {urltext}\nOwner: {ctx.guild.owner.mention}\nServer created at: `{ctx.guild.created_at.__format__('%A %d. %B %Y at %H:%M:%S')}`",
        )
        em.add_field(
            name="Roles", value=f"{', '.join([role.name for role in ctx.guild.roles])}"
        )
        em.add_field(
            name="Shard",
            value=f"`{ctx.guild.shard_id + 1}` of `{self.bot.shard_count}`",
        )
        em.set_thumbnail(url=ctx.guild.icon_url)
        await ctx.send(embed=em)

    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    async def settings(self, ctx):
        """Change the settings."""
        await ctx.send(f"Please use `{ctx.prefix}settings (prefix/unknown) value`")

    @commands.has_permissions(manage_guild=True)
    @settings.command(name="prefix")
    async def prefix_(self, ctx, *, prefix: str):
        """Change the server bot prefix."""
        if len(prefix) > 10:
            return await ctx.send("Prefixes may not be longer than 10 characters.")
        # ToDo: handle default prefix here
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
    @settings.command()
    async def unknown(self, ctx, value: bool):
        """Toggles messages on unknown commands invoked."""
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
    @settings.command()
    async def reset(self, ctx):
        """Resets the server settings."""
        await self.bot.pool.execute('DELETE FROM server WHERE "id"=$1;', ctx.guild.id)
        self.bot.all_prefixes.pop(ctx.guild.id, None)
        await ctx.send("Done!")

    @commands.guild_only()
    @commands.command(aliases=["user", "member", "memberinfo"])
    async def userinfo(self, ctx, member: discord.Member = Author):
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
        embed1 = discord.Embed(
            title=str(member),
            description=f"`Joined at`: {str(member.joined_at).split('.')[0]}\n`Status...`: {statuses[str(member.status)]}{str(member.status).capitalize()}\n`Top Role.`: {member.top_role.name}\n`Roles....`: {', '.join([role.name for role in member.roles])}\n`Game.....`: {member.activity if member.activity else 'No Game Playing'}",
            color=member.color,
        ).set_thumbnail(url=member.avatar_url)
        embed2 = discord.Embed(
            title="Permissions",
            description="\n".join(
                [
                    "`"
                    + value[0].replace("_", " ").title().ljust(21, ".")
                    + "`"
                    + ": "
                    + ticks[str(value[1])]
                    for value in member.guild_permissions
                ]
            ),
            color=member.color,
        ).set_thumbnail(url=member.avatar_url)
        await self.bot.paginator.Paginator(extras=[embed1, embed2]).paginate(ctx)

    @commands.guild_only()
    @commands.command()
    async def prefix(self, ctx):
        """View the bot prefix."""
        prefix_ = self.bot.all_prefixes.get(ctx.guild.id, self.bot.config.global_prefix)
        await ctx.send(
            f"The prefix for server **{ctx.guild.name}** is `{prefix_}`.\n\n`{ctx.prefix}settings prefix` changes it."
        )

    @commands.command()
    async def avatar(self, ctx, target: discord.Member = Author):
        """Shows someone's (or your) avatar."""
        await ctx.send(
            embed=discord.Embed(
                title="Download Link",
                url=str(target.avatar_url_as(static_format="png")),
                color=target.color,
            ).set_image(url=target.avatar_url_as(static_format="png"))
        )


def setup(bot):
    bot.add_cog(Server(bot))
