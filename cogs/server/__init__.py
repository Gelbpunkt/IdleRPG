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
import discord

from discord.ext import commands
from discord.ext.commands.default import Author


class Server(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @commands.command(aliases=["server"])
    @locale_doc
    async def serverinfo(self, ctx):
        _("""Shows information about your server.""")
        text = _("Link")
        urltext = (
            f"[{text} <:external_link:429288989560930314>]({ctx.guild.icon_url})"
            if ctx.guild.icon_url
            else _("`No icon has been set yet!`")
        )
        em = discord.Embed(
            title=_("Server Information"),
            description=_("Compact information about this server"),
            colour=0xDEADBF,
        )
        em.add_field(
            name=_("Information"),
            value=_(
                """\
Server: `{name}`
Server Region: `{region}`
Members Total: `{members}`
ID: `{id}`
Icon: {urltext}
Owner: {owner}
Server created at: `{created_at}`"""
            ).format(
                name=ctx.guild.name,
                region=ctx.guild.region,
                members=ctx.guild.member_count,
                urltext=urltext,
                owner=ctx.guild.owner.mention,
                id=ctx.guild.id,
                created_at=ctx.guild.created_at.__format__("%A %d. %B %Y at %H:%M:%S"),
            ),
        )
        em.add_field(
            name=_("Roles"), value=", ".join([role.name for role in ctx.guild.roles])
        )
        text = _("{num} of {total}")
        em.add_field(
            name=_("Shard"),
            value=text.format(num=ctx.guild.shard_id + 1, total=self.bot.shard_count),
        )
        em.set_thumbnail(url=ctx.guild.icon_url)
        await ctx.send(embed=em)

    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    @locale_doc
    async def settings(self, ctx):
        _("""Change the settings.""")
        await ctx.send(
            _("Please use `{prefix}settings (prefix/unknown) value`").format(
                prefix=ctx.prefix
            )
        )

    @commands.has_permissions(manage_guild=True)
    @settings.command(name="prefix")
    @locale_doc
    async def prefix_(self, ctx, *, prefix: str):
        _("""Change the server bot prefix.""")
        if len(prefix) > 10:
            return await ctx.send(_("Prefixes may not be longer than 10 characters."))
        if self.bot.all_prefixes.get(ctx.guild.id):
            if prefix == self.bot.config.global_prefix:
                del self.bot.all_prefixes[ctx.guild.id]
                await self.bot.pool.execute(
                    'DELETE FROM server WHERE "id"=$1;', ctx.guild.id
                )
            else:
                await self.bot.pool.execute(
                    'UPDATE server SET "prefix"=$1 WHERE "id"=$2;', prefix, ctx.guild.id
                )
        else:
            await self.bot.pool.execute(
                'INSERT INTO server ("id", "prefix") VALUES ($1, $2);',
                ctx.guild.id,
                prefix,
            )
        if prefix != self.bot.config.global_prefix:
            self.bot.all_prefixes[ctx.guild.id] = prefix
        await ctx.send(_("Prefix changed to `{prefix}`.").format(prefix=prefix))

    @commands.has_permissions(manage_guild=True)
    @settings.command()
    @locale_doc
    async def reset(self, ctx):
        _("""Resets the server settings.""")
        await self.bot.pool.execute('DELETE FROM server WHERE "id"=$1;', ctx.guild.id)
        self.bot.all_prefixes.pop(ctx.guild.id, None)
        await ctx.send(_("Done!"))

    @commands.guild_only()
    @commands.command(aliases=["user", "member", "memberinfo"])
    @locale_doc
    async def userinfo(self, ctx, member: discord.Member = Author):
        _("""Shows detailed information about a member in the server.""")
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
            description=_(
                """\
`Joined at`: {joined}
`Status...`: {status}
`Top Role.`: {toprole}
`Roles....`: {roles}
`Game.....`: {game}"""
            ).format(
                joined=str(member.joined_at).split(".")[0],
                status=f"{statuses[str(member.status)]}{str(member.status).capitalize()}",
                toprole=member.top_role.name,
                roles=", ".join([role.name for role in member.roles]),
                game=str(member.activity) if member.activity else _("No Game Playing"),
            ),
            color=member.color,
        ).set_thumbnail(url=member.avatar_url)
        embed2 = discord.Embed(
            title=_("Permissions"),
            description="\n".join(
                [
                    "`"
                    + _(value[0].replace("_", " ").title()).ljust(21, ".")
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
    @locale_doc
    async def prefix(self, ctx):
        _("""View the bot prefix.""")
        prefix_ = self.bot.all_prefixes.get(ctx.guild.id, self.bot.config.global_prefix)
        await ctx.send(
            _(
                "The prefix for server **{server}** is `{serverprefix}`.\n\n`{prefix}settings prefix` changes it."
            ).format(server=ctx.guild, serverprefix=prefix_, prefix=ctx.prefix)
        )

    @commands.command()
    @locale_doc
    async def avatar(self, ctx, target: discord.Member = Author):
        _("""Shows someone's (or your) avatar.""")
        await ctx.send(
            embed=discord.Embed(
                title=_("Download Link"),
                url=str(target.avatar_url_as(static_format="png")),
                color=target.color,
            ).set_image(url=target.avatar_url_as(static_format="png"))
        )


def setup(bot):
    bot.add_cog(Server(bot))
