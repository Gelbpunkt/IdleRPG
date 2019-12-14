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
from utils.checks import has_char, has_guild, is_guild_leader, is_alliance_leader, guild_has_money, owns_city


class Alliance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @has_guild()
    @commands.group(invoke_without_command=True)
    async def alliance(self, ctx):
        _("""This command contains all alliance-related commands.""")
        async with self.bot.pool.acquire() as conn:
            alliance_id = await conn.fetchval('SELECT alliance FROM guild WHERE "id"=$1;', ctx.character_data["guild"])
            allied_guilds = await conn.fetch(
                'SELECT * FROM guild WHERE "alliance"=$1;', alliance_id
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
        alliance_embed.set_footer(
            text=_("{prefix}alliance buildings | {prefix}alliance defenses").format(
                prefix=ctx.prefix
            )
        )

        await ctx.send(embed=alliance_embed)

    @is_alliance_leader()
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
            _("**{newguild}** is now part of your alliance, {user}!").format(
                newguild=newguild["name"],
                user=ctx.author.mention,
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
                'UPDATE guild SET "alliance"=$1 WHERE "id"=$1;', guild["id"]
            )

        await ctx.send(
            _("**{guild}** is no longer part of your alliance.").format(
                guild=guild["name"]
            )
        )

    def list_subcommands(self, ctx):
        if not ctx.command.commands:
            return "None"
        return [ctx.prefix + x.qualified_name for x in ctx.command.commands]

    def get_upgrade_price(self, current):
        # let's just make the price 1 until we have a sufficient formula
        return 1


    @alliance.group(invoke_without_command=True)
    async def build(self, ctx):
        _("""This command contains all alliance-building-related commands.""")
        subcommands = "```" + "\n".join(self.list_subcommands(ctx)) + "```"
        await ctx.send(
            _(
                "Please use one of these subcommands:\n\n"
            ) + subcommands
        )

    @is_alliance_leader()
    @build.command()
    async def building(self, ctx, name: str):
        if not name.lower() in ["thief", "raid", "trade", "adventure"]:
            return await ctx.send(_("Invalid building. Please use `{prefix}{cmd} [thief/raid/trade/adventure]`."))
        async with self.bot.pool.acquire() as conn:
            cur_level = await conn.fetchval(
                f'SELECT {name}_building FROM city WHERE "owner"=$1;',
                ctx.character_data["guild"]  # can only be done by the leading guild so this works here
            )
            up_price = self.get_upgrade_price(cur_level)
            if not await ctx.confirm(
                _("Are you sure you want to upgrade the **{name} building** to level {new_level}? This will cost $**{price}**.").format(
                    name=name, new_level=cur_level+1, price=up_price
                )
            ):
                return
            if not await guild_has_money(self.bot, ctx.character_data["guild"], up_price):
                return await ctx.send(
                    _("Your guild doesn't have enough money to upgrade the city's {name} building.").format(
                        name=name
                    )
                )

            await conn.execute(
                f'UPDATE city SET "{name}_building"="{name}_building"+1 WHERE "owner"=$1;',
                ctx.character_data["guild"]
            )
            await conn.execute(
                'UPDATE guild SET "money"="money"-$1 WHERE "id"=$2;',
                up_price,
                ctx.character_data["guild"]
            )

        await ctx.send(
            _("Successfully upgraded the city's {name} building to level **{new_level}**").format(
                name=name, new_level=cur_level+1
            )
        )


    @is_alliance_leader()
    @build.command()
    async def defense(self, ctx, *, name: str):
        if not name.lower() in ["cannons", "archers", "outer wall"]:
            return await ctx.send(_("Invalid defense. Please use `{prefix}{cmd} [cannons/archers/outer wall]`."))
        async with self.bot.pool.acquire() as conn:
            city_name = await conn.fetchval(
                'SELECT name FROM city WHERE "owner"=$1;',
                ctx.character_data["guild"]
            )
            cur_level = await conn.fetchval(
                f'SELECT {name.replace(" ", "_")} FROM defenses WHERE "city"=$1;',
                city_name
            )
            up_price = self.get_upgrade_price(cur_level)  # maybe use another formula here?
            if not await ctx.confirm(
                _("Are you sure you want to upgrade the city's **{defense}** to level {new_level}? This will cost $**{price}**.").format(
                    defense=name, new_level=cur_level+1, price=up_price
                )
            ):
                return
            if not await guild_has_money(self.bot, ctx.character_data["guild"], up_price):
                return await ctx.send(
                    _("Your guild doesn't have enough money to upgrade the city's {defense}.").format(
                        defense=name
                    )
                )

            await conn.execute(
                f'UPDATE defenses SET "{name}"="{name}"+1 WHERE "city"=$1;',
                city_name
            )
            await conn.execute(
                'UPDATE guild SET "money"="money"-$1 WHERE "id"=$2;',
                up_price,
                ctx.character_data["guild"]
            )

        await ctx.send(
            _("Successfully upgraded the city's {defense} building to level **{new_level}**").format(
                defense=name, new_level=cur_level+1
            )
        )

def setup(bot):
    bot.add_cog(Alliance(bot))
