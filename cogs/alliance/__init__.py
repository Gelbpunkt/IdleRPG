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
from typing import Union

import discord

from discord.ext import commands

from classes.converters import MemberWithCharacter
from utils import misc as rpgtools
from utils.checks import has_char, has_guild, is_guild_leader


class Alliance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @has_guild()
    @commands.group(invoke_without_command=True)
    async def alliance(self, ctx):
        _("""This command contains all alliance-related commands.""")
        allied_guilds = await self.bot.pool.fetch(
            'SELECT * FROM guild WHERE "alliance"=$1;', ctx.character_data["guild"]
        )
        if (
            len(allied_guilds) <= 1
        ):  # your guild is the only one OR error and query returns zero guilds
            return await ctx.send(_("You are not in an alliance."))
        alliance_embed = discord.Embed(
            title=_("Your allied guilds"), color=self.bot.config.primary_colour
        )
        for guild in allied_guilds:
            alliance_embed.add_field(
                name=guild[1],
                value=_("Lead by {leader}").format(
                    leader=await rpgtools.lookup(self.bot, guild["leader"])
                ),
                inline=False,
            )

        await ctx.send(embed=alliance_embed)

    @is_guild_leader()
    @alliance.command()
    async def invite(self, ctx, newleader: MemberWithCharacter):
        if not ctx.user_data["guild"]:
            return await ctx.send(_("That member is not in a guild."))
        newguild = await self.bot.pool.fetchrow(
            'SELECT * FROM guild WHERE "id"=$1', ctx.user_data["guild"]
        )
        if newleader.id != newguild["leader"]:
            return await ctx.send(_("That member is not the leader of their guild."))
        elif (
            newguild["alliance"] == ctx.character_data["guild"]
        ):  # already part of your alliance
            return await ctx.send(
                _("This member's guild is already part of your alliance.")
            )

        if not await ctx.confirm(
            _(
                "{newleader}, {author} invites you to join their alliance. React to join now."
            ).format(newleader=newleader.mention, author=ctx.author.mention),
            user=newleader,
        ):
            return

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE guild SET "alliance"=$1 WHERE "id"=$2;',
                ctx.character_data["guild"],
                ctx.user_data["guild"],
            )

        await ctx.send(
            _("**{newguild}** is now part of your alliance!").format(
                newguild=newguild["name"]
            )
        )

    @is_guild_leader()
    @alliance.command()
    async def kick(self, ctx, *, guild_to_kick: Union[int, str]):
        _(
            """Kick a guild from your alliance.\n Use either the guild name or ID for guild_to_kick."""
        )
        if isinstance(guild_to_kick, str):
            guild = await self.bot.pool.fetchrow(
                'SELECT * FROM guild WHERE "name"=$1;', guild_to_kick
            )
        else:
            guild = await self.bot.pool.fetchrow(
                'SELECT * FROM guild WHERE "id"=$1;', guild_to_kick
            )

        if not guild:
            return await ctx.send(
                _(
                    "Cannot find guild `{guild_to_kick}`. Are you sure that's the right name/ID?"
                ).format(guild_to_kick=guild_to_kick)
            )
        if guild["id"] == ctx.character_data["guild"]:
            return await ctx.send(_("That won't work."))

        if guild["alliance"] != ctx.character_data["guild"]:
            return await ctx.send(_("This guild is not in your alliance."))

        if not await ctx.confirm(
            _("Do you really want to kick **{guild}** from your alliance?").format(
                guild=guild["name"]
            )
        ):
            return

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE guild SET "alliance"="id" WHERE "id"=$1;', guild["id"]
            )

        await ctx.send(
            _("**{guild}** is no longer part of your alliance.").format(
                guild=guild["name"]
            )
        )


def setup(bot):
    bot.add_cog(Alliance(bot))
