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
import discord

from discord.ext import commands

from classes.bot import Bot
from classes.context import Context
from utils.i18n import _, locale_doc


class Server(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.guild_only()
    @commands.group(
        invoke_without_command=True, brief=_("Change the server settings for the bot")
    )
    @locale_doc
    async def settings(self, ctx: Context) -> None:
        _("""Change the server settings for the bot.""")
        await ctx.send(
            _("Please use `{prefix}settings prefix value`").format(prefix=ctx.prefix)
        )

    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @settings.command(name="prefix", brief=_("Change the prefix"))
    @locale_doc
    async def prefix_(self, ctx: Context, prefix: str) -> None:
        _(
            """`<prefix>` - The new prefix to use. Use "" quotes to surround it if you want multiple words or trailing spaces.

            Change the bot prefix, it cannot exceed 10 characters.

            Only users with the Manage Server permission can use this command."""
        )
        if len(prefix) > 10:
            return await ctx.send(_("Prefixes may not be longer than 10 characters."))
        if prefix == self.bot.config.bot.global_prefix:
            await self.bot.pool.execute(
                'DELETE FROM server WHERE "id"=$1;', ctx.guild.id
            )
        else:
            async with self.bot.pool.acquire() as conn:
                prev = await conn.fetchrow(
                    'SELECT * FROM server WHERE "id"=$1;', ctx.guild.id
                )
                if prev:
                    await conn.execute(
                        'UPDATE server SET "prefix"=$1 WHERE "id"=$2;',
                        prefix,
                        ctx.guild.id,
                    )
                else:
                    await conn.execute(
                        'INSERT INTO server ("prefix", "id") VALUES ($1, $2);',
                        prefix,
                        ctx.guild.id,
                    )
        self.bot.all_prefixes[ctx.guild.id] = prefix
        await ctx.send(_("Prefix changed to `{prefix}`.").format(prefix=prefix))

    @commands.has_permissions(manage_guild=True)
    @settings.command(brief=_("Reset the server settings"))
    @locale_doc
    async def reset(self, ctx: Context) -> None:
        _("""Resets the server settings.""")
        await self.bot.pool.execute('DELETE FROM server WHERE "id"=$1;', ctx.guild.id)
        self.bot.all_prefixes.pop(ctx.guild.id, None)
        await ctx.send(_("Done!"))

    @commands.guild_only()
    @commands.command(brief=_("View this server's prefix"))
    @locale_doc
    async def prefix(self, ctx: Context) -> None:
        _("""View the bot prefix for the server""")
        prefix_ = self.bot.all_prefixes.get(
            ctx.guild.id, self.bot.config.bot.global_prefix
        )
        await ctx.send(
            _(
                "The prefix for server **{server}** is"
                " `{serverprefix}`.\n\n`{prefix}settings prefix` changes it."
            ).format(server=ctx.guild, serverprefix=prefix_, prefix=ctx.prefix)
        )

    @commands.command(brief=_("Show someone's avatar"))
    @locale_doc
    async def avatar(self, ctx: Context, target: discord.Member = None) -> None:
        _(
            """`<target>` - The user whose avatar to show; defaults to oneself

            Shows someone's avatar, also known as their icon or profile picture."""
        )
        target = target or ctx.author
        await ctx.send(
            embed=discord.Embed(
                title=_("Download Link"),
                url=target.display_avatar.url,
                color=target.color,
            ).set_image(url=target.display_avatar.url)
        )


async def setup(bot: Bot) -> None:
    await bot.add_cog(Server(bot))
